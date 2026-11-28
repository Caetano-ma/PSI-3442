#!/usr/bin/env python3
"""Métricas de um ensaio a partir do CSV de evidência (exportar_csv.py) — seção 7 do enunciado.

Tarefa 1: erro de altura (deslocamentos e permanências), desvio da trajetória em relação ao quadrado, fechamento
(posição do toque em relação à decolagem), permanência contínua concluída por vértice, reinícios, |vz| no toque e
tempo de missão. Tarefa 2: por balão, tempo contínuo válido, reinícios da contagem, contatos estimados, alvos
descartados/inalcançáveis e, se houver o avaliacao.csv do Gazebo, a distância VERDADEIRA durante a contagem.
Todas as posições aqui são as ESTIMADAS pela aplicação (/estado); a verdade do simulador só entra pelo avaliador.

    python3 analisar_ensaio.py <ensaio.csv> [--avaliacao avaliacao.csv] [--titulo "..."] [-o metricas.md]
"""
import argparse
import csv
import json
import math
import os

QUADRADO = [(0.0, 0.0), (1.5, 0.0), (1.5, 1.5), (0.0, 1.5)]
ALTURA_ALVO_M = 1.80


def ler_csv(caminho):
    with open(caminho, newline='') as f:
        return list(csv.DictReader(f))


def distancia_ao_quadrado(x, y):
    melhor = math.inf
    for (ax, ay), (bx, by) in zip(QUADRADO, QUADRADO[1:] + QUADRADO[:1]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        melhor = min(melhor, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return melhor


def f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return math.nan


def metricas_tarefa1(linhas, eventos):
    em_t1 = [l for l in linhas if l['tarefa'] in ('1', 'tarefa1')] or linhas
    altura = [abs(f(l['z_m']) - ALTURA_ALVO_M) for l in em_t1 if l['estado'] in ('pairando', 'deslocando')]
    trajeto = [distancia_ao_quadrado(f(l['x_m']), f(l['y_m'])) for l in em_t1 if l['estado'] == 'deslocando']
    pairando = [math.hypot(f(l['vx_mps']), f(l['vy_mps'])) for l in em_t1 if l['estado'] == 'pairando'
                and l['dentro'] in ('1', 'True', 'true')]
    concluidas = [(e['vertice'], f(e['permanencia_s'])) for e in eventos if e['tipo'] == 'PERMANENCIA_CONCLUIDA']
    reinicios = sum(1 for e in eventos if e['tipo'] == 'PERMANENCIA_INTERROMPIDA')
    toque = [f(e['valor']) for e in eventos if e['tipo'] == 'POUSO_CONFIRMADO']
    no_solo = [l for l in em_t1 if f(l['z_m']) < 0.05]
    fechamento = math.hypot(f(no_solo[-1]['x_m']), f(no_solo[-1]['y_m'])) if no_solo else math.nan
    inicio = next((f(e['instante_s']) for e in eventos if e['tipo'] == 'TRANSICAO' and e['estado'] == 'decolando'), 0)
    fim = next((f(e['instante_s']) for e in eventos if e['tipo'] in ('TAREFA_CONCLUIDA', 'TAREFA_ABORTADA')), math.nan)
    resultado = next((e['tipo'] for e in eventos if e['tipo'] in ('TAREFA_CONCLUIDA', 'TAREFA_ABORTADA')), '—')
    return {
        'resultado': resultado,
        'erro_altura_max_m': max(altura, default=math.nan),
        'erro_altura_rms_m': math.sqrt(sum(e * e for e in altura) / len(altura)) if altura else math.nan,
        'desvio_trajetoria_max_m': max(trajeto, default=math.nan),
        'velocidade_horizontal_max_pairado_mps': max(pairando, default=math.nan),
        'permanencias_concluidas': concluidas,
        'reinicios_contagem': reinicios,
        'fechamento_toque_m': fechamento,
        'vz_toque_mps': toque[-1] if toque else math.nan,
        'tempo_missao_s': fim - inicio,
        'falhas': [e['tipo'] for e in eventos if e['origem'] == 'supervisao'],
    }


def metricas_tarefa2(eventos, avaliacao=None, linhas=None):
    por_balao = {}
    for e in eventos:
        if e['origem'] != 'tarefa2' or not e['vertice']:
            continue
        b = por_balao.setdefault(e['vertice'], {'continuo_s': 0.0, 'reinicios': 0, 'destruido': False,
                                                'contato_estimado': 0, 'descartado': False, 'inalcancavel': False})
        if e['tipo'] == 'PERMANENCIA_CONCLUIDA':
            b['continuo_s'] = max(b['continuo_s'], f(e['permanencia_s']))
        elif e['tipo'] == 'PERMANENCIA_INTERROMPIDA':
            b['reinicios'] += 1
        elif e['tipo'] == 'BALAO_DESTRUIDO':
            b['destruido'] = True
        elif e['tipo'] == 'COLISAO_ESTIMADA':
            b['contato_estimado'] += 1
        elif e['tipo'] == 'ALVO_DESCARTADO':
            b['descartado'] = True
        elif e['tipo'] == 'ALVO_INALCANCAVEL':
            b['inalcancavel'] = True
    resultado = next((e['tipo'] for e in eventos if e['tipo'] in ('TAREFA_CONCLUIDA', 'TAREFA_ABORTADA')), '—')
    saida = {'resultado': resultado, 'baloes': por_balao,
             'falhas': [e['tipo'] for e in eventos if e['origem'] == 'supervisao']}
    def percentil(valores, q):
        v = sorted(valores)
        return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))] if v else math.nan

    pares = [(f(l['d_estimada_m']), f(l['d_real_m']), l['dentro'] in ('1', 'True', 'true')) for l in (linhas or [])
             if l.get('d_estimada_m') and l.get('d_real_m')]
    if pares:
        erros = [abs(e - r) for e, r, _ in pares]
        contando = [abs(e - r) for e, r, c in pares if c]
        saida['erro_estimacao_mediana_m'] = percentil(erros, 0.5)
        saida['erro_estimacao_p95_m'] = percentil(erros, 0.95)
        saida['erro_estimacao_contando_mediana_m'] = percentil(contando, 0.5)
        saida['erro_estimacao_contando_max_m'] = max(contando, default=math.nan)
        saida['amostras_estimacao'] = len(erros)
    if avaliacao:
        contando = [f(l['d_real_alvo_m']) for l in avaliacao if l['contando'] == '1']
        saida['d_real_contando_min_m'] = min(contando, default=math.nan)
        saida['d_real_contando_max_m'] = max(contando, default=math.nan)
        saida['amostras_contando'] = len(contando)
        saida['folga_min_nao_alvo_m'] = min((f(l['folga_nao_alvo_m']) for l in avaliacao), default=math.nan)
    return saida


def markdown(titulo, m1, m2):
    linhas = [f'## {titulo}', '']
    if m1:
        linhas += ['| Métrica (Tarefa 1) | Valor |', '|---|---|',
                   f"| Resultado | {m1['resultado']} |",
                   f"| Erro de altura máx. / RMS (pairando e deslocando) | {m1['erro_altura_max_m']:.3f} / "
                   f"{m1['erro_altura_rms_m']:.3f} m |",
                   f"| Desvio máx. da trajetória (deslocando) | {m1['desvio_trajetoria_max_m']:.3f} m |",
                   f"| Velocidade horizontal máx. contando permanência | {m1['velocidade_horizontal_max_pairado_mps']:.3f} m/s |",
                   '| Permanências concluídas | ' + ', '.join(f'{v} {t:.1f} s' for v, t in m1['permanencias_concluidas'])
                   + ' |',
                   f"| Reinícios da contagem | {m1['reinicios_contagem']} |",
                   f"| Fechamento (toque × decolagem) | {m1['fechamento_toque_m']:.3f} m |",
                   f"| \\|vz\\| no toque | {m1['vz_toque_mps']:.2f} m/s |",
                   f"| Tempo de missão | {m1['tempo_missao_s']:.1f} s |",
                   f"| Falhas da supervisão | {', '.join(m1['falhas']) or 'nenhuma'} |", '']
    if m2:
        linhas += ['| Balão (Tarefa 2) | Contínuo válido | Reinícios | Destruído | Contato estimado | Descartado/inalcançável |',
                   '|---|---|---|---|---|---|']
        for nome, b in m2['baloes'].items():
            linhas.append(f"| {nome} | {b['continuo_s']:.1f} s | {b['reinicios']} | {'sim' if b['destruido'] else 'não'} | "
                          f"{b['contato_estimado']} | {'descartado' if b['descartado'] else ''}"
                          f"{'inalcançável' if b['inalcancavel'] else ''} |")
        linhas += ['', f"Resultado: {m2['resultado']}; falhas da supervisão: {', '.join(m2['falhas']) or 'nenhuma'}."]
        if 'd_real_contando_min_m' in m2:
            linhas.append(f"Distância VERDADEIRA durante a contagem (avaliador): {m2['d_real_contando_min_m'] * 100:.1f} a "
                          f"{m2['d_real_contando_max_m'] * 100:.1f} cm em {m2['amostras_contando']} amostras; menor folga a "
                          f"balões não alvo: {m2['folga_min_nao_alvo_m']:.2f} m.")
        if 'erro_estimacao_mediana_m' in m2:
            linhas.append(f"Erro de estimação de d, |estimada − real|, na aproximação final e na permanência "
                          f"({m2['amostras_estimacao']} amostras): mediana {m2['erro_estimacao_mediana_m'] * 100:.1f} cm, "
                          f"percentil 95 {m2['erro_estimacao_p95_m'] * 100:.1f} cm; durante a contagem: mediana "
                          f"{m2['erro_estimacao_contando_mediana_m'] * 100:.1f} cm, máximo "
                          f"{m2['erro_estimacao_contando_max_m'] * 100:.1f} cm.")
        linhas.append('')
    return '\n'.join(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv')
    ap.add_argument('--avaliacao', default='')
    ap.add_argument('--titulo', default='Ensaio')
    ap.add_argument('-o', '--saida', default='')
    a = ap.parse_args()
    linhas = ler_csv(a.csv)
    eventos = ler_csv(os.path.splitext(a.csv)[0] + '_eventos.csv')
    tarefas = {e['origem'] for e in eventos}
    m1 = metricas_tarefa1(linhas, [e for e in eventos if e['origem'] in ('tarefa1', 'supervisao', 'operador')]) \
        if 'tarefa1' in tarefas else None
    m2 = metricas_tarefa2(eventos, ler_csv(a.avaliacao) if a.avaliacao else None, linhas) if 'tarefa2' in tarefas \
        else None
    texto = markdown(a.titulo, m1, m2)
    print(texto)
    if a.saida:
        with open(a.saida, 'w') as fh:
            fh.write(texto)
        with open(os.path.splitext(a.saida)[0] + '.json', 'w') as fh:
            json.dump({'tarefa1': m1, 'tarefa2': m2}, fh, indent=2, ensure_ascii=False, default=str)


if __name__ == '__main__':
    main()
