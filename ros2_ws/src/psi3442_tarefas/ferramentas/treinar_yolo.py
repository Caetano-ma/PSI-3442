"""Treina o detector de balões (YOLOv8n), exporta em ONNX e avalia com o mesmo código do nó de visão.

Treino e exportação usam PyTorch + ultralytics (fora do ROS 2, num venv):
    python3 -m venv ~/venvs/yolo
    ~/venvs/yolo/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    ~/venvs/yolo/bin/pip install ultralytics onnx onnxslim
    ~/venvs/yolo/bin/python treinar_yolo.py treinar --dados ~/psi3442_dados/baloes/baloes.yaml --epocas 20

A avaliação usa só OpenCV (DetectorYolo de no_visao_computacional, como em voo), com o Python do sistema:
    python3 treinar_yolo.py avaliar --dados ~/psi3442_dados/baloes --modelo ../modelos/baloes_yolov8n.onnx

Aumentos de matiz ficam pequenos: a classe É a cor do balão.
"""
import argparse
import glob
import json
import os
import shutil
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELOS = os.path.join(os.path.dirname(AQUI), 'modelos')
TAMANHO = 416


def treinar(a):
    from ultralytics import YOLO

    modelo = YOLO(a.base)
    modelo.train(data=os.path.expanduser(a.dados), imgsz=TAMANHO, epochs=a.epocas, batch=a.lote, device='cpu',
                 workers=a.workers, project=os.path.expanduser(a.projeto), name='baloes', exist_ok=True,
                 hsv_h=0.005, hsv_s=0.4, hsv_v=0.4, degrees=0.0, fliplr=0.5, mosaic=1.0, close_mosaic=3,
                 patience=8, plots=True, verbose=True)
    melhor = os.path.join(os.path.expanduser(a.projeto), 'baloes', 'weights', 'best.pt')
    exportar_onnx(melhor)


def exportar_onnx(pesos):
    from ultralytics import YOLO

    caminho = YOLO(pesos).export(format='onnx', imgsz=TAMANHO, opset=12, simplify=True, dynamic=False)
    os.makedirs(MODELOS, exist_ok=True)
    destino = os.path.join(MODELOS, 'baloes_yolov8n.onnx')
    shutil.copy(caminho, destino)
    print(f'modelo exportado: {destino}')


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    inter = max(0, min(ax1, bx1) - max(ax0, bx0)) * max(0, min(ay1, by1) - max(ay0, by0))
    return inter / ((ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter + 1e-9)


def avaliar(a):
    import cv2

    sys.path.insert(0, os.path.dirname(AQUI))
    from psi3442_tarefas.no_visao_computacional import DetectorYolo

    classes = ('vermelho', 'azul', 'verde', 'amarelo', 'roxo')
    detector = DetectorYolo(a.modelo, classes, TAMANHO, a.confianca, 0.45)
    imagens = sorted(glob.glob(os.path.join(os.path.expanduser(a.dados), 'images', 'val', '*.jpg')))
    vp = fp = fn = troca_cor = 0
    por_tamanho = {}                                    # recall por diâmetro aparente (px)
    tempos = []
    for caminho in imagens:
        img = cv2.imread(caminho)
        h, w = img.shape[:2]
        verdade = []
        with open(caminho.replace('images', 'labels').rsplit('.', 1)[0] + '.txt') as f:
            for linha in f:
                c, x, y, bw, bh = map(float, linha.split())
                verdade.append((int(c), ((x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h)))
        t0 = time.perf_counter()
        deteccoes = detector.detectar(img)
        tempos.append(time.perf_counter() - t0)
        usadas = set()
        for c, caixa in verdade:
            faixa = min(int(max(caixa[2] - caixa[0], caixa[3] - caixa[1]) // 20) * 20, 200)
            total, achou = por_tamanho.get(faixa, (0, 0))
            melhor, k_melhor = 0.0, None
            for k, d in enumerate(deteccoes):
                if k in usadas:
                    continue
                cd = (d.u - d.largura_px / 2, d.v - d.altura_px / 2, d.u + d.largura_px / 2, d.v + d.altura_px / 2)
                v = iou(caixa, cd)
                if v > melhor:
                    melhor, k_melhor = v, k
            if melhor >= 0.5:
                usadas.add(k_melhor)
                if classes.index(deteccoes[k_melhor].cor) == c:
                    vp += 1
                    achou += 1
                else:
                    troca_cor += 1
                    fn += 1
            else:
                fn += 1
            por_tamanho[faixa] = (total + 1, achou)
        fp += len(deteccoes) - len(usadas)
    precisao, revocacao = vp / max(1, vp + fp + troca_cor), vp / max(1, vp + fn)
    resultado = {
        'imagens': len(imagens), 'verdadeiros_positivos': vp, 'falsos_positivos': fp, 'falsos_negativos': fn,
        'cor_trocada': troca_cor, 'precisao': round(precisao, 3), 'revocacao': round(revocacao, 3),
        'limiar_confianca': a.confianca, 'iou_min': 0.5,
        'tempo_medio_ms': round(1000 * sum(tempos) / max(1, len(tempos)), 1),
        'revocacao_por_diametro_px': {f'{k}-{k + 19}' if k < 200 else '200+': round(achou / total, 3)
                                      for k, (total, achou) in sorted(por_tamanho.items())},
    }
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    if a.salvar:
        with open(a.salvar, 'w') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='comando', required=True)
    t = sub.add_parser('treinar')
    t.add_argument('--dados', default='~/psi3442_dados/baloes/baloes.yaml')
    t.add_argument('--base', default='yolov8n.pt', help='pesos iniciais (COCO)')
    t.add_argument('--epocas', type=int, default=20)
    t.add_argument('--lote', type=int, default=16)
    t.add_argument('--workers', type=int, default=4)
    t.add_argument('--projeto', default='~/psi3442_dados/treinos')
    e = sub.add_parser('exportar')
    e.add_argument('pesos')
    v = sub.add_parser('avaliar')
    v.add_argument('--dados', default='~/psi3442_dados/baloes')
    v.add_argument('--modelo', default=os.path.join(MODELOS, 'baloes_yolov8n.onnx'))
    v.add_argument('--confianca', type=float, default=0.5)
    v.add_argument('--salvar', default='')
    a = ap.parse_args()
    {'treinar': treinar, 'exportar': lambda a: exportar_onnx(a.pesos), 'avaliar': avaliar}[a.comando](a)


if __name__ == '__main__':
    main()
