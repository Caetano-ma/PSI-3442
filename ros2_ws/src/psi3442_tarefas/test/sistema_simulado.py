"""Malha fechada sem ROS 2 para os testes: liga as classes de lógica dos nós ao DroneCinematico com relógio
injetado, na mesma topologia de tópicos do nível 1 (sem a camada rclpy). Cada passo = 0,1 s (cadeia a 10 Hz);
a dinâmica do simulador roda a 100 Hz. As mensagens da ponte passam pela codificação JSON real.
"""
import math
import os

from psi3442_tarefas import carregador_config
from psi3442_tarefas.cliente_socket_ponte import codificar, decodificar
from psi3442_tarefas.no_controle_voo import ControladorPosicao
from psi3442_tarefas.no_estimacao_estado import EstimadorEstado, local_de_solo
from psi3442_tarefas.no_gerenciador_tarefas import SeletorTarefa
from psi3442_tarefas.no_ponte_dji import json_de_acao, json_de_cmd_vel, json_de_telemetria, telemetria_de_json
from psi3442_tarefas.no_supervisao import MonitorFalhas
from psi3442_tarefas.no_tarefa1 import MaquinaTarefa1
from psi3442_tarefas.simulador_cinematico import DroneCinematico, ParametrosSimulacao
from psi3442_tarefas.tipos import COMANDO_REJEITADO, TERMINO_SEGURO, VOLTAR_OCIOSO, Falha

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'tarefas.yaml')


def ida_e_volta(mensagem):
    return decodificar(codificar(mensagem))


class SistemaSimulado:
    def __init__(self, cfg=None, parametros=None, simulacao=True, drone=None):
        self.cfg = cfg or carregador_config.carregar(CONFIG)
        c = self.cfg
        self.drone = drone or DroneCinematico(parametros or ParametrosSimulacao())
        self.seletor = SeletorTarefa(simulacao=simulacao, arquivo_progresso=None,
                                     prazo_telemetria_s=c.seguranca.prazo_telemetria_s)
        self.tarefa1 = MaquinaTarefa1(c.tarefa1, c.seguranca.bateria_minima_pct)
        self.estimador = EstimadorEstado(c.estimacao.idade_max_amostra_s, c.estimacao.altura_tof_max_m)
        self.controlador = ControladorPosicao(c.controle.kp, c.controle.v_max_horizontal_mps,
                                              c.controle.v_max_vertical_mps)
        self.monitor = MonitorFalhas(c.seguranca, self.tarefa1.planejador.pontos, c.tarefa1.altura_alvo_m)
        self.t = 0.0
        self.ativa = 0
        self.t_tel = None
        self.ultima_tel = None
        self.silencio = None                # (início, fim): ponte calada (nem telemetria nem heartbeat)
        self.eventos, self.falhas, self.acoes, self.trajeto = [], [], [], []
        self.passo()                          # primeira telemetria

    # ------------------------------------------------------------------
    def posicao_real_local(self):
        """Posição verdadeira do simulador no ReferencialLocal (para comparar com a estimativa)."""
        x, y = local_de_solo(self.drone.norte, self.drone.leste, self.drone.p.guinada_inicial_graus)
        return x, y, self.drone.altura

    def _despachar(self):
        for tipo, valor in self.seletor.consumir_saidas():
            if tipo == 'ativa':
                self.ativa = valor
                continue
            self.acoes.append((self.t, valor))
            if self._calada():
                continue
            for resposta in self.drone.receber(ida_e_volta(json_de_acao(valor)), self.t):
                em_voo = self.drone.em_voo or self.drone.motores
                falha = Falha(COMANDO_REJEITADO, TERMINO_SEGURO if em_voo else VOLTAR_OCIOSO, resposta['mensagem'])
                self.falhas.append((self.t, falha))
                self.seletor.ao_falha(falha)

    def _calada(self):
        return self.silencio is not None and self.silencio[0] <= self.t < self.silencio[1]

    def comando(self, acao):
        self.seletor.ao_comando(acao, self.t)
        self._despachar()
        return self.seletor.mensagem

    def passo(self):
        for _ in range(10):
            self.t = round(self.t + 0.01, 6)
            self.drone.passo(0.01, self.t)
        nova = None
        if not self._calada():
            self.drone.receber({'tipo': 'heartbeat'}, self.t)
            nova = telemetria_de_json(ida_e_volta(json_de_telemetria(self.drone.telemetria(self.t))))
            self.t_tel = self.t
            self.estimador.atualizar(nova, self.t)
            self.seletor.ao_telemetria(nova, self.t)
            self._despachar()
        else:
            self.estimador.verificar_idade(self.t)
        estado = self.estimador.estado
        self.seletor.ao_estado(estado)

        if nova is not None:
            self.ultima_tel = nova
        fresca = self.t_tel is not None and self.t - self.t_tel <= self.cfg.seguranca.prazo_telemetria_s
        setpoint, eventos = self.tarefa1.passo(self.t, self.ativa, estado, self.ultima_tel if fresca else None)
        for ev in eventos:
            self.eventos.append((self.t, ev))
            self.seletor.ao_evento(ev, self.t)
            self._despachar()
        for falha in self.monitor.avaliar(self.t, nova, self.t_tel, estado):
            self.falhas.append((self.t, falha))
            self.seletor.ao_falha(falha)
            self._despachar()

        comando = self.controlador.calcular(estado, setpoint)
        if comando is not None and not self._calada():
            self.drone.receber(ida_e_volta(json_de_cmd_vel(comando)), self.t)
        self.trajeto.append((self.t, self.tarefa1.estado, estado, self.posicao_real_local()))

    def rodar_ate(self, condicao, limite_s):
        fim = self.t + limite_s
        while self.t < fim:
            self.passo()
            if condicao(self):
                return True
        return False

    # ------------------------------------------------------------------ consultas
    def tipos_evento(self, tipo=None):
        return [ev for _, ev in self.eventos if tipo is None or ev.tipo == tipo]

    def estados_visitados(self):
        return [ev.estado for ev in self.tipos_evento('TRANSICAO')]

    def falhas_do_tipo(self, tipo):
        return [f for _, f in self.falhas if f.tipo == tipo]


def pousado(s):
    return not s.drone.em_voo and not s.drone.motores and s.seletor.modo == 'ocioso' and s.t > 1.0


def finita(valor):
    return valor is not None and math.isfinite(valor)
