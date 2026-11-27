"""Canal de vídeo e obstáculos do app ponte (Tarefa 2), lado ROS 2, sem ROS 2."""
import json
import math
import socket
import threading
import time

import pytest

from psi3442_tarefas.cliente_socket_ponte import ClienteVideo, ErroProtocolo, LeitorQuadros, decodificar
from psi3442_tarefas.no_ponte_dji import scan_de_obstaculos


def quadro(n, instante=1.0):
    corpo = bytes(range(256)) * (n // 256) + bytes(n % 256)
    cab = json.dumps({'tipo': 'quadro', 'instante_s': instante, 'largura': 640, 'altura': 360, 'formato': 'jpeg',
                      'bytes': len(corpo), 'pitch_gimbal_graus': 0.0}).encode() + b'\n'
    return cab, corpo


def test_leitor_de_quadros_remonta_pedacos():
    leitor = LeitorQuadros()
    c1, j1 = quadro(1000, 1.0)
    c2, j2 = quadro(70000, 1.2)
    fluxo = c1 + j1 + c2 + j2
    recebidos = []
    for k in range(0, len(fluxo), 777):
        recebidos += leitor.alimentar(fluxo[k:k + 777])
    assert [(c['instante_s'], j) for c, j in recebidos] == [(1.0, j1), (1.2, j2)]


def test_cabecalho_invalido_e_rejeitado():
    with pytest.raises(ErroProtocolo):
        LeitorQuadros().alimentar(b'{"tipo":"telemetria","bytes":10}\n')
    with pytest.raises(ErroProtocolo):
        LeitorQuadros().alimentar(b'{"tipo":"quadro","bytes":-5}\n')


def test_obstaculos_viram_laser_scan_anti_horario():
    msg = decodificar(json.dumps({'tipo': 'obstaculos', 'instante_s': 1.0, 'passo_graus': 5.0,
                                  'distancias_m': [1.5, None, 3.0]}))
    scan = scan_de_obstaculos(msg)
    assert scan['angle_min'] == 0.0
    assert scan['angle_increment'] == pytest.approx(-math.radians(5))     # horário -> negativo
    assert scan['ranges'][0] == 1.5 and math.isinf(scan['ranges'][1])


def test_cliente_video_recebe_do_servidor():
    servidor = socket.socket()
    servidor.bind(('127.0.0.1', 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    recebidos = []
    cliente = ClienteVideo('127.0.0.1', porta, lambda c, j: recebidos.append((c, j)), intervalo_reconexao_s=0.1)
    cliente.iniciar()
    conexao, _ = servidor.accept()
    c, j = quadro(5000)
    conexao.sendall(c + j)
    limite = time.time() + 3
    while not recebidos and time.time() < limite:
        time.sleep(0.02)
    cliente.parar()
    conexao.close()
    servidor.close()
    assert recebidos and recebidos[0][1] == j
