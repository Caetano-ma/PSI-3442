"""ControladorPosicao (nível n) e nó ROS 2 de controle de voo.

Algoritmo: por eixo, v = saturacao(kp * erro, vMax), no ReferencialLocal. Sem guinada (taxa zero).
- setpoint ausente, velho ou inativo (decolagem/pouso automáticos da DJI): nada é publicado; o app ponte, sem
  comando por 0,2 s, envia velocidade zero (watchdog).
- estado inválido ou velho com setpoint ativo: velocidade zero (pairar no lugar).

Assina /setpoint e /estado; publica /dji/cmd_vel a 10 Hz.
"""
from .tipos import ComandoVelocidade


def saturar(valor, limite):
    return max(-limite, min(limite, valor))


class ControladorPosicao:
    def __init__(self, kp=0.8, v_max_horizontal_mps=0.30, v_max_vertical_mps=0.30):
        self.kp = kp
        self.v_max_horizontal_mps = v_max_horizontal_mps
        self.v_max_vertical_mps = v_max_vertical_mps

    def calcular(self, estado, setpoint):
        """Devolve o ComandoVelocidade, ou None se nada deve ser enviado."""
        if setpoint is None or not setpoint.ativo:
            return None
        if estado is None or not estado.valido:
            return ComandoVelocidade(psi0_graus=0.0 if estado is None else estado.psi0_graus)
        return ComandoVelocidade(
            vx_mps=saturar(self.kp * (setpoint.x_m - estado.x_m), self.v_max_horizontal_mps),
            vy_mps=saturar(self.kp * (setpoint.y_m - estado.y_m), self.v_max_horizontal_mps),
            vz_mps=saturar(self.kp * (setpoint.z_m - estado.z_m), self.v_max_vertical_mps),
            psi0_graus=estado.psi0_graus,
        )


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import ComandoVelocidade as ComandoVelocidadeMsg, EstadoEstimado
    from psi3442_interfaces.msg import Setpoint as SetpointMsg

    from . import ros_util
    from .tipos import Estado, Setpoint, copiar_campos, de_mensagem

    class NoControleVoo(Node):
        def __init__(self):
            super().__init__('controle_voo')
            cfg = ros_util.carregar_config(self).controle
            self.cfg = cfg
            self.controlador = ControladorPosicao(cfg.kp, cfg.v_max_horizontal_mps, cfg.v_max_vertical_mps)
            self.estado, self.t_estado = None, None
            self.setpoint, self.t_setpoint = None, None
            self.pub = self.create_publisher(ComandoVelocidadeMsg, '/dji/cmd_vel', ros_util.QOS_FLUXO)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_subscription(SetpointMsg, '/setpoint', self.ao_setpoint, ros_util.QOS_FLUXO)
            self.create_timer(0.1, self.ao_temporizar)

        def ao_estado(self, msg):
            self.estado, self.t_estado = de_mensagem(Estado, msg), ros_util.agora()

        def ao_setpoint(self, msg):
            self.setpoint, self.t_setpoint = de_mensagem(Setpoint, msg), ros_util.agora()

        def ao_temporizar(self):
            agora = ros_util.agora()
            if self.t_setpoint is None or agora - self.t_setpoint > self.cfg.idade_max_setpoint_s:
                return
            estado = self.estado
            if self.t_estado is None or agora - self.t_estado > self.cfg.idade_max_estado_s:
                estado = None
            comando = self.controlador.calcular(estado, self.setpoint)
            if comando is not None:
                self.pub.publish(ros_util.carimbar(self, copiar_campos(comando, ComandoVelocidadeMsg())))

    rclpy.init(args=args)
    ros_util.executar(NoControleVoo())


if __name__ == '__main__':
    main()
