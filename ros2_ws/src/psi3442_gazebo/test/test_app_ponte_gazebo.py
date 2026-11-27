"""App ponte do Gazebo sem o Gazebo: um "Gazebo falso" integra a velocidade no referencial do corpo (como o
VelocityControl) e devolve a odometria; a Tarefa 1 completa precisa fechar na malha do SistemaSimulado."""
import dataclasses
import math
import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
TAREFAS = os.path.join(os.path.dirname(os.path.dirname(AQUI)), 'psi3442_tarefas')
for caminho in (os.path.dirname(AQUI), TAREFAS, os.path.join(TAREFAS, 'test')):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

from psi3442_gazebo.app_ponte_gazebo import (DroneGazebo, guinada_bussola, mundo_para_corpo,  # noqa: E402
                                             yaw_de_quaternio)
from psi3442_tarefas import carregador_config  # noqa: E402
from psi3442_tarefas.simulador_cinematico import ParametrosSimulacao  # noqa: E402
from psi3442_tarefas.tipos import EXECUTAR_TAREFA1  # noqa: E402
from sistema_simulado import CONFIG, SistemaSimulado, pousado  # noqa: E402


class GazeboFalso(DroneGazebo):
    """Corpo cinemático (integra a taxa de guinada como o VelocityControl), tempo de simulação = tempo do teste."""

    def __init__(self, yaw=0.0):
        self.corpo = (0.0, 0.0, 0.0, 0.0)
        self.yaw = yaw
        self.xyz = [0.0, 0.0, 0.0]
        super().__init__(ParametrosSimulacao(altura_toque_m=0.01, ruido_velocidade_mps=0.0),
                         lambda vx, vy, vz, wz=0.0, wx=0.0, wy=0.0: setattr(self, 'corpo', (vx, vy, vz, wz)))
        self.ao_odometria(0.0, 0.0, 0.0, 0.0, yaw)

    def passo(self, dt, agora):
        super().passo(dt, agora)
        vx, vy, vz, wz = self.corpo
        self.yaw += wz * dt
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        self.xyz[0] += (c * vx - s * vy) * dt
        self.xyz[1] += (s * vx + c * vy) * dt
        self.xyz[2] = max(0.0, self.xyz[2] + vz * dt)          # piso
        self.ao_odometria(agora, *self.xyz, self.yaw)


def test_convencoes():
    assert guinada_bussola(0.0) == pytest.approx(90.0)            # +x do mundo = leste
    assert guinada_bussola(math.pi / 2) == pytest.approx(0.0)     # +y do mundo = norte
    assert yaw_de_quaternio(0, 0, math.sin(0.3), math.cos(0.3)) == pytest.approx(0.6)
    assert mundo_para_corpo(1.0, 0.0, math.pi / 2) == pytest.approx((0.0, -1.0))


@pytest.mark.parametrize('yaw', [0.0, 0.4])
def test_tarefa1_fecha_com_o_app_ponte_do_gazebo(yaw):
    base = carregador_config.carregar(CONFIG)
    cfg = dataclasses.replace(base, tarefa1=dataclasses.replace(base.tarefa1, tempo_permanencia_s=3.0))
    drone = GazeboFalso(yaw)
    s = SistemaSimulado(cfg=cfg, drone=drone)
    em_b = []

    def registrar_e_parar(s):
        if s.tarefa1.estado == 'pairando' and s.tarefa1._nome_vertice() == 'B':
            em_b.append(tuple(drone.xyz))
        return pousado(s)

    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(registrar_e_parar, 200.0), s.tarefa1.estado
    assert s.tarefa1.estado == 'concluida'
    assert [ev.nome_vertice for ev in s.tipos_evento('PERMANENCIA_CONCLUIDA')] == ['A', 'B', 'C', 'D']
    # B fica a 1,50 m na direção do nariz (yaw), a 1,80 m de altura; pouso de volta em A
    bx, by, bz = em_b[-1]
    alvo = (1.5 * math.cos(yaw), 1.5 * math.sin(yaw))
    assert math.hypot(bx - alvo[0], by - alvo[1]) <= cfg.tarefa1.tol_horizontal_m
    assert abs(bz - 1.8) <= cfg.tarefa1.tol_vertical_m
    x, y, z = drone.xyz
    assert math.hypot(x, y) <= cfg.tarefa1.tol_horizontal_m and z <= 0.01
