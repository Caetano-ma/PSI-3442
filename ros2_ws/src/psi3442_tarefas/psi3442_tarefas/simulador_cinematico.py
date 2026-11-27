"""Simulador cinemático simples do conjunto app ponte + SDK + aeronave (ciclo C2; tempo real 1:1).

Faz o papel do app ponte no ContratoSocketPonte (servidor TCP, mesmo JSON por linha), de modo que os nós ROS 2
rodam sem drone e sem Android. Reproduz o comportamento especificado para o app ponte:
- cmd_vel no ReferencialLocal convertido para norte/leste com psi0 (como o EmissorComandos);
- watchdog: sem cmd_vel por 0,2 s com controle virtual ativo -> velocidade zero;
- sem heartbeat por 2 s em voo -> pouso automático (perdaPonte);
- decolagem e pouso automáticos (alturas e velocidades da DJI a verificar: valores aqui são hipóteses).
Dinâmica: velocidade de 1ª ordem (constante de tempo tau) rumo ao alvo; ruído e viés (deriva) opcionais nas
velocidades medidas, com semente fixa (reprodutibilidade, R09). Injeção de falhas por linha de comando.

Uso: ros2 run psi3442_tarefas simulador_ponte [--porta 5760] [--rejeitar decolar] [--vies-norte 0.01] ...
"""
import argparse
from dataclasses import dataclass, field
import math
import random
import shlex
import socket
import sys
import threading
import time

from .cliente_socket_ponte import ErroProtocolo, LeitorLinhas, codificar, decodificar
from .no_estimacao_estado import solo_de_local
from .no_ponte_dji import json_de_telemetria
from .tipos import Telemetria


@dataclass
class ParametrosSimulacao:
    guinada_inicial_graus: float = 30.0      # nariz para B; diferente de 0 para exercitar a conversão
    altura_decolagem_m: float = 1.2          # decolagem automática da DJI — verificar no manual
    v_decolagem_mps: float = 0.8
    v_pouso_mps: float = 0.4                 # pouso automático — verificar
    tau_s: float = 0.3
    bateria_inicial_pct: float = 80.0
    consumo_pct_por_s: float = 0.06
    ruido_velocidade_mps: float = 0.01
    vies_norte_mps: float = 0.0
    vies_leste_mps: float = 0.0
    semente: int = 1
    prazo_watchdog_s: float = 0.2
    prazo_perda_ponte_s: float = 2.0
    rejeitar: tuple = ()
    acao_perda_sinal: str = 'pousar'
    sem_posicionamento_visual_em_s: float = math.inf   # instante (desde a decolagem) em que o PV desliga
    altura_toque_m: float = 0.0              # altura em que se considera o toque no piso
    falhas: dict = field(default_factory=dict)


class DroneCinematico:
    def __init__(self, p=None):
        self.p = p or ParametrosSimulacao()
        self.rng = random.Random(self.p.semente)
        self.norte = self.leste = self.altura = 0.0
        self.v_norte = self.v_leste = self.v_baixo = 0.0
        self.alvo = (0.0, 0.0, 0.0)
        self.alvo_taxa_guinada = 0.0          # graus/s, horária (como a bússola)
        self.taxa_guinada = 0.0
        self.guinada = self.p.guinada_inicial_graus
        self.em_voo = self.motores = self.controle_virtual = False
        self.manobra = None                  # 'decolagem', 'pouso' ou None
        self.bateria = self.p.bateria_inicial_pct
        self.t_cmd = self.t_heartbeat = self.t_decolagem = None
        self.v_toque_mps = math.nan
        self.registro = []                   # eventos do simulador (para testes)

    # ------------------------------------------------------------------ entradas do protocolo
    def receber(self, mensagem, agora):
        """Processa uma mensagem do nó ponte; devolve a lista de respostas (erros)."""
        tipo = mensagem.get('tipo')
        if tipo == 'heartbeat':
            self.t_heartbeat = agora
        elif tipo == 'cmd_vel':
            self.t_cmd = agora
            if self.controle_virtual and self.em_voo and self.manobra is None:
                n, e = solo_de_local(float(mensagem['vx_mps']), float(mensagem['vy_mps']),
                                     float(mensagem['psi0_graus']))
                self.alvo = (n, e, -float(mensagem['vz_mps']))
                self.alvo_taxa_guinada = float(mensagem.get('taxa_guinada_grausps', 0.0))
        elif tipo == 'acao':
            erro = self._acao(mensagem.get('comando'), agora)
            self.registro.append((agora, mensagem.get('comando'), erro))
            if erro:
                return [{'tipo': 'erro', 'comando': mensagem.get('comando'), 'mensagem': erro}]
        return []

    def _acao(self, comando, agora):
        if comando in self.p.rejeitar:
            return 'rejeitado (falha injetada no simulador)'
        if comando == 'decolar':
            if self.motores or self.em_voo:
                return 'aeronave já em voo'
            self.motores, self.manobra, self.t_decolagem = True, 'decolagem', agora
        elif comando == 'pousar':
            if not self.em_voo:
                return 'aeronave não está em voo'
            self.manobra = 'pouso'
        elif comando == 'habilitar_controle_virtual':
            self.controle_virtual = True
        elif comando == 'desabilitar_controle_virtual':
            self.controle_virtual = False
        elif comando == 'parar_e_pairar':
            self.alvo = (0.0, 0.0, 0.0)
            self.alvo_taxa_guinada = 0.0
        else:
            return f'comando desconhecido: {comando}'
        return None

    # ------------------------------------------------------------------ dinâmica
    def passo(self, dt, agora):
        """Etapas separadas para que outro "mundo" (Gazebo) substitua só o movimento e a medição."""
        self._atualizar_alvo(agora)
        self._responder(dt)
        self._mover(dt)
        self._verificar_toque(agora)

    def _atualizar_alvo(self, agora):
        """Comportamento do app ponte e do firmware: watchdog, perda da ponte, decolagem e pouso automáticos."""
        p = self.p
        if self.em_voo and self.manobra is None:
            if self.controle_virtual and (self.t_cmd is None or agora - self.t_cmd > p.prazo_watchdog_s):
                self.alvo = (0.0, 0.0, 0.0)              # watchdog do app ponte
                self.alvo_taxa_guinada = 0.0
            if self.t_heartbeat is not None and agora - self.t_heartbeat > p.prazo_perda_ponte_s:
                self.manobra = 'pouso'                    # perdaPonte: pouso automático
                self.registro.append((agora, 'perda_ponte', None))
        if self.manobra == 'decolagem':
            self.alvo = (0.0, 0.0, -p.v_decolagem_mps)
            if self.altura >= p.altura_decolagem_m:
                self.manobra, self.alvo = None, (0.0, 0.0, 0.0)
                self.t_cmd = agora                        # o watchdog só conta a partir daqui
        elif self.manobra == 'pouso':
            self.alvo = (0.0, 0.0, p.v_pouso_mps)
        if self.manobra is not None or not self.em_voo:
            self.alvo_taxa_guinada = 0.0

    def _responder(self, dt):
        """Resposta de 1ª ordem da velocidade (estabilização da DJI, caixa-preta)."""
        fator = min(1.0, dt / self.p.tau_s)
        self.v_norte += (self.alvo[0] - self.v_norte) * fator
        self.v_leste += (self.alvo[1] - self.v_leste) * fator
        self.v_baixo += (self.alvo[2] - self.v_baixo) * fator
        self.taxa_guinada += (self.alvo_taxa_guinada - self.taxa_guinada) * fator

    def _mover(self, dt):
        if self.motores:
            self.norte += self.v_norte * dt
            self.leste += self.v_leste * dt
            self.altura -= self.v_baixo * dt
            self.guinada = (self.guinada + self.taxa_guinada * dt + 180.0) % 360.0 - 180.0
            self.bateria = max(0.0, self.bateria - self.p.consumo_pct_por_s * dt)

    def _verificar_toque(self, agora):
        if self.altura > 0.02 and self.motores:
            self.em_voo = True
        if self.altura <= self.p.altura_toque_m:
            if self.em_voo:
                self.v_toque_mps = abs(self.v_baixo)
                self.em_voo = self.motores = False
                self.manobra, self.alvo = None, (0.0, 0.0, 0.0)
                self.registro.append((agora, 'toque', self.v_toque_mps))
            self.altura = 0.0
            if not self.motores:
                self.v_norte = self.v_leste = self.v_baixo = 0.0

    def velocidades_medidas(self):
        """(norte, leste, baixo) que o sensor "vê"; aqui, a própria velocidade simulada."""
        return self.v_norte, self.v_leste, self.v_baixo

    def instante_medida(self, agora):
        return agora

    def telemetria(self, agora):
        p = self.p
        ruido = (lambda: self.rng.gauss(0.0, p.ruido_velocidade_mps)) if p.ruido_velocidade_mps > 0 else (lambda: 0.0)
        no_ar = self.motores
        pv = not (self.t_decolagem is not None and agora - self.t_decolagem >= p.sem_posicionamento_visual_em_s)
        v_norte, v_leste, v_baixo = self.velocidades_medidas()
        return Telemetria(
            instante_android_s=self.instante_medida(agora),
            v_norte_mps=v_norte + ((p.vies_norte_mps + ruido()) if no_ar else 0.0),
            v_leste_mps=v_leste + ((p.vies_leste_mps + ruido()) if no_ar else 0.0),
            v_baixo_mps=v_baixo + (ruido() if no_ar else 0.0),
            altitude_m=self.altura,
            altura_tof_m=self.altura,
            guinada_graus=self.guinada,
            em_voo=self.em_voo,
            motores_ligados=self.motores,
            modo_voo={'decolagem': 'AUTO_TAKE_OFF', 'pouso': 'AUTO_LANDING'}.get(
                self.manobra, 'VIRTUAL_STICK' if self.controle_virtual and self.em_voo else 'GPS_NORMAL'),
            bateria_pct=self.bateria,
            conectado=True,
            posicionamento_visual_ativo=pv,
            controle_virtual_ativo=self.controle_virtual,
            acao_perda_sinal=p.acao_perda_sinal,
        )


class ServidorSimulado:
    """Servidor TCP (um cliente por vez) que expõe o DroneCinematico pelo protocolo do app ponte."""

    def __init__(self, drone, host='127.0.0.1', porta=5760, silencio=None, log=print):
        self.drone, self.host, self.porta, self.log = drone, host, porta, log
        self.silencio = silencio             # (início_s, duração_s) sem telemetria, relativo ao início
        self.trava = threading.Lock()
        self.cliente = None

    def _enviar(self, mensagem):
        cliente = self.cliente
        if cliente is None:
            return
        try:
            cliente.sendall(codificar(mensagem))
        except OSError:
            self.cliente = None

    def _atender(self, conexao):
        leitor = LeitorLinhas()
        conexao.settimeout(0.5)
        while self.cliente is conexao:
            try:
                dados = conexao.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not dados:
                break
            try:
                linhas = leitor.alimentar(dados)
            except ErroProtocolo as erro:
                self.log(f'protocolo: {erro}')
                continue
            for linha in linhas:
                try:
                    mensagem = decodificar(linha)
                except ErroProtocolo as erro:
                    self.log(f'protocolo: {erro}')
                    continue
                if mensagem['tipo'] == 'acao':
                    self.log(f"ação recebida: {mensagem.get('comando')}")
                with self.trava:
                    respostas = self.drone.receber(mensagem, time.monotonic())
                for resposta in respostas:
                    self._enviar(resposta)
        if self.cliente is conexao:
            self.cliente = None
        self.log('nó ponte desconectado')

    def _aceitar(self, servidor):
        while True:
            conexao, endereco = servidor.accept()
            conexao.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.log(f'nó ponte conectado de {endereco}')
            self.cliente = conexao
            threading.Thread(target=self._atender, args=(conexao,), daemon=True).start()

    def executar(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((self.host, self.porta))
        servidor.listen(1)
        self.log(f'simulador escutando em {self.host}:{self.porta}')
        threading.Thread(target=self._aceitar, args=(servidor,), daemon=True).start()
        inicio = anterior = time.monotonic()
        proxima_tel = proximo_hb = inicio
        em_voo_antes = False
        ultimo_instante = None
        while True:
            time.sleep(0.01)
            agora = time.monotonic()
            with self.trava:
                self.drone.passo(agora - anterior, agora)
                tel = self.drone.telemetria(agora)
            anterior = agora
            if tel.em_voo != em_voo_antes:
                em_voo_antes = tel.em_voo
                self.log('decolou' if tel.em_voo else f'pousou: |vz| no toque = {self.drone.v_toque_mps:.2f} m/s')
            calado = self.silencio is not None and 0 <= agora - inicio - self.silencio[0] < self.silencio[1]
            if agora >= proxima_tel:
                proxima_tel += 0.1
                # no Gazebo o instante é o do simulador: se ele atrasou, não há medida nova (o app real usa relógio
                # monotônico e nunca repete o instante); repetir a amostra invalidaria a estimação
                if not calado and tel.instante_android_s != ultimo_instante:
                    ultimo_instante = tel.instante_android_s
                    self._enviar(json_de_telemetria(tel))
            if agora >= proximo_hb:
                proximo_hb += 1.0
                if not calado:
                    self._enviar({'tipo': 'heartbeat', 'instante_s': agora})


def main(argv=None):
    parser = argparse.ArgumentParser(description='Simulador cinemático do app ponte DJI (PSI3442).')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--porta', type=int, default=5760)
    parser.add_argument('--guinada-inicial', type=float, default=30.0, help='graus (nariz para B)')
    parser.add_argument('--bateria-inicial', type=float, default=80.0)
    parser.add_argument('--ruido', type=float, default=0.01, help='desvio-padrão do ruído de velocidade (m/s)')
    parser.add_argument('--vies-norte', type=float, default=0.0, help='viés da velocidade norte (m/s): deriva')
    parser.add_argument('--vies-leste', type=float, default=0.0)
    parser.add_argument('--semente', type=int, default=1)
    parser.add_argument('--rejeitar', action='append', default=[], help='comando a rejeitar (ex.: decolar)')
    parser.add_argument('--acao-perda-sinal', default='pousar')
    parser.add_argument('--sem-posicionamento-visual-em', type=float, default=math.inf,
                        help='segundos após a decolagem em que o posicionamento visual desliga')
    parser.add_argument('--silencio', type=float, nargs=2, metavar=('INICIO_S', 'DURACAO_S'),
                        help='para de enviar telemetria e heartbeat nesse intervalo (desde o início do simulador)')
    # o launch passa "simulador_args" como um único argumento: separa por espaços; ignora --ros-args ...
    argv = [parte for arg in (sys.argv[1:] if argv is None else argv) for parte in shlex.split(arg)]
    if '--ros-args' in argv:
        argv = argv[:argv.index('--ros-args')]
    args = parser.parse_args(argv)
    p = ParametrosSimulacao(
        guinada_inicial_graus=args.guinada_inicial, bateria_inicial_pct=args.bateria_inicial,
        ruido_velocidade_mps=args.ruido, vies_norte_mps=args.vies_norte, vies_leste_mps=args.vies_leste,
        semente=args.semente, rejeitar=tuple(args.rejeitar), acao_perda_sinal=args.acao_perda_sinal,
        sem_posicionamento_visual_em_s=args.sem_posicionamento_visual_em)
    servidor = ServidorSimulado(DroneCinematico(p), args.host, args.porta, silencio=args.silencio,
                                log=lambda texto: print(f'[simulador] {texto}', flush=True))
    try:
        servidor.executar()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
