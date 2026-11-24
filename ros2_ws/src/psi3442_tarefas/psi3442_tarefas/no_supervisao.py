"""MonitorFalhas (nível n) e nó ROS 2 de supervisão e segurança (R07).

Tabela de tratamento (tipo -> detecção -> reação), conforme 03_NivelN.sysml:
    perdaEnlace                 conectado = false (em voo)          término seguro (a aeronave já pousa sozinha)
    perdaPonte                  sem telemetria > prazo_perda_ponte   término seguro (o app ponte comanda pouso)
    telemetriaAtrasada          amostra > prazo_telemetria           velocidade zero; persistindo, término seguro
    bateriaBaixa                carga < bateria_critica (em voo)     término seguro
    estimativaInvalida          estado.valido = false (em voo)       velocidade zero; persistindo, término seguro
    posicionamentoVisualInativo chave do SDK = false (em voo)        término seguro
    desvioExcessivo             distância à trajetória > desvio_max  término seguro
    tempoTarefaExcedido         tempo desde a partida > tempo_max    término seguro
    comandoRejeitado            erro devolvido pelo SDK              publicado pelo nó ponte (no_ponte_dji)
Velocidade zero é aplicada pelo controle (estado inválido/velho) e pelo watchdog do app ponte; a supervisão só
registra. Término seguro = pouso no local, executado pelo gerenciador. Cada falha é publicada na borda de subida.

Desvio: distância horizontal de (x, y) ao contorno do quadrado, ou excesso de altura acima de altura_alvo — não
penaliza a descida vertical do pouso no local.

Assina /dji/telemetria e /estado; publica /falhas.
"""
import math

from .tipos import (BATERIA_BAIXA, DESVIO_EXCESSIVO, ESTIMATIVA_INVALIDA, PERDA_ENLACE, PERDA_PONTE,
                    POSICIONAMENTO_VISUAL_INATIVO, REGISTRAR, TELEMETRIA_ATRASADA, TEMPO_TAREFA_EXCEDIDO,
                    TERMINO_SEGURO, VELOCIDADE_ZERO, Falha)


def distancia_ponto_segmento_2d(px, py, a, b):
    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]
    dx, dy = bx - ax, by - ay
    comprimento2 = dx * dx + dy * dy
    t = 0.0 if comprimento2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / comprimento2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class MonitorFalhas:
    def __init__(self, seguranca, vertices_sequencia, altura_alvo_m):
        """`seguranca`: ConfigSeguranca; `vertices_sequencia`: pontos (x, y, z) na ordem do percurso."""
        self.cfg = seguranca
        pontos = list(vertices_sequencia)
        self.segmentos = [(pontos[i], pontos[i + 1]) for i in range(len(pontos) - 1)] or [(pontos[0], pontos[0])]
        self.altura_alvo_m = altura_alvo_m
        self.ativas = set()                 # chaves das falhas presentes (para detectar a borda de subida)
        self._desde = {}                    # chave -> instante em que a condição começou
        self._partida_s = None
        self._motores_antes = False
        self._ultima_tel = None

    def desvio(self, estado):
        horizontal = min(distancia_ponto_segmento_2d(estado.x_m, estado.y_m, a, b) for a, b in self.segmentos)
        return max(horizontal, estado.z_m - self.altura_alvo_m)

    def _condicao(self, novas, chave, presente, agora, falha):
        if presente:
            self._desde.setdefault(chave, agora)
            if chave not in self.ativas:
                self.ativas.add(chave)
                novas.append(falha)
        else:
            self.ativas.discard(chave)
            self._desde.pop(chave, None)

    def _persistente(self, chave, agora):
        return chave in self._desde and agora - self._desde[chave] > self.cfg.persistencia_falha_s

    def avaliar(self, agora, tel, recepcao_tel_s, estado):
        """Avalia uma vez (10 Hz). `tel`: última telemetria (ou None); devolve a lista de falhas novas."""
        novas = []
        if tel is not None:
            self._ultima_tel = tel
            if tel.motores_ligados and not self._motores_antes:
                self._partida_s = agora
            if not tel.motores_ligados and not tel.em_voo:
                self._partida_s = None
            self._motores_antes = tel.motores_ligados
        ultima = self._ultima_tel
        if ultima is None or recepcao_tel_s is None:
            return novas
        em_voo = ultima.em_voo or ultima.motores_ligados

        idade = agora - recepcao_tel_s
        self._condicao(novas, 'atrasada', idade > self.cfg.prazo_telemetria_s, agora,
                       Falha(TELEMETRIA_ATRASADA, VELOCIDADE_ZERO, f'última amostra há {idade:.2f} s'))
        self._condicao(novas, 'atrasada_persistente',
                       em_voo and self._persistente('atrasada', agora) and idade <= self.cfg.prazo_perda_ponte_s,
                       agora, Falha(TELEMETRIA_ATRASADA, TERMINO_SEGURO, 'telemetria atrasada persistente'))
        perda_ponte = idade > self.cfg.prazo_perda_ponte_s
        detalhe = f'sem telemetria há {idade:.1f} s (o app ponte comanda pouso)'
        self._condicao(novas, 'perda_ponte_voo', perda_ponte and em_voo, agora,
                       Falha(PERDA_PONTE, TERMINO_SEGURO, detalhe))
        self._condicao(novas, 'perda_ponte_solo', perda_ponte and not em_voo, agora,
                       Falha(PERDA_PONTE, REGISTRAR, detalhe))
        if idade > self.cfg.prazo_telemetria_s:
            return novas                    # o resto depende de amostras atuais

        detalhe = 'aeronave desconectada (failsafe da aeronave: pousar)'
        self._condicao(novas, 'enlace_voo', not ultima.conectado and em_voo, agora,
                       Falha(PERDA_ENLACE, TERMINO_SEGURO, detalhe))
        self._condicao(novas, 'enlace_solo', not ultima.conectado and not em_voo, agora,
                       Falha(PERDA_ENLACE, REGISTRAR, detalhe))
        carga = ultima.bateria_pct
        self._condicao(novas, 'bateria_voo', em_voo and carga < self.cfg.bateria_critica_pct, agora,
                       Falha(BATERIA_BAIXA, TERMINO_SEGURO,
                             f'bateria {carga:.0f} % < {self.cfg.bateria_critica_pct:.0f} % em voo'))
        self._condicao(novas, 'bateria_solo', not em_voo and carga < self.cfg.bateria_minima_pct, agora,
                       Falha(BATERIA_BAIXA, REGISTRAR,
                             f'bateria {carga:.0f} % < {self.cfg.bateria_minima_pct:.0f} % para iniciar'))
        self._condicao(novas, 'posicionamento', ultima.em_voo and not ultima.posicionamento_visual_ativo, agora,
                       Falha(POSICIONAMENTO_VISUAL_INATIVO, TERMINO_SEGURO, 'posicionamento visual inativo'))

        invalida = em_voo and (estado is None or not estado.valido)
        motivo = 'sem estado' if estado is None else estado.motivo_invalido
        self._condicao(novas, 'estimativa', invalida, agora,
                       Falha(ESTIMATIVA_INVALIDA, VELOCIDADE_ZERO, f'estimativa inválida: {motivo}'))
        self._condicao(novas, 'estimativa_persistente', invalida and self._persistente('estimativa', agora), agora,
                       Falha(ESTIMATIVA_INVALIDA, TERMINO_SEGURO, f'estimativa inválida persistente: {motivo}'))

        desvio = self.desvio(estado) if (ultima.em_voo and estado is not None and estado.valido) else 0.0
        self._condicao(novas, 'desvio', desvio > self.cfg.desvio_maximo_m, agora,
                       Falha(DESVIO_EXCESSIVO, TERMINO_SEGURO, f'desvio de {desvio:.2f} m da trajetória'))

        decorrido = 0.0 if self._partida_s is None else agora - self._partida_s
        self._condicao(novas, 'tempo', decorrido > self.cfg.tempo_max_tarefa_s, agora,
                       Falha(TEMPO_TAREFA_EXCEDIDO, TERMINO_SEGURO, f'{decorrido:.0f} s desde a partida dos motores'))
        return novas


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import EstadoEstimado, Falha as FalhaMsg, Telemetria as TelemetriaMsg

    from . import ros_util
    from .planejador_trajetoria import PlanejadorTrajetoria
    from .tipos import NOMES_REACAO, Estado, Telemetria, de_mensagem

    class NoSupervisao(Node):
        def __init__(self):
            super().__init__('supervisao')
            cfg = ros_util.carregar_config(self)
            t1 = cfg.tarefa1
            planejador = PlanejadorTrajetoria(t1.vertices, t1.sentido)
            self.monitor = MonitorFalhas(cfg.seguranca, planejador.pontos, t1.altura_alvo_m)
            self.tel, self.t_tel, self.nova_tel, self.estado = None, None, False, None
            self.pub = self.create_publisher(FalhaMsg, '/falhas', ros_util.QOS_CONFIAVEL)
            self.create_subscription(TelemetriaMsg, '/dji/telemetria', self.ao_telemetria, ros_util.QOS_FLUXO)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_timer(0.1, self.ao_temporizar)

        def ao_telemetria(self, msg):
            self.tel, self.t_tel, self.nova_tel = de_mensagem(Telemetria, msg), ros_util.agora(), True

        def ao_estado(self, msg):
            self.estado = de_mensagem(Estado, msg)

        def ao_temporizar(self):
            tel = self.tel if self.nova_tel else None
            self.nova_tel = False
            for falha in self.monitor.avaliar(ros_util.agora(), tel, self.t_tel, self.estado):
                msg = FalhaMsg(tipo=falha.tipo, nome_tipo=falha.nome_tipo, reacao=falha.reacao,
                               detalhe=falha.detalhe)
                self.pub.publish(ros_util.carimbar(self, msg))
                self.get_logger().warn(f'falha {falha.nome_tipo} ({NOMES_REACAO[falha.reacao]}): {falha.detalhe}')

    rclpy.init(args=args)
    ros_util.executar(NoSupervisao())


if __name__ == '__main__':
    main()
