#!/usr/bin/env python3
"""T00 — teste de eixos do app ponte com a aeronave real (antes do T01).

Confere, a baixa velocidade, o mapeamento do controle virtual (DroneDji.ROLL_E_NORTE) e o referencial da
velocidade lida (KeyAircraftVelocity). Fala direto com o app ponte pelo ContratoSocketPonte, sem ROS 2.

Sequência: habilita o controle virtual, decola (pouso/decolagem automáticos da DJI), anda 0,2 m/s PARA A FRENTE
(direção do nariz) por 2 s, para, anda 0,2 m/s PARA A ESQUERDA por 2 s, para e pousa. Para cada trecho compara o rumo
da velocidade medida com o comandado. O operador deve CONFIRMAR VISUALMENTE que a aeronave foi para a frente e
depois para a esquerda: se comando e leitura estivessem trocados do mesmo jeito, só a observação revelaria.
Ctrl+C a qualquer momento manda pousar.

Uso: python3 ensaios/teste_eixos.py [--host IP_DO_CELULAR] [--porta 5760]
"""
import argparse
import json
import math
import socket
import threading
import time

VELOCIDADE = 0.2
DURACAO_S = 2.0


class Ponte:
    def __init__(self, host, porta):
        self.sock = socket.create_connection((host, porta), timeout=5)
        self.sock.settimeout(0.5)
        self.trava = threading.Lock()
        self.tel = None
        self.erros = []
        self.ativo = True
        threading.Thread(target=self._ler, daemon=True).start()
        threading.Thread(target=self._heartbeat, daemon=True).start()

    def enviar(self, mensagem):
        with self.trava:
            self.sock.sendall((json.dumps(mensagem) + '\n').encode())

    def acao(self, comando):
        self.enviar({'tipo': 'acao', 'comando': comando})

    def cmd_vel(self, vx, vy, psi0):
        self.enviar({'tipo': 'cmd_vel', 'vx_mps': vx, 'vy_mps': vy, 'vz_mps': 0.0, 'taxa_guinada_grausps': 0.0,
                     'psi0_graus': psi0})

    def _heartbeat(self):
        while self.ativo:
            try:
                self.enviar({'tipo': 'heartbeat', 'instante_s': time.monotonic()})
            except OSError:
                return
            time.sleep(0.5)

    def _ler(self):
        buffer = b''
        while self.ativo:
            try:
                dados = self.sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            if not dados:
                return
            *linhas, buffer = (buffer + dados).split(b'\n')
            for linha in linhas:
                if not linha.strip():
                    continue
                msg = json.loads(linha)
                if msg['tipo'] == 'telemetria':
                    self.tel = msg
                elif msg['tipo'] == 'erro':
                    self.erros.append(msg)
                    print(f"  ERRO do app: {msg.get('comando')}: {msg.get('mensagem')}")

    def esperar(self, condicao, limite_s, descricao):
        fim = time.monotonic() + limite_s
        while time.monotonic() < fim:
            if self.tel is not None and condicao(self.tel):
                return self.tel
            time.sleep(0.05)
        raise TimeoutError(f'tempo esgotado esperando: {descricao}')


def trecho(ponte, nome, vx, vy, psi0):
    """Anda por DURACAO_S com o comando local (vx, vy) e devolve o rumo medido e o esperado (graus, a partir do norte)."""
    print(f'\n>>> {nome}: observe a aeronave agora.')
    n_esp = vx * math.cos(math.radians(psi0)) + vy * math.sin(math.radians(psi0))
    e_esp = vx * math.sin(math.radians(psi0)) - vy * math.cos(math.radians(psi0))
    soma_n = soma_e = 0.0
    fim = time.monotonic() + DURACAO_S
    while time.monotonic() < fim:
        ponte.cmd_vel(vx, vy, psi0)
        tel = ponte.tel
        if tel and time.monotonic() > fim - DURACAO_S / 2:     # só a 2ª metade, já em regime
            soma_n += tel['v_norte_mps']
            soma_e += tel['v_leste_mps']
        time.sleep(0.05)
    for _ in range(20):
        ponte.cmd_vel(0.0, 0.0, psi0)
        time.sleep(0.05)
    rumo_med = math.degrees(math.atan2(soma_e, soma_n))
    rumo_esp = math.degrees(math.atan2(e_esp, n_esp))
    erro = (rumo_med - rumo_esp + 180) % 360 - 180
    print(f'    rumo esperado {rumo_esp:6.1f}°, medido {rumo_med:6.1f}°, diferença {erro:6.1f}°')
    return erro


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--porta', type=int, default=5760)
    args = ap.parse_args()
    ponte = Ponte(args.host, args.porta)
    try:
        tel = ponte.esperar(lambda t: t['conectado'], 10, 'aeronave conectada')
        psi0 = tel['guinada_graus']
        print(f"Conectado. Guinada (nariz) = {psi0:.1f}°, bateria = {tel['bateria_pct']:.0f} %, "
              f"PV = {tel['posicionamento_visual_ativo']}, perda de sinal = {tel['acao_perda_sinal']}")
        input('Área livre e aeronave no chão? ENTER decola (Ctrl+C cancela) ')
        ponte.acao('habilitar_controle_virtual')
        ponte.esperar(lambda t: t['controle_virtual_ativo'], 10, 'controle virtual ativo')
        ponte.acao('decolar')
        ponte.esperar(lambda t: t['em_voo'] and t['modo_voo'] not in ('AUTO_TAKE_OFF',), 30, 'fim da decolagem')
        time.sleep(2.0)
        erro_frente = trecho(ponte, 'PARA A FRENTE (direção do nariz)', VELOCIDADE, 0.0, psi0)
        erro_esquerda = trecho(ponte, 'PARA A ESQUERDA', 0.0, VELOCIDADE, psi0)
        ponte.acao('pousar')
        ponte.esperar(lambda t: not t['em_voo'] and not t['motores_ligados'], 60, 'pouso')
        ok = abs(erro_frente) < 30 and abs(erro_esquerda) < 30
        print('\nTelemetria coerente com o comando.' if ok else
              '\nDIVERGÊNCIA entre comando e telemetria: rever DroneDji.ROLL_E_NORTE e o referencial da velocidade.')
        print('Confirme também o que você VIU: a aeronave foi para a frente e depois para a esquerda?')
    except KeyboardInterrupt:
        print('\nInterrompido: pousando.')
        ponte.acao('pousar')
        time.sleep(1.0)
    finally:
        ponte.ativo = False


if __name__ == '__main__':
    main()
