"""Visão computacional (Tarefa 2, R02): detecta e classifica balões por cor nos quadros da câmera do drone.

- DetectorYolo: modelo YOLOv8 nano treinado com imagens sintéticas (ferramentas/treinar_yolo.py), exportado em ONNX e
  executado pelo ONNX Runtime (ou, sem ele, pelo dnn do OpenCV >= 4.7; o 4.6 do Ubuntu 24.04 não aceita a cabeça do
  YOLOv8). Sem PyTorch em tempo de voo. Uma classe por cor.
- GeometriaCamera: câmera pinhole com o campo de visão horizontal do Mini 4 Pro (a verificar). A direção vem do
  centro da caixa; a distância, da LARGURA aparente e do raio horizontal nominal do balão (a altura da caixa inclui o
  alongamento do balão e o nó). Pouco confiável quando a caixa toca a borda da imagem.
- cor_central: a curta distância o balão ocupa a imagem inteira e o detector não o enquadra; a confirmação passa a
  ser a cor dominante no centro da imagem (limiares HSV).
- Proximidade: de perto, o balão da cor central ainda mostra as duas bordas laterais (até ~2 cm do envelope, com o
  campo de visão nominal). Entre as linhas que cruzam a coluna central, a de trecho MAIS LARGO passa pelo centro do
  balão: sua largura angular dá a distância câmera -> centro (precisão de milímetros), as bordas dão o azimute e a
  linha dá a elevação. É o que mantém 0 < d <= 5 cm por 60 s apesar da deriva da posição integrada (R04). Se o trecho
  toca a borda da imagem, a largura vista é uma corda menor que o diâmetro: a distância calculada é só um limite
  SUPERIOR (publicada com sinal negativo).

Assina /dji/camera (sensor_msgs/Image) e /estado; publica /alvos (no máximo `taxa_max_hz`).
"""
from dataclasses import dataclass
import math

import numpy as np

# faixas HSV do OpenCV (H em 0..180): (h_min, h_max) — vermelho dá a volta no 0
FAIXAS_HSV = {
    'vermelho': ((0, 10), (170, 180)),
    'amarelo': ((20, 35),),
    'verde': ((40, 85),),
    'azul': ((95, 130),),
    'roxo': ((131, 160),),
}
S_MIN, V_MIN = 90, 50


@dataclass
class Deteccao:
    cor: str
    confianca: float
    u: int
    v: int
    largura_px: int
    altura_px: int
    azimute_graus: float = 0.0
    elevacao_graus: float = 0.0
    distancia_m: float = math.nan
    cortada: bool = False


class GeometriaCamera:
    def __init__(self, hfov_graus, largura_px, altura_px, raio_balao_m):
        self.largura, self.altura = largura_px, altura_px
        self.f = (largura_px / 2.0) / math.tan(math.radians(hfov_graus) / 2.0)
        self.raio_balao_m = raio_balao_m

    def completar(self, det, guinada_local_graus, margem_px=3):
        """Preenche azimute (ReferencialLocal), elevação, distância e se a caixa está cortada pela borda."""
        x0, y0 = det.u - det.largura_px / 2.0, det.v - det.altura_px / 2.0
        x1, y1 = det.u + det.largura_px / 2.0, det.v + det.altura_px / 2.0
        det.cortada = (x0 <= margem_px or y0 <= margem_px or x1 >= self.largura - margem_px
                       or y1 >= self.altura - margem_px)
        az_rel = math.degrees(math.atan2(self.largura / 2.0 - det.u, self.f))      # esquerda positiva
        det.azimute_graus = (guinada_local_graus + az_rel + 180.0) % 360.0 - 180.0
        # elevação do raio (f, du, dv) em relação ao plano horizontal: não é atan(dv / f) fora do eixo óptico
        det.elevacao_graus = math.degrees(math.atan2(self.altura / 2.0 - det.v, math.hypot(self.f, self.largura / 2.0 - det.u)))
        # raio angular pela largura (a altura inclui alongamento e nó); se a largura está cortada, pela altura
        cortada_h = x0 <= margem_px or x1 >= self.largura - margem_px
        r_px = (max(det.largura_px, det.altura_px) if cortada_h else det.largura_px) / 2.0
        alfa = math.atan2(r_px, self.f)
        det.distancia_m = self.raio_balao_m / math.sin(alfa) if alfa > 0 else math.nan
        return det

    def proximidade(self, u0, u1, guinada_local_graus):
        """Bordas esquerda/direita (px) do balão na linha do centro -> (distância câmera -> centro, azimute local)."""
        a0 = math.atan2(self.largura / 2.0 - u0, self.f)
        a1 = math.atan2(self.largura / 2.0 - u1, self.f)
        meia = abs(a0 - a1) / 2.0
        if meia <= 0:
            return math.nan, math.nan
        azimute = (guinada_local_graus + math.degrees((a0 + a1) / 2.0) + 180.0) % 360.0 - 180.0
        return self.raio_balao_m / math.sin(meia), azimute

    def elevacao(self, v, u=None):
        """Elevação (graus) do raio que passa pela linha v (e coluna u; padrão: centro)."""
        du = 0.0 if u is None else self.largura / 2.0 - u
        return math.degrees(math.atan2(self.altura / 2.0 - v, math.hypot(self.f, du)))

    def distancia_minima_mensuravel(self):
        """Distância câmera -> centro em que o balão ocupa exatamente a largura da imagem."""
        return self.raio_balao_m / math.sin(math.atan2(self.largura / 2.0, self.f))

    def projetar(self, ponto_cam):
        """Ponto no referencial da câmera (x à frente, y à esquerda, z acima) -> pixel (u, v), ou None se atrás."""
        x, y, z = ponto_cam
        if x <= 1e-6:
            return None
        return self.largura / 2.0 - self.f * y / x, self.altura / 2.0 - self.f * z / x


def cor_central(imagem_bgr, cores, fracao_regiao=0.3):
    """Cor dominante na região central (fração da largura/altura) e a fração de pixels com ela."""
    import cv2

    h, w = imagem_bgr.shape[:2]
    dh, dw = int(h * fracao_regiao / 2), int(w * fracao_regiao / 2)
    centro = imagem_bgr[h // 2 - dh:h // 2 + dh, w // 2 - dw:w // 2 + dw]
    hsv = cv2.cvtColor(centro, cv2.COLOR_BGR2HSV)
    total = hsv.shape[0] * hsv.shape[1]
    melhor, fracao = '', 0.0
    for cor in cores:
        f = float(np.count_nonzero(mascara_cor(hsv, cor))) / total
        if f > fracao:
            melhor, fracao = cor, f
    return melhor, fracao


def mascara_cor(hsv, cor):
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    mascara = np.zeros(hue.shape, dtype=bool)
    for h0, h1 in FAIXAS_HSV.get(cor, ()):
        mascara |= (hue >= h0) & (hue <= h1)
    return mascara & (sat >= S_MIN) & (val >= V_MIN)


def bordas_centrais(imagem_bgr, cor):
    """Linha do centro do balão da cor `cor` que cruza a coluna central: entre as linhas em que o pixel central tem a
    cor, a de trecho contínuo mais largo (passa pelo centro de uma esfera). Devolve (u0, u1, v, cortado_h, cortado_v):
    bordas em px, a linha, e se o trecho toca a borda lateral (largura subestimada) ou se a linha mais larga está na
    borda superior/inferior (centro fora da imagem). None se a cor não está na coluna central."""
    import cv2

    h, w = imagem_bgr.shape[:2]
    mascara = mascara_cor(cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV), cor)
    centro = w // 2
    linhas = np.flatnonzero(mascara[:, centro])
    if not len(linhas):
        return None
    # só o trecho vertical contínuo que contém o centro da imagem (ou o mais próximo dele)
    quebras = np.flatnonzero(np.diff(linhas) > 1)
    grupos = np.split(linhas, quebras + 1)
    grupo = min(grupos, key=lambda g: 0 if g[0] <= h // 2 <= g[-1] else min(abs(g[0] - h // 2), abs(g[-1] - h // 2)))
    melhor = None
    for v in grupo:
        fora = np.flatnonzero(~mascara[v])
        esquerda, direita = fora[fora < centro], fora[fora > centro]
        u0 = float(esquerda[-1]) + 0.5 if len(esquerda) else 0.0
        u1 = float(direita[0]) - 0.5 if len(direita) else float(w)
        if melhor is None or u1 - u0 > melhor[1] - melhor[0]:
            melhor = (u0, u1, float(v), not len(esquerda) or not len(direita))
    u0, u1, v, cortado_h = melhor
    cortado_v = v <= grupo[0] + 1 and grupo[0] <= 1 or v >= grupo[-1] - 1 and grupo[-1] >= h - 2
    return u0, u1, v, cortado_h, bool(cortado_v)


class DetectorYolo:
    """YOLOv8 (ultralytics) exportado em ONNX, saída (1, 4 + nc, N): cx, cy, w, h no tamanho de entrada."""

    def __init__(self, caminho_onnx, classes, tamanho_entrada=416, limiar_confianca=0.5, limiar_nms=0.45):
        import cv2

        self.cv2 = cv2
        try:
            import onnxruntime

            self.sessao = onnxruntime.InferenceSession(caminho_onnx, providers=['CPUExecutionProvider'])
            self.entrada = self.sessao.get_inputs()[0].name
            self.motor = f'onnxruntime {onnxruntime.__version__}'
        except ImportError:
            self.sessao = None
            self.rede = cv2.dnn.readNetFromONNX(caminho_onnx)
            self.motor = f'opencv dnn {cv2.__version__}'
        self.classes = tuple(classes)
        self.tamanho = tamanho_entrada
        self.limiar_confianca = limiar_confianca
        self.limiar_nms = limiar_nms

    def _letterbox(self, imagem):
        h, w = imagem.shape[:2]
        escala = self.tamanho / max(h, w)
        nh, nw = int(round(h * escala)), int(round(w * escala))
        quadro = np.full((self.tamanho, self.tamanho, 3), 114, dtype=np.uint8)
        dy, dx = (self.tamanho - nh) // 2, (self.tamanho - nw) // 2
        quadro[dy:dy + nh, dx:dx + nw] = self.cv2.resize(imagem, (nw, nh))
        return quadro, escala, dx, dy

    def detectar(self, imagem_bgr):
        quadro, escala, dx, dy = self._letterbox(imagem_bgr)
        blob = self.cv2.dnn.blobFromImage(quadro, 1 / 255.0, (self.tamanho, self.tamanho), swapRB=True)
        if self.sessao is not None:
            saida = self.sessao.run(None, {self.entrada: blob})[0][0]     # (4 + nc, N)
        else:
            self.rede.setInput(blob)
            saida = self.rede.forward()[0]
        saida = saida.T
        pontuacoes = saida[:, 4:4 + len(self.classes)]
        classe = np.argmax(pontuacoes, axis=1)
        confianca = pontuacoes[np.arange(len(classe)), classe]
        manter = confianca >= self.limiar_confianca
        caixas, confs, idx_classes = [], [], []
        for (cx, cy, bw, bh), c, k in zip(saida[manter, :4], confianca[manter], classe[manter]):
            x = (cx - bw / 2 - dx) / escala
            y = (cy - bh / 2 - dy) / escala
            caixas.append([float(x), float(y), float(bw / escala), float(bh / escala)])
            confs.append(float(c))
            idx_classes.append(int(k))
        deteccoes = []
        for i in np.array(self.cv2.dnn.NMSBoxes(caixas, confs, self.limiar_confianca, self.limiar_nms)).flatten():
            x, y, bw, bh = caixas[i]
            deteccoes.append(Deteccao(cor=self.classes[idx_classes[i]], confianca=confs[i],
                                      u=int(round(x + bw / 2)), v=int(round(y + bh / 2)),
                                      largura_px=int(round(bw)), altura_px=int(round(bh))))
        return deteccoes


def caminho_modelo_padrao():
    import os

    from ament_index_python.packages import get_package_share_directory
    return os.path.join(get_package_share_directory('psi3442_tarefas'), 'modelos', 'baloes_yolov8n.onnx')


def main(args=None):
    import os

    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Image
    from psi3442_interfaces.msg import Alvos, DeteccaoBalao, EstadoEstimado

    from . import ros_util
    from .tipos import Estado, de_mensagem

    class NoVisaoComputacional(Node):
        def __init__(self):
            super().__init__('visao_computacional')
            cfg = ros_util.carregar_config(self)
            v = cfg.visao
            self.cfg = v
            self.cores = cfg.tarefa2.cores_conhecidas
            self.raio_balao_m = cfg.tarefa2.raio_balao_m
            self.geometria = GeometriaCamera(v.hfov_graus, v.largura_px, v.altura_px, self.raio_balao_m)
            caminho = v.modelo_onnx or caminho_modelo_padrao()
            self.detector = None
            if os.path.exists(caminho):
                self.detector = DetectorYolo(caminho, v.classes, v.tamanho_entrada, v.limiar_confianca, v.limiar_nms)
                self.get_logger().info(f'modelo de visão carregado: {caminho} ({self.detector.motor})')
            else:
                self.get_logger().error(f'modelo de visão ausente ({caminho}): só a cor central será publicada')
            self.estado = None
            self.t_ultimo = 0.0
            self.pub = self.create_publisher(Alvos, '/alvos', ros_util.QOS_FLUXO)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_subscription(Image, '/dji/camera', self.ao_quadro, ros_util.QOS_FLUXO)

        def ao_estado(self, msg):
            self.estado = de_mensagem(Estado, msg)

        def ao_quadro(self, msg):
            agora = ros_util.agora()
            if agora - self.t_ultimo < 1.0 / self.cfg.taxa_max_hz or self.estado is None:
                return
            self.t_ultimo = agora
            imagem = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, -1)
            if msg.encoding == 'rgb8':
                imagem = imagem[..., ::-1]
            imagem = np.ascontiguousarray(imagem[..., :3])
            if (msg.width, msg.height) != (self.geometria.largura, self.geometria.altura):
                # resolução real do quadro (o fluxo da DJI é 16:9); o campo de visão horizontal vem da config
                self.geometria = GeometriaCamera(self.cfg.hfov_graus, msg.width, msg.height, self.raio_balao_m)
                self.get_logger().info(f'quadros de {msg.width}x{msg.height} px')
            e = self.estado
            saida = Alvos(x_m=e.x_m, y_m=e.y_m, z_m=e.z_m, guinada_local_graus=e.guinada_local_graus)
            if self.detector is not None:
                for det in self.detector.detectar(imagem):
                    det = self.geometria.completar(det, e.guinada_local_graus)
                    if det.distancia_m > self.cfg.distancia_max_m:
                        continue
                    saida.deteccoes.append(DeteccaoBalao(
                        cor=det.cor, confianca=det.confianca, u=det.u, v=det.v, largura_px=det.largura_px,
                        altura_px=det.altura_px, azimute_graus=det.azimute_graus, elevacao_graus=det.elevacao_graus,
                        distancia_m=det.distancia_m, cortada=det.cortada))
            saida.cor_central, saida.fracao_cor_central = cor_central(imagem, self.cores)
            saida.distancia_central_m = saida.azimute_central_graus = saida.elevacao_central_graus = math.nan
            bordas = bordas_centrais(imagem, saida.cor_central) if saida.cor_central else None
            if bordas is not None:
                u0, u1, v, cortado_h, cortado_v = bordas
                d, az = self.geometria.proximidade(u0, u1, e.guinada_local_graus)
                saida.elevacao_central_graus = self.geometria.elevacao(v, (u0 + u1) / 2)
                # cortado: a largura vista é uma corda menor que o diâmetro -> d é um limite superior (sinal negativo);
                # com a linha mais larga na borda vertical, a elevação é a da borda (o centro está além dela)
                if cortado_h or cortado_v:
                    saida.distancia_central_m = -d
                    saida.azimute_central_graus = math.nan if cortado_h else az
                else:
                    saida.distancia_central_m, saida.azimute_central_graus = d, az
            self.pub.publish(ros_util.carimbar(self, saida))

    rclpy.init(args=args)
    ros_util.executar(NoVisaoComputacional())


if __name__ == '__main__':
    main()
