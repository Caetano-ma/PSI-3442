"""Gerador da sala da Tarefa 2 e avaliador (sem Gazebo)."""
import math
import os
import random
import xml.etree.ElementTree as ET

from psi3442_gazebo.avaliador_t2 import Avaliacao
from psi3442_gazebo.gerar_sala_t2 import SEPARACAO_MIN_M, gerar, sortear_baloes

MUNDO_T1 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'worlds', 'sala_tarefa1.sdf')
VOLUME = ((-0.4, 4.8), (-0.4, 3.8))


def test_sorteio_respeita_volume_separacao_e_cores_alvo():
    for semente in range(10):
        baloes = sortear_baloes(random.Random(semente), 7, ('vermelho', 'azul'),
                                ['vermelho', 'azul', 'verde', 'amarelo', 'roxo'], VOLUME, 0.13)
        assert len(baloes) == 7
        assert {'vermelho', 'azul'} <= {b['cor'] for b in baloes}
        for b in baloes:
            assert -0.4 < b['x'] < 4.8 and -0.4 < b['y'] < 3.8 and 0.9 <= b['z'] <= 2.0
            assert math.hypot(b['x'], b['y']) >= 1.2
        for i, a in enumerate(baloes):
            for b in baloes[i + 1:]:
                assert math.dist((a['x'], a['y'], a['z']), (b['x'], b['y'], b['z'])) >= SEPARACAO_MIN_M


def test_mesma_semente_mesma_sala():
    cores = ['vermelho', 'azul', 'verde']
    a = sortear_baloes(random.Random(3), 5, ('vermelho',), cores, VOLUME, 0.13)
    b = sortear_baloes(random.Random(3), 5, ('vermelho',), cores, VOLUME, 0.13)
    assert a == b


def test_sdf_valido_com_camera_lidar_e_baloes():
    baloes = sortear_baloes(random.Random(1), 4, ('vermelho', 'azul'), ['vermelho', 'azul', 'verde'], VOLUME, 0.13)
    mundo = ET.fromstring(gerar(MUNDO_T1, baloes, VOLUME))
    modelos = [m.get('name') for m in mundo.iter('model')]
    assert 'mini4pro' in modelos and 'sala' in modelos
    assert sum(1 for m in modelos if m.startswith('balao_')) == 4
    sensores = {s.get('type'): s for s in mundo.iter('sensor')}
    assert set(sensores) == {'camera', 'gpu_lidar'}
    assert sensores['camera'].find('topic').text == '/mini4pro/camera'
    assert any(p.get('name') == 'gz::sim::systems::Sensors' for p in mundo.iter('plugin'))


def test_avaliador_mede_a_faixa_e_colisoes():
    av = Avaliacao([{'cor': 'vermelho', 'x': 1.0, 'y': 0.0, 'z': 1.5, 'raio': 0.13, 'alvo': True},
                    {'cor': 'verde', 'x': 1.0, 'y': 2.0, 'z': 1.5, 'raio': 0.13, 'alvo': False}])
    av.evento(0.0, 'PERMANENCIA_INICIADA', 'vermelho#1', 0, 0, 0, 0)
    for k in range(10):                         # frente das hélices a 3 cm da superfície
        av.amostra(k * 0.1, 1.0 - 0.13 - 0.03 - 0.149, 0.0, 1.5, 0.0)
    av.evento(1.0, 'PERMANENCIA_CONCLUIDA', 'vermelho#1', 60.0, 0, 0, 0)
    av.evento(1.0, 'BALAO_DESTRUIDO', 'vermelho#1', 0, 1.0, 0.01, 1.5)
    r = av.resumo()
    assert r['permanencias'][0]['dentro_da_faixa'] and abs(r['permanencias'][0]['d_min_m'] - 0.03) < 1e-6
    assert r['colisoes'] == 0 and r['todos_os_alvos_destruidos']
    av.amostra(2.0, 1.0 - 0.13 - 0.149 + 0.01, 0.0, 1.5, 0.0)    # encostou
    assert av.resumo()['colisoes'] == 1
