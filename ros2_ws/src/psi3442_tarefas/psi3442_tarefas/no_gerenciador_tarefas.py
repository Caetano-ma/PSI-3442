"""SeletorTarefa (nível n) e nó ROS 2 do gerenciador de tarefas.

Executa Nivel1::ModosOperacao: ocioso -> tarefa1 / tarefa2 -> ocioso; falha ou "interromper" -> terminoSeguro
(pouso no local, nunca retorno por GNSS) -> ocioso.
- Só o gerenciador envia comandos discretos ao SDK (/dji/acao): repassa os pedidos (SOLICITA_ACAO) da tarefa ativa
  e comanda o pouso no término seguro.
- Critério de progressão: a Tarefa 2 só é aceita depois de a Tarefa 1 ter sido concluída em voo real. O registro
  persiste em arquivo (`arquivo_progresso`); conclusões com `simulacao = true` não contam.
- Publica /tarefa/status a 2 Hz com o que o painel mostra (estado, vértice, cronômetro, posição, bateria, falhas).

Assina /operador/comando, /tarefa/evento, /falhas, /dji/telemetria, /estado.
Publica /tarefa/ativa, /dji/acao, /tarefa/status.
"""
import datetime
import json
import os

from .tipos import (DESABILITAR_CONTROLE_VIRTUAL, EXECUTAR_TAREFA1, EXECUTAR_TAREFA2, INTERROMPER, NOMES_ACAO,
                    POUSAR, TERMINO_SEGURO, VOLTAR_OCIOSO)

OCIOSO, TAREFA1, TAREFA2, TERMINO = 'ocioso', 'tarefa1', 'tarefa2', 'terminoSeguro'
MODO_DA_TAREFA = {1: TAREFA1, 2: TAREFA2}
TAREFA_DO_MODO = {TAREFA1: 1, TAREFA2: 2}


class SeletorTarefa:
    def __init__(self, simulacao=False, arquivo_progresso=None, prazo_telemetria_s=0.5):
        self.simulacao = simulacao
        self.arquivo_progresso = arquivo_progresso
        self.prazo_telemetria_s = prazo_telemetria_s
        self.modo = OCIOSO
        self.tarefa1_concluida_voo_real = self._ler_progresso()
        self.mensagem = 'pronto'
        self.ultima_falha = ''
        self.tel, self.t_tel, self.estado = None, None, None
        self._acompanhamento = {'estado': '', 'vertice': -1, 'nome_vertice': '', 'permanencia_s': 0.0,
                                'contando_desde': None}
        self.saidas = []                    # ('ativa', n) e ('acao', tipo), consumidas pelo nó

    # ------------------------------------------------------------------ progresso persistente
    def _ler_progresso(self):
        if not self.arquivo_progresso or not os.path.exists(self.arquivo_progresso):
            return False
        try:
            with open(self.arquivo_progresso, encoding='utf-8') as arquivo:
                return bool(json.load(arquivo).get('tarefa1_concluida_voo_real', False))
        except (OSError, ValueError):
            return False

    def _gravar_progresso(self, detalhe):
        if not self.arquivo_progresso:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.arquivo_progresso)), exist_ok=True)
        with open(self.arquivo_progresso, 'w', encoding='utf-8') as arquivo:
            json.dump({'tarefa1_concluida_voo_real': True,
                       'quando': datetime.datetime.now().isoformat(timespec='seconds'),
                       'detalhe': detalhe}, arquivo, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ auxiliares
    def _em_voo(self):
        return self.tel is not None and (self.tel.em_voo or self.tel.motores_ligados)

    def _telemetria_atual(self, agora):
        return self.t_tel is not None and agora - self.t_tel <= self.prazo_telemetria_s

    def _ativar(self, numero):
        self.saidas.append(('ativa', numero))

    def _acao(self, tipo):
        self.saidas.append(('acao', tipo))

    def _ir_ocioso(self, mensagem):
        self.modo = OCIOSO
        self.mensagem = mensagem
        self._ativar(0)
        self._acao(DESABILITAR_CONTROLE_VIRTUAL)

    def _termino_seguro(self, motivo):
        self._ativar(0)
        if self._em_voo():
            self.modo = TERMINO
            self._acao(POUSAR)
            self.mensagem = f'término seguro (pouso no local): {motivo}'
        else:
            self._ir_ocioso(f'tarefa encerrada antes do voo: {motivo}')

    def consumir_saidas(self):
        saidas, self.saidas = self.saidas, []
        return saidas

    # ------------------------------------------------------------------ entradas
    def ao_comando(self, acao, agora):
        if acao == INTERROMPER:
            if self.modo in (TAREFA1, TAREFA2):
                self._termino_seguro('interrompida pelo operador')
            elif self.modo == TERMINO:
                self._acao(POUSAR)
                self.mensagem = 'já em término seguro: pouso reenviado'
            else:
                self.mensagem = 'nada a interromper'
            return
        if acao not in (EXECUTAR_TAREFA1, EXECUTAR_TAREFA2):
            self.mensagem = f'comando desconhecido: {acao}'
            return
        numero = 1 if acao == EXECUTAR_TAREFA1 else 2
        if self.modo != OCIOSO:
            self.mensagem = f'recusado: executar tarefa {numero} com o sistema em {self.modo}'
            return
        if numero == 2:
            if not self.tarefa1_concluida_voo_real:
                self.mensagem = 'recusado: a Tarefa 2 só é aceita depois da Tarefa 1 concluída em voo real'
            else:
                self.mensagem = 'recusado: Tarefa 2 ainda não implementada (ciclo C5)'
            return
        if not self._telemetria_atual(agora):
            self.mensagem = 'recusado: sem telemetria da ponte DJI'
            return
        if self._em_voo():
            self.mensagem = 'recusado: a aeronave precisa estar pousada em A com os motores desligados'
            return
        self.modo = MODO_DA_TAREFA[numero]
        self.mensagem = f'tarefa {numero} iniciada'
        self.ultima_falha = ''
        self._acompanhamento.update(estado='', vertice=-1, nome_vertice='', permanencia_s=0.0, contando_desde=None)
        self._ativar(numero)

    def ao_evento(self, ev, agora):
        a = self._acompanhamento
        if ev.estado:
            a['estado'] = ev.estado
        a['vertice'], a['nome_vertice'] = ev.vertice, ev.nome_vertice
        if ev.tipo == 'PERMANENCIA_INICIADA':
            a['permanencia_s'], a['contando_desde'] = 0.0, agora
        elif ev.tipo in ('PERMANENCIA_INTERROMPIDA', 'TRANSICAO'):
            a['permanencia_s'] = 0.0 if ev.tipo == 'PERMANENCIA_INTERROMPIDA' else a['permanencia_s']
            a['contando_desde'] = None
        elif ev.tipo == 'PERMANENCIA_CONCLUIDA':
            a['permanencia_s'], a['contando_desde'] = ev.permanencia_s, None

        modo_da_tarefa = MODO_DA_TAREFA.get(ev.tarefa)
        if ev.tipo == 'SOLICITA_ACAO':
            if self.modo == modo_da_tarefa or (self.modo == TERMINO and ev.acao == POUSAR):
                self._acao(ev.acao)
            else:
                self.mensagem = f'pedido {NOMES_ACAO.get(ev.acao, ev.acao)} ignorado no modo {self.modo}'
        elif ev.tipo == 'TAREFA_CONCLUIDA' and self.modo == modo_da_tarefa:
            if ev.tarefa == 1 and not self.simulacao:
                self.tarefa1_concluida_voo_real = True
                self._gravar_progresso(ev.detalhe)
            sufixo = ' (simulação: não conta como voo real)' if self.simulacao else ''
            self._ir_ocioso(f'tarefa {ev.tarefa} concluída{sufixo}')
        elif ev.tipo == 'TAREFA_ABORTADA' and self.modo in (modo_da_tarefa, TERMINO):
            self._ir_ocioso(f'tarefa {ev.tarefa} abortada: {ev.detalhe}')
        elif ev.tipo == 'PREPARACAO_FALHOU' and self.modo == modo_da_tarefa:
            self._ir_ocioso(f'preparação falhou: {ev.detalhe}')

    def ao_falha(self, falha):
        self.ultima_falha = f'{falha.nome_tipo}: {falha.detalhe}'
        if falha.reacao == TERMINO_SEGURO:
            if self.modo in (TAREFA1, TAREFA2):
                self._termino_seguro(falha.nome_tipo)
            elif self.modo == OCIOSO and self._em_voo():
                self.modo = TERMINO
                self._acao(POUSAR)
                self.mensagem = f'aeronave em voo sem tarefa ativa: pouso no local ({falha.nome_tipo})'
        elif falha.reacao == VOLTAR_OCIOSO and self.modo in (TAREFA1, TAREFA2) and not self._em_voo():
            self._ir_ocioso(f'tarefa encerrada antes do voo: {falha.nome_tipo}')

    def ao_telemetria(self, tel, agora):
        self.tel, self.t_tel = tel, agora
        if self.modo == TERMINO and not tel.em_voo and not tel.motores_ligados:
            self._ir_ocioso('pousado após término seguro')

    def ao_estado(self, estado):
        self.estado = estado

    # ------------------------------------------------------------------ painel
    def status(self, agora):
        a = self._acompanhamento
        permanencia = a['permanencia_s'] if a['contando_desde'] is None else agora - a['contando_desde']
        e, tel = self.estado, self.tel
        return {
            'modo': self.modo,
            'tarefa': TAREFA_DO_MODO.get(self.modo, 0),
            'estado': a['estado'],
            'vertice': a['vertice'],
            'nome_vertice': a['nome_vertice'],
            'permanencia_s': float(permanencia),
            'dentro': a['contando_desde'] is not None,
            'x_m': e.x_m if e else 0.0, 'y_m': e.y_m if e else 0.0, 'z_m': e.z_m if e else 0.0,
            'vx_mps': e.vx_mps if e else 0.0, 'vy_mps': e.vy_mps if e else 0.0, 'vz_mps': e.vz_mps if e else 0.0,
            'estado_valido': bool(e.valido) if e else False,
            'bateria_pct': float(tel.bateria_pct) if tel else 0.0,
            'ponte_conectada': self._telemetria_atual(agora),
            'tarefa1_concluida_voo_real': self.tarefa1_concluida_voo_real,
            'ultima_falha': self.ultima_falha,
            'mensagem': self.mensagem,
        }


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import (ComandoDiscreto, ComandoOperador, EstadoEstimado, EventoTarefa,
                                        Falha as FalhaMsg, StatusTarefa, TarefaAtiva, Telemetria as TelemetriaMsg)

    from . import ros_util
    from .tipos import Estado, Evento, Falha, Telemetria, de_mensagem

    class NoGerenciadorTarefas(Node):
        def __init__(self):
            super().__init__('gerenciador_tarefas')
            cfg = ros_util.carregar_config(self)
            self.declare_parameter('simulacao', False)
            self.declare_parameter('arquivo_progresso', os.path.expanduser('~/.psi3442/progresso.json'))
            simulacao = self.get_parameter('simulacao').get_parameter_value().bool_value
            arquivo = self.get_parameter('arquivo_progresso').get_parameter_value().string_value
            self.seletor = SeletorTarefa(simulacao, arquivo, cfg.seguranca.prazo_telemetria_s)
            self.ultima_linha = ''
            if simulacao:
                self.get_logger().warn('modo simulação: conclusões não contam como voo real')
            self.pub_ativa = self.create_publisher(TarefaAtiva, '/tarefa/ativa', ros_util.QOS_LATCHED)
            self.pub_acao = self.create_publisher(ComandoDiscreto, '/dji/acao', ros_util.QOS_CONFIAVEL)
            self.pub_status = self.create_publisher(StatusTarefa, '/tarefa/status', ros_util.QOS_CONFIAVEL)
            self.create_subscription(ComandoOperador, '/operador/comando', self.ao_comando, ros_util.QOS_CONFIAVEL)
            self.create_subscription(EventoTarefa, '/tarefa/evento', self.ao_evento, ros_util.QOS_CONFIAVEL)
            self.create_subscription(FalhaMsg, '/falhas', self.ao_falha, ros_util.QOS_CONFIAVEL)
            self.create_subscription(TelemetriaMsg, '/dji/telemetria', self.ao_telemetria, ros_util.QOS_FLUXO)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_timer(0.5, self.publicar_status)
            self.pub_ativa.publish(ros_util.carimbar(self, TarefaAtiva(numero=0)))

        def despachar(self):
            for tipo, valor in self.seletor.consumir_saidas():
                if tipo == 'ativa':
                    self.pub_ativa.publish(ros_util.carimbar(self, TarefaAtiva(numero=valor)))
                else:
                    self.pub_acao.publish(ros_util.carimbar(self, ComandoDiscreto(tipo=valor)))
                    self.get_logger().info(f'/dji/acao: {NOMES_ACAO.get(valor, valor)}')
            linha = f'[{self.seletor.modo}] {self.seletor.mensagem}'
            if linha != self.ultima_linha:
                self.ultima_linha = linha
                self.get_logger().info(linha)

        def ao_comando(self, msg):
            self.seletor.ao_comando(msg.acao, ros_util.agora())
            self.despachar()
            self.publicar_status()

        def ao_evento(self, msg):
            self.seletor.ao_evento(de_mensagem(Evento, msg), ros_util.agora())
            self.despachar()

        def ao_falha(self, msg):
            self.seletor.ao_falha(Falha(tipo=msg.tipo, reacao=msg.reacao, detalhe=msg.detalhe))
            self.despachar()

        def ao_telemetria(self, msg):
            self.seletor.ao_telemetria(de_mensagem(Telemetria, msg), ros_util.agora())
            self.despachar()

        def ao_estado(self, msg):
            self.seletor.ao_estado(de_mensagem(Estado, msg))

        def publicar_status(self):
            status = StatusTarefa(**self.seletor.status(ros_util.agora()))
            self.pub_status.publish(ros_util.carimbar(self, status))

    rclpy.init(args=args)
    ros_util.executar(NoGerenciadorTarefas())


if __name__ == '__main__':
    main()
