"""T07 (R07): reação de cada TipoFalha conforme a tabela do MonitorFalhas (telemetria injetada) e, em malha
fechada com o simulador, término seguro = pouso no local."""
import math

import pytest

from psi3442_tarefas.carregador_config import ConfigSeguranca
from psi3442_tarefas.no_supervisao import MonitorFalhas
from psi3442_tarefas.simulador_cinematico import ParametrosSimulacao
from psi3442_tarefas.tipos import (BATERIA_BAIXA, COMANDO_REJEITADO, DESVIO_EXCESSIVO, ESTIMATIVA_INVALIDA,
                                   EXECUTAR_TAREFA1, PERDA_ENLACE, PERDA_PONTE, POSICIONAMENTO_VISUAL_INATIVO,
                                   REGISTRAR, TELEMETRIA_ATRASADA, TEMPO_TAREFA_EXCEDIDO, TERMINO_SEGURO,
                                   VELOCIDADE_ZERO, Estado, Telemetria)
from sistema_simulado import SistemaSimulado, pousado

H = 1.8
VERTICES = [(0, 0, H), (1.5, 0, H), (1.5, 1.5, H), (0, 1.5, H), (0, 0, H)]


def monitor():
    return MonitorFalhas(ConfigSeguranca(), VERTICES, H)


def tel_voo(**campos):
    base = dict(em_voo=True, motores_ligados=True, bateria_pct=60.0, conectado=True,
                posicionamento_visual_ativo=True)
    base.update(campos)
    return Telemetria(**base)


def estado(x=0.75, y=0.0, z=H, valido=True):
    return Estado(x_m=x, y_m=y, z_m=z, valido=valido, motivo_invalido='' if valido else 'teste')


def rodar(m, n, tel_fn, estado_fn, t0=0.0, telemetria_ate=math.inf):
    """n amostras a 10 Hz; a telemetria para de chegar em `telemetria_ate`. Devolve todas as falhas."""
    falhas, t_tel = [], None
    for i in range(n):
        t = t0 + i * 0.1
        tel = None
        if t < telemetria_ate:
            tel, t_tel = tel_fn(t), t
        falhas += m.avaliar(t, tel, t_tel, estado_fn(t))
    return falhas


def reacoes(falhas, tipo):
    return [f.reacao for f in falhas if f.tipo == tipo]


def test_sem_falhas_em_voo_normal():
    assert rodar(monitor(), 100, lambda t: tel_voo(), lambda t: estado()) == []


def test_perda_enlace():
    f = rodar(monitor(), 10, lambda t: tel_voo(conectado=t < 0.5), lambda t: estado())
    assert reacoes(f, PERDA_ENLACE) == [TERMINO_SEGURO]


def test_bateria_baixa_em_voo_e_no_solo():
    f = rodar(monitor(), 10, lambda t: tel_voo(bateria_pct=14.0), lambda t: estado())
    assert reacoes(f, BATERIA_BAIXA) == [TERMINO_SEGURO]
    f = rodar(monitor(), 10, lambda t: tel_voo(bateria_pct=20.0), lambda t: estado())
    assert reacoes(f, BATERIA_BAIXA) == []                    # entre a crítica (15) e a mínima (30): segue
    solo = lambda t: Telemetria(bateria_pct=25.0)              # noqa: E731
    f = rodar(monitor(), 10, solo, lambda t: estado())
    assert reacoes(f, BATERIA_BAIXA) == [REGISTRAR]


def test_posicionamento_visual_inativo():
    f = rodar(monitor(), 10, lambda t: tel_voo(posicionamento_visual_ativo=False), lambda t: estado())
    assert reacoes(f, POSICIONAMENTO_VISUAL_INATIVO) == [TERMINO_SEGURO]


def test_estimativa_invalida_escalona():
    f = rodar(monitor(), 30, lambda t: tel_voo(), lambda t: estado(valido=False))
    assert reacoes(f, ESTIMATIVA_INVALIDA) == [VELOCIDADE_ZERO, TERMINO_SEGURO]
    # breve (< persistência): só velocidade zero
    f = rodar(monitor(), 30, lambda t: tel_voo(), lambda t: estado(valido=not (1.0 <= t < 1.5)))
    assert reacoes(f, ESTIMATIVA_INVALIDA) == [VELOCIDADE_ZERO]


def test_telemetria_atrasada_e_perda_da_ponte():
    f = rodar(monitor(), 40, lambda t: tel_voo(), lambda t: estado(), telemetria_ate=1.0)
    assert reacoes(f, TELEMETRIA_ATRASADA) == [VELOCIDADE_ZERO, TERMINO_SEGURO]
    assert reacoes(f, PERDA_PONTE) == [TERMINO_SEGURO]


def test_desvio_excessivo():
    assert monitor().desvio(estado(x=0.75, y=0.0)) == pytest.approx(0.0)
    assert monitor().desvio(estado(x=0.75, y=0.75)) == pytest.approx(0.75)   # centro do quadrado
    assert monitor().desvio(estado(x=0.0, y=0.0, z=2.5)) == pytest.approx(0.7)
    f = rodar(monitor(), 10, lambda t: tel_voo(), lambda t: estado(x=-0.7, y=0.5))
    assert reacoes(f, DESVIO_EXCESSIVO) == [TERMINO_SEGURO]
    # descida vertical do pouso no local, sob o contorno, não é desvio
    assert rodar(monitor(), 10, lambda t: tel_voo(), lambda t: estado(x=1.5, y=0.7, z=0.3)) == []


def test_tempo_tarefa_excedido():
    m = MonitorFalhas(ConfigSeguranca(tempo_max_tarefa_s=2.0), VERTICES, H)
    f = rodar(m, 40, lambda t: tel_voo(), lambda t: estado())
    assert reacoes(f, TEMPO_TAREFA_EXCEDIDO) == [TERMINO_SEGURO]


def test_borda_de_subida_reemite_apos_normalizar():
    f = rodar(monitor(), 40, lambda t: tel_voo(conectado=not (0.5 <= t < 1.0 or 2.0 <= t < 2.5)),
              lambda t: estado())
    assert reacoes(f, PERDA_ENLACE) == [TERMINO_SEGURO, TERMINO_SEGURO]


# ---------------------------------------------------------------------- malha fechada (simulador)
def decolar_e_chegar_em(s, estado_alvo='pairando'):
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(lambda s: s.tarefa1.estado == estado_alvo, 60.0)


def test_t07_perda_da_ponte_em_voo_aeronave_pousa_sozinha():
    s = SistemaSimulado()
    decolar_e_chegar_em(s)
    s.silencio = (s.t, s.t + 30.0)                 # ponte calada: nem telemetria nem heartbeat
    assert s.rodar_ate(lambda s: not s.drone.em_voo, 30.0)
    assert any(acao == 'perda_ponte' for _, acao, _ in s.drone.registro)   # watchdog de 2 s do app ponte
    assert reacoes([f for _, f in s.falhas], PERDA_PONTE) == [TERMINO_SEGURO]
    s.silencio = None
    assert s.rodar_ate(pousado, 10.0)
    assert s.tarefa1.estado == 'abortada'
    assert s.drone.v_toque_mps <= s.cfg.tarefa1.v_toque_max_mps


def test_t07_comando_rejeitado_antes_do_voo_volta_a_ocioso():
    s = SistemaSimulado(parametros=ParametrosSimulacao(rejeitar=('decolar',)))
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(lambda s: s.seletor.modo == 'ocioso', 20.0)
    assert reacoes([f for _, f in s.falhas], COMANDO_REJEITADO) != []
    assert not s.drone.motores


def test_t07_bateria_critica_em_voo_pousa_no_local():
    s = SistemaSimulado(parametros=ParametrosSimulacao(bateria_inicial_pct=31.0, consumo_pct_por_s=1.0))
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(pousado, 120.0)
    assert reacoes([f for _, f in s.falhas], BATERIA_BAIXA)[0] == TERMINO_SEGURO
    assert s.tarefa1.estado == 'abortada'
    assert 'pousoSeguro' in s.estados_visitados()


def test_t07_estimativa_invalida_persistente_pousa_no_local():
    s = SistemaSimulado(parametros=ParametrosSimulacao(sem_posicionamento_visual_em_s=20.0))
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(pousado, 120.0)
    tipos = {f.tipo for _, f in s.falhas}
    assert POSICIONAMENTO_VISUAL_INATIVO in tipos
    assert s.tarefa1.estado == 'abortada'
