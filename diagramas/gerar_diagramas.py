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
INFO, COM, EN, FORCA, VIS = "#4A86E8", "#E53935", "#E69138", "#00ACC1", "#C9A100"
CAIXA_PRETA = "#3C3C3C"


class Canvas:
    def __init__(self, w, h):
        self.fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(h, 0)
        self.ax.axis("off")

    def box(self, x0, y0, x1, y1, fc, ec=GRAY, lw=1.3, ls="-", fill=True, z=1):
        self.ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc if fill else "none",
                                    ec=ec, lw=lw, ls=ls, zorder=z))

    def text(self, x, y, s, color=GRAY, fs=18, ha="left", va="bottom", **kw):
        return self.ax.text(x, y, s, color=color, fontsize=fs, ha=ha, va=va, zorder=5, **kw)

    def arrow(self, pts, color=GRAY, both=False, ls="-", lw=1.6):
        pts = np.array(pts, dtype=float)
        self.ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, ls=ls, zorder=3, solid_capstyle="butt")
        self._head(pts[-2], pts[-1], color, lw)
        if both:
            self._head(pts[1], pts[0], color, lw)

    def _head(self, a, b, color, lw):
        d = (b - a) / np.linalg.norm(b - a)
        self.ax.annotate("", xy=b, xytext=b - d * 0.5, zorder=4,
                         arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                         mutation_scale=16, shrinkA=0, shrinkB=0))

    def bloco(self, x0, y0, x1, y1, fc, titulo, sub="", cor_titulo="black", cor_sub="#424242", fs=13, fs_sub=9.5):
        self.box(x0, y0, x1, y1, fc, ec="#333333", lw=1.1, z=2)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if sub:
            self.text(cx, cy, titulo, color=cor_titulo, fs=fs, ha="center", va="bottom", weight="bold")
            self.text(cx, cy + 3, sub, color=cor_sub, fs=fs_sub, ha="center", va="top")
        else:
            self.text(cx, cy, titulo, color=cor_titulo, fs=fs, ha="center", va="center", weight="bold")

    def save(self, name):
        self.fig.savefig(OUT / name, dpi=150, facecolor="white")
        plt.close(self.fig)


def legenda(c, x, y):
    itens = [(INFO, "-", "informação (tópicos ROS 2 / dados)"),
             (COM, "-", "comunicação (TCP / USB / RF)"),
             (EN, "-", "energia"),
             (FORCA, "-", "força / movimento"),
             (VIS, "-", "sinal visual"),
             (LIGHT, "--", "indisponível em ambiente interno")]
    c.text(x, y - 14, "Legenda", fs=11, weight="bold", va="center")
    for i, (cor, ls, nome) in enumerate(itens):
        yy = y + 20 * i
        c.ax.plot([x, x + 26], [yy, yy], color=cor, ls=ls, lw=2)
        c.text(x + 34, yy, nome, fs=10.5, va="center")
    yy = y + 20 * len(itens)
    c.box(x, yy - 7, x + 26, yy + 7, "none", ec=INFO, ls="--", lw=1.1, fill=False)
    c.text(x + 34, yy, "ambiente físico", fs=10.5, va="center")
    c.box(x, yy + 13, x + 26, yy + 27, CAIXA_PRETA, z=2)
    c.text(x + 34, yy + 20, "componente caixa-preta (só entradas e saídas)", fs=10.5, va="center")


# ------------------------------------------------------------------ Nível 0
def nivel_0():
    c = Canvas(1500, 900)
    c.text(750, 25, "Nível 0 — Sistema de Missões Autônomas com DJI Mini 4 Pro", fs=22, ha="center", va="top",
           weight="bold", color="#333333")

    # sistema de interesse
    c.box(430, 170, 1090, 600, "#93C47D")
    c.text(760, 180, "Sistema de Missões Autônomas", fs=20, ha="center", va="top", color="#1E3D14", weight="bold")
    c.text(760, 210, "Tarefa 1: voo de familiarização  ·  Tarefa 2: balões", fs=12, ha="center", va="top", color="#1E3D14")

    # notebook
    c.box(450, 245, 760, 580, "#FFF2CC")
    c.text(605, 252, "Notebook Linux", fs=14, ha="center", va="top", weight="bold", color="#5D4600")
    c.bloco(470, 280, 740, 422, "#FFE599", "ROS 2", "lógica das tarefas\n(gerenciador, tarefas, estimação,\nmapeamento, controle, supervisão,\nregistro)",
            fs=15, fs_sub=10)
    c.bloco(470, 450, 740, 560, "#F9CB9C", "Android emulado", "app ponte DJI\n(DJI Mobile SDK v5)", fs=14, fs_sub=10.5)
    c.arrow([(605, 422), (605, 450)], color=COM, both=True)
    c.text(615, 436, "TCP (adb)", fs=10, color=COM, va="center")

    # controle remoto e drone
    c.bloco(785, 455, 880, 555, "#EA9999", "Rádio\nDJI", "RC-N2 só\ncomo enlace,\nsem pilotagem", fs=11.5, fs_sub=8)
    c.arrow([(740, 505), (785, 505)], color=COM, both=True)
    c.text(762, 500, "USB", fs=10, color=COM, ha="center")
    c.box(940, 270, 1070, 570, CAIXA_PRETA, ec="#111111", z=2)
    c.text(1005, 410, "Drone\nDJI Mini 4 Pro", fs=12.5, ha="center", va="bottom", color="white", weight="bold")
    c.text(1005, 416, "caixa-preta", fs=11, ha="center", va="top", color="#DDDDDD", style="italic")
    c.arrow([(880, 505), (940, 505)], color=COM, both=True)
    c.text(910, 500, "RF O4", fs=10, color=COM, ha="center")

    # entradas e saídas de informação (esquerda)
    c.arrow([(30, 300), (430, 300)], color=INFO)
    c.text(30, 296, "Comandos: executar tarefa 1 / 2, interromper", fs=13)
    c.arrow([(430, 345), (30, 345)], color=INFO)
    c.text(40, 341, "Painel de Acompanhamento", fs=14)
    c.arrow([(430, 390), (30, 390)], color=INFO)
    c.text(40, 386, "Logs Exportáveis (rosbag / CSV)", fs=14)
    c.arrow([(30, 435), (430, 435)], color=INFO)
    c.text(30, 431, "Arquivo de Configuração das Tarefas", fs=14)
    c.arrow([(30, 520), (450, 520)], color=EN)
    c.text(30, 516, "Alimentação do Notebook", fs=14, color=EN)

    # entradas e saídas físicas do drone (direita)
    c.box(1095, 240, 1460, 405, "none", ec=INFO, ls="--", lw=1.1, fill=False)
    c.text(1105, 246, "Ambiente físico — sala de aula", fs=10, va="top", color=INFO, style="italic")
    for y, nome in [(290, "Distância (ToF / visão)"), (325, "Pressão (barômetro)"),
                    (360, "Textura do Piso / Iluminação"), (395, "Imagem (balões — Tarefa 2)")]:
        c.arrow([(1450, y), (1070, y)], color=INFO)
        c.text(1105, y - 4, nome, fs=13)
    c.arrow([(1450, 445), (1070, 445)], color=LIGHT, ls="--")
    c.text(1105, 441, "GPS (indisponível indoor)", fs=13, color=LIGHT)
    c.arrow([(1070, 500), (1450, 500)], color=FORCA)
    c.text(1105, 496, "Empuxo / Torque", fs=13, color=FORCA)
    c.arrow([(1070, 550), (1450, 550)], color=VIS)
    c.text(1105, 546, "LED ON e Ready", fs=13, color=VIS)

    # energia e ação manual (abaixo)
    for x, nome, cor, alvo in [(832, "Bateria\ndo rádio", EN, 555), (970, "Bateria\nde voo", EN, 570),
                               (1045, "Botão\nON/OFF", VIS, 570)]:
        c.arrow([(x, 640), (x, alvo)], color=cor)
        c.text(x, 646, nome, fs=12, ha="center", va="top", color=cor)

    c.text(30, 640, "Drone, rádio DJI e Android emulado são componentes de comunicação e execução, tratados só pelas\n"
                    "entradas e saídas. O alvo da decomposição são as tarefas. Ninguém pilota: o operador só comanda tarefas.",
           fs=11, va="top", style="italic")
    legenda(c, 40, 720)
    c.save("nivel_0.png")


# ------------------------------------------------------------------ Nível 1
NOS_SUPERIORES = [
    ("Interface do\nOperador", "executar tarefa 1 / 2,\ninterromper; painel", "#D9EAD3",
     ["pub /operador/comando", "sub /tarefa/status", "sub /falhas"]),
    ("Gerenciador\nde Tarefas", "configuração, ativa\na tarefa pedida", "#FFD966",
     ["pub /tarefa/ativa", "pub /tarefa/status", "pub /dji/acao", "sub /operador/comando", "sub /tarefa/evento", "sub /falhas"]),
    ("Tarefa 1", "voo de familiarização\nA→B→C→D→A, 4 × 60 s", "#FCE5CD",
     ["pub /setpoint", "pub /tarefa/evento", "sub /estado", "sub /tarefa/ativa"]),
    ("Tarefa 2", "balões: aproximação\n0 < d ≤ 5 cm por 60 s", "#FCE5CD",
     ["pub /setpoint", "pub /tarefa/evento", "sub /estado", "sub /alvos", "sub /mapa", "sub /tarefa/ativa"]),
    ("Supervisão e\nSegurança", "falhas, watchdog,\ntérmino seguro", "#EA9999",
     ["pub /falhas", "sub /dji/telemetria", "sub /estado"]),
    ("Registro", "rosbag2 + CSV", "#D9D9D9",
     ["sub (todos os", "tópicos)"]),
]
NOS_INFERIORES = [
    ("Estimação\nde Estado", "referencial local,\nposição, velocidade", "#CFE2F3",
     ["pub /estado", "sub /dji/telemetria"]),
    ("Controle\nde Voo", "setpoint + estado →\nvelocidade comandada", "#F4CCCC",
     ["pub /dji/cmd_vel", "sub /setpoint", "sub /estado"]),
    ("Percepção\nVisual", "detectar balões e\nestimar distância", "#CFE2F3",
     ["pub /alvos", "sub /dji/camera"]),
    ("Mapeamento\nLocal", "mapa grosseiro:\nobstáculos e balões", "#D9D2E9",
     ["pub /mapa", "sub /estado", "sub /alvos", "sub /dji/obstaculos"]),
    ("Nó Ponte\nROS 2 ↔ DJI", "tópicos ↔ socket\ndo app Android", "#F9CB9C",
     ["pub /dji/telemetria", "pub /dji/camera", "pub /dji/obstaculos", "sub /dji/cmd_vel", "sub /dji/acao"]),
]


def nivel_1():
    c = Canvas(1720, 1390)
    c.text(860, 6, "Nível 1 — Decomposição funcional do Sistema de Missões Autônomas", fs=22, ha="center", va="top",
           weight="bold", color="#333333")

    c.box(330, 100, 1390, 1150, "#93C47D")
    c.text(342, 108, "Sistema de Missões Autônomas", fs=14, va="top", weight="bold", color="#1E3D14")
    c.box(350, 140, 1370, 800, "#FFF2CC")
    c.text(362, 146, "Notebook Linux", fs=12, va="top", weight="bold", color="#5D4600")
    c.box(365, 172, 1355, 660, "#FFF9E6", ec="#C9A100")
    c.text(377, 178, "ROS 2 — nós comunicando por tópicos (publica / assina)", fs=11, va="top", weight="bold", color="#5D4600")

    largura, passo, x_ini = 152, 164, 375
    topo, base, bus0, bus1 = (205, 285), (560, 640), 408, 432
    c.box(x_ini, bus0, x_ini + 6 * passo - 12, bus1, "#A4C2F4", ec=INFO, lw=1.3, z=2)
    c.text(x_ini + (6 * passo - 12) / 2, (bus0 + bus1) / 2, "Barramento ROS 2 (DDS) — tópicos", fs=11.5,
           ha="center", va="center", color="#1C4587", weight="bold")

    def topicos(x, y_meio, linhas):
        c.text(x, y_meio, "\n".join(linhas), fs=8.5, va="center", color="#1C4587", linespacing=1.25)

    centros = {}
    for i, (tit, sub, cor, tops) in enumerate(NOS_SUPERIORES):
        x0 = x_ini + i * passo
        c.bloco(x0, topo[0], x0 + largura, topo[1], cor, tit, sub, fs=11.5, fs_sub=8.5)
        cx = x0 + largura / 2
        centros[tit] = (x0, cx)
        c.arrow([(cx, topo[1]), (cx, bus0)], color=INFO, both=True)
        topicos(cx + 6, (topo[1] + bus0) / 2, tops)
    for i, (tit, sub, cor, tops) in enumerate(NOS_INFERIORES):
        x0 = x_ini + i * passo
        c.bloco(x0, base[0], x0 + largura, base[1], cor, tit, sub, fs=11.5, fs_sub=8.5)
        cx = x0 + largura / 2
        centros[tit] = (x0, cx)
        c.arrow([(cx, bus1), (cx, base[0])], color=INFO, both=True)
        topicos(cx + 6, (bus1 + base[0]) / 2, tops)

    # cadeia de comunicação com o drone (coluna da ponte)
    _, cx_ponte = centros["Nó Ponte\nROS 2 ↔ DJI"]
    c.bloco(1060, 690, 1350, 780, "#F6B26B", "Android emulado", "app ponte DJI — Mobile SDK v5 (Kotlin)",
            fs=12.5, fs_sub=9)
    c.arrow([(cx_ponte, base[1]), (cx_ponte, 690)], color=COM, both=True)
    c.text(cx_ponte - 8, 676, "TCP (adb forward)", fs=9, color=COM, ha="right", va="center")
    c.bloco(1130, 830, 1330, 890, "#EA9999", "Rádio DJI (RC-N2)", "só enlace — sem pilotagem", fs=12, fs_sub=9)
    c.arrow([(1230, 780), (1230, 830)], color=COM, both=True)
    c.text(1240, 815, "USB (passthrough)", fs=9, color=COM, va="center")
    c.box(1060, 930, 1370, 1125, CAIXA_PRETA, ec="#111111", z=2)
    c.text(1215, 1020, "Drone DJI Mini 4 Pro", fs=14, ha="center", va="bottom", color="white", weight="bold")
    c.text(1215, 1026, "caixa-preta: estabilização, sensores,\natuadores e energia (firmware DJI)", fs=9.5,
           ha="center", va="top", color="#DDDDDD", style="italic")
    c.arrow([(1230, 890), (1230, 930)], color=COM, both=True)
    c.text(1240, 910, "RF O4", fs=9, color=COM, va="center")

    # entradas e saídas do operador, configuração e logs
    x0_if, _ = centros["Interface do\nOperador"]
    c.arrow([(30, 230), (x0_if, 230)], color=INFO)
    c.text(30, 226, "Comandos: executar tarefa 1 / 2", fs=13)
    c.arrow([(x0_if, 262), (30, 262)], color=INFO)
    c.text(40, 258, "Painel de Acompanhamento", fs=14)
    _, cx_ger = centros["Gerenciador\nde Tarefas"]
    c.arrow([(cx_ger, 72), (cx_ger, topo[0])], color=INFO)
    c.text(cx_ger, 66, "Arquivo de Configuração das Tarefas (YAML)", fs=14, ha="center")
    _, cx_reg = centros["Registro"]
    c.arrow([(cx_reg, topo[0]), (cx_reg, 72)], color=INFO)
    c.text(cx_reg, 66, "Logs Exportáveis (rosbag / CSV)", fs=14, ha="center")
    c.arrow([(30, 740), (350, 740)], color=EN)
    c.text(30, 736, "Alimentação do Notebook", fs=14, color=EN)
    c.arrow([(30, 860), (1130, 860)], color=EN)
    c.text(30, 856, "Bateria do rádio (RC)", fs=14, color=EN)

    # entradas e saídas físicas do drone
    c.box(1395, 925, 1705, 1030, "none", ec=INFO, ls="--", lw=1.1, fill=False)
    c.text(1400, 921, "Ambiente físico — sala de aula", fs=10, va="bottom", color=INFO, style="italic")
    for y, nome in [(950, "Distância (ToF / visão)"), (975, "Pressão (barômetro)"),
                    (1000, "Textura do Piso / Iluminação"), (1025, "Imagem (balões — Tarefa 2)")]:
        c.arrow([(1700, y), (1370, y)], color=INFO)
        c.text(1405, y - 3, nome, fs=11)
    c.arrow([(1700, 1055), (1370, 1055)], color=LIGHT, ls="--")
    c.text(1405, 1052, "GPS (indisponível indoor)", fs=11, color=LIGHT)
    c.arrow([(1370, 1085), (1700, 1085)], color=FORCA)
    c.text(1405, 1082, "Empuxo / Torque", fs=11, color=FORCA)
    c.arrow([(1370, 1113), (1700, 1113)], color=VIS)
    c.text(1405, 1110, "LED ON e Ready", fs=11, color=VIS)
    for x, nome, cor in [(1130, "Bateria de voo", EN), (1300, "Botão ON/OFF", VIS)]:
        c.arrow([(x, 1190), (x, 1125)], color=cor)
        c.text(x, 1196, nome, fs=12, ha="center", va="top", color=cor)

    c.text(370, 930, "Alvo da decomposição: as tarefas e os serviços ROS 2 que elas usam.\n"
                     "Tarefa 1 e Tarefa 2 reutilizam gerenciador, estimação, controle,\n"
                     "supervisão, registro e a ponte DJI; só a Tarefa 2 usa percepção\n"
                     "e mapeamento (mapa grosseiro para localizar os balões).\n"
                     "O operador só comanda \"executar tarefa N\" ou \"interromper\".\n\n"
                     "Android emulado, rádio DJI e drone: componentes de\n"
                     "comunicação e execução, tratados só pelas entradas e saídas.",
           fs=11.5, va="top", style="italic", linespacing=1.4)
    legenda(c, 40, 1215)
    c.save("nivel_1.png")


if __name__ == "__main__":
    nivel_0()
    nivel_1()
