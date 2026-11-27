"""ConversorMensagens (nível n) e nó ROS 2 ponte ROS 2 <-> app ponte DJI.

JSON <-> mensagens psi3442_interfaces: publica /dji/telemetria, /dji/obstaculos (sensor_msgs/LaserScan) e
/dji/camera (sensor_msgs/Image, do canal de vídeo na porta + 1); assina /dji/cmd_vel e /dji/acao.
- cmd_vel: o último comando é reenviado a 20 Hz enquanto tiver no máximo `IDADE_MAX_CMD_S`; depois disso nada é
  enviado e o watchdog do app ponte zera a velocidade em 0,2 s.
- heartbeat a 1 Hz; sem heartbeat por 2 s o app ponte comanda pouso automático (perdaPonte).
- mensagem "erro" do app (comando rejeitado pelo SDK) vira /falhas comandoRejeitado: em voo, término seguro;
  no solo, volta a ocioso.

Mensagens trocadas (uma por linha):
  app -> ROS  {"tipo":"telemetria","instante_s":..,"v_norte_mps":..,"v_leste_mps":..,"v_baixo_mps":..,
               "altitude_m":..,"altura_tof_m":..|null,"guinada_graus":..,"em_voo":..,"motores_ligados":..,
               "modo_voo":"..","bateria_pct":..,"conectado":..,"posicionamento_visual_ativo":..,
               "controle_virtual_ativo":..,"acao_perda_sinal":"pousar"}
              {"tipo":"heartbeat","instante_s":..}
              {"tipo":"erro","comando":"decolar","mensagem":".."}
              {"tipo":"obstaculos","instante_s":..,"passo_graus":..,"distancias_m":[..|null]}   (horário, do nariz)
  app -> ROS, canal de vídeo (porta + 1): {"tipo":"quadro","instante_s":..,"largura":..,"altura":..,
              "formato":"jpeg","bytes":N,"pitch_gimbal_graus":..}\n + N bytes de JPEG (só o quadro mais recente)
  ROS -> app  {"tipo":"cmd_vel","vx_mps":..,"vy_mps":..,"vz_mps":..,"taxa_guinada_grausps":..,"psi0_graus":..}
              {"tipo":"acao","comando":"decolar|pousar|habilitar_controle_virtual|desabilitar_controle_virtual|parar_e_pairar"}
              {"tipo":"heartbeat","instante_s":..}
"""
import math

from .tipos import ACAO_POR_NOME, NOMES_ACAO, Telemetria

IDADE_MAX_CMD_S = 0.3
CAMPOS_TELEMETRIA = {
    'instante_s': 'instante_android_s', 'v_norte_mps': 'v_norte_mps', 'v_leste_mps': 'v_leste_mps',
    'v_baixo_mps': 'v_baixo_mps', 'altitude_m': 'altitude_m', 'altura_tof_m': 'altura_tof_m',
    'guinada_graus': 'guinada_graus', 'em_voo': 'em_voo', 'motores_ligados': 'motores_ligados',
    'modo_voo': 'modo_voo', 'bateria_pct': 'bateria_pct', 'conectado': 'conectado',
    'posicionamento_visual_ativo': 'posicionamento_visual_ativo',
    'controle_virtual_ativo': 'controle_virtual_ativo', 'acao_perda_sinal': 'acao_perda_sinal',
}
BOOLEANOS = ('em_voo', 'motores_ligados', 'conectado', 'posicionamento_visual_ativo', 'controle_virtual_ativo')
TEXTOS = ('modo_voo', 'acao_perda_sinal')


def telemetria_de_json(mensagem):
    """Converte a mensagem JSON do app ponte em Telemetria (campos ausentes ficam com o padrão)."""
    valores = {}
    for chave_json, campo in CAMPOS_TELEMETRIA.items():
        if chave_json not in mensagem:
            continue
        valor = mensagem[chave_json]
        if campo in BOOLEANOS:
            valores[campo] = bool(valor)
        elif campo in TEXTOS:
            valores[campo] = str(valor)
        else:
            valores[campo] = math.nan if valor is None else float(valor)
    return Telemetria(**valores)


def json_de_telemetria(tel):
    """Inversa de telemetria_de_json (usada pelo simulador)."""
    mensagem = {'tipo': 'telemetria'}
    for chave_json, campo in CAMPOS_TELEMETRIA.items():
        valor = getattr(tel, campo)
        mensagem[chave_json] = None if isinstance(valor, float) and not math.isfinite(valor) else valor
    return mensagem


def scan_de_obstaculos(mensagem, alcance_max_m=40.0):
    """obstaculos (horário a partir do nariz) -> campos de um LaserScan (anti-horário, radianos): o ângulo k é
    -k * passo. Sem leitura = +inf (nada até o alcance)."""
    passo = math.radians(float(mensagem['passo_graus']))
    distancias = [math.inf if d is None or not math.isfinite(float(d)) else float(d)
                  for d in mensagem['distancias_m']]
    return {'angle_min': 0.0, 'angle_max': -passo * (len(distancias) - 1), 'angle_increment': -passo,
            'range_min': 0.05, 'range_max': alcance_max_m, 'ranges': distancias}


def json_de_cmd_vel(cmd):
    return {'tipo': 'cmd_vel', 'vx_mps': cmd.vx_mps, 'vy_mps': cmd.vy_mps, 'vz_mps': cmd.vz_mps,
            'taxa_guinada_grausps': cmd.taxa_guinada_grausps, 'psi0_graus': cmd.psi0_graus}


def json_de_acao(tipo):
    if tipo not in NOMES_ACAO:
        raise ValueError(f'ação desconhecida: {tipo}')
    return {'tipo': 'acao', 'comando': NOMES_ACAO[tipo]}


def acao_de_json(mensagem):
    return ACAO_POR_NOME[mensagem['comando']]


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Image, LaserScan
    from psi3442_interfaces.msg import ComandoDiscreto, ComandoVelocidade as ComandoVelocidadeMsg
    from psi3442_interfaces.msg import Falha as FalhaMsg, Telemetria as TelemetriaMsg

    from . import ros_util
    from .cliente_socket_ponte import ClienteSocketPonte, ClienteVideo
    from .tipos import (COMANDO_REJEITADO, NOMES_FALHA, TERMINO_SEGURO, VOLTAR_OCIOSO, ComandoVelocidade,
                        copiar_campos, de_mensagem)

    class NoPonteDji(Node):
        def __init__(self):
            super().__init__('ponte_dji')
            cfg = ros_util.carregar_config(self).ponte
            self.declare_parameter('host', cfg.host)
            self.declare_parameter('porta', cfg.porta)
            self.declare_parameter('video', True)      # false no Gazebo: câmera e distâncias vêm do ros_gz_bridge
            host = self.get_parameter('host').get_parameter_value().string_value
            porta = self.get_parameter('porta').get_parameter_value().integer_value
            self.cmd, self.t_cmd, self.em_voo = None, None, False
            self.pub_tel = self.create_publisher(TelemetriaMsg, '/dji/telemetria', ros_util.QOS_FLUXO)
            self.pub_falha = self.create_publisher(FalhaMsg, '/falhas', ros_util.QOS_CONFIAVEL)
            self.create_subscription(ComandoVelocidadeMsg, '/dji/cmd_vel', self.ao_cmd_vel, ros_util.QOS_FLUXO)
            self.create_subscription(ComandoDiscreto, '/dji/acao', self.ao_acao, ros_util.QOS_CONFIAVEL)
            self.pub_obstaculos = self.create_publisher(LaserScan, '/dji/obstaculos', ros_util.QOS_FLUXO)
            self.pub_camera = self.create_publisher(Image, '/dji/camera', ros_util.QOS_FLUXO)
            self.video = None
            if self.get_parameter('video').get_parameter_value().bool_value:
                self.video = ClienteVideo(host, porta + 1, self.ao_quadro,
                                          lambda texto: self.get_logger().warn(f'vídeo: {texto}'))
                self.video.iniciar()
                self.get_logger().info(f'canal de vídeo em {host}:{porta + 1}')
            self.aviso_gimbal = 0.0
            self.cliente = ClienteSocketPonte(host, porta, self.ao_receber, self.ao_mudar_conexao,
                                              lambda texto: self.get_logger().warn(f'socket: {texto}'))
            self.create_timer(1.0 / cfg.taxa_cmd_vel_hz, self.enviar_cmd_vel)
            self.create_timer(1.0 / cfg.taxa_heartbeat_hz, self.enviar_heartbeat)
            self.get_logger().info(f'conectando ao app ponte em {host}:{porta}')
            self.cliente.iniciar()

        def ao_mudar_conexao(self, conectado):
            self.get_logger().info('app ponte conectado' if conectado else 'app ponte desconectado')

        def ao_receber(self, mensagem):
            tipo = mensagem['tipo']
            if tipo == 'telemetria':
                try:
                    tel = telemetria_de_json(mensagem)
                except (TypeError, ValueError) as erro:
                    self.get_logger().warn(f'telemetria inválida: {erro}')
                    return
                self.em_voo = tel.em_voo or tel.motores_ligados
                self.pub_tel.publish(ros_util.carimbar(self, copiar_campos(tel, TelemetriaMsg())))
            elif tipo == 'obstaculos':
                try:
                    campos = scan_de_obstaculos(mensagem)
                except (KeyError, TypeError, ValueError) as erro:
                    self.get_logger().warn(f'obstáculos inválidos: {erro}')
                    return
                scan = LaserScan(**{k: v for k, v in campos.items() if k != 'ranges'})
                scan.ranges = campos['ranges']
                scan.header.frame_id = 'mini4pro'
                scan.header.stamp = self.get_clock().now().to_msg()
                self.pub_obstaculos.publish(scan)
            elif tipo == 'erro':
                reacao = TERMINO_SEGURO if self.em_voo else VOLTAR_OCIOSO
                detalhe = f"{mensagem.get('comando', '?')}: {mensagem.get('mensagem', '')}"
                falha = FalhaMsg(tipo=COMANDO_REJEITADO, nome_tipo=NOMES_FALHA[COMANDO_REJEITADO],
                                 reacao=reacao, detalhe=detalhe)
                self.pub_falha.publish(ros_util.carimbar(self, falha))
                self.get_logger().error(f'comando rejeitado pelo SDK: {detalhe}')

        def ao_quadro(self, cabecalho, jpeg):
            import cv2
            import numpy as np

            imagem = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if imagem is None:
                self.get_logger().warn('quadro JPEG inválido')
                return
            pitch = cabecalho.get('pitch_gimbal_graus')
            if pitch is not None and math.isfinite(pitch) and abs(pitch) > 3.0 and ros_util.agora() - self.aviso_gimbal > 5:
                self.aviso_gimbal = ros_util.agora()
                self.get_logger().warn(f'gimbal com pitch {pitch:.1f}°: a visão supõe câmera nivelada')
            msg = Image(height=imagem.shape[0], width=imagem.shape[1], encoding='bgr8', is_bigendian=0,
                        step=imagem.shape[1] * 3, data=imagem.tobytes())
            msg.header.frame_id = 'camera'
            msg.header.stamp = self.get_clock().now().to_msg()
            self.pub_camera.publish(msg)

        def ao_cmd_vel(self, msg):
            self.cmd, self.t_cmd = de_mensagem(ComandoVelocidade, msg), ros_util.agora()

        def enviar_cmd_vel(self):
            if self.t_cmd is not None and ros_util.agora() - self.t_cmd <= IDADE_MAX_CMD_S:
                self.cliente.enviar(json_de_cmd_vel(self.cmd))

        def enviar_heartbeat(self):
            self.cliente.enviar({'tipo': 'heartbeat', 'instante_s': ros_util.agora()})

        def ao_acao(self, msg):
            if not self.cliente.enviar(json_de_acao(msg.tipo)):
                self.get_logger().error(f'ação {NOMES_ACAO.get(msg.tipo)} não enviada: app ponte desconectado')

        def destroy_node(self):
            self.cliente.parar()
            if self.video is not None:
                self.video.parar()
            return super().destroy_node()

    rclpy.init(args=args)
    ros_util.executar(NoPonteDji())


if __name__ == '__main__':
    main()
