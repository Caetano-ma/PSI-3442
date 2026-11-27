"""Avaliador da Tarefa 2 no Gazebo (R04/R05): usa a VERDADE do simulador, que nunca chega à aplicação.

Assina a odometria verdadeira do Gazebo e /tarefa/evento; lê verdade.yaml (gerado com o mundo). Calcula, a cada
amostra, a distância real d entre a frente das hélices (envelope) e a superfície do balão-alvo mais próximo, e a
folga até os balões não alvo. Publica /avaliador/distancia_m e grava avaliacao.csv; ao fim da tarefa imprime e grava
resumo.yaml: por permanência, d real mín./máx. durante a contagem e se ficou em 0 < d <= 5 cm; colisões; menor folga
a não alvos; cores realmente "destruídas".
"""
import argparse
import csv
import math
import os

import yaml

RAIO_ENVELOPE_FRONTAL_M = 0.149
MEIA_DIAGONAL_M = math.hypot(0.298, 0.373) / 2


def frente(x, y, z, yaw):
    return x + RAIO_ENVELOPE_FRONTAL_M * math.cos(yaw), y + RAIO_ENVELOPE_FRONTAL_M * math.sin(yaw), z


def distancia_superficie(ponto, b):
    return math.dist(ponto, (b['x'], b['y'], b['z'])) - b['raio']


class Avaliacao:
    def __init__(self, baloes):
        self.alvos = [b for b in baloes if b['alvo']]
        self.nao_alvos = [b for b in baloes if not b['alvo']]
        self.contando = False
        self.permanencias = []
        self.folga_min = math.inf
        self.colisoes = 0
        self._em_colisao = False
        self.destruidos = []
        self.ultima = None

    def amostra(self, t, x, y, z, yaw):
        p = frente(x, y, z, yaw)
        d, alvo = min(((distancia_superficie(p, b), b) for b in self.alvos), key=lambda par: par[0],
                      default=(math.inf, None))
        folga = min((math.dist((x, y, z), (b['x'], b['y'], b['z'])) - b['raio'] - MEIA_DIAGONAL_M
                     for b in self.nao_alvos), default=math.inf)
        self.folga_min = min(self.folga_min, folga)
        colidiu = d <= 0 or folga <= 0
        if colidiu and not self._em_colisao:
            self.colisoes += 1
        self._em_colisao = colidiu
        if self.contando and self.permanencias:
            atual = self.permanencias[-1]
            atual['d_min_m'] = min(atual['d_min_m'], d)
            atual['d_max_m'] = max(atual['d_max_m'], d)
            atual['amostras'] += 1
        self.ultima = (t, d, alvo['cor'] if alvo else '', folga)
        return self.ultima

    def evento(self, t, tipo, nome, permanencia_s, x, y, z):
        if tipo == 'PERMANENCIA_INICIADA':
            self.contando = True
            self.permanencias.append({'alvo': nome, 'inicio_s': round(t, 2), 'd_min_m': math.inf, 'd_max_m': -math.inf,
                                      'amostras': 0})
        elif tipo in ('PERMANENCIA_INTERROMPIDA', 'PERMANENCIA_CONCLUIDA') and self.contando:
            self.contando = False
            atual = self.permanencias[-1]
            atual.update(fim_s=round(t, 2), duracao_s=round(permanencia_s, 2), resultado=tipo.split('_')[1].lower(),
                         dentro_da_faixa=bool(0 < atual['d_min_m'] and atual['d_max_m'] <= 0.05))
        elif tipo == 'BALAO_DESTRUIDO':
            real = min(self.alvos + self.nao_alvos, key=lambda b: math.dist((x, y, z), (b['x'], b['y'], b['z'])),
                       default=None)
            self.destruidos.append({'rotulo': nome, 'cor_real': real['cor'] if real else '?',
                                    'erro_centro_m': round(math.dist((x, y, z), (real['x'], real['y'], real['z'])), 3)
                                    if real else None})

    def resumo(self):
        def limpo(v):
            return round(v, 4) if isinstance(v, float) and math.isfinite(v) else v
        return {'permanencias': [{k: limpo(v) for k, v in p.items()} for p in self.permanencias],
                'destruidos': self.destruidos, 'colisoes': self.colisoes,
                'folga_min_nao_alvo_m': limpo(self.folga_min),
                'alvos_reais': [b['cor'] for b in self.alvos],
                'todos_os_alvos_destruidos': sorted(d['cor_real'] for d in self.destruidos)
                == sorted(b['cor'] for b in self.alvos)}


def main(args=None):
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from std_msgs.msg import Float64
    from psi3442_interfaces.msg import EventoTarefa

    ap = argparse.ArgumentParser()
    ap.add_argument('--verdade', default=os.path.expanduser('~/.ros/psi3442_sala_t2/verdade.yaml'))
    ap.add_argument('--saida', default=os.path.expanduser('~/.ros/psi3442_sala_t2'))
    a, _ = ap.parse_known_args()
    with open(a.verdade) as f:
        verdade = yaml.safe_load(f)
    avaliacao = Avaliacao(verdade['baloes'])
    os.makedirs(a.saida, exist_ok=True)
    arquivo = open(os.path.join(a.saida, 'avaliacao.csv'), 'w', newline='')
    escritor = csv.writer(arquivo)
    escritor.writerow(['t_sim_s', 'x_m', 'y_m', 'z_m', 'guinada_graus', 'd_real_alvo_m', 'cor_alvo',
                       'folga_nao_alvo_m', 'contando'])

    rclpy.init(args=args)
    no = Node('avaliador_t2')
    pub = no.create_publisher(Float64, '/avaliador/distancia_m', 10)
    estado = {'t': 0.0, 't_csv': -1.0}

    def ao_odometria(msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        estado['t'] = t
        _, d, cor, folga = avaliacao.amostra(t, p.x, p.y, p.z, yaw)
        if t - estado['t_csv'] >= 0.1:
            estado['t_csv'] = t
            pub.publish(Float64(data=float(d)))
            escritor.writerow([f'{t:.2f}', f'{p.x:.4f}', f'{p.y:.4f}', f'{p.z:.4f}', f'{math.degrees(yaw):.2f}',
                               f'{d:.4f}', cor, f'{folga:.3f}', int(avaliacao.contando)])

    def ao_evento(msg):
        if msg.tarefa != 2:
            return
        avaliacao.evento(estado['t'], msg.tipo, msg.nome_vertice, msg.permanencia_s, msg.x_m, msg.y_m, msg.z_m)
        if msg.tipo in ('PERMANENCIA_CONCLUIDA', 'PERMANENCIA_INTERROMPIDA') and avaliacao.permanencias:
            p = avaliacao.permanencias[-1]
            no.get_logger().info(f"[AVALIADOR] {p['alvo']}: {p.get('resultado')} após {p.get('duracao_s')} s; "
                                 f"d real {p['d_min_m'] * 100:.1f}..{p['d_max_m'] * 100:.1f} cm")
        if msg.tipo in ('TAREFA_CONCLUIDA', 'TAREFA_ABORTADA'):
            resumo = avaliacao.resumo()
            resumo['resultado'] = msg.tipo
            with open(os.path.join(a.saida, 'resumo.yaml'), 'w') as f:
                yaml.safe_dump(resumo, f, allow_unicode=True, sort_keys=False)
            arquivo.flush()
            no.get_logger().info(f'[AVALIADOR] resumo: {resumo}')

    no.create_subscription(Odometry, '/gazebo/mini4pro/odometria', ao_odometria, 50)
    no.create_subscription(EventoTarefa, '/tarefa/evento', ao_evento, 50)
    try:
        rclpy.spin(no)
    except (KeyboardInterrupt, Exception):
        pass
    finally:
        arquivo.close()


if __name__ == '__main__':
    main()
