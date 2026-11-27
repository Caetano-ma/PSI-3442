"""App ponte simulado sobre o Gazebo: substitui app ponte + SDK + aeronave na simulação da Tarefa 1.

Fala com o nó `ponte_dji` pelo mesmo ContratoSocketPonte (TCP 5760, JSON por linha) que o app Kotlin usará;
a cadeia ROS 2 (gerenciador, Tarefa 1, estimação, controle, supervisão) roda sem nenhuma mudança.
- Comportamento do app/firmware (decolagem e pouso automáticos, watchdog de 0,2 s, pouso após 2 s sem heartbeat,
  resposta de 1ª ordem da velocidade) vem do DroneCinematico de psi3442_tarefas.
- O movimento é executado no Gazebo: a velocidade resultante vai para o VelocityControl do modelo `mini4pro`
  (no referencial do corpo) e a telemetria é medida na odometria do Gazebo (posição derivada no tempo de
  simulação), com o instante da amostra em tempo de simulação.
- Mundo ENU do Gazebo = ReferencialLocal (x para B, y para D). A "bússola" simulada põe o nariz (+x) a leste:
  norte = y, leste = x, baixo = -z, guinada = 90° - yaw.
"""
import math
import threading

from psi3442_tarefas.simulador_cinematico import DroneCinematico, ParametrosSimulacao, ServidorSimulado

ALFA_FILTRO = 0.5            # filtro passa-baixas da velocidade derivada da posição


def guinada_bussola(yaw_enu_rad):
    """Yaw ENU (rad, anti-horário a partir de leste) -> guinada da bússola (graus, horário a partir do norte)."""
    graus = 90.0 - math.degrees(yaw_enu_rad)
    return (graus + 180.0) % 360.0 - 180.0


def yaw_de_quaternio(x, y, z, w):
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def mundo_para_corpo(vx, vy, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return c * vx + s * vy, -s * vx + c * vy


class DroneGazebo(DroneCinematico):
    def __init__(self, parametros, enviar_velocidade_corpo):
        super().__init__(parametros)
        self.enviar_velocidade_corpo = enviar_velocidade_corpo
        self._trava = threading.Lock()
        self.pose = None                     # (t_sim, x, y, z, yaw)
        self.v_medida = (0.0, 0.0, 0.0)      # norte, leste, baixo

    def ao_odometria(self, t_sim, x, y, z, yaw):
        with self._trava:
            if self.pose is not None:
                t0, x0, y0, z0, _ = self.pose
                dt = t_sim - t0
                if dt <= 0:
                    return
                bruta = ((y - y0) / dt, (x - x0) / dt, -(z - z0) / dt)
                self.v_medida = tuple(ALFA_FILTRO * b + (1 - ALFA_FILTRO) * a
                                      for a, b in zip(self.v_medida, bruta))
            self.pose = (t_sim, x, y, z, yaw)
            self.norte, self.leste, self.altura = y, x, z
            self.guinada = guinada_bussola(yaw)

    def _mover(self, dt):
        """Envia ao Gazebo a velocidade de resposta (norte/leste/baixo -> mundo -> corpo)."""
        if self.motores:
            self.bateria = max(0.0, self.bateria - self.p.consumo_pct_por_s * dt)
            vx_mundo, vy_mundo, vz_mundo = self.v_leste, self.v_norte, -self.v_baixo
        else:
            vx_mundo = vy_mundo = vz_mundo = 0.0
        yaw = self.pose[4] if self.pose is not None else 0.0
        vx, vy = mundo_para_corpo(vx_mundo, vy_mundo, yaw)
        # taxa de guinada da DJI é horária (graus/s); no Gazebo, anti-horária (rad/s)
        wz = -math.radians(self.taxa_guinada) if self.motores else 0.0
        self.enviar_velocidade_corpo(vx, vy, vz_mundo, wz)
        if self.pose is not None:
            with self._trava:
                self.norte, self.leste, self.altura = self.pose[2], self.pose[1], self.pose[3]

    def velocidades_medidas(self):
        return self.v_medida if self.motores else (0.0, 0.0, 0.0)

    def instante_medida(self, agora):
        return self.pose[0] if self.pose is not None else agora


def main(args=None):
    import argparse
    import shlex
    import sys

    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rclpy.node import Node

    parser = argparse.ArgumentParser(description='App ponte simulado no Gazebo (PSI3442).')
    parser.add_argument('--porta', type=int, default=5760)
    parser.add_argument('--bateria-inicial', type=float, default=80.0)
    parser.add_argument('--ruido', type=float, default=0.01, help='ruído da velocidade medida (m/s)')
    parser.add_argument('--vies-norte', type=float, default=0.0, help='viés (deriva) da velocidade norte (m/s)')
    parser.add_argument('--vies-leste', type=float, default=0.0)
    parser.add_argument('--semente', type=int, default=1)
    # o launch passa "app_args" como um único argumento (possivelmente vazio): separa por espaços
    argv = [parte for arg in (sys.argv[1:] if args is None else args) for parte in shlex.split(arg)]
    if '--ros-args' in argv:
        argv = argv[:argv.index('--ros-args')]
    opcoes = parser.parse_args(argv)

    rclpy.init()
    no = Node('app_ponte_gazebo')
    pub = no.create_publisher(Twist, '/gazebo/mini4pro/cmd_vel', 10)

    def enviar(vx, vy, vz, wz=0.0):
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.linear.z = float(vx), float(vy), float(vz)
        msg.angular.z = float(wz)
        pub.publish(msg)

    parametros = ParametrosSimulacao(
        altura_toque_m=0.01, bateria_inicial_pct=opcoes.bateria_inicial, ruido_velocidade_mps=opcoes.ruido,
        vies_norte_mps=opcoes.vies_norte, vies_leste_mps=opcoes.vies_leste, semente=opcoes.semente)
    drone = DroneGazebo(parametros, enviar)

    def ao_odometria(msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        drone.ao_odometria(t, p.x, p.y, p.z, yaw_de_quaternio(q.x, q.y, q.z, q.w))

    no.create_subscription(Odometry, '/gazebo/mini4pro/odometria', ao_odometria, 10)
    threading.Thread(target=rclpy.spin, args=(no,), daemon=True).start()
    servidor = ServidorSimulado(drone, '127.0.0.1', opcoes.porta,
                                log=lambda texto: no.get_logger().info(texto))
    try:
        servidor.executar()
    except KeyboardInterrupt:
        pass
    finally:
        enviar(0.0, 0.0, 0.0)


if __name__ == '__main__':
    main()
