"""Utilidades comuns aos nós ROS 2: perfis de QoS (seção 5.1 do relatório), relógio e configuração.

Só é importado pelos nós (main); a lógica das tarefas não depende deste módulo.
"""
import time

from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from . import carregador_config

# sob demanda / reliable
QOS_CONFIAVEL = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE)
# /tarefa/ativa: reliable, transient local (quem chega depois recebe a tarefa vigente)
QOS_LATCHED = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
# fluxos a 10 Hz: best effort; só a amostra mais recente importa
QOS_FLUXO = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)


def agora():
    """Relógio monotônico (tempo real) usado por toda a lógica: cronômetro, prazos, watchdogs."""
    return time.monotonic()


def carregar_config(no):
    """Lê o parâmetro `config` (caminho do YAML) e devolve a Configuracao validada."""
    no.declare_parameter('config', carregador_config.caminho_padrao())
    caminho = no.get_parameter('config').get_parameter_value().string_value
    cfg = carregador_config.carregar(caminho)
    no.get_logger().info(f'configuração carregada de {cfg.arquivo}')
    return cfg


def carimbar(no, msg):
    """Preenche msg.stamp com o relógio do nó (tempo do Linux; usado no registro e na medida de latência)."""
    msg.stamp = no.get_clock().now().to_msg()
    return msg


def executar(no):
    """Gira o nó até Ctrl+C e encerra de forma limpa."""
    import rclpy
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
