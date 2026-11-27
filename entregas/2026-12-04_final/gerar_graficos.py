"""Gráficos do relatório e da apresentação a partir dos resultados em ensaios/simulacao/ (Python do sistema +
matplotlib). Todos os resultados aqui são de SIMULAÇÃO (Gazebo, relógio do simulador) ou do conjunto sintético.

    python3 gerar_graficos.py      # grava figuras/*.png
"""
import csv
import json
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parent.parent
SIM = RAIZ / 'ensaios' / 'simulacao'
FIG = PASTA / 'figuras'

# paleta de referência (categórica em ordem fixa) e tintas de texto
AZUL, LARANJA, AQUA = '#257de0', '#f47230', '#00b894'
TEXTO, TEXTO2, GRADE, FAIXA = '#191919', '#666666', '#e6e6e6', '#cce3fd'
COR_BALAO = {'vermelho': '#ec4647', 'azul': '#257de0', 'verde': '#008a17', 'amarelo': '#f2a600', 'roxo': '#6a4ce2'}

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': TEXTO2, 'axes.labelcolor': TEXTO,
    'xtick.color': TEXTO2, 'ytick.color': TEXTO2, 'axes.grid': True, 'grid.color': GRADE, 'grid.linewidth': 0.8,
    'axes.spines.top': False, 'axes.spines.right': False, 'lines.linewidth': 2, 'figure.dpi': 160,
    'axes.titlesize': 10, 'axes.titleweight': 'bold', 'axes.titlecolor': TEXTO, 'legend.frameon': False,
    'axes.axisbelow': True, 'axes.formatter.use_locale': False,
})


def virgula(v, casas=2):
    return f'{v:.{casas}f}'.replace('.', ',')


def ler_csv(caminho):
    with open(caminho, newline='') as f:
        return list(csv.DictReader(f))


def salvar(fig, nome, ajustar=True):
    FIG.mkdir(exist_ok=True)
    if ajustar:
        fig.tight_layout()
    fig.savefig(FIG / nome, facecolor='white')
    plt.close(fig)
    print('figura:', FIG / nome)


def tarefa1(pasta):
    linhas = ler_csv(pasta / 'ensaio.csv')
    t = [float(l['instante_s']) for l in linhas]
    z = [float(l['z_m']) for l in linhas]
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.axhspan(1.70, 1.90, color=FAIXA, lw=0, label='tolerância P05 (±0,10 m)')
    verdade = pasta / 'verdade.csv'
    if verdade.exists():
        v = ler_csv(verdade)
        ax.plot([float(l['t_s']) for l in v], [float(l['z_real_m']) for l in v], color=LARANJA, lw=1.2,
                label='altura real (simulador)')
    ax.plot(t, z, color=AZUL, label='altura estimada (ToF)')
    for e in ler_csv(pasta / 'ensaio_eventos.csv'):
        if e['tipo'] == 'PERMANENCIA_CONCLUIDA':
            ax.annotate(f"{e['vertice']}: {float(e['permanencia_s']):.0f} s", (float(e['instante_s']), 1.93),
                        ha='right', fontsize=7.5, color=TEXTO2)
    ax.set(xlabel='tempo (s, relógio do simulador)', ylabel='z (m)', ylim=(0, 2.1),
           title='Tarefa 1 no Gazebo — altura e permanências de 60 s')
    ax.legend(loc='lower center', ncol=3, fontsize=7.5)
    salvar(fig, 't1_altura.png')

    fig, ax = plt.subplots(figsize=(3.6, 3.6))
    q = [(0, 0), (1.5, 0), (1.5, 1.5), (0, 1.5), (0, 0)]
    ax.plot(*zip(*q), color=TEXTO2, lw=1, ls='--', label='quadrado de referência')
    if verdade.exists():
        v = [l for l in ler_csv(verdade) if float(l['z_real_m']) > 0.3]
        ax.plot([float(l['x_real_m']) for l in v], [float(l['y_real_m']) for l in v], color=LARANJA, lw=1.2,
                label='trajetória real')
    voo = [l for l in linhas if float(l['z_m']) > 0.3]
    ax.plot([float(l['x_m']) for l in voo], [float(l['y_m']) for l in voo], color=AZUL, label='estimada')
    for nome, (x, y) in zip('ABCD', q):
        ax.annotate(nome, (x, y), xytext=(-12 if x == 0 else 6, -12 if y == 0 else 6), textcoords='offset points',
                    fontweight='bold', color=TEXTO)
    ax.set(xlabel='x (m)', ylabel='y (m)', aspect='equal', xlim=(-0.4, 1.9), ylim=(-0.4, 1.9),
           title='Tarefa 1 — vista de cima')
    ax.legend(loc='center', fontsize=7)
    salvar(fig, 't1_trajetoria.png')


def tarefa2(pasta, sufixo=''):
    sala = pasta / 'sala'
    av = ler_csv(sala / 'avaliacao.csv')
    verdade = yaml.safe_load((sala / 'verdade.yaml').read_text())
    resumo = yaml.safe_load((sala / 'resumo.yaml').read_text()) if (sala / 'resumo.yaml').exists() else {}

    # distância real ao alvo mais próximo, nas janelas de aproximação final e permanência
    t = [float(l['t_sim_s']) for l in av]
    d = [float(l['d_real_alvo_m']) * 100 for l in av]
    contando = [l['contando'] == '1' for l in av]
    perms = resumo.get('permanencias', [])
    if perms:
        n = len(perms)
        fig, eixos = plt.subplots(1, n, figsize=(min(2.3 * n + 0.6, 7.2), 2.6), sharey=True, squeeze=False)
        for ax, p in zip(eixos[0], perms):
            ini, fim = p['inicio_s'] - 8, p.get('fim_s', p['inicio_s']) + 3
            idx = [k for k, tk in enumerate(t) if ini <= tk <= fim]
            ax.axhspan(0, 5, color=FAIXA, lw=0)
            ax.plot([t[k] - p['inicio_s'] for k in idx], [d[k] for k in idx], color=AZUL, lw=1.4)
            cont = [k for k in idx if contando[k]]
            ax.plot([t[k] - p['inicio_s'] for k in cont], [d[k] for k in cont], color=LARANJA, lw=2.4)
            ax.set(title=p['alvo'], xlabel='s desde o início da contagem', ylim=(0, 25))
        eixos[0][0].set_ylabel('d real (cm)')
        eixos[0][0].plot([], [], color=AZUL, label='aproximação')
        eixos[0][0].plot([], [], color=LARANJA, lw=2.4, label='contando (0 < d ≤ 5 cm)')
        eixos[0][0].legend(loc='upper right', fontsize=7)
        fig.suptitle('Tarefa 2 no Gazebo — distância VERDADEIRA durante a aproximação e a permanência',
                     fontsize=9.5, fontweight='bold', color=TEXTO)
        salvar(fig, f't2_distancia{sufixo}.png')

    # vista de cima: balões reais e trajetória real
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    ax.plot([float(l['x_m']) for l in av], [float(l['y_m']) for l in av], color='#9c9c9c', lw=1, label='trajetória real')
    destruidas = [x['cor_real'] for x in resumo.get('destruidos', [])]
    for b in verdade['baloes']:
        cor = COR_BALAO[b['cor']]
        ax.scatter(b['x'], b['y'], s=150, color=cor, edgecolors='white', linewidths=2, zorder=3)
        rot = b['cor'] + (' (alvo)' if b['alvo'] else '')
        ax.annotate(rot, (b['x'], b['y']), xytext=(8, -3), textcoords='offset points', fontsize=7.5, color=TEXTO)
    ax.scatter(0, 0, marker='s', s=60, color=TEXTO, zorder=3)
    ax.annotate('decolagem', (0, 0), xytext=(6, -10), textcoords='offset points', fontsize=7.5, color=TEXTO2)
    ax.set(xlabel='x (m)', ylabel='y (m)', aspect='equal',
           title=f"Sala (semente {verdade['semente']}) — balões destruídos: {len(destruidas)}")
    ax.legend(loc='upper right', fontsize=7)
    salvar(fig, f't2_sala{sufixo}.png')


def detector():
    caminho = RAIZ / 'ros2_ws' / 'src' / 'psi3442_tarefas' / 'modelos' / 'metricas_detector.json'
    if not caminho.exists():
        return
    m = json.loads(caminho.read_text())
    faixas = list(m['revocacao_por_diametro_px'].items())
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    ax.bar([f for f, _ in faixas], [v for _, v in faixas], color=AZUL, width=0.75)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: virgula(v)))
    ax.set(ylim=(0, 1.05), ylabel='revocação', xlabel='diâmetro aparente do balão (px)',
           title='Revocação do detector por tamanho aparente')
    ax.tick_params(axis='x', labelsize=7, rotation=30)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.text(0.01, 0.015, f"Validação sintética ({m['imagens']} imagens): precisão {virgula(m['precisao'])}, "
             f"revocação {virgula(m['revocacao'])}, {m['cor_trocada']} trocas de cor", fontsize=8, color=TEXTO2)
    salvar(fig, 'detector_revocacao.png', ajustar=False)


def main():
    if (SIM / 't1_gazebo_60s').exists():
        tarefa1(SIM / 't1_gazebo_60s')
    for pasta in sorted(SIM.glob('t2_gazebo_*')):
        if (pasta / 'sala' / 'avaliacao.csv').exists():
            tarefa2(pasta, '_' + pasta.name.split('_')[-1])
    detector()


if __name__ == '__main__':
    main()
