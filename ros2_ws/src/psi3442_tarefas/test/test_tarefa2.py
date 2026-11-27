"""Tarefa 2 em malha fechada (visão sintética): R03, R04, R06 e cenários da seção 7 do enunciado.

A permanência é encurtada para 5 s; a lógica é a mesma dos 60 s. A distância verdadeira (avaliador) só é usada aqui,
para validar a estimativa (R04/R05).
"""
import dataclasses
import math

import pytest

from psi3442_tarefas import carregador_config
from psi3442_tarefas.no_mapeamento_local import CONFIRMADO, MapeamentoLocal
from psi3442_tarefas.no_tarefa2 import pontos_de_busca
from psi3442_tarefas.no_visao_computacional import Deteccao, GeometriaCamera
from psi3442_tarefas.simulador_cinematico import ParametrosSimulacao
from psi3442_tarefas.tipos import EXECUTAR_TAREFA2, INTERROMPER

from sistema_simulado_t2 import CONFIG, BalaoVerdadeiro, SistemaSimuladoT2, pousado

ALVOS = [BalaoVerdadeiro('vermelho', 3.0, 1.0, 1.6), BalaoVerdadeiro('azul', 1.0, 3.0, 1.1)]
NAO_ALVOS = [BalaoVerdadeiro('verde', 2.0, 2.0, 1.5), BalaoVerdadeiro('amarelo', 3.8, 3.0, 1.2)]
MEIA_DIAGONAL_M = math.hypot(0.298, 0.373) / 2          # envelope com hélices, visto de qualquer lado


def cfg_rapida(**t2):
    base = carregador_config.carregar(CONFIG)
    t2.setdefault('tempo_permanencia_s', 5.0)
    return dataclasses.replace(base, tarefa2=dataclasses.replace(base.tarefa2, **t2))


def destruidos(s):
    return [ev for ev in s.tipos_evento('BALAO_DESTRUIDO')]


def distancias_reais_contando(s, alvos=ALVOS):
    """Distância verdadeira (avaliador) da frente das hélices ao alvo mais próximo, em cada passo com a contagem
    da permanência em andamento."""
    ds = []
    for t, _, (x, y, z, g), contando, _ in s.registro:
        if contando:
            frente = (x + 0.149 * math.cos(math.radians(g)), y + 0.149 * math.sin(math.radians(g)), z)
            ds.append((t, min(math.dist(frente, (b.x, b.y, b.z)) - b.raio for b in alvos)))
    return ds


def cor_verdadeira_do_id(s, id_balao):
    b = next(b for b in s.mapa.baloes if b.id == id_balao)
    return s.balao_verdadeiro(b.x_m, b.y_m, b.z_m).cor


@pytest.fixture(scope='module')
def missao():
    s = SistemaSimuladoT2(ALVOS + NAO_ALVOS, cfg=cfg_rapida())
    assert 'iniciada' in s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(pousado, 1500.0), s.tarefa2.estado
    return s


def test_destroi_todos_os_alvos_e_conclui(missao):
    assert missao.tarefa2.estado == 'concluida'
    assert sorted(cor_verdadeira_do_id(missao, int(ev.valor)) for ev in destruidos(missao)) == ['azul', 'vermelho']
    assert not missao.falhas


def test_nao_aproxima_de_cor_nao_alvo(missao):
    selecionados = [cor_verdadeira_do_id(missao, ev.vertice) for ev in missao.tipos_evento('ALVO_SELECIONADO')]
    assert set(selecionados) <= {'vermelho', 'azul'}


def test_permanencia_validada_pela_distancia_verdadeira(missao):
    """R04: durante a contagem, a distância verdadeira (avaliador) fica em 0 < d <= 5 cm; a estimativa não usa a
    verdade (R05)."""
    ds = distancias_reais_contando(missao)
    assert ds
    for t, d in ds:
        assert 0.0 < d <= 0.05, f't={t:.1f}: d verdadeira = {d * 100:.2f} cm'


@pytest.mark.parametrize('vies', [(0.004, -0.003)], ids=['0,5 cm/s'])
def test_permanencia_de_60s_com_deriva_da_posicao(vies):
    """A posição integrada deriva (viés na velocidade); a reancoragem pela medida de proximidade da visão mantém
    a distância verdadeira na faixa por 60 s, e o realinhamento do mapa evita revisitar o balão destruído."""
    par = ParametrosSimulacao(vies_norte_mps=vies[0], vies_leste_mps=vies[1], ruido_velocidade_mps=0.02)
    s = SistemaSimuladoT2(ALVOS + NAO_ALVOS, cfg=cfg_rapida(tempo_permanencia_s=60.0), parametros=par)
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(pousado, 2000.0)
    assert s.tarefa2.estado == 'concluida' and not s.falhas
    assert len(destruidos(s)) == 2 and all(ev.permanencia_s >= 60.0 for ev in s.tipos_evento('PERMANENCIA_CONCLUIDA'))
    assert all(0.0 < d <= 0.05 for _, d in distancias_reais_contando(s))


def test_deriva_extrema_nunca_conta_fora_da_faixa():
    """Deriva de ~2 cm/s: a missão pode não cumprir, mas a contagem nunca corre fora de 0 < d <= 5 cm e a aeronave
    termina pousada."""
    par = ParametrosSimulacao(vies_norte_mps=0.02, vies_leste_mps=-0.01, ruido_velocidade_mps=0.02)
    s = SistemaSimuladoT2(ALVOS + NAO_ALVOS, cfg=cfg_rapida(tempo_permanencia_s=60.0), parametros=par)
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(pousado, 2000.0)
    assert all(0.0 < d <= 0.05 for _, d in distancias_reais_contando(s))


def test_mantem_margem_dos_balões_nao_alvo(missao):
    """R06: a aeronave nunca encosta nos balões não selecionados."""
    for _, _, (x, y, z, _), _, _ in missao.registro:
        for b in NAO_ALVOS:
            folga = math.dist((x, y, z), (b.x, b.y, b.z)) - b.raio - MEIA_DIAGONAL_M
            assert folga > 0.15, f'folga de {folga:.2f} m do balão {b.cor}'


def test_balao_destruido_nao_e_contado_de_novo(missao):
    ids = [int(ev.valor) for ev in destruidos(missao)]
    assert len(ids) == len(set(ids))
    assert all(b.situacao == 2 for b in missao.mapa.baloes if b.id in ids)


def test_pouso_suave_ao_fim(missao):
    toque = missao.tipos_evento('POUSO_CONFIRMADO')[-1].valor
    assert toque <= missao.cfg.tarefa1.v_toque_max_mps


def test_sem_alvos_varre_e_pousa():
    """Cenário: ausência de alvos (só cores não alvo)."""
    s = SistemaSimuladoT2(NAO_ALVOS, cfg=cfg_rapida())
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(pousado, 1500.0)
    assert s.tarefa2.estado == 'concluida'
    assert not destruidos(s) and not s.tipos_evento('ALVO_SELECIONADO')


def test_reinicia_contagem_ao_sair_da_faixa():
    """R04: uma rajada empurra a aeronave para fora da faixa; a contagem reinicia e conclui depois."""
    s = SistemaSimuladoT2(ALVOS[:1], cfg=cfg_rapida())
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(lambda s: s.tarefa2.cronometro.contando and s.tarefa2.cronometro.decorrido(s.t) > 2.0, 200)
    g = math.radians(s.drone.guinada)
    for _ in range(3):                         # rajada de 0,4 m/s para trás (afasta do balão)
        s.drone.v_norte -= 0.4 * math.cos(g)
        s.drone.v_leste -= 0.4 * math.sin(g)
        s.passo()
    assert s.rodar_ate(lambda s: destruidos(s), 200)
    interrupcoes = s.tipos_evento('PERMANENCIA_INTERROMPIDA')
    assert interrupcoes and interrupcoes[0].permanencia_s > 2.0
    concluida = s.tipos_evento('PERMANENCIA_CONCLUIDA')[-1]
    assert concluida.permanencia_s >= 5.0 and 'reinício' in concluida.detalhe


def test_perda_de_deteccao_na_permanencia_reinicia():
    """Cenário: perda de detecção durante a permanência (a visão some por 3 s)."""
    s = SistemaSimuladoT2(ALVOS[:1], cfg=cfg_rapida())
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(lambda s: s.tarefa2.cronometro.contando and s.tarefa2.cronometro.decorrido(s.t) > 2.0, 200)
    visiveis = s.visao_sintetica.baloes
    s.visao_sintetica.baloes = []
    s.rodar_ate(lambda s: False, 3.0)
    s.visao_sintetica.baloes = visiveis
    assert s.tipos_evento('PERMANENCIA_INTERROMPIDA')
    assert s.rodar_ate(lambda s: destruidos(s), 200)


def test_interromper_pousa_no_local():
    s = SistemaSimuladoT2(ALVOS, cfg=cfg_rapida())
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(lambda s: s.tarefa2.estado == 'aproximando', 100)
    s.comando(INTERROMPER)
    assert s.rodar_ate(pousado, 100)
    assert s.tarefa2.estado == 'abortada'


def test_pontos_de_busca_dentro_do_volume():
    cfg = carregador_config.carregar(CONFIG).tarefa2
    pontos = pontos_de_busca(cfg)
    assert pontos[0] == (0.0, 0.0) and len(pontos) >= 4
    assert all(cfg.volume_x_min_m <= x <= cfg.volume_x_max_m and cfg.volume_y_min_m <= y <= cfg.volume_y_max_m
               for x, y in pontos)


def test_mapeamento_associa_e_confirma():
    cfg = carregador_config.carregar(CONFIG)
    mapa = MapeamentoLocal(cfg.tarefa2)
    geo = GeometriaCamera(cfg.visao.hfov_graus, 640, 480, 0.13)
    # balão 2 m à frente, centrado: raio aparente = f * tan(asin(0.13 / 2.03))
    r_px = geo.f * math.tan(math.asin(0.13 / 2.03))
    for k in range(4):
        det = geo.completar(Deteccao('vermelho', 0.9, 320 + k, 240, int(2 * r_px), int(2 * r_px)), 0.0)
        alvos = type('A', (), {'x_m': 0.0, 'y_m': 0.0, 'z_m': 1.5, 'guinada_local_graus': 0.0, 'deteccoes': [det]})
        mapa.atualizar_deteccoes(alvos, float(k))
    assert len(mapa.baloes) == 1
    b = mapa.baloes[0]
    assert b.situacao == CONFIRMADO and b.alvo
    assert math.dist((b.x_m, b.y_m, b.z_m), (2.13, 0.0, 1.53)) < 0.1


def test_mapeamento_ignora_deteccoes_no_solo():
    cfg = carregador_config.carregar(CONFIG)
    mapa = MapeamentoLocal(cfg.tarefa2)
    det = Deteccao('azul', 0.9, 320, 240, 60, 60, 0.0, 0.0, 2.0)
    mapa.atualizar_deteccoes(type('A', (), {'x_m': 0, 'y_m': 0, 'z_m': 0.05, 'guinada_local_graus': 0,
                                            'deteccoes': [det]}), 0.0)
    assert not mapa.baloes


def test_balao_em_movimento_mantem_a_faixa():
    """R04: "o controle deverá manter a posição relativa à bexiga caso ela se movimente". O balão-alvo deriva
    a 1 cm/s durante a permanência; a reancoragem pela visão segue o balão."""
    alvo = BalaoVerdadeiro('vermelho', 3.0, 1.0, 1.6)
    s = SistemaSimuladoT2([alvo], cfg=cfg_rapida(tempo_permanencia_s=30.0))
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(lambda s: s.tarefa2.estado == 'permanecendo', 300)
    inicio = (alvo.x, alvo.y)
    reais = []                                # distância verdadeira no instante de cada passo com contagem
    while not destruidos(s) and s.t < 600:
        alvo.x += 0.007 * 0.1                 # ~1 cm/s, na diagonal
        alvo.y += 0.007 * 0.1
        s.passo()
        if s.registro[-1][3]:
            reais.append(s.distancia_real(alvo))
    assert destruidos(s)
    assert math.dist(inicio, (alvo.x, alvo.y)) > 0.25
    assert reais and all(0.0 < d <= 0.05 for d in reais), (min(reais), max(reais))


def test_mapa_nao_trata_balao_como_obstaculo_fixo():
    cfg = carregador_config.carregar(CONFIG)
    mapa = MapeamentoLocal(cfg.tarefa2)
    r_px = GeometriaCamera(cfg.visao.hfov_graus, 640, 480, 0.13)
    geo = r_px
    raio = geo.f * math.tan(math.asin(0.13 / 2.03))
    for k in range(4):
        det = geo.completar(Deteccao('vermelho', 0.9, 320, 240, int(2 * raio), int(2 * raio)), 0.0)
        mapa.atualizar_deteccoes(type('A', (), {'x_m': 0.0, 'y_m': 0.0, 'z_m': 1.5, 'guinada_local_graus': 0.0,
                                                'deteccoes': [det]}), float(k))
    b = mapa.baloes[0]
    # o sensor de distâncias acerta a superfície do balão várias vezes
    for _ in range(5):
        mapa.atualizar_obstaculos(0.0, 0.0, 0.0, -0.01, 0.01, [b.x_m - 0.13] * 3, 8.0)
    assert not mapa.obstaculo_perto(b.x_m - 0.4, b.y_m, 0.4)
    # uma parede de verdade continua sendo obstáculo
    for _ in range(5):
        mapa.atualizar_obstaculos(0.0, 0.0, 180.0, -0.01, 0.01, [1.0] * 3, 8.0)
    assert mapa.obstaculo_perto(-0.8, 0.0, 0.4)


def test_proximidade_pela_linha_mais_larga_numa_imagem():
    """bordas_centrais + GeometriaCamera numa imagem desenhada: balão vermelho acima e à direita do centro."""
    import cv2
    import numpy as np

    from psi3442_tarefas.no_visao_computacional import bordas_centrais

    geo = GeometriaCamera(82.1, 640, 480, 0.13)
    img = np.full((480, 640, 3), 200, np.uint8)
    cu, cv, r_px = 350, 190, 150                       # centro 50 px acima e 30 px à direita do centro da imagem
    cv2.circle(img, (cu, cv), r_px, (20, 20, 220), -1)
    u0, u1, v, cortado_h, cortado_v = bordas_centrais(img, 'vermelho')
    assert not cortado_h and not cortado_v and abs(v - cv) <= 1
    d, az = geo.proximidade(u0, u1, 0.0)
    esperado = 0.13 / math.sin(math.atan(r_px / geo.f))
    assert abs(d - esperado) / esperado < 0.03
    assert az < 0                                       # à direita = azimute negativo
    assert abs(geo.elevacao(v, (u0 + u1) / 2) - math.degrees(math.atan2(240 - cv, math.hypot(geo.f, 320 - cu)))) < 0.5
    # balão maior que a imagem: limite superior
    img2 = np.full((480, 640, 3), 200, np.uint8)
    cv2.circle(img2, (320, 240), 400, (20, 20, 220), -1)
    assert bordas_centrais(img2, 'vermelho')[3]


def test_fantasma_perto_de_balao_destruido_nao_e_contado_de_novo():
    """Uma entrada falsa do mapa a ~0,5 m do balão já destruído é selecionada; medida de perto, ela é o mesmo balão:
    descartada, sem nova contagem (R04: impedir contagem duplicada)."""
    from types import SimpleNamespace
    s = SistemaSimuladoT2(ALVOS[:1], cfg=cfg_rapida())
    s.comando(EXECUTAR_TAREFA2)
    assert s.rodar_ate(lambda s: destruidos(s), 300)
    destruido = next(b for b in s.mapa.baloes if b.situacao == 2)
    fantasma = SimpleNamespace(**{**destruido.__dict__})
    fantasma.id, fantasma.situacao, fantasma.observacoes = 999, CONFIRMADO, 5
    fantasma.y_m += 0.7                               # além da fusão do mapa (0,6 m): só a medida de perto o pega
    s.mapa.baloes.append(s.mapa.baloes[0].__class__(**fantasma.__dict__))
    assert s.rodar_ate(lambda s: any(ev.vertice == 999 for ev in s.tipos_evento('ALVO_DESCARTADO')) or
                       len(destruidos(s)) > 1, 300)
    assert len(destruidos(s)) == 1


def test_alvo_com_posicao_muito_incerta_nao_e_selecionado():
    from psi3442_tarefas.no_tarefa2 import MaquinaTarefa2
    from types import SimpleNamespace
    cfg = cfg_rapida().tarefa2
    m = MaquinaTarefa2(cfg, 30.0)
    estado = SimpleNamespace(x_m=0.0, y_m=0.0, z_m=1.4, valido=True)
    incerto = SimpleNamespace(id=1, cor='vermelho', alvo=True, situacao=CONFIRMADO, x_m=2, y_m=1, z_m=1.5,
                              incerteza_m=0.35)
    baixo = SimpleNamespace(id=2, cor='azul', alvo=True, situacao=CONFIRMADO, x_m=2, y_m=2, z_m=0.1, incerteza_m=0.1)
    bom = SimpleNamespace(id=3, cor='azul', alvo=True, situacao=CONFIRMADO, x_m=3, y_m=1, z_m=1.5, incerteza_m=0.1)
    assert m._escolher_alvo(SimpleNamespace(baloes=[incerto, baixo]), estado) is None
    assert m._escolher_alvo(SimpleNamespace(baloes=[incerto, baixo, bom]), estado).id == 3
