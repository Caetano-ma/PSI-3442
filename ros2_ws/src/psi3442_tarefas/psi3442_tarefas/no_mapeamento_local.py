"""MapeamentoLocal (Tarefa 2): mapa grosseiro da sala no ReferencialLocal, relativo ao ponto de decolagem.

- Balões: cada detecção (/alvos) vira um ponto = posição da câmera + distância x direção. Detecções da mesma cor dentro
  de uma janela de associação atualizam o mesmo balão (média ponderada por 1/distância², pois a distância pelo
  diâmetro aparente piora com o afastamento); caixas cortadas pela borda não entram (distância pouco confiável).
  Candidato -> confirmado com `observacoes_min`; destruído quando a Tarefa 2 publica BALAO_DESTRUIDO (fica no mapa,
  mas é ignorado na varredura). A incerteza cresce também com a deriva da estimação de estado.
- Deriva: balões bem observados viram marcos; o resíduo deles realinha o mapa inteiro (_realinhar), e ao destruir
  um balão o centro medido de perto pela Tarefa 2 faz o mesmo (marcar_destruido).
- Obstáculos: grade 2D de ocupação a partir das distâncias medidas em volta da aeronave (/dji/obstaculos).

Assina /alvos, /estado, /dji/obstaculos (sensor_msgs/LaserScan) e /tarefa/evento; publica /mapa a 2 Hz.
"""
from dataclasses import dataclass, field
import math

CANDIDATO, CONFIRMADO, DESTRUIDO = 0, 1, 2
DESLOCAMENTO_CAMERA = (0.10, 0.0, 0.03)       # câmera em relação ao centro da aeronave (frente, esquerda, cima)
DERIVA_MAX_CORRIGIDA_M = 1.0                  # correção de deriva maior que isto indica erro de associação
OBSERVACOES_MARCO = 20                        # balão com mais observações que isto vira marco (posição fixa)
DISTANCIA_MAX_MARCO_M = 2.5                   # só detecções de perto realinham o mapa pelo marco
GANHO_MARCO = 0.05                            # fração do resíduo aplicada ao mapa inteiro a cada detecção


@dataclass
class Balao:
    id: int
    cor: str
    alvo: bool
    x_m: float
    y_m: float
    z_m: float
    peso: float
    soma_quadrados: float = 0.0
    observacoes: int = 1
    situacao: int = CANDIDATO
    t_ultima: float = 0.0
    incerteza_m: float = 0.3

    def posicao(self):
        return self.x_m, self.y_m, self.z_m


def posicao_camera(x, y, z, guinada_local_graus):
    g = math.radians(guinada_local_graus)
    fx, fy, fz = DESLOCAMENTO_CAMERA
    return x + fx * math.cos(g) - fy * math.sin(g), y + fx * math.sin(g) + fy * math.cos(g), z + fz


def ponto_da_deteccao(x, y, z, guinada_local_graus, det):
    cx, cy, cz = posicao_camera(x, y, z, guinada_local_graus)
    az, el = math.radians(det.azimute_graus), math.radians(det.elevacao_graus)
    d = det.distancia_m
    return cx + d * math.cos(el) * math.cos(az), cy + d * math.cos(el) * math.sin(az), cz + d * math.sin(el)


@dataclass
class Grade:
    x0: float
    y0: float
    resolucao: float
    largura: int
    altura: int
    acertos: list = field(default_factory=list)
    livres: list = field(default_factory=list)

    def __post_init__(self):
        self.acertos = [0] * (self.largura * self.altura)
        self.livres = [0] * (self.largura * self.altura)

    def indice(self, x, y):
        i, j = int((x - self.x0) / self.resolucao), int((y - self.y0) / self.resolucao)
        if 0 <= i < self.largura and 0 <= j < self.altura:
            return j * self.largura + i
        return None

    def ocupacao(self):
        valores = []
        for acertos, livres in zip(self.acertos, self.livres):
            if acertos >= 2 and acertos >= 0.3 * livres:
                valores.append(100)
            elif livres or acertos:
                valores.append(0)
            else:
                valores.append(-1)
        return valores

    def ocupado(self, x, y):
        k = self.indice(x, y)
        return k is not None and self.acertos[k] >= 2 and self.acertos[k] >= 0.3 * self.livres[k]


class MapeamentoLocal:
    def __init__(self, cfg_t2, resolucao_m=0.2, margem_grade_m=1.5):
        self.cfg = cfg_t2
        self.baloes = []
        self._proximo_id = 1
        x0, y0 = cfg_t2.volume_x_min_m - margem_grade_m, cfg_t2.volume_y_min_m - margem_grade_m
        largura = int(math.ceil((cfg_t2.volume_x_max_m + margem_grade_m - x0) / resolucao_m))
        altura = int(math.ceil((cfg_t2.volume_y_max_m + margem_grade_m - y0) / resolucao_m))
        self.grade = Grade(x0, y0, resolucao_m, largura, altura)

    # ------------------------------------------------------------------ balões
    def _janela(self, balao, distancia):
        return max(0.45, 3.0 * balao.incerteza_m, 0.15 * distancia)

    def atualizar_deteccoes(self, alvos, agora):
        """`alvos`: objeto com x_m, y_m, z_m, guinada_local_graus e deteccoes (azimute, elevação, distância, cor).
        No solo a referência de guinada (psi0) ainda não foi registrada: detecções abaixo de 0,3 m são ignoradas."""
        if alvos.z_m < 0.3:
            return
        for det in alvos.deteccoes:
            if det.cortada or not math.isfinite(det.distancia_m) or det.distancia_m <= 0:
                continue
            if det.cor not in self.cfg.cores_conhecidas:
                continue
            p = ponto_da_deteccao(alvos.x_m, alvos.y_m, alvos.z_m, alvos.guinada_local_graus, det)
            peso = 1.0 / max(det.distancia_m, 0.3) ** 2
            candidatos = [(math.dist(b.posicao(), p), b) for b in self.baloes if b.cor == det.cor]
            candidatos = [(d, b) for d, b in candidatos if d <= self._janela(b, det.distancia_m)]
            if candidatos:
                b = min(candidatos, key=lambda par: par[0])[1]
                if b.observacoes >= OBSERVACOES_MARCO and det.distancia_m <= DISTANCIA_MAX_MARCO_M:
                    self._realinhar(b, p, agora)
                else:
                    self._fundir(b, p, peso, agora)
            else:
                self.baloes.append(Balao(self._proximo_id, det.cor, det.cor in self.cfg.cores_alvo, *p, peso=peso,
                                         t_ultima=agora, incerteza_m=max(0.1, 0.1 * det.distancia_m)))
                self._proximo_id += 1
        self._unir_duplicados()

    def _fundir(self, b, p, peso, agora):
        total = b.peso + peso
        antigo = b.posicao()
        novo = tuple((b.peso * a + peso * q) / total for a, q in zip(antigo, p))
        b.soma_quadrados += peso * math.dist(p, novo) ** 2 + b.peso * math.dist(antigo, novo) ** 2
        b.x_m, b.y_m, b.z_m = novo
        b.peso = total
        b.observacoes += 1
        b.t_ultima = agora
        b.incerteza_m = max(0.03, math.sqrt(b.soma_quadrados / total))
        if b.situacao == CANDIDATO and b.observacoes >= self.cfg.observacoes_min:
            b.situacao = CONFIRMADO

    def _realinhar(self, marco, p, agora):
        """Balões são estáticos: o resíduo horizontal de um marco bem observado é deriva da posição integrada,
        comum ao mapa inteiro. Desloca todos os balões por uma fração dele (filtro), em vez de mover só o marco."""
        dx, dy = GANHO_MARCO * (p[0] - marco.x_m), GANHO_MARCO * (p[1] - marco.y_m)
        for b in self.baloes:
            b.x_m += dx
            b.y_m += dy
        marco.z_m += GANHO_MARCO * (p[2] - marco.z_m)
        marco.observacoes += 1
        marco.t_ultima = agora

    def _unir_duplicados(self):
        for a in list(self.baloes):
            for b in list(self.baloes):
                if a is b or a not in self.baloes or b not in self.baloes or a.cor != b.cor:
                    continue
                if math.dist(a.posicao(), b.posicao()) < 1.2 * self.cfg.raio_balao_m * 2:
                    manter, sair = (a, b) if a.id < b.id else (b, a)
                    total = manter.peso + sair.peso
                    manter.x_m, manter.y_m, manter.z_m = (
                        (manter.peso * m + sair.peso * s) / total for m, s in zip(manter.posicao(), sair.posicao()))
                    manter.peso, manter.observacoes = total, manter.observacoes + sair.observacoes
                    manter.situacao = max(manter.situacao, sair.situacao)
                    manter.t_ultima = max(manter.t_ultima, sair.t_ultima)
                    self.baloes.remove(sair)

    def marcar_destruido(self, id_balao, centro_medido=None):
        """Marca o balão como destruído. `centro_medido`: centro medido de perto pela Tarefa 2 no referencial estimado
        atual; a diferença horizontal para o mapa é a deriva acumulada da posição integrada, comum a todo o mapa
        (os balões são estáticos), então todos os balões são deslocados por ela. Sem isso, a deriva faria o balão
        destruído reaparecer como outro e ser visitado de novo."""
        for b in self.baloes:
            if b.id == id_balao:
                if centro_medido is not None and all(math.isfinite(c) for c in centro_medido):
                    dx, dy = centro_medido[0] - b.x_m, centro_medido[1] - b.y_m
                    if math.hypot(dx, dy) <= DERIVA_MAX_CORRIGIDA_M:
                        for outro in self.baloes:
                            outro.x_m += dx
                            outro.y_m += dy
                b.situacao = DESTRUIDO
                return True
        return False

    # ------------------------------------------------------------------ obstáculos
    def atualizar_obstaculos(self, x, y, guinada_local_graus, angulo_min, incremento, distancias, alcance_max):
        g = math.radians(guinada_local_graus)
        r = self.grade.resolucao
        for k, d in enumerate(distancias):
            if not math.isfinite(d) or d <= 0:
                continue
            a = g + angulo_min + k * incremento
            c, s = math.cos(a), math.sin(a)
            limite = min(d, alcance_max)
            passo = r
            while passo < limite - r:
                idx = self.grade.indice(x + passo * c, y + passo * s)
                if idx is not None:
                    self.grade.livres[idx] += 1
                passo += r
            if d < alcance_max:
                idx = self.grade.indice(x + d * c, y + d * s)
                if idx is not None:
                    self.grade.acertos[idx] += 1

    def _de_balao(self, x, y):
        """Célula ocupada por um balão já mapeado (o sensor de distâncias também vê os balões; eles são tratados
        pelas margens próprias da Tarefa 2, não como obstáculo fixo)."""
        folga = self.cfg.raio_balao_m + self.grade.resolucao
        return any(math.hypot(x - b.x_m, y - b.y_m) <= folga for b in self.baloes)

    def obstaculo_perto(self, x, y, margem):
        r = self.grade.resolucao
        n = int(math.ceil(margem / r))
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                px, py = x + i * r, y + j * r
                if math.hypot(i * r, j * r) <= margem and self.grade.ocupado(px, py) and not self._de_balao(px, py):
                    return True
        return False


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan
    from psi3442_interfaces.msg import Alvos, BalaoMapa, EstadoEstimado, EventoTarefa, MapaLocal

    from . import ros_util
    from .tipos import Estado, de_mensagem

    class NoMapeamentoLocal(Node):
        def __init__(self):
            super().__init__('mapeamento_local')
            cfg = ros_util.carregar_config(self)
            self.mapa = MapeamentoLocal(cfg.tarefa2)
            self.estado = None
            self.pub = self.create_publisher(MapaLocal, '/mapa', ros_util.QOS_CONFIAVEL)
            self.create_subscription(Alvos, '/alvos', self.ao_alvos, ros_util.QOS_FLUXO)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_subscription(LaserScan, '/dji/obstaculos', self.ao_obstaculos, ros_util.QOS_FLUXO)
            self.create_subscription(EventoTarefa, '/tarefa/evento', self.ao_evento, ros_util.QOS_CONFIAVEL)
            self.create_timer(0.5, self.publicar)

        def ao_estado(self, msg):
            self.estado = de_mensagem(Estado, msg)

        def ao_alvos(self, msg):
            antes = len(self.mapa.baloes)
            self.mapa.atualizar_deteccoes(msg, ros_util.agora())
            for b in self.mapa.baloes[antes:]:
                self.get_logger().info(f'balão {b.id} ({b.cor}) em ({b.x_m:.2f}, {b.y_m:.2f}, {b.z_m:.2f}) m')

        def ao_obstaculos(self, msg):
            e = self.estado
            if e is None or not e.valido or e.z_m < 0.3:
                return
            self.mapa.atualizar_obstaculos(e.x_m, e.y_m, e.guinada_local_graus, msg.angle_min, msg.angle_increment,
                                           msg.ranges, msg.range_max)

        def ao_evento(self, msg):
            if msg.tipo == 'BALAO_DESTRUIDO' and self.mapa.marcar_destruido(int(msg.valor),
                                                                            (msg.x_m, msg.y_m, msg.z_m)):
                self.get_logger().info(f'balão {int(msg.valor)} marcado como destruído')

        def publicar(self):
            g = self.mapa.grade
            ocupacao = g.ocupacao()
            for k, valor in enumerate(ocupacao):            # células de balões não são obstáculo fixo
                if valor == 100 and self.mapa._de_balao(g.x0 + (k % g.largura + 0.5) * g.resolucao,
                                                         g.y0 + (k // g.largura + 0.5) * g.resolucao):
                    ocupacao[k] = 0
            msg = MapaLocal(resolucao_m=g.resolucao, largura=g.largura, altura=g.altura, origem_x_m=g.x0,
                            origem_y_m=g.y0, ocupacao=ocupacao)
            msg.baloes = [BalaoMapa(id=b.id, cor=b.cor, alvo=b.alvo, x_m=b.x_m, y_m=b.y_m, z_m=b.z_m,
                                    incerteza_m=b.incerteza_m, observacoes=min(b.observacoes, 65535),
                                    situacao=b.situacao) for b in self.mapa.baloes]
            self.pub.publish(ros_util.carimbar(self, msg))

    rclpy.init(args=args)
    ros_util.executar(NoMapeamentoLocal())


if __name__ == '__main__':
    main()
