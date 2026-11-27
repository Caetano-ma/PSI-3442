"""Conjunto de dados sintético para o detector de balões (R02): imagens 640x480 no formato YOLO.

Randomização de domínio, sem depender do Gazebo: fundo de sala (piso, paredes, móveis e objetos coloridos que não
são balões, inclusive nas cores-alvo), balões renderizados como elipsoides com sombreamento difuso e especular,
cordão, oclusão por objetos à frente, cortes na borda, desfoque, ruído, JPEG e balanço de branco. As matizes seguem
as faixas HSV de no_visao_computacional.FAIXAS_HSV. A caixa rotulada é a parte visível do balão.

    python3 gerar_dataset_baloes.py --saida ~/psi3442_dados/baloes --treino 2500 --validacao 400 [--semente 1]

Gera <saida>/images/{train,val}, <saida>/labels/{train,val} e <saida>/baloes.yaml (para o ultralytics).
"""
import argparse
import math
import os

import cv2
import numpy as np

CLASSES = ('vermelho', 'azul', 'verde', 'amarelo', 'roxo')
# matizes do OpenCV (0..180) no miolo das faixas de FAIXAS_HSV, para não gerar cores ambíguas
MATIZES = {'vermelho': ((0, 7), (173, 180)), 'azul': ((100, 125),), 'verde': ((45, 80),),
           'amarelo': ((22, 33),), 'roxo': ((135, 155),)}
L, A = 640, 480
VISIVEL_MIN = 0.35            # fração visível mínima para rotular o balão (mais ocluído que isso é ignorado)


def cor_hsv(rng, cor):
    faixas = MATIZES[cor]
    h0, h1 = faixas[rng.integers(len(faixas))]
    return rng.uniform(h0, h1), rng.uniform(150, 255), rng.uniform(150, 255)


def hsv_para_bgr(h, s, v):
    pixel = np.uint8([[[int(h) % 180, int(s), int(v)]]])
    return cv2.cvtColor(pixel, cv2.COLOR_HSV2BGR)[0, 0].astype(np.float32) / 255.0


def fundo(rng):
    """Sala: parede e piso com gradiente e textura, horizonte aleatório, móveis e objetos coloridos."""
    img = np.zeros((A, L, 3), np.float32)
    horizonte = int(rng.uniform(0.2, 0.9) * A)
    parede = rng.uniform(0.25, 0.95, 3) * rng.uniform(0.6, 1.0)
    piso = rng.uniform(0.15, 0.8, 3)
    if rng.random() < 0.5:                                  # paredes acinzentadas são o caso comum
        parede[:] = parede.mean()
    grad = np.linspace(rng.uniform(0.7, 1.1), rng.uniform(0.7, 1.1), A)[:, None, None]
    img[:horizonte] = parede
    img[horizonte:] = piso
    img *= grad
    ruido = cv2.resize(rng.normal(0, 1, (A // 16, L // 16)).astype(np.float32), (L, A))
    img += 0.04 * ruido[..., None]
    if rng.random() < 0.5:                                  # piso em placas
        passo = int(rng.uniform(30, 120))
        for x in range(0, L, passo):
            cv2.line(img, (x, horizonte), (int(L / 2 + (x - L / 2) * 3), A), tuple(piso * 0.7), 1)
    for _ in range(rng.integers(0, 7)):                     # móveis, portas, quadros
        x0, y0 = int(rng.uniform(-50, L)), int(rng.uniform(0, A))
        w, h = int(rng.uniform(20, 300)), int(rng.uniform(20, 300))
        cor = tuple(float(c) for c in rng.uniform(0.05, 0.9, 3))
        cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), cor, -1)
    for _ in range(rng.integers(0, 4)):                     # distratores nas cores dos balões (não redondos)
        h, s, v = cor_hsv(rng, CLASSES[rng.integers(len(CLASSES))])
        cor = tuple(float(c) for c in hsv_para_bgr(h, s, v))
        x0, y0 = int(rng.uniform(0, L)), int(rng.uniform(0, A))
        if rng.random() < 0.6:
            cv2.rectangle(img, (x0, y0), (x0 + int(rng.uniform(10, 150)), y0 + int(rng.uniform(10, 150))), cor, -1)
        else:
            pts = (rng.uniform(-60, 60, (int(rng.integers(3, 6)), 2)) + [x0, y0]).astype(np.int32)
            cv2.fillPoly(img, [pts], cor)
    return np.clip(img, 0, 1)


def balao(rng, img, ocupacao, cor, cx, cy, raio, luz):
    """Desenha um balão (elipsoide) e devolve a máscara (float) do balão inteiro, antes das oclusões."""
    alongamento = rng.uniform(1.0, 1.22)
    rx, ry = raio, raio * alongamento
    inclinacao = math.radians(rng.uniform(-12, 12))
    x0, x1 = int(max(0, cx - rx * 1.3 - 2)), int(min(L, cx + rx * 1.3 + 2))
    y0, y1 = int(max(0, cy - ry * 1.3 - 2)), int(min(A, cy + ry * 1.3 + 2))
    mascara = np.zeros((A, L), np.float32)
    if x1 <= x0 or y1 <= y0:
        return mascara
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xs - cx, ys - cy
    c, s = math.cos(inclinacao), math.sin(inclinacao)
    u, v = (c * dx + s * dy) / rx, (-s * dx + c * dy) / ry
    r2 = u * u + v * v
    borda = np.clip((1.0 - np.sqrt(r2)) * min(rx, ry) + 0.5, 0, 1)          # 1 px de anti-serrilhado
    nz = np.sqrt(np.clip(1.0 - r2, 0, 1))
    normal = np.stack([u, -v, nz], -1)
    difusa = np.clip(normal @ luz, 0, 1)
    refletida = 2 * difusa[..., None] * normal - luz
    especular = np.clip(refletida[..., 2], 0, 1) ** rng.uniform(15, 60) * rng.uniform(0.3, 0.9)
    albedo = hsv_para_bgr(*cor)
    ambiente = rng.uniform(0.35, 0.6)
    tom = albedo * (ambiente + (1 - ambiente) * difusa[..., None]) + especular[..., None]
    tom *= 1.0 - 0.25 * (1 - nz[..., None]) ** 3                            # escurece na silhueta
    regiao = img[y0:y1, x0:x1]
    img[y0:y1, x0:x1] = regiao * (1 - borda[..., None]) + np.clip(tom, 0, 1) * borda[..., None]
    mascara[y0:y1, x0:x1] = borda
    # nó e cordão (abaixo do balão)
    base = (int(cx + s * ry), int(cy + c * ry))
    escuro = tuple(float(x) for x in albedo * 0.6)
    cv2.circle(img, base, max(1, int(raio * 0.06)), escuro, -1)
    if rng.random() < 0.7:
        fim = (base[0] + int(rng.uniform(-raio, raio)), base[1] + int(rng.uniform(raio, 4 * raio)))
        cv2.line(img, base, fim, tuple(float(x) for x in rng.uniform(0.6, 1.0, 3)), 1)
    ocupacao += mascara
    return mascara


def amostra(rng):
    img = fundo(rng)
    luz = rng.normal(0, 1, 3)
    luz[2] = abs(luz[2]) + 0.5
    luz /= np.linalg.norm(luz)
    ocupacao = np.zeros((A, L), np.float32)
    n = int(rng.choice([0, 1, 1, 2, 2, 3, 4, 5, 6], p=None))
    # raio aparente com distribuição log-uniforme: de longe (~6 px) a muito perto (balão maior que a imagem)
    candidatos = []
    for _ in range(n):
        raio = math.exp(rng.uniform(math.log(5), math.log(260 if rng.random() < 0.85 else 420)))
        candidatos.append((raio, CLASSES[rng.integers(len(CLASSES))]))
    candidatos.sort()                                        # menores (mais longe) primeiro
    mascaras = []
    for raio, nome in candidatos:
        cx, cy = rng.uniform(-0.3 * raio, L + 0.3 * raio), rng.uniform(-0.3 * raio, A + 0.3 * raio)
        m = balao(rng, img, ocupacao, cor_hsv(rng, nome), cx, cy, raio, luz)
        for anterior in mascaras:                           # o mais perto esconde os de trás
            anterior[1] *= 1 - m
        mascaras.append([nome, m, m.sum() + 1e-6])
    for _ in range(rng.integers(0, 3)):                     # oclusores à frente (pessoas, cadeiras, colunas)
        x0, y0 = int(rng.uniform(-50, L)), int(rng.uniform(0, A))
        w, h = int(rng.uniform(15, 200)), int(rng.uniform(40, 400))
        cor = tuple(float(c) for c in rng.uniform(0.05, 0.8, 3))
        oclusor = np.zeros((A, L), np.float32)
        cv2.rectangle(oclusor, (x0, y0), (x0 + w, y0 + h), 1.0, -1)
        img = img * (1 - oclusor[..., None]) + np.array(cor, np.float32) * oclusor[..., None]
        for item in mascaras:
            item[1] *= 1 - oclusor
    # pós-processamento fotométrico
    img *= rng.uniform(0.6, 1.3) * rng.uniform(0.9, 1.1, 3)                  # exposição e balanço de branco
    if rng.random() < 0.5:
        k = int(rng.choice([3, 5, 7]))
        img = cv2.GaussianBlur(img, (k, k), 0) if rng.random() < 0.6 else cv2.blur(img, (k, 1))
    img += rng.normal(0, rng.uniform(0.0, 0.04), img.shape).astype(np.float32)
    img8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    rotulos = []
    for nome, m, total in mascaras:
        visivel = m > 0.5
        if visivel.sum() < 30 or m.sum() / total < VISIVEL_MIN:
            continue
        ys, xs = np.nonzero(visivel)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        rotulos.append((CLASSES.index(nome), (x0 + x1) / 2 / L, (y0 + y1) / 2 / A, (x1 - x0) / L, (y1 - y0) / A))
    return img8, rotulos


def gerar(saida, n, conjunto, semente):
    rng = np.random.default_rng(semente)
    pasta_img = os.path.join(saida, 'images', conjunto)
    pasta_rot = os.path.join(saida, 'labels', conjunto)
    os.makedirs(pasta_img, exist_ok=True)
    os.makedirs(pasta_rot, exist_ok=True)
    for i in range(n):
        img, rotulos = amostra(rng)
        nome = f'{conjunto}_{i:05d}'
        cv2.imwrite(os.path.join(pasta_img, nome + '.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, int(rng.uniform(55, 95))])
        with open(os.path.join(pasta_rot, nome + '.txt'), 'w') as f:
            f.writelines(f'{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n' for c, x, y, w, h in rotulos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--saida', default=os.path.expanduser('~/psi3442_dados/baloes'))
    ap.add_argument('--treino', type=int, default=2500)
    ap.add_argument('--validacao', type=int, default=400)
    ap.add_argument('--semente', type=int, default=1)
    a = ap.parse_args()
    saida = os.path.abspath(os.path.expanduser(a.saida))
    gerar(saida, a.treino, 'train', a.semente)
    gerar(saida, a.validacao, 'val', a.semente + 1000)
    with open(os.path.join(saida, 'baloes.yaml'), 'w') as f:
        f.write(f'path: {saida}\ntrain: images/train\nval: images/val\n')
        f.write('names:\n' + ''.join(f'  {i}: {c}\n' for i, c in enumerate(CLASSES)))
    print(f'{a.treino} + {a.validacao} imagens em {saida}')


if __name__ == '__main__':
    main()
