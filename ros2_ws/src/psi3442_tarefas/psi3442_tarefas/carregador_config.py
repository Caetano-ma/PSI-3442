"""CarregadorConfig (nível n): lê e valida o YAML das tarefas.

Unidades SI; tolerâncias de P05 obrigatórias e positivas; vértices coerentes com a aresta e a altura.
Seções de segurança, estimação, controle e ponte têm valores padrão (os do modelo SysML) quando ausentes.
Sem dependência de ROS 2: testável isoladamente.
"""
from dataclasses import dataclass, field, fields
import math
import os

import yaml

NOMES_VERTICES = ('A', 'B', 'C', 'D')
TOLERANCIA_GEOMETRIA_M = 0.001


class ErroConfiguracao(ValueError):
    pass


@dataclass(frozen=True)
class ConfigTarefa1:
    altura_alvo_m: float
    aresta_m: float
    vertices: dict            # nome -> (x, y, z)
    sentido: str
    tempo_permanencia_s: float
    tol_horizontal_m: float
    tol_vertical_m: float
    v_pairado_max_mps: float
    v_toque_max_mps: float
    v_deslocamento_max_mps: float
    tempo_estabilizacao_s: float
    altura_inicio_pouso_m: float
    altura_min_decolagem_m: float
    tempo_max_preparacao_s: float
    tempo_max_decolagem_s: float


@dataclass(frozen=True)
class ConfigSeguranca:
    bateria_minima_pct: float = 30.0
    bateria_critica_pct: float = 15.0
    tempo_max_tarefa_s: float = 600.0
    desvio_maximo_m: float = 0.60
    prazo_telemetria_s: float = 0.50
    prazo_perda_ponte_s: float = 2.0
    persistencia_falha_s: float = 1.0


@dataclass(frozen=True)
class ConfigEstimacao:
    idade_max_amostra_s: float = 0.30
    altura_tof_max_m: float = 10.0


@dataclass(frozen=True)
class ConfigControle:
    kp: float = 0.8
    v_max_horizontal_mps: float = 0.30
    v_max_vertical_mps: float = 0.30
    idade_max_setpoint_s: float = 0.50
    idade_max_estado_s: float = 0.30


@dataclass(frozen=True)
class ConfigPonte:
    host: str = '127.0.0.1'
    porta: int = 5760
    taxa_cmd_vel_hz: float = 20.0
    taxa_heartbeat_hz: float = 1.0


@dataclass(frozen=True)
class Configuracao:
    tarefa1: ConfigTarefa1
    seguranca: ConfigSeguranca = field(default_factory=ConfigSeguranca)
    estimacao: ConfigEstimacao = field(default_factory=ConfigEstimacao)
    controle: ConfigControle = field(default_factory=ConfigControle)
    ponte: ConfigPonte = field(default_factory=ConfigPonte)
    arquivo: str = ''


def _numero(secao, chave, valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ErroConfiguracao(f'{secao}.{chave} deve ser um número finito (recebido: {valor!r})')
    return float(valor)


def _secao_opcional(classe, dados, nome):
    dados = dados or {}
    if not isinstance(dados, dict):
        raise ErroConfiguracao(f'seção {nome} deve ser um mapa')
    conhecidas = {f.name: f for f in fields(classe)}
    desconhecidas = set(dados) - set(conhecidas)
    if desconhecidas:
        raise ErroConfiguracao(f'chaves desconhecidas em {nome}: {sorted(desconhecidas)}')
    valores = {}
    for chave, valor in dados.items():
        tipo = conhecidas[chave].type
        if tipo in (str, 'str'):
            valores[chave] = str(valor)
        elif tipo in (int, 'int'):
            valores[chave] = int(_numero(nome, chave, valor))
        else:
            valores[chave] = _numero(nome, chave, valor)
    return classe(**valores)


def _tarefa1(dados):
    if not isinstance(dados, dict):
        raise ErroConfiguracao('seção tarefa1 ausente ou inválida')
    obrigatorias = [f.name for f in fields(ConfigTarefa1)]
    faltando = [c for c in obrigatorias if c not in dados]
    if faltando:
        raise ErroConfiguracao(f'tarefa1: chaves obrigatórias ausentes: {faltando}')
    desconhecidas = set(dados) - set(obrigatorias)
    if desconhecidas:
        raise ErroConfiguracao(f'chaves desconhecidas em tarefa1: {sorted(desconhecidas)}')

    valores = {}
    for chave in obrigatorias:
        if chave in ('vertices', 'sentido'):
            continue
        valores[chave] = _numero('tarefa1', chave, dados[chave])
        if valores[chave] <= 0:
            raise ErroConfiguracao(f'tarefa1.{chave} deve ser positivo')

    sentido = str(dados['sentido'])
    if sentido not in ('abcd', 'adcb'):
        raise ErroConfiguracao("tarefa1.sentido deve ser 'abcd' ou 'adcb'")
    valores['sentido'] = sentido

    brutos = dados['vertices']
    if not isinstance(brutos, dict) or set(brutos) != set(NOMES_VERTICES):
        raise ErroConfiguracao('tarefa1.vertices deve ter exatamente A, B, C e D')
    vertices = {}
    for nome in NOMES_VERTICES:
        ponto = brutos[nome]
        if not isinstance(ponto, (list, tuple)) or len(ponto) != 3:
            raise ErroConfiguracao(f'vértice {nome} deve ser [x, y, z]')
        vertices[nome] = tuple(_numero('tarefa1.vertices', nome, v) for v in ponto)
    valores['vertices'] = vertices

    # coerência geométrica com a aresta e a altura (P02): A sobre a origem, B em +x, D em +y
    h, a = valores['altura_alvo_m'], valores['aresta_m']
    esperado = {'A': (0.0, 0.0, h), 'B': (a, 0.0, h), 'C': (a, a, h), 'D': (0.0, a, h)}
    for nome in NOMES_VERTICES:
        erro = max(abs(p - q) for p, q in zip(vertices[nome], esperado[nome]))
        if erro > TOLERANCIA_GEOMETRIA_M:
            raise ErroConfiguracao(
                f'vértice {nome} = {vertices[nome]} incoerente com aresta {a} m e altura {h} m '
                f'(esperado {esperado[nome]})')

    if valores['altura_inicio_pouso_m'] >= h:
        raise ErroConfiguracao('altura_inicio_pouso_m deve ser menor que altura_alvo_m')
    if valores['v_pairado_max_mps'] >= valores['v_deslocamento_max_mps']:
        raise ErroConfiguracao('v_pairado_max_mps deve ser menor que v_deslocamento_max_mps')
    return ConfigTarefa1(**valores)


def carregar_dict(dados, arquivo=''):
    if not isinstance(dados, dict):
        raise ErroConfiguracao('o arquivo de configuração deve conter um mapa')
    desconhecidas = set(dados) - {'tarefa1', 'tarefa2', 'seguranca', 'estimacao', 'controle', 'ponte'}
    if desconhecidas:
        raise ErroConfiguracao(f'seções desconhecidas: {sorted(desconhecidas)}')
    cfg = Configuracao(
        tarefa1=_tarefa1(dados.get('tarefa1')),
        seguranca=_secao_opcional(ConfigSeguranca, dados.get('seguranca'), 'seguranca'),
        estimacao=_secao_opcional(ConfigEstimacao, dados.get('estimacao'), 'estimacao'),
        controle=_secao_opcional(ConfigControle, dados.get('controle'), 'controle'),
        ponte=_secao_opcional(ConfigPonte, dados.get('ponte'), 'ponte'),
        arquivo=arquivo,
    )
    if cfg.seguranca.bateria_critica_pct >= cfg.seguranca.bateria_minima_pct:
        raise ErroConfiguracao('bateria_critica_pct deve ser menor que bateria_minima_pct')
    return cfg


def carregar(caminho):
    with open(caminho, encoding='utf-8') as arquivo:
        dados = yaml.safe_load(arquivo)
    return carregar_dict(dados, arquivo=os.path.abspath(caminho))


def caminho_padrao():
    """config/tarefas.yaml instalado no share do pacote (ou o da árvore de fontes, fora do ROS)."""
    try:
        from ament_index_python.packages import get_package_share_directory
        return os.path.join(get_package_share_directory('psi3442_tarefas'), 'config', 'tarefas.yaml')
    except Exception:  # noqa: BLE001 — sem ROS 2: usa a árvore de fontes
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'tarefas.yaml')
