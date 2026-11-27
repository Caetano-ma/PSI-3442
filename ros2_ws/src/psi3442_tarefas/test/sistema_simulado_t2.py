"""Malha fechada da Tarefa 2 sem ROS 2, sem Gazebo e sem o modelo YOLO.

A "visão sintética" gera, a 5 Hz, as detecções que a câmera veria: projeta os balões verdadeiros a partir da pose
VERDADEIRA do simulador (campo de visão, oclusão simples, ruído em pixels, caixa cortada na borda) e as completa com a
GeometriaCamera usando a guinada ESTIMADA, como o nó de visão. A cor central aparece quando um balão ocupa o centro
da imagem. O avaliador calcula a distância verdadeira (R04/R05), que nunca entra no algoritmo.
"""
from dataclasses import dataclass, field
import math
import os
import random
from types import SimpleNamespace

from psi3442_tarefas import carregador_config
from psi3442_tarefas.no_controle_voo import ControladorPosicao
from psi3442_tarefas.no_estimacao_estado import EstimadorEstado, local_de_solo, solo_de_local
from psi3442_tarefas.no_gerenciador_tarefas import SeletorTarefa
from psi3442_tarefas.no_mapeamento_local import MapeamentoLocal, posicao_camera
from psi3442_tarefas.no_ponte_dji import json_de_acao, json_de_cmd_vel, json_de_telemetria, telemetria_de_json
from psi3442_tarefas.no_supervisao import MonitorFalhas
from psi3442_tarefas.no_tarefa1 import MaquinaTarefa1
from psi3442_tarefas.no_tarefa2 import MaquinaTarefa2
from psi3442_tarefas.no_visao_computacional import Deteccao, GeometriaCamera
from psi3442_tarefas.simulador_cinematico import DroneCinematico, ParametrosSimulacao
from psi3442_tarefas.tipos import COMANDO_REJEITADO, TERMINO_SEGURO, VOLTAR_OCIOSO, Falha

from sistema_simulado import ida_e_volta

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'tarefas.yaml')


@dataclass
class BalaoVerdadeiro:
    cor: str
    x: float
    y: float
    z: float
    raio: float = 0.13


@dataclass
class VisaoSintetica:
    geometria: GeometriaCamera
    hfov_graus: float
    baloes: list
    ruido_px: float = 1.5
    alcance_m: float = 6.0
    rng: random.Random = field(default_factory=lambda: random.Random(7))

    def observar(self, pose_real, guinada_estimada, cores):
        """pose_real = (x, y, z, guinada_local) verdadeira -> (deteccoes, cor_central, fracao, (distância, azimute)
        da medida de proximidade pelas bordas na linha central, ou NaN)."""
        x, y, z, g = pose_real
        cx, cy, cz = posicao_camera(x, y, z, g)
        gr = math.radians(g)
        vfov = 2 * math.atan(math.tan(math.radians(self.hfov_graus) / 2) * self.geometria.altura / self.geometria.largura)
        candidatos = []
        for b in self.baloes:
            dx, dy, dz = b.x - cx, b.y - cy, b.z - cz
            frente = dx * math.cos(gr) + dy * math.sin(gr)
            esquerda = -dx * math.sin(gr) + dy * math.cos(gr)
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            candidatos.append((d, b, frente, esquerda, dz))
        candidatos.sort(key=lambda c: c[0])
        deteccoes, ocupados = [], []
        cor_central, fracao, proximidade = '', 0.0, (math.nan, math.nan)
        for d, b, frente, esquerda, cima in candidatos:
            if d <= b.raio:
                continue
            angular = math.asin(min(1.0, b.raio / d))
            if frente > 0 and math.hypot(math.atan2(esquerda, frente), math.atan2(cima, frente)) < angular \
                    and d - b.raio < 0.4 and not cor_central:
                cor_central, fracao = b.cor, 0.9
                proximidade = self._proximidade(b, frente, esquerda, cima, guinada_estimada)
            if frente <= 0.05 or d > self.alcance_m:
                continue
            if abs(math.atan2(esquerda, frente)) > math.radians(self.hfov_graus) / 2 + angular \
                    or abs(math.atan2(cima, frente)) > vfov / 2 + angular:
                continue
            uv = self.geometria.projetar((frente, esquerda, cima))
            r_px = self.geometria.f * math.tan(angular)
            if any(math.hypot(uv[0] - u, uv[1] - v) < 0.5 * (r_px + r) for u, v, r in ocupados):
                continue                       # oculto por um balão mais próximo
            ocupados.append((uv[0], uv[1], r_px))
            u = uv[0] + self.rng.gauss(0, self.ruido_px)
            v = uv[1] + self.rng.gauss(0, self.ruido_px)
            x0, x1 = max(0.0, u - r_px), min(self.geometria.largura, u + r_px)
            y0, y1 = max(0.0, v - r_px), min(self.geometria.altura, v + r_px)
            if x1 - x0 < 4 or y1 - y0 < 4:
                continue
            det = Deteccao(cor=b.cor, confianca=0.9, u=int((x0 + x1) / 2), v=int((y0 + y1) / 2),
                           largura_px=int(round(x1 - x0)), altura_px=int(round(y1 - y0)))
            deteccoes.append(self.geometria.completar(det, guinada_estimada))
        return [d for d in deteccoes if d.cor in cores], cor_central, fracao, proximidade

    def _proximidade(self, b, frente, esquerda, cima, guinada_estimada):
        """Bordas do balão na linha central (plano z = 0 da câmera), com ruído, -> GeometriaCamera.proximidade."""
        if abs(cima) >= b.raio:
            return math.nan, math.nan
        raio_corte = math.sqrt(b.raio ** 2 - cima ** 2)
        d_h = math.hypot(frente, esquerda)
        a = math.atan2(esquerda, frente)
        meia = math.asin(min(1.0, raio_corte / d_h))
        if abs(a) + meia >= math.radians(89):
            return -self.geometria.distancia_minima_mensuravel(), math.nan
        w, f = self.geometria.largura, self.geometria.f
        u0 = w / 2 - f * math.tan(a + meia) + self.rng.gauss(0, 0.5)
        u1 = w / 2 - f * math.tan(a - meia) + self.rng.gauss(0, 0.5)
        if u0 <= 0 or u1 >= w:                   # cortado pela borda: só um limite superior da distância
            d, _ = self.geometria.proximidade(max(u0, 0.0), min(u1, float(w)), guinada_estimada)
            return -d, math.nan
        return self.geometria.proximidade(u0, u1, guinada_estimada)


class SistemaSimuladoT2:
    def __init__(self, baloes, cfg=None, parametros=None, ruido_px=1.5):
        self.cfg = cfg or carregador_config.carregar(CONFIG)
        c = self.cfg
        self.drone = DroneCinematico(parametros or ParametrosSimulacao())
        self.seletor = SeletorTarefa(simulacao=True, arquivo_progresso=None,
                                     prazo_telemetria_s=c.seguranca.prazo_telemetria_s, liberar_tarefa2=True)
        self.tarefa2 = MaquinaTarefa2(c.tarefa2, c.seguranca.bateria_minima_pct)
        planejador = MaquinaTarefa1(c.tarefa1, c.seguranca.bateria_minima_pct).planejador
        self.monitor = MonitorFalhas(c.seguranca, planejador.pontos, c.tarefa1.altura_alvo_m, c.tarefa2)
        self.monitor.tarefa = 2
        self.estimador = EstimadorEstado(c.estimacao.idade_max_amostra_s, c.estimacao.altura_tof_max_m)
        k = c.controle
        self.controlador = ControladorPosicao(k.kp, k.v_max_horizontal_mps, k.v_max_vertical_mps, k.kp_guinada,
                                              k.taxa_guinada_max_grausps)
        self.mapa = MapeamentoLocal(c.tarefa2)
        v = c.visao
        self.baloes = baloes
        self.visao_sintetica = VisaoSintetica(GeometriaCamera(v.hfov_graus, v.largura_px, v.altura_px,
                                                              c.tarefa2.raio_balao_m), v.hfov_graus, baloes, ruido_px)
        self.visao = None
        self.t = 0.0
        self.ativa = 0
        self.t_tel = None
        self.ultima_tel = None
        self.eventos, self.falhas, self.registro = [], [], []
        self.passo()

    # ------------------------------------------------------------------ verdade (só para avaliação)
    def pose_real(self):
        psi0 = self.drone.p.guinada_inicial_graus
        x, y = local_de_solo(self.drone.norte, self.drone.leste, psi0)
        g = (psi0 - self.drone.guinada + 180.0) % 360.0 - 180.0
        return x, y, self.drone.altura, g

    def distancia_real(self, balao):
        x, y, z, g = self.pose_real()
        r = self.cfg.tarefa2.raio_envelope_frontal_m
        frente = (x + r * math.cos(math.radians(g)), y + r * math.sin(math.radians(g)), z)
        return math.dist(frente, (balao.x, balao.y, balao.z)) - balao.raio

    def balao_verdadeiro(self, x, y, z):
        return min(self.baloes, key=lambda b: math.dist((b.x, b.y, b.z), (x, y, z)))

    # ------------------------------------------------------------------
    def _despachar(self):
        for tipo, valor in self.seletor.consumir_saidas():
            if tipo == 'ativa':
                self.ativa = valor
                continue
            for resposta in self.drone.receber(ida_e_volta(json_de_acao(valor)), self.t):
                em_voo = self.drone.em_voo or self.drone.motores
                falha = Falha(COMANDO_REJEITADO, TERMINO_SEGURO if em_voo else VOLTAR_OCIOSO, resposta['mensagem'])
                self.falhas.append((self.t, falha))
                self.seletor.ao_falha(falha)

    def comando(self, acao):
        self.seletor.ao_comando(acao, self.t)
        self._despachar()
        return self.seletor.mensagem

    def passo(self):
        for _ in range(10):
            self.t = round(self.t + 0.01, 6)
            self.drone.passo(0.01, self.t)
        self.drone.receber({'tipo': 'heartbeat'}, self.t)
        nova = telemetria_de_json(ida_e_volta(json_de_telemetria(self.drone.telemetria(self.t))))
        self.t_tel = self.ultima_tel_t = self.t
        self.ultima_tel = nova
        estado = self.estimador.atualizar(nova, self.t)
        self.seletor.ao_telemetria(nova, self.t)
        self.seletor.ao_estado(estado)
        self._despachar()

        if round(self.t * 10) % 2 == 0 and estado.valido:                  # visão a 5 Hz
            deteccoes, cor, fracao, (d_c, az_c) = self.visao_sintetica.observar(
                self.pose_real(), estado.guinada_local_graus, self.cfg.tarefa2.cores_conhecidas)
            self.visao = SimpleNamespace(t=self.t, deteccoes=deteccoes, cor_central=cor, fracao_cor_central=fracao,
                                         distancia_central_m=d_c, azimute_central_graus=az_c,
                                         x_m=estado.x_m, y_m=estado.y_m, z_m=estado.z_m,
                                         guinada_local_graus=estado.guinada_local_graus)
            self.mapa.atualizar_deteccoes(self.visao, self.t)

        setpoint, eventos = self.tarefa2.passo(self.t, self.ativa, estado, nova, self.mapa, self.visao)
        for ev in eventos:
            self.eventos.append((self.t, ev))
            if ev.tipo == 'BALAO_DESTRUIDO':
                self.mapa.marcar_destruido(int(ev.valor), (ev.x_m, ev.y_m, ev.z_m))
            self.seletor.ao_evento(ev, self.t)
            self._despachar()
        for falha in self.monitor.avaliar(self.t, nova, self.t_tel, estado):
            self.falhas.append((self.t, falha))
            self.seletor.ao_falha(falha)
            self._despachar()
        comando = self.controlador.calcular(estado, setpoint)
        if comando is not None:
            self.drone.receber(ida_e_volta(json_de_cmd_vel(comando)), self.t)
        self.registro.append((self.t, self.tarefa2.estado, self.pose_real(),
                              self.tarefa2.cronometro.contando if self.tarefa2.estado == 'permanecendo' else False,
                              self.tarefa2.alvo['id'] if self.tarefa2.alvo else None))

    def rodar_ate(self, condicao, limite_s):
        fim = self.t + limite_s
        while self.t < fim:
            self.passo()
            if condicao(self):
                return True
        return False

    def tipos_evento(self, tipo):
        return [ev for _, ev in self.eventos if ev.tipo == tipo]


def pousado(s):
    return not s.drone.em_voo and not s.drone.motores and s.seletor.modo == 'ocioso' and s.t > 1.0


__all__ = ['BalaoVerdadeiro', 'SistemaSimuladoT2', 'pousado', 'solo_de_local']
