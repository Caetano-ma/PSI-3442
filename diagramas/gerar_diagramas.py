import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from pathlib import Path

plt.rcParams["font.family"] = "Liberation Sans"
OUT = Path(__file__).parent
GRAY = "#595959"
LIGHT = "#9E9E9E"
MARK = "#D81B60"


class Canvas:
    def __init__(self, w, h):
        self.fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(h, 0)
        self.ax.axis("off")
        self.marked = []

    def box(self, x0, y0, x1, y1, fc, ec=GRAY, lw=1.3, ls="-", fill=True, z=1):
        self.ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc if fill else "none",
                                    ec=ec, lw=lw, ls=ls, zorder=z))

    def text(self, x, y, s, color=GRAY, fs=18, ha="left", va="bottom", mark=False, **kw):
        t = self.ax.text(x, y, s, color=color, fontsize=fs, ha=ha, va=va, zorder=5, **kw)
        if mark:
            self.marked.append(t)
        return t

    def arrow(self, pts, color=GRAY, both=False, ls="-", lw=1.6):
        pts = np.array(pts, dtype=float)
        self.ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, ls=ls, zorder=3,
                     solid_capstyle="butt")
        self._head(pts[-2], pts[-1], color, lw)
        if both:
            self._head(pts[1], pts[0], color, lw)

    def _head(self, a, b, color, lw):
        d = (b - a) / np.linalg.norm(b - a)
        self.ax.annotate("", xy=b, xytext=b - d * 0.5, zorder=4,
                         arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                         mutation_scale=16, shrinkA=0, shrinkB=0))

    def save(self, name):
        self.fig.canvas.draw()
        r = self.fig.canvas.get_renderer()
        inv = self.ax.transData.inverted()
        for t in self.marked:
            bb = t.get_window_extent(r)
            x, y = inv.transform((bb.x0, (bb.y0 + bb.y1) / 2))
            self.ax.plot(x - 9, y, "o", color=MARK, ms=6, zorder=6)
        self.fig.savefig(OUT / name, dpi=150, facecolor="white")
        plt.close(self.fig)


def legenda(c, x, y, extra=()):
    c.ax.plot(x + 8, y, "o", color=MARK, ms=6)
    c.text(x + 22, y, "acrescentado ou alterado", fs=11, va="center")
    c.ax.plot([x, x + 16], [y + 22, y + 22], color=LIGHT, ls="--", lw=1.6)
    c.text(x + 22, y + 22, "indisponível em ambiente interno", fs=11, va="center")
    for i, s in enumerate(extra):
        c.text(x, y + 44 + 22 * i, s, fs=11, va="center", style="italic")


# ------------------------------------------------------------------ Nível 0
def nivel_0():
    c = Canvas(1400, 960)
    c.text(700, 30, "Nível 0 — DJI Mini 4 Pro", fs=22, ha="center", va="top", weight="bold", color="#333333")

    # Drone
    c.box(520, 240, 925, 490, "#93C47D")
    c.text(722, 352, "Drone", fs=24, ha="center", va="center")
    c.text(722, 388, "DJI Mini 4 Pro", fs=15, ha="center", va="center", mark=True)

    # entradas superiores
    c.arrow([(545, 175), (545, 240)], both=True)
    c.text(545, 165, "Conexão\nUSB", ha="center")
    c.arrow([(690, 175), (690, 240)])
    c.text(690, 165, "Imagem", ha="center")
    c.arrow([(880, 175), (880, 240)], both=True)
    c.text(905, 165, "Cartão de Memória", ha="center", mark=True)

    # entradas à esquerda
    c.arrow([(40, 262), (520, 262)])
    c.text(40, 258, "Bateria")
    c.arrow([(40, 298), (520, 298)])
    c.text(40, 294, "Botão ON/OFF")
    c.box(25, 314, 380, 448, "none", ec="#4A86E8", ls="--", lw=1.2, fill=False)
    c.text(50, 318, "Ambiente físico — sala de aula", fs=11, va="top", color="#4A86E8", style="italic", mark=True)
    c.arrow([(40, 368), (520, 368)])
    c.text(40, 364, "Distância (ToF / visão)", mark=True)
    c.arrow([(40, 404), (520, 404)])
    c.text(40, 400, "Pressão (barômetro)", mark=True)
    c.arrow([(40, 440), (520, 440)])
    c.text(40, 436, "Textura do Piso / Iluminação", mark=True)
    c.arrow([(40, 482), (520, 482)], color=LIGHT, ls="--")
    c.text(40, 478, "GPS (indisponível indoor)", color=LIGHT, mark=True)

    # saídas à direita
    c.arrow([(925, 282), (1130, 282)])
    c.text(940, 278, "Empuxo/Torque")
    c.arrow([(925, 382), (1130, 382)])
    c.text(940, 378, "Led ON e Ready")

    # Estação de Solo
    c.box(440, 590, 1010, 760, "#FFE599")
    c.text(725, 598, "Estação de Solo", fs=18, ha="center", va="top")
    c.box(470, 635, 700, 740, "#FFF2CC")
    c.text(585, 674, "Controle Remoto", fs=15, ha="center", va="center", mark=True)
    c.text(585, 702, "(RC-N2 — verificar)", fs=12, ha="center", va="center")
    c.box(760, 635, 985, 740, "#FFF2CC")
    c.text(872, 667, "Celular Android", fs=15, ha="center", va="center", mark=True)
    c.text(872, 691, "App de Missão", fs=13, ha="center", va="center")
    c.text(872, 714, "(DJI Mobile SDK v5)", fs=12, ha="center", va="center")
    c.arrow([(700, 688), (760, 688)], both=True)
    c.text(730, 683, "USB", fs=12, ha="center")

    c.arrow([(600, 490), (600, 635)], both=True)
    c.text(615, 545, "Sinais RF", va="center")
    c.text(615, 572, "(enlace O4)", fs=14, va="center", mark=True)

    # entradas / saídas da estação
    c.arrow([(40, 700), (440, 700)])
    c.text(40, 696, "Bateria (RC e celular)", mark=True)
    c.arrow([(1200, 655), (1010, 655)])
    c.text(1030, 651, "Arquivo de Configuração\nda Missão (JSON)", fs=15, mark=True)
    c.arrow([(1010, 725), (1200, 725)])
    c.text(1030, 721, "Logs Exportáveis (CSV)", fs=15, mark=True)
    c.arrow([(620, 760), (620, 815)])
    c.text(620, 822, "Display Gráfico dos\nDados do Drone", ha="center", va="top")
    c.arrow([(900, 815), (900, 760)])
    c.text(900, 822, "Comandos do Operador\n(iniciar / interromper)", ha="center", va="top", mark=True)

    legenda(c, 40, 895, ["Botão Reset removido: não existe no Mini 4 Pro."])
    c.save("nivel_0.png")


# ------------------------------------------------------------------ Nível 1
def nivel_1():
    c = Canvas(1400, 1330)
    c.text(700, 30, "Nível 1 — DJI Mini 4 Pro", fs=22, ha="center", va="top", weight="bold", color="#333333")

    OR, YE, BL, RD, CY, PU = "#E69138", "#C9A100", "#4A86E8", "#E53935", "#00ACC1", "#8E44AD"

    # Drone
    c.box(380, 250, 1000, 680, "#93C47D")
    c.text(990, 674, "Drone — DJI Mini 4 Pro", fs=13, ha="right", va="bottom", weight="bold", color="#2E5E1E", mark=True)

    def bloco(x0, y0, x1, y1, fc, titulo, sub=""):
        c.box(x0, y0, x1, y1, fc, ec="#333333", lw=1.1)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if not titulo:
            return
        if sub:
            c.text(cx, cy, titulo, color="black", fs=13, ha="center", va="bottom")
            c.text(cx, cy + 2, sub, color="#424242", fs=9.5, ha="center", va="top", mark=True)
        else:
            c.text(cx, cy, titulo, color="black", fs=13, ha="center", va="center")

    bloco(405, 285, 500, 345, "#F6B26B", "Energia", "bateria\ninteligente")
    bloco(525, 285, 765, 425, "#FFE599", "Unidade de\nComputação\nEmbarcada", "controlador de voo DJI\n(firmware fechado)")
    bloco(830, 285, 980, 410, "#00FFFF", "Atuadores", "motores + ESCs\ngimbal 3 eixos")
    bloco(440, 455, 680, 600, "#A4C2F4", "Sensoriamento", "IMU · barômetro · ToF inferior\nvisão omnidirecional · câmera")
    bloco(770, 535, 985, 640, "#B4A7D6", "Estrutura Física", "")
    bloco(400, 622, 720, 668, "#EA9999", "", "")
    c.text(560, 640, "Comunicação", color="black", fs=13, ha="center", va="center")
    c.text(560, 659, "transceptor O4 · USB-C", color="#424242", fs=9.5, ha="center", va="center", mark=True)

    # fluxos internos
    c.arrow([(500, 315), (525, 315)], color=OR)
    c.arrow([(470, 345), (470, 455)], color=OR)
    c.arrow([(415, 345), (415, 622)], color=OR)
    c.arrow([(452, 285), (452, 268), (905, 268), (905, 285)], color=OR)
    c.text(780, 265, "Alimentação", fs=9, color=OR, ha="center")
    c.arrow([(765, 335), (830, 335)], color=YE)
    c.text(797, 330, "Sinais PWM", fs=9, color=YE, ha="center")
    c.arrow([(620, 455), (620, 425)], color=BL)
    c.text(626, 440, "Informação\nde Sensores", fs=8.5, color=BL, va="center")
    c.arrow([(560, 425), (560, 455)], color=BL)
    c.text(554, 440, "Triggers", fs=8.5, color=BL, ha="right", va="center")
    c.arrow([(710, 425), (710, 622)], color=RD, both=True)
    c.text(716, 500, "Pacotes de\nInformação", fs=8.5, color=RD, va="center")
    c.arrow([(900, 535), (900, 410)], color=PU)
    c.arrow([(770, 575), (680, 575)], color=PU)
    c.text(906, 470, "Fixação\nMecânica", fs=8.5, color=PU, va="center")

    # entradas à esquerda
    c.arrow([(30, 315), (405, 315)], color=OR)
    c.text(30, 311, "Bateria", color=OR, fs=17)
    c.arrow([(30, 400), (525, 400)], color=YE)
    c.text(30, 396, "Botão ON/OFF", color=YE, fs=17)
    c.box(20, 422, 395, 560, "none", ec=BL, ls="--", lw=1.1, fill=False)
    c.text(40, 426, "Ambiente físico — sala de aula", fs=10, va="top", color=BL, style="italic", mark=True)
    c.arrow([(30, 470), (440, 470)], color=BL)
    c.text(30, 466, "Distância (ToF / visão)", color=BL, fs=15, mark=True)
    c.arrow([(30, 497), (440, 497)], color=BL)
    c.text(30, 493, "Pressão (barômetro)", color=BL, fs=15, mark=True)
    c.arrow([(30, 524), (440, 524)], color=BL)
    c.text(30, 520, "Textura do Piso / Iluminação", color=BL, fs=15, mark=True)
    c.arrow([(30, 551), (440, 551)], color=BL)
    c.text(30, 547, "Imagem", color=BL, fs=15)
    c.arrow([(30, 590), (440, 590)], color=LIGHT, ls="--")
    c.text(30, 586, "GPS (indisponível indoor)", color=LIGHT, fs=15, mark=True)
    c.arrow([(30, 645), (400, 645)], color=RD, both=True)
    c.text(30, 641, "Conexão USB", color=RD, fs=17)

    # entrada superior
    c.arrow([(640, 160), (640, 285)], color=YE, both=True)
    c.text(640, 150, "Cartão de Memória", color=YE, fs=17, ha="center", mark=True)

    # saídas à direita
    c.arrow([(980, 345), (1200, 345)], color=CY)
    c.text(1012, 340, "Empuxo/Torque", color=CY, fs=19)
    c.arrow([(745, 425), (745, 445), (1200, 445)], color=YE)
    c.text(1012, 440, "Led ON e Ready", color=YE, fs=19)

    # Estação de Solo
    c.box(380, 780, 1000, 1160, "#FFE599")
    c.text(392, 788, "Estação de Solo", fs=15, va="top", weight="bold", color="#5D4600", mark=True)
    bloco(400, 830, 600, 905, "#EA9999", "Controle Remoto", "RC-N2 (verificar)\nenlace O4 ↔ USB")
    c.box(630, 820, 985, 1145, "#FFF2CC")
    c.text(807, 826, "Celular Android — App de Missão", fs=12, ha="center", va="top", weight="bold", color="#5D4600")
    bloco(650, 852, 965, 902, "#F9CB9C", "Adaptador DJI", "DJI Mobile SDK v5 (Kotlin)")
    bloco(650, 927, 965, 1022, "#FFE599", "Lógica de Missão",
          "máquina de estados · cronômetro 60 s\ncontrole de posição · supervisão de falhas")
    bloco(650, 1050, 800, 1130, "#D9EAD3", "Interface /\nPainel", "")
    bloco(815, 1050, 965, 1130, "#D9D9D9", "Registro\n(logs)", "")

    c.arrow([(580, 668), (580, 830)], color=RD, both=True)
    c.text(592, 730, "Sinais RF\n(enlace O4)", color=RD, fs=15, va="center")
    c.arrow([(600, 877), (650, 877)], color=RD, both=True)
    c.text(625, 872, "USB", color=RD, fs=10, ha="center")
    c.arrow([(740, 902), (740, 927)], color=BL, both=True)
    c.text(750, 914, "telemetria ↑  comandos ↓", color=BL, fs=9, va="center")
    c.arrow([(725, 1022), (725, 1050)], color=BL, both=True)
    c.arrow([(890, 1022), (890, 1050)], color=BL)

    c.arrow([(30, 980), (380, 980)], color=OR)
    c.text(30, 976, "Bateria (RC e celular)", color=OR, fs=15, mark=True)
    c.arrow([(1200, 975), (965, 975)], color=GRAY)
    c.text(1015, 970, "Arquivo de Configuração\nda Missão (JSON)", fs=14, mark=True)
    c.arrow([(965, 1090), (1200, 1090)], color=GRAY)
    c.text(1015, 1085, "Logs Exportáveis (CSV)", fs=14, mark=True)
    c.arrow([(690, 1220), (690, 1130)], color=GRAY)
    c.text(680, 1228, "Comandos do Operador\n(iniciar / interromper)", fs=15, ha="right", va="top", mark=True)
    c.arrow([(760, 1130), (760, 1220)], color=GRAY)
    c.text(770, 1228, "Display Gráfico dos\nDados do Drone", fs=15, va="top")

    legenda(c, 1010, 1200, ["Botão Reset removido:",
                            "não existe no Mini 4 Pro.",
                            "GPS: de Comunicação",
                            "para Sensoriamento."])
    c.save("nivel_1.png")


if __name__ == "__main__":
    nivel_0()
    nivel_1()
