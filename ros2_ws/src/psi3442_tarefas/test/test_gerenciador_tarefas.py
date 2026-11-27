"""T10 (R03): só "executar tarefa 1" basta para a tarefa percorrer todos os estados até concluida;
"executar tarefa 2" é recusado enquanto a Tarefa 1 não tiver sido concluída em voo real.
Malha fechada com o simulador cinemático (SistemaSimulado), configuração real (60 s por vértice)."""
import dataclasses
import json
import math

import pytest
import yaml

from psi3442_tarefas import carregador_config
from psi3442_tarefas.no_gerenciador_tarefas import SeletorTarefa
from psi3442_tarefas.tipos import EXECUTAR_TAREFA1, EXECUTAR_TAREFA2, INTERROMPER, POUSAR, TERMINO_SEGURO, Telemetria
from sistema_simulado import CONFIG, SistemaSimulado, pousado

ESTADOS_P06 = ['preparando', 'decolando', 'subindo', 'pairando', 'deslocando', 'retornando', 'estabilizandoEmA',
               'pousando', 'concluida']


@pytest.fixture(scope='module')
def missao_completa():
    s = SistemaSimulado()
    assert 'Tarefa 1' in s.comando(EXECUTAR_TAREFA2)           # recusada antes da Tarefa 1
    assert s.seletor.modo == 'ocioso'
    s.comando(EXECUTAR_TAREFA1)                                 # único comando do operador
    assert s.rodar_ate(pousado, 700.0), f'não pousou; estado {s.tarefa1.estado}'
    return s


def test_t10_um_comando_percorre_todos_os_estados(missao_completa):
    s = missao_completa
    visitados = s.estados_visitados()
    for estado in ESTADOS_P06:
        assert estado in visitados, f'{estado} não visitado: {visitados}'
    assert visitados[-1] == 'concluida'
    assert s.tipos_evento('TAREFA_CONCLUIDA')
    assert not [f for _, f in s.falhas if f.reacao == TERMINO_SEGURO]


def test_t10_permanencias_na_ordem_e_com_60s(missao_completa):
    concluidas = missao_completa.tipos_evento('PERMANENCIA_CONCLUIDA')
    assert [ev.nome_vertice for ev in concluidas] == ['A', 'B', 'C', 'D']      # sem segunda espera em A
    assert all(ev.permanencia_s >= 60.0 for ev in concluidas)


def test_t10_trajetoria_dentro_das_tolerancias(missao_completa):
    s = missao_completa
    cfg = s.cfg.tarefa1
    planejador = s.tarefa1.planejador
    # nos instantes de permanência concluída, posição real dentro da tolerância do vértice
    for t_ev, ev in s.eventos:
        if ev.tipo != 'PERMANENCIA_CONCLUIDA':
            continue
        real = next(r for t, _, _, r in s.trajeto if t >= t_ev)
        alvo = planejador.pontos[ev.vertice]
        assert math.hypot(real[0] - alvo[0], real[1] - alvo[1]) <= cfg.tol_horizontal_m
        assert abs(real[2] - alvo[2]) <= cfg.tol_vertical_m


def test_t10_pouso_suave_em_a(missao_completa):
    s = missao_completa
    confirmacao = s.tipos_evento('POUSO_CONFIRMADO')[0]
    assert confirmacao.valor <= s.cfg.tarefa1.v_toque_max_mps
    x, y, _ = s.posicao_real_local()
    assert math.hypot(x, y) <= s.cfg.tarefa1.tol_horizontal_m
    assert POUSAR in [a for _, a in s.acoes]


def test_t10_simulacao_nao_conta_como_voo_real(missao_completa):
    s = missao_completa
    assert not s.seletor.tarefa1_concluida_voo_real
    assert 'Tarefa 1' in s.comando(EXECUTAR_TAREFA2)


def test_sentido_adcb():
    with open(CONFIG, encoding='utf-8') as arquivo:
        dados = yaml.safe_load(arquivo)
    dados['tarefa1']['sentido'] = 'adcb'
    dados['tarefa1']['tempo_permanencia_s'] = 3.0
    s = SistemaSimulado(cfg=carregador_config.carregar_dict(dados))
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(pousado, 200.0)
    assert [ev.nome_vertice for ev in s.tipos_evento('PERMANENCIA_CONCLUIDA')] == ['A', 'D', 'C', 'B']
    assert s.tarefa1.estado == 'concluida'


def test_interromper_em_voo_pousa_no_local():
    s = SistemaSimulado()
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(lambda s: s.tarefa1.estado == 'deslocando', 120.0)
    s.rodar_ate(lambda s: False, 2.0)
    x0, y0, _ = s.posicao_real_local()
    s.comando(INTERROMPER)
    assert s.seletor.modo == 'terminoSeguro'
    assert s.rodar_ate(pousado, 30.0)
    assert s.tarefa1.estado == 'abortada'
    x, y, _ = s.posicao_real_local()
    assert math.hypot(x - x0, y - y0) < 0.3                  # pousou no local, não voltou a A
    assert not s.seletor.tarefa1_concluida_voo_real


def test_interromper_na_preparacao_e_recusas():
    s = SistemaSimulado()
    s.comando(EXECUTAR_TAREFA1)
    assert 'recusado' in s.comando(EXECUTAR_TAREFA1)          # já em execução
    s.comando(INTERROMPER)
    assert s.seletor.modo == 'ocioso'
    s.rodar_ate(lambda s: False, 1.0)
    assert s.tarefa1.estado == 'aguardando'
    assert not s.drone.motores
    assert s.comando(INTERROMPER) == 'nada a interromper'


def test_recusa_sem_telemetria():
    seletor = SeletorTarefa()
    seletor.ao_comando(EXECUTAR_TAREFA1, 10.0)
    assert 'sem telemetria' in seletor.mensagem and seletor.modo == 'ocioso'


def test_progresso_em_voo_real_persistido(tmp_path):
    arquivo = tmp_path / 'progresso.json'
    base = carregador_config.carregar(CONFIG)
    cfg = dataclasses.replace(base, tarefa1=dataclasses.replace(base.tarefa1, tempo_permanencia_s=2.0))
    s = SistemaSimulado(cfg=cfg, simulacao=False)
    s.seletor.arquivo_progresso = str(arquivo)
    s.comando(EXECUTAR_TAREFA1)
    assert s.rodar_ate(pousado, 200.0)
    assert s.seletor.tarefa1_concluida_voo_real
    assert json.loads(arquivo.read_text(encoding='utf-8'))['tarefa1_concluida_voo_real'] is True
    assert 'tarefa 2 iniciada' in s.comando(EXECUTAR_TAREFA2)          # liberada depois do voo real
    # outro processo lê o progresso do arquivo
    assert SeletorTarefa(arquivo_progresso=str(arquivo)).tarefa1_concluida_voo_real


def test_recusa_com_aeronave_em_voo():
    seletor = SeletorTarefa()
    seletor.ao_telemetria(Telemetria(em_voo=True, motores_ligados=True), 1.0)
    seletor.ao_comando(EXECUTAR_TAREFA1, 1.0)
    assert 'pousada' in seletor.mensagem and seletor.modo == 'ocioso'
