"""Testes unitários dos demais módulos: configuração, planejador, verificador, controle, protocolo da ponte,
interface do operador e exportador de CSV."""
import math
import socket
import time

import pytest
import yaml

from psi3442_tarefas import carregador_config
from psi3442_tarefas.carregador_config import ErroConfiguracao
from psi3442_tarefas.cliente_socket_ponte import ClienteSocketPonte, ErroProtocolo, LeitorLinhas, codificar, decodificar
from psi3442_tarefas.no_controle_voo import ControladorPosicao
from psi3442_tarefas.no_interface_operador import interpretar
from psi3442_tarefas.no_ponte_dji import json_de_acao, json_de_telemetria, telemetria_de_json
from psi3442_tarefas.planejador_trajetoria import PlanejadorTrajetoria
from psi3442_tarefas.tipos import (DECOLAR, EXECUTAR_TAREFA1, EXECUTAR_TAREFA2, INTERROMPER, ComandoVelocidade, Estado,
                                   Evento, Setpoint, Telemetria)
from psi3442_tarefas.verificador_tolerancia import VerificadorTolerancia
from sistema_simulado import CONFIG


@pytest.fixture
def dados():
    with open(CONFIG, encoding='utf-8') as arquivo:
        return yaml.safe_load(arquivo)


# ---------------------------------------------------------------------- configuração (P05, R01)
def test_config_oficial_carrega_com_valores_p05():
    cfg = carregador_config.carregar(CONFIG)
    t = cfg.tarefa1
    assert (t.tol_vertical_m, t.tol_horizontal_m, t.v_pairado_max_mps, t.v_toque_max_mps) == (0.10, 0.30, 0.15, 0.50)
    assert t.tempo_permanencia_s == 60.0 and t.altura_alvo_m == 1.80 and t.aresta_m == 1.50
    assert cfg.seguranca.bateria_minima_pct == 30.0


@pytest.mark.parametrize('alteracao,trecho', [
    (lambda d: d['tarefa1'].pop('tol_vertical_m'), 'ausentes'),
    (lambda d: d['tarefa1'].__setitem__('tol_horizontal_m', -0.3), 'positivo'),
    (lambda d: d['tarefa1']['vertices'].__setitem__('C', [1.5, 1.4, 1.8]), 'incoerente'),
    (lambda d: d['tarefa1'].__setitem__('sentido', 'horario'), 'sentido'),
    (lambda d: d['tarefa1'].__setitem__('tolerancia_extra', 1), 'desconhecidas'),
    (lambda d: d['seguranca'].__setitem__('bateria_critica_pct', 40.0), 'bateria_critica'),
    (lambda d: d['tarefa1'].__setitem__('tempo_permanencia_s', 'sessenta'), 'número'),
])
def test_config_invalida_e_rejeitada(dados, alteracao, trecho):
    alteracao(dados)
    with pytest.raises(ErroConfiguracao, match=trecho):
        carregador_config.carregar_dict(dados)


def test_config_tarefa2_oficial():
    cfg = carregador_config.carregar(CONFIG)
    t2 = cfg.tarefa2
    assert t2.cores_alvo == ('vermelho', 'azul') and t2.d_max_m == 0.05 and t2.tempo_permanencia_s == 60.0
    assert 0 < t2.d_alvo_m < t2.d_max_m and cfg.visao.classes == t2.cores_conhecidas


@pytest.mark.parametrize('alteracao', [
    lambda d: d['tarefa2'].__setitem__('cores_alvo', ['laranja']),
    lambda d: d['tarefa2'].__setitem__('d_alvo_m', 0.06),
    lambda d: d['tarefa2'].__setitem__('volume_x_max_m', -1.0),
    lambda d: d['tarefa2'].__setitem__('altura_busca_m', 3.0),
    lambda d: d['visao'].__setitem__('classes', ['vermelho']),
    lambda d: d['tarefa2'].__setitem__('cor_extra', 1),
])
def test_config_tarefa2_invalida_e_rejeitada(dados, alteracao):
    alteracao(dados)
    with pytest.raises(ErroConfiguracao):
        carregador_config.carregar_dict(dados)


def test_config_teste_rapido_usa_padroes():
    cfg = carregador_config.carregar(CONFIG.replace('tarefas.yaml', 'tarefas_teste_rapido.yaml'))
    assert cfg.tarefa1.tempo_permanencia_s == 5.0
    assert cfg.controle.kp == 0.8


# ---------------------------------------------------------------------- planejador e verificador
def test_planejador_sequencias():
    cfg = carregador_config.carregar(CONFIG).tarefa1
    assert PlanejadorTrajetoria(cfg.vertices, 'abcd').nomes == ('A', 'B', 'C', 'D', 'A')
    p = PlanejadorTrajetoria(cfg.vertices, 'adcb')
    assert p.nomes == ('A', 'D', 'C', 'B', 'A')
    sp = p.setpoint(1)
    assert (sp.x_m, sp.y_m, sp.z_m, sp.nome, sp.ativo) == (0.0, 1.5, 1.8, 'D', True)
    assert len(p.segmentos()) == 5


def test_verificador_limites():
    v = VerificadorTolerancia(0.30, 0.10, 0.15)
    sp = Setpoint(ativo=True, x_m=1.5, y_m=0.0, z_m=1.8)
    assert v.avaliar(Estado(x_m=1.5 + 0.29, y_m=0.0, z_m=1.8 + 0.09, valido=True), sp).dentro
    assert not v.avaliar(Estado(x_m=1.5, y_m=0.31, z_m=1.8, valido=True), sp).dentro_horizontal
    assert not v.avaliar(Estado(x_m=1.5, z_m=1.91, valido=True), sp).dentro_vertical
    assert not v.avaliar(Estado(x_m=1.5, z_m=1.8, vx_mps=0.12, vy_mps=0.1, valido=True),
                         sp).dentro_velocidade                     # |v| = 0,156 m/s > 0,15 m/s
    assert not v.avaliar(Estado(x_m=1.5, z_m=1.8, valido=False), sp).dentro


# ---------------------------------------------------------------------- controle
def test_controlador_saturacao_e_casos_sem_comando():
    c = ControladorPosicao(0.8, 0.3, 0.3)
    cmd = c.calcular(Estado(valido=True, psi0_graus=12.0), Setpoint(ativo=True, x_m=1.5, y_m=0.1, z_m=1.8))
    assert (cmd.vx_mps, cmd.vz_mps, cmd.psi0_graus) == (0.3, 0.3, 12.0)
    assert cmd.vy_mps == pytest.approx(0.08)
    assert c.calcular(Estado(valido=True), Setpoint(ativo=False)) is None
    assert c.calcular(Estado(valido=True), None) is None
    zero = c.calcular(Estado(valido=False), Setpoint(ativo=True, x_m=1.0))
    assert (zero.vx_mps, zero.vy_mps, zero.vz_mps) == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------- protocolo da ponte
def test_protocolo_ida_e_volta_telemetria():
    tel = Telemetria(instante_android_s=12.5, v_norte_mps=0.1, altura_tof_m=math.nan, em_voo=True, bateria_pct=55.0)
    linha = codificar(json_de_telemetria(tel))
    assert linha.endswith(b'\n') and b'NaN' not in linha
    volta = telemetria_de_json(decodificar(linha.strip()))
    assert volta.instante_android_s == 12.5 and volta.em_voo and math.isnan(volta.altura_tof_m)


def test_protocolo_rejeita_lixo():
    with pytest.raises(ErroProtocolo):
        decodificar(b'{"sem_tipo": 1}')
    with pytest.raises(ErroProtocolo):
        decodificar(b'nao e json')
    with pytest.raises(ErroProtocolo):
        codificar({'tipo': 'desconhecido'})
    assert json_de_acao(DECOLAR) == {'tipo': 'acao', 'comando': 'decolar'}


def test_leitor_linhas_fragmentadas():
    leitor = LeitorLinhas()
    assert leitor.alimentar(b'{"tipo":"heart') == []
    assert leitor.alimentar(b'beat"}\n{"tipo":"erro"}\n{"ti') == [b'{"tipo":"heartbeat"}', b'{"tipo":"erro"}']
    assert leitor.alimentar(b'po":"acao"}\n') == [b'{"tipo":"acao"}']


def test_cliente_socket_conecta_envia_recebe_e_reconecta():
    servidor = socket.socket()
    servidor.bind(('127.0.0.1', 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    recebidas, conexoes = [], []
    cliente = ClienteSocketPonte('127.0.0.1', porta, recebidas.append, conexoes.append, intervalo_reconexao_s=0.1)
    cliente.iniciar()
    try:
        conexao, _ = servidor.accept()
        conexao.sendall(codificar({'tipo': 'heartbeat', 'instante_s': 1.0}))
        limite = time.monotonic() + 2.0
        while not cliente.conectado and time.monotonic() < limite:
            time.sleep(0.01)
        assert cliente.enviar({'tipo': 'acao', 'comando': 'pousar'})
        assert decodificar(conexao.recv(4096).strip()) == {'tipo': 'acao', 'comando': 'pousar'}
        while not recebidas and time.monotonic() < limite:
            time.sleep(0.01)
        assert recebidas == [{'tipo': 'heartbeat', 'instante_s': 1.0}]
        conexao.close()                                   # derruba: o cliente deve reconectar
        servidor.settimeout(3.0)
        conexao2, _ = servidor.accept()
        conexao2.close()
        assert conexoes[:2] == [True, False]
    finally:
        cliente.parar()
        servidor.close()


# ---------------------------------------------------------------------- interface do operador (R03)
@pytest.mark.parametrize('texto,acao', [
    ('executar tarefa 1', EXECUTAR_TAREFA1), ('  Executar   Tarefa 2 ', EXECUTAR_TAREFA2),
    ('INTERROMPER', INTERROMPER), ('decolar', None), ('subir 1 m', None), ('executar tarefa 3', None),
])
def test_parser_aceita_so_os_tres_comandos(texto, acao):
    assert interpretar(texto) == acao


# ---------------------------------------------------------------------- exportador de CSV
def test_montador_csv(tmp_path):
    from exportar_csv import COLUNAS, MontadorCsv
    m = MontadorCsv()
    m.ao_telemetria(100.0, Telemetria(bateria_pct=77.0))
    m.ao_evento(100.0, Evento(tipo='TRANSICAO', estado='pairando', vertice=0, nome_vertice='A'))
    m.ao_evento(100.1, Evento(tipo='PERMANENCIA_INICIADA', estado='pairando', vertice=0, nome_vertice='A'))
    m.ao_estado(100.6, Estado(x_m=0.01, z_m=1.79, valido=True))
    m.ao_evento(100.7, Evento(tipo='PERMANENCIA_INTERROMPIDA', estado='pairando', vertice=0, nome_vertice='A'))
    m.ao_estado(100.8, Estado(valido=True))
    m.ao_cmd_vel(100.85, ComandoVelocidade(vx_mps=0.3))
    m.ao_evento(100.85, Evento(tipo='SOLICITA_ACAO', estado='pousando', acao=2))
    m.ao_estado(100.9, Estado(valido=True))
    m.ao_estado(101.5, Estado(valido=True))
    linhas = m.linhas
    assert linhas[2][12] == '0.3000' and linhas[2][16] == 'SOLICITA_ACAO:pousar'
    assert linhas[3][12] == '0.0000'                          # comando velho: nada comandado
    assert len(linhas[0]) == len(COLUNAS)
    assert linhas[0][2:4] == ['pairando', 'A'] and linhas[0][10] == 1 and linhas[0][11] == '0.50'
    assert linhas[0][15] == '77.0' and linhas[0][16] == 'pairando|PERMANENCIA_INICIADA'
    assert linhas[1][10] == 0 and linhas[1][16] == 'PERMANENCIA_INTERROMPIDA'
    csv_principal, csv_eventos = m.gravar(str(tmp_path / 'saida.csv'))
    assert open(csv_principal, encoding='utf-8').readline().strip().split(',') == COLUNAS
    assert len(open(csv_eventos, encoding='utf-8').readlines()) == 1 + 4
