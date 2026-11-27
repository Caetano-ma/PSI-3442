"""PainelTerminal (nível n): mostra tarefa, estado, vértice ou alvo, cronômetro, distância estimada ao balão (Tarefa 2),
x/y/z, velocidades, bateria e falhas (R08).

Assina /tarefa/status e /falhas; redesenha o terminal a 2 Hz.
Uso: ros2 run psi3442_tarefas painel
"""
from collections import deque
import math

LIMPAR_TELA = '\033[2J\033[H'


def formatar(status, falhas):
    """Texto do painel. `status`: objeto com os campos de StatusTarefa; `falhas`: textos das últimas falhas."""
    if status is None:
        return 'aguardando /tarefa/status do gerenciador...'
    s = status
    vertice = f'{s.nome_vertice} (índice {s.vertice})' if s.vertice >= 0 else '—'
    dentro = 'DENTRO' if s.dentro else 'fora'
    linhas = [
        'PSI3442 — Sistema de Missões Autônomas — DJI Mini 4 Pro',
        '=' * 60,
        f'modo: {s.modo:<14} tarefa: {s.tarefa or "—"}    estado: {s.estado or "—"}',
        f'vértice/alvo: {vertice:<16} permanência: {s.permanencia_s:6.1f} s  [{dentro}]'
        + (f'   d estimada: {s.distancia_alvo_m * 100:5.1f} cm'
           if s.tarefa == 2 and math.isfinite(getattr(s, 'distancia_alvo_m', math.nan)) else ''),
        f'posição  x={s.x_m:+6.2f}  y={s.y_m:+6.2f}  z={s.z_m:+6.2f} m'
        f'   estimativa: {"válida" if s.estado_valido else "INVÁLIDA"}',
        f'velocid. vx={s.vx_mps:+6.2f} vy={s.vy_mps:+6.2f} vz={s.vz_mps:+6.2f} m/s',
        f'bateria: {s.bateria_pct:5.1f} %   ponte: {"conectada" if s.ponte_conectada else "SEM TELEMETRIA"}'
        f'   Tarefa 1 em voo real: {"concluída" if s.tarefa1_concluida_voo_real else "pendente"}',
        f'mensagem: {s.mensagem}',
        f'última falha: {s.ultima_falha or "—"}',
        '-' * 60,
        'falhas recentes:',
    ]
    linhas += [f'  {texto}' for texto in falhas] or ['  —']
    return '\n'.join(linhas)


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import Falha as FalhaMsg, StatusTarefa

    from . import ros_util
    from .tipos import NOMES_REACAO

    class NoPainel(Node):
        def __init__(self):
            super().__init__('painel')
            self.status = None
            self.falhas = deque(maxlen=8)
            self.create_subscription(StatusTarefa, '/tarefa/status', self.ao_status, ros_util.QOS_CONFIAVEL)
            self.create_subscription(FalhaMsg, '/falhas', self.ao_falha, ros_util.QOS_CONFIAVEL)
            self.create_timer(0.5, self.desenhar)

        def ao_status(self, msg):
            self.status = msg

        def ao_falha(self, msg):
            instante = msg.stamp.sec + msg.stamp.nanosec * 1e-9
            self.falhas.appendleft(f'{instante:.1f}  {msg.nome_tipo} ({NOMES_REACAO.get(msg.reacao, msg.reacao)}): '
                                   f'{msg.detalhe}')

        def desenhar(self):
            print(LIMPAR_TELA + formatar(self.status, list(self.falhas)), flush=True)

    rclpy.init(args=args)
    ros_util.executar(NoPainel())


if __name__ == '__main__':
    main()
