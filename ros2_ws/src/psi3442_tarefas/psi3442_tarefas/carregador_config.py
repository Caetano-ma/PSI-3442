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
    kp_guinada: float = 1.5
    taxa_guinada_max_grausps: float = 30.0


@dataclass(frozen=True)
class ConfigTarefa2:
    """Tarefa 2 (Questão 2, R01-R09). Distâncias de superfície a superfície; volume relativo ao ponto de decolagem."""
    cores_alvo: tuple = ('vermelho', 'azul')
    cores_conhecidas: tuple = ('vermelho', 'azul', 'verde', 'amarelo', 'roxo')
    volume_x_min_m: float = -0.4
    volume_x_max_m: float = 4.8
    volume_y_min_m: float = -0.4
    volume_y_max_m: float = 3.8
    volume_z_min_m: float = 0.5
    volume_z_max_m: float = 2.3
    altura_busca_m: float = 1.4
    passo_busca_m: float = 2.2              # espaçamento da grade de pontos de varredura
    passo_giro_graus: float = 45.0
    pausa_giro_s: float = 1.5                # parada em cada direção para a visão
    raio_balao_m: float = 0.13               # nominal (diâmetro ~26 cm)
    raio_envelope_frontal_m: float = 0.149   # centro da aeronave -> frente das hélices (verificar no manual)
    d_alvo_m: float = 0.025                  # distância desejada na permanência
    d_max_m: float = 0.05                    # faixa válida: 0 < d <= d_max (R04)
    tempo_permanencia_s: float = 60.0
    distancia_aproximacao_m: float = 0.60    # distância de superfície do ponto de espera antes da aproximação final
    v_aproximacao_final_mps: float = 0.08
    margem_obstaculos_m: float = 0.40        # paredes e mobiliário (R06)
    margem_nao_alvo_m: float = 0.50          # balões de cor não alvo (R06)
    margem_outros_alvos_m: float = 0.30      # outros balões de cor-alvo, ainda não selecionados ou já destruídos (R06)
    observacoes_min: int = 3
    tempo_confirmacao_s: float = 4.0
    fracao_cor_central_min: float = 0.5
    tempo_sem_confirmacao_s: float = 1.0     # confirmação perdida por mais que isto interrompe a contagem
    tol_posicao_m: float = 0.15
    tol_guinada_graus: float = 6.0
    v_pairado_max_mps: float = 0.10
    tentativas_por_balao: int = 3
    tempo_max_tarefa_s: float = 1500.0
    altura_inicio_pouso_m: float = 0.30
    altura_min_decolagem_m: float = 0.50
    tempo_max_preparacao_s: float = 10.0
    tempo_max_decolagem_s: float = 20.0


@dataclass(frozen=True)
class ConfigVisao:
    """Visão computacional (R02): modelo YOLO em ONNX e câmera do Mini 4 Pro (valores a verificar)."""
    modelo_onnx: str = ''                    # vazio: modelos/baloes_yolov8n.onnx no share do pacote
    classes: tuple = ('vermelho', 'azul', 'verde', 'amarelo', 'roxo')
    tamanho_entrada: int = 416
    limiar_confianca: float = 0.5
    limiar_nms: float = 0.45
    hfov_graus: float = 82.1
    largura_px: int = 640
    altura_px: int = 480
    distancia_max_m: float = 6.0
    taxa_max_hz: float = 5.0


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
    tarefa2: ConfigTarefa2 = field(default_factory=ConfigTarefa2)
    visao: ConfigVisao = field(default_factory=ConfigVisao)
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
        elif tipo in (tuple, 'tuple'):
            if not isinstance(valor, (list, tuple)) or not valor:
                raise ErroConfiguracao(f'{nome}.{chave} deve ser uma lista não vazia')
            valores[chave] = tuple(str(v) for v in valor)
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
    desconhecidas = set(dados) - {'tarefa1', 'tarefa2', 'seguranca', 'estimacao', 'controle', 'ponte', 'visao'}
    if desconhecidas:
        raise ErroConfiguracao(f'seções desconhecidas: {sorted(desconhecidas)}')
    cfg = Configuracao(
        tarefa1=_tarefa1(dados.get('tarefa1')),
        seguranca=_secao_opcional(ConfigSeguranca, dados.get('seguranca'), 'seguranca'),
        estimacao=_secao_opcional(ConfigEstimacao, dados.get('estimacao'), 'estimacao'),
        controle=_secao_opcional(ConfigControle, dados.get('controle'), 'controle'),
        ponte=_secao_opcional(ConfigPonte, dados.get('ponte'), 'ponte'),
        tarefa2=_secao_opcional(ConfigTarefa2, dados.get('tarefa2'), 'tarefa2'),
        visao=_secao_opcional(ConfigVisao, dados.get('visao'), 'visao'),
        arquivo=arquivo,
    )
    _validar_tarefa2(cfg.tarefa2, cfg.visao)
    if cfg.seguranca.bateria_critica_pct >= cfg.seguranca.bateria_minima_pct:
        raise ErroConfiguracao('bateria_critica_pct deve ser menor que bateria_minima_pct')
    return cfg


def _validar_tarefa2(t2, visao):
    desconhecidas = set(t2.cores_alvo) - set(t2.cores_conhecidas)
    if desconhecidas:
        raise ErroConfiguracao(f'tarefa2.cores_alvo fora de cores_conhecidas: {sorted(desconhecidas)}')
    if set(visao.classes) != set(t2.cores_conhecidas):
        raise ErroConfiguracao('visao.classes deve conter as mesmas cores de tarefa2.cores_conhecidas')
    if not 0 < t2.d_alvo_m < t2.d_max_m:
        raise ErroConfiguracao('tarefa2: exige 0 < d_alvo_m < d_max_m (faixa do R04)')
    if t2.volume_x_min_m >= t2.volume_x_max_m or t2.volume_y_min_m >= t2.volume_y_max_m \
            or t2.volume_z_min_m >= t2.volume_z_max_m:
        raise ErroConfiguracao('tarefa2: volume permitido vazio')
    if not t2.volume_z_min_m <= t2.altura_busca_m <= t2.volume_z_max_m:
        raise ErroConfiguracao('tarefa2.altura_busca_m fora do volume permitido')


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
