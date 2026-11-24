"""T08 (P02): conversão de referencial e integração — erro < 1 mm em 10 s contra a solução analítica."""
import math

import pytest

from psi3442_tarefas.no_estimacao_estado import EstimadorEstado, local_de_solo, solo_de_local
from psi3442_tarefas.tipos import Telemetria


def amostra(t, vn, ve, vb=0.0, **extras):
    campos = dict(instante_android_s=t, v_norte_mps=vn, v_leste_mps=ve, v_baixo_mps=vb, altura_tof_m=1.8,
                  altitude_m=1.8, em_voo=True, motores_ligados=True, guinada_graus=extras.pop('guinada', 0.0))
    campos.update(extras)
    return Telemetria(**campos)


@pytest.mark.parametrize('psi0', [0.0, 30.0, 90.0, -135.0, 179.0])
@pytest.mark.parametrize('vn,ve', [(0.3, 0.0), (0.0, -0.2), (0.12, 0.25)])
def test_t08_velocidade_constante_10s(psi0, vn, ve):
    est = EstimadorEstado()
    est.reiniciar(psi0)
    est._motores_antes = True
    for i in range(101):                       # 10 Hz durante 10 s
        estado = est.atualizar(amostra(1.0 + i * 0.1, vn, ve, guinada=psi0), 1.0 + i * 0.1)
    p = math.radians(psi0)
    x_analitico = (vn * math.cos(p) + ve * math.sin(p)) * 10.0
    y_analitico = (vn * math.sin(p) - ve * math.cos(p)) * 10.0
    assert abs(estado.x_m - x_analitico) < 1e-3
    assert abs(estado.y_m - y_analitico) < 1e-3
    assert estado.valido


def test_eixos_do_referencial():
    # nariz para o norte (psi0 = 0): norte é +x, oeste é +y (y à esquerda do nariz)
    assert local_de_solo(1.0, 0.0, 0.0) == pytest.approx((1.0, 0.0))
    assert local_de_solo(0.0, -1.0, 0.0) == pytest.approx((0.0, 1.0))
    # nariz para o leste (psi0 = 90): leste é +x, norte é +y
    assert local_de_solo(0.0, 1.0, 90.0) == pytest.approx((1.0, 0.0), abs=1e-12)
    assert local_de_solo(1.0, 0.0, 90.0) == pytest.approx((0.0, 1.0), abs=1e-12)


@pytest.mark.parametrize('psi0', [0.0, 37.0, -120.0])
def test_conversao_inversa(psi0):
    n, e = solo_de_local(0.3, -0.1, psi0)
    assert local_de_solo(n, e, psi0) == pytest.approx((0.3, -0.1))


def test_trapezio_exato_em_rampa():
    est = EstimadorEstado()
    est.reiniciar(0.0)
    est._motores_antes = True
    for i in range(101):                       # v = 0,1 t  ->  x = 0,05 t²
        t = i * 0.1
        estado = est.atualizar(amostra(1.0 + t, 0.1 * t, 0.0), 1.0 + t)
    assert estado.x_m == pytest.approx(0.05 * 10.0 ** 2, abs=1e-9)


def test_origem_e_psi0_na_partida_dos_motores():
    est = EstimadorEstado()
    est.atualizar(amostra(1.0, 0.0, 0.0, guinada=42.0, em_voo=False, motores_ligados=False), 1.0)
    estado = est.atualizar(amostra(1.1, 0.0, 0.0, guinada=42.0, em_voo=False, motores_ligados=True), 1.1)
    assert est.psi0_graus == 42.0 and estado.psi0_graus == 42.0
    assert (estado.x_m, estado.y_m) == (0.0, 0.0)


def test_sem_integracao_no_chao():
    est = EstimadorEstado()
    for i in range(20):
        estado = est.atualizar(amostra(1.0 + i * 0.1, 0.05, 0.05, em_voo=False, motores_ligados=False), 1.0 + i * 0.1)
    assert (estado.x_m, estado.y_m) == (0.0, 0.0)


def test_altura_tof_e_reserva():
    est = EstimadorEstado(altura_tof_max_m=10.0)
    assert est.atualizar(amostra(1.0, 0, 0, altura_tof_m=1.75, altitude_m=1.9), 1.0).z_m == 1.75
    assert est.atualizar(amostra(1.1, 0, 0, altura_tof_m=math.nan, altitude_m=1.9), 1.1).z_m == 1.9
    assert est.atualizar(amostra(1.2, 0, 0, altura_tof_m=25.0, altitude_m=1.9), 1.2).z_m == 1.9


def test_invalido_amostra_velha_posicionamento_desconexao():
    est = EstimadorEstado(idade_max_amostra_s=0.3)
    est.atualizar(amostra(1.0, 0, 0), 1.0)
    assert not est.atualizar(amostra(1.5, 0, 0), 1.5).valido                       # intervalo de 0,5 s
    assert est.atualizar(amostra(1.6, 0, 0), 1.6).valido
    assert not est.atualizar(amostra(1.7, 0, 0, posicionamento_visual_ativo=False), 1.7).valido
    assert not est.atualizar(amostra(1.8, 0, 0, conectado=False), 1.8).valido
    est.atualizar(amostra(1.9, 0, 0), 1.9)
    assert est.verificar_idade(2.5) and not est.estado.valido
    assert est.estado.motivo_invalido == 'telemetria velha'
