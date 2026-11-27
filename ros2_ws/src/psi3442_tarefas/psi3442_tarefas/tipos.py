"""Tipos de dados compartilhados (espelham Comum::* do modelo e as mensagens de psi3442_interfaces).

Os nomes dos campos são os mesmos das mensagens ROS 2, de modo que a lógica aceita indistintamente estes
dataclasses (testes, simulador) ou as próprias mensagens (nós).
"""
from dataclasses import dataclass
import math

# ComandoDiscreto.tipo
DECOLAR = 1
POUSAR = 2
HABILITAR_CONTROLE_VIRTUAL = 3
DESABILITAR_CONTROLE_VIRTUAL = 4
PARAR_E_PAIRAR = 5
NOMES_ACAO = {
    DECOLAR: 'decolar', POUSAR: 'pousar', HABILITAR_CONTROLE_VIRTUAL: 'habilitar_controle_virtual',
    DESABILITAR_CONTROLE_VIRTUAL: 'desabilitar_controle_virtual', PARAR_E_PAIRAR: 'parar_e_pairar',
}
ACAO_POR_NOME = {v: k for k, v in NOMES_ACAO.items()}

# ComandoOperador.acao
EXECUTAR_TAREFA1 = 1
EXECUTAR_TAREFA2 = 2
INTERROMPER = 3

# Falha.tipo (Comum::TipoFalha)
PERDA_ENLACE = 1
PERDA_PONTE = 2
TELEMETRIA_ATRASADA = 3
BATERIA_BAIXA = 4
ESTIMATIVA_INVALIDA = 5
POSICIONAMENTO_VISUAL_INATIVO = 6
DESVIO_EXCESSIVO = 7
TEMPO_TAREFA_EXCEDIDO = 8
COMANDO_REJEITADO = 9
NOMES_FALHA = {
    PERDA_ENLACE: 'perdaEnlace', PERDA_PONTE: 'perdaPonte', TELEMETRIA_ATRASADA: 'telemetriaAtrasada',
    BATERIA_BAIXA: 'bateriaBaixa', ESTIMATIVA_INVALIDA: 'estimativaInvalida',
    POSICIONAMENTO_VISUAL_INATIVO: 'posicionamentoVisualInativo', DESVIO_EXCESSIVO: 'desvioExcessivo',
    TEMPO_TAREFA_EXCEDIDO: 'tempoTarefaExcedido', COMANDO_REJEITADO: 'comandoRejeitado',
}

# Falha.reacao
REGISTRAR = 0
VELOCIDADE_ZERO = 1
TERMINO_SEGURO = 2
VOLTAR_OCIOSO = 3
NOMES_REACAO = {REGISTRAR: 'registrar', VELOCIDADE_ZERO: 'velocidadeZero', TERMINO_SEGURO: 'terminoSeguro',
                VOLTAR_OCIOSO: 'voltarOcioso'}


@dataclass
class Telemetria:
    instante_android_s: float = 0.0
    v_norte_mps: float = 0.0
    v_leste_mps: float = 0.0
    v_baixo_mps: float = 0.0
    altitude_m: float = 0.0
    altura_tof_m: float = math.nan
    guinada_graus: float = 0.0
    em_voo: bool = False
    motores_ligados: bool = False
    modo_voo: str = ''
    bateria_pct: float = 100.0
    conectado: bool = True
    posicionamento_visual_ativo: bool = True
    controle_virtual_ativo: bool = False
    acao_perda_sinal: str = 'pousar'


@dataclass
class Estado:
    x_m: float = 0.0
    y_m: float = 0.0
    z_m: float = 0.0
    vx_mps: float = 0.0
    vy_mps: float = 0.0
    vz_mps: float = 0.0
    psi0_graus: float = 0.0
    guinada_local_graus: float = 0.0
    valido: bool = False
    motivo_invalido: str = 'sem telemetria'


@dataclass
class Setpoint:
    ativo: bool = False
    x_m: float = 0.0
    y_m: float = 0.0
    z_m: float = 0.0
    indice: int = -1
    nome: str = ''
    guinada_ativa: bool = False
    guinada_graus: float = 0.0


@dataclass
class ComandoVelocidade:
    vx_mps: float = 0.0
    vy_mps: float = 0.0
    vz_mps: float = 0.0
    taxa_guinada_grausps: float = 0.0
    psi0_graus: float = 0.0


@dataclass
class Evento:
    tipo: str
    estado: str = ''
    vertice: int = -1
    nome_vertice: str = ''
    permanencia_s: float = 0.0
    acao: int = 0
    valor: float = 0.0
    detalhe: str = ''
    tarefa: int = 1
    x_m: float = 0.0
    y_m: float = 0.0
    z_m: float = 0.0


@dataclass
class Falha:
    tipo: int
    reacao: int
    detalhe: str = ''

    @property
    def nome_tipo(self):
        return NOMES_FALHA.get(self.tipo, str(self.tipo))


def normalizar_graus(angulo):
    """Ângulo em (-180, 180]."""
    a = (angulo + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def copiar_campos(origem, destino):
    """Copia os campos homônimos de um dataclass para uma mensagem ROS 2."""
    for nome in origem.__dataclass_fields__:
        if hasattr(destino, nome):
            setattr(destino, nome, getattr(origem, nome))
    return destino


def de_mensagem(classe, msg):
    """Cria o dataclass a partir de uma mensagem ROS 2 com campos homônimos."""
    return classe(**{nome: getattr(msg, nome) for nome in classe.__dataclass_fields__ if hasattr(msg, nome)})
