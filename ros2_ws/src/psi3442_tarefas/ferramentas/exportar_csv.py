#!/usr/bin/env python3
"""ExportadorCsv (nível n): converte o bag de uma execução no CSV de evidência (P05, P06, T01–T04).

Uma linha por amostra de /estado (10 Hz), com colunas:
    instante_s, tarefa, estado, vertice, x_m, y_m, z_m, vx_mps, vy_mps, vz_mps, dentro, permanencia_s,
    cmd_vx_mps, cmd_vy_mps, cmd_vz_mps, bateria_pct, evento, tipo_falha, d_estimada_m, d_real_m
`evento` e `tipo_falha` listam (separados por "|") o que ocorreu desde a linha anterior. Também gera
<saida>_eventos.csv com todos os eventos discretos e falhas, um por linha.

Uso (com o ROS 2 carregado):  python3 exportar_csv.py <pasta_do_bag> [-o saida.csv]
"""
import argparse
import csv
import math
import os
import sys

COLUNAS = ['instante_s', 'tarefa', 'estado', 'vertice', 'x_m', 'y_m', 'z_m', 'vx_mps', 'vy_mps', 'vz_mps',
           'dentro', 'permanencia_s', 'cmd_vx_mps', 'cmd_vy_mps', 'cmd_vz_mps', 'bateria_pct', 'evento',
           'tipo_falha', 'd_estimada_m', 'd_real_m']
COLUNAS_EVENTOS = ['instante_s', 'origem', 'tipo', 'estado', 'vertice', 'permanencia_s', 'valor', 'detalhe']
NOMES_ACAO = {1: 'decolar', 2: 'pousar', 3: 'habilitar_controle_virtual', 4: 'desabilitar_controle_virtual',
              5: 'parar_e_pairar'}
IDADE_MAX_CMD_S = 0.3       # sem cmd_vel mais novo que isto, as colunas cmd_* ficam em zero (nada comandado)


class MontadorCsv:
    """Monta as linhas a partir das mensagens em ordem de tempo (t em segundos). Sem dependência de ROS 2."""

    def __init__(self):
        self.d_estimada = self.d_real = math.nan     # Tarefa 2: /tarefa2/distancia e /avaliador/distancia_m
        self.t0 = None
        self.linhas, self.eventos = [], []
        self.tarefa, self.estado, self.vertice = 0, '', ''
        self.contando_desde, self.permanencia = None, 0.0
        self.cmd, self.t_cmd = (0.0, 0.0, 0.0), None
        self.bateria = float('nan')
        self.pendentes_evento, self.pendentes_falha = [], []

    def _rel(self, t):
        if self.t0 is None:
            self.t0 = t
        return t - self.t0

    def ao_evento(self, t, ev):
        rel = self._rel(t)
        self.tarefa = ev.tarefa
        if ev.estado:
            self.estado = ev.estado
        self.vertice = ev.nome_vertice
        if ev.tipo == 'PERMANENCIA_INICIADA':
            self.contando_desde, self.permanencia = t, 0.0
        elif ev.tipo == 'PERMANENCIA_INTERROMPIDA':
            self.contando_desde, self.permanencia = None, 0.0
        elif ev.tipo == 'PERMANENCIA_CONCLUIDA':
            self.contando_desde, self.permanencia = None, ev.permanencia_s
        elif ev.tipo == 'TRANSICAO':
            self.contando_desde = None
        tipo = ev.tipo
        if tipo == 'SOLICITA_ACAO':
            tipo = f'SOLICITA_ACAO:{NOMES_ACAO.get(ev.acao, ev.acao)}'
        self.pendentes_evento.append(ev.estado if ev.tipo == 'TRANSICAO' else tipo)
        self.eventos.append([f'{rel:.3f}', f'tarefa{ev.tarefa}', tipo, ev.estado, ev.nome_vertice,
                             f'{ev.permanencia_s:.2f}', f'{ev.valor:.3f}', ev.detalhe])

    def ao_falha(self, t, falha):
        rel = self._rel(t)
        self.pendentes_falha.append(falha.nome_tipo)
        self.eventos.append([f'{rel:.3f}', 'supervisao', falha.nome_tipo, '', '', '', str(falha.reacao),
                             falha.detalhe])

    def ao_comando_operador(self, t, msg):
        rel = self._rel(t)
        nomes = {1: 'executar tarefa 1', 2: 'executar tarefa 2', 3: 'interromper'}
        self.pendentes_evento.append(f'operador:{nomes.get(msg.acao, msg.acao)}')
        self.eventos.append([f'{rel:.3f}', 'operador', nomes.get(msg.acao, str(msg.acao)), '', '', '', '', ''])

    def ao_cmd_vel(self, t, cmd):
        self._rel(t)
        self.cmd, self.t_cmd = (cmd.vx_mps, cmd.vy_mps, cmd.vz_mps), t

    def ao_telemetria(self, t, tel):
        self._rel(t)
        self.bateria = tel.bateria_pct

    def ao_distancia(self, t, msg):
        self.d_estimada = msg.data

    def ao_distancia_real(self, t, msg):
        self.d_real = msg.data

    def ao_estado(self, t, e):
        rel = self._rel(t)
        dentro = self.contando_desde is not None
        permanencia = t - self.contando_desde if dentro else self.permanencia
        if self.t_cmd is None or t - self.t_cmd > IDADE_MAX_CMD_S:
            self.cmd = (0.0, 0.0, 0.0)
        self.linhas.append([
            f'{rel:.3f}', self.tarefa, self.estado, self.vertice,
            f'{e.x_m:.4f}', f'{e.y_m:.4f}', f'{e.z_m:.4f}', f'{e.vx_mps:.4f}', f'{e.vy_mps:.4f}', f'{e.vz_mps:.4f}',
            int(dentro), f'{permanencia:.2f}',
            f'{self.cmd[0]:.4f}', f'{self.cmd[1]:.4f}', f'{self.cmd[2]:.4f}', f'{self.bateria:.1f}',
            '|'.join(self.pendentes_evento), '|'.join(self.pendentes_falha),
            f'{self.d_estimada:.4f}' if math.isfinite(self.d_estimada) else '',
            f'{self.d_real:.4f}' if math.isfinite(self.d_real) else '',
        ])
        self.pendentes_evento, self.pendentes_falha = [], []

    def gravar(self, caminho):
        with open(caminho, 'w', newline='', encoding='utf-8') as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(COLUNAS)
            escritor.writerows(self.linhas)
        caminho_eventos = os.path.splitext(caminho)[0] + '_eventos.csv'
        with open(caminho_eventos, 'w', newline='', encoding='utf-8') as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(COLUNAS_EVENTOS)
            escritor.writerows(self.eventos)
        return caminho, caminho_eventos


def ler_bag(pasta, topicos=None):
    """Gera (t_s, tópico, mensagem) em ordem de gravação, só dos `topicos` pedidos (os outros nem são
    desserializados: um bag gravado com outra versão de uma mensagem não usada não impede a exportação)."""
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    leitor = rosbag2_py.SequentialReader()
    try:
        leitor.open(rosbag2_py.StorageOptions(uri=pasta, storage_id=''),
                    rosbag2_py.ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr'))
    except RuntimeError as erro:
        if not os.path.exists(os.path.join(pasta, 'metadata.yaml')):
            raise SystemExit(f'{pasta} sem metadata.yaml (gravação interrompida sem Ctrl+C?). '
                             f'Recupere com: ros2 bag reindex {pasta} -s mcap') from erro
        raise
    tipos = {t.name: get_message(t.type) for t in leitor.get_all_topics_and_types()}
    descartadas = 0
    while leitor.has_next():
        topico, dados, t_ns = leitor.read_next()
        if topicos is not None and topico not in topicos:
            continue
        try:
            msg = deserialize_message(dados, tipos[topico])
        except Exception:
            descartadas += 1
            continue
        yield t_ns * 1e-9, topico, msg
    if descartadas:
        print(f'aviso: {descartadas} mensagens ilegíveis ignoradas (definição diferente da gravada)')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument('bag', help='pasta do bag (rosbag2)')
    parser.add_argument('-o', '--saida', help='CSV de saída (padrão: <bag>.csv)')
    args = parser.parse_args(argv)
    montador = MontadorCsv()
    despacho = {'/estado': montador.ao_estado, '/tarefa/evento': montador.ao_evento,
                '/falhas': montador.ao_falha, '/dji/cmd_vel': montador.ao_cmd_vel,
                '/dji/telemetria': montador.ao_telemetria, '/operador/comando': montador.ao_comando_operador,
                '/tarefa2/distancia': montador.ao_distancia, '/avaliador/distancia_m': montador.ao_distancia_real}
    for t, topico, msg in ler_bag(args.bag, set(despacho)):
        if topico in despacho:
            despacho[topico](t, msg)
    saida = args.saida or os.path.normpath(args.bag) + '.csv'
    for caminho in montador.gravar(saida):
        print(f'gravado: {caminho}')
    print(f'{len(montador.linhas)} linhas, {len(montador.eventos)} eventos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
