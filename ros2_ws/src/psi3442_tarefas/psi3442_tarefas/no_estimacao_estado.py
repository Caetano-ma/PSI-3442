"""EstimadorEstado (nível n) e nó ROS 2 de estimação de estado.

Algoritmo: x, y por integração trapezoidal das velocidades norte/leste do posicionamento visual da DJI, a partir
de A, convertidas ao ReferencialLocal com psi0; z pela altura ToF (reserva: altitude relativa).
    x =  N cos(psi0) + E sin(psi0);   y = N sin(psi0) - E cos(psi0);   vz = -vBaixo.
Origem e psi0: registrados na borda de subida de motores_ligados (partida para a decolagem em A, nariz para B).
Com a aeronave no chão e motores desligados não há integração (só ruído).
Estado inválido se a amostra estiver velha, a aeronave desconectada ou o posicionamento visual inativo em voo.
A deriva da integração é o principal risco (H5): validar com medição externa (T02).

Assina /dji/telemetria; publica /estado a cada amostra e, se a telemetria parar, a 10 Hz com valido = false.
"""
import math

from .tipos import Estado


def local_de_solo(v_norte, v_leste, psi0_graus):
    """Converte (norte, leste) para (x, y) do ReferencialLocal."""
    psi0 = math.radians(psi0_graus)
    return (v_norte * math.cos(psi0) + v_leste * math.sin(psi0),
            v_norte * math.sin(psi0) - v_leste * math.cos(psi0))


def solo_de_local(vx, vy, psi0_graus):
    """Inversa de local_de_solo: (x, y) do ReferencialLocal para (norte, leste)."""
    psi0 = math.radians(psi0_graus)
    return (vx * math.cos(psi0) + vy * math.sin(psi0),
            vx * math.sin(psi0) - vy * math.cos(psi0))


class EstimadorEstado:
    def __init__(self, idade_max_amostra_s=0.30, altura_tof_max_m=10.0):
        self.idade_max_amostra_s = idade_max_amostra_s
        self.altura_tof_max_m = altura_tof_max_m
        self._motores_antes = False
        self._ultima_recepcao_s = None
        self.reiniciar(0.0)

    def reiniciar(self, psi0_graus):
        self.psi0_graus = psi0_graus
        self.x_m = 0.0
        self.y_m = 0.0
        self._anterior = None          # (instante_s, vx, vy)
        self.estado = Estado(psi0_graus=psi0_graus)

    def _altura(self, tel):
        tof = tel.altura_tof_m
        if tof is not None and math.isfinite(tof) and 0.0 <= tof <= self.altura_tof_max_m:
            return tof, ''
        if math.isfinite(tel.altitude_m):
            return tel.altitude_m, ''
        return math.nan, 'altura indisponível'

    def atualizar(self, tel, recepcao_s):
        """Processa uma amostra de telemetria recebida no instante `recepcao_s` (relógio monotônico)."""
        self._ultima_recepcao_s = recepcao_s
        instante = tel.instante_android_s if tel.instante_android_s > 0 else recepcao_s

        if tel.motores_ligados and not self._motores_antes:
            self.reiniciar(tel.guinada_graus)
        self._motores_antes = tel.motores_ligados

        vx, vy = local_de_solo(tel.v_norte_mps, tel.v_leste_mps, self.psi0_graus)
        vz = -tel.v_baixo_mps
        motivo = ''

        integrando = tel.motores_ligados or tel.em_voo
        if self._anterior is not None and integrando:
            t0, vx0, vy0 = self._anterior
            dt = instante - t0
            if dt <= 0:
                motivo = 'instante repetido ou fora de ordem'
            else:
                self.x_m += 0.5 * (vx0 + vx) * dt
                self.y_m += 0.5 * (vy0 + vy) * dt
                if dt > self.idade_max_amostra_s:
                    motivo = f'intervalo entre amostras de {dt:.2f} s'
        if self._anterior is None or instante > self._anterior[0]:
            self._anterior = (instante, vx, vy)

        z, motivo_z = self._altura(tel)
        motivo = motivo or motivo_z
        if not tel.conectado:
            motivo = 'aeronave desconectada'
        elif tel.em_voo and not tel.posicionamento_visual_ativo:
            motivo = 'posicionamento visual inativo'

        self.estado = Estado(x_m=self.x_m, y_m=self.y_m, z_m=z, vx_mps=vx, vy_mps=vy, vz_mps=vz,
                             psi0_graus=self.psi0_graus, valido=(motivo == ''), motivo_invalido=motivo)
        return self.estado

    def verificar_idade(self, agora_s):
        """Marca o estado como inválido se a última amostra estiver velha; devolve True se marcou."""
        if self._ultima_recepcao_s is None:
            return True
        if agora_s - self._ultima_recepcao_s > self.idade_max_amostra_s:
            e = self.estado
            self.estado = Estado(x_m=e.x_m, y_m=e.y_m, z_m=e.z_m, vx_mps=e.vx_mps, vy_mps=e.vy_mps,
                                 vz_mps=e.vz_mps, psi0_graus=e.psi0_graus, valido=False,
                                 motivo_invalido='telemetria velha')
            return True
        return False


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import EstadoEstimado, Telemetria as TelemetriaMsg

    from . import ros_util
    from .tipos import Telemetria, copiar_campos, de_mensagem

    class NoEstimacaoEstado(Node):
        def __init__(self):
            super().__init__('estimacao_estado')
            cfg = ros_util.carregar_config(self)
            self.estimador = EstimadorEstado(cfg.estimacao.idade_max_amostra_s, cfg.estimacao.altura_tof_max_m)
            self.pub = self.create_publisher(EstadoEstimado, '/estado', ros_util.QOS_FLUXO)
            self.create_subscription(TelemetriaMsg, '/dji/telemetria', self.ao_receber, ros_util.QOS_FLUXO)
            self.create_timer(0.1, self.ao_temporizar)

        def publicar(self, estado):
            self.pub.publish(ros_util.carimbar(self, copiar_campos(estado, EstadoEstimado())))

        def ao_receber(self, msg):
            self.publicar(self.estimador.atualizar(de_mensagem(Telemetria, msg), ros_util.agora()))

        def ao_temporizar(self):
            if self.estimador.verificar_idade(ros_util.agora()):
                self.publicar(self.estimador.estado)

    rclpy.init(args=args)
    ros_util.executar(NoEstimacaoEstado())


if __name__ == '__main__':
    main()
