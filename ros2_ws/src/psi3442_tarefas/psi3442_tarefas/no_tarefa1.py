"""SupervisorTarefa1 (nível n): máquina de estados da Tarefa 1 (NivelN::MaquinaEstadosTarefa1) e nó ROS 2.

aguardando -> preparando -> [emVoo: decolando -> subindo -> pairando <-> deslocando ... retornando ->
estabilizandoEmA] -> pousando -> concluida; falha ou interrupção em voo -> pousoSeguro -> abortada.

- Ativação/interrupção: /tarefa/ativa (1 = esta tarefa; outro valor com a tarefa em voo = InterromperTarefa).
  As falhas chegam pelo gerenciador, que desativa a tarefa e comanda o pouso no local.
- Comandos discretos (habilitar controle virtual, decolar, pousar) são pedidos ao gerenciador por /tarefa/evento
  (SOLICITA_ACAO); só ele publica em /dji/acao.
- Setpoint inativo durante a decolagem e o pouso automáticos da DJI (o controle não envia velocidades).

Assina /tarefa/ativa, /estado e /dji/telemetria; publica /setpoint e /tarefa/evento a 10 Hz.
"""
import math

from .cronometro_permanencia import CONCLUIDA, INICIADA, INTERROMPIDA, CronometroPermanencia
from .planejador_trajetoria import PlanejadorTrajetoria
from .tipos import DECOLAR, HABILITAR_CONTROLE_VIRTUAL, POUSAR, Evento, Setpoint
from .verificador_tolerancia import VerificadorTolerancia

EM_VOO = ('decolando', 'subindo', 'pairando', 'deslocando', 'retornando', 'estabilizandoEmA')
FINAIS = ('aguardando', 'concluida', 'abortada')
INATIVO = Setpoint(ativo=False)
REPETICAO_POUSO_S = 5.0


class MaquinaTarefa1:
    NUMERO = 1

    def __init__(self, cfg, bateria_minima_pct):
        """`cfg`: ConfigTarefa1 (P05)."""
        self.cfg = cfg
        self.bateria_minima_pct = bateria_minima_pct
        self.planejador = PlanejadorTrajetoria(cfg.vertices, cfg.sentido)
        self.verificador = VerificadorTolerancia(cfg.tol_horizontal_m, cfg.tol_vertical_m, cfg.v_pairado_max_mps)
        self.cronometro = CronometroPermanencia(cfg.tempo_permanencia_s)
        self.estado = 'aguardando'
        self.indice = -1
        self.t_entrada = 0.0
        self.permanencias = []          # (nome, duração, interrupções) de cada vértice concluído
        self.vz_toque_mps = math.nan
        self._ativa_anterior = 0
        self._eventos = []
        self._estavel_desde = None
        self._pouso_pedido_s = None
        self._vz_em_voo = 0.0
        self.veredito = None

    # ------------------------------------------------------------------ auxiliares
    def _nome_vertice(self):
        return self.planejador.nomes[self.indice] if 0 <= self.indice < len(self.planejador) else ''

    def _evento(self, tipo, **campos):
        campos.setdefault('estado', self.estado)
        campos.setdefault('vertice', self.indice)
        campos.setdefault('nome_vertice', self._nome_vertice())
        self._eventos.append(Evento(tipo=tipo, tarefa=self.NUMERO, **campos))

    def _pedir(self, acao, agora, detalhe=''):
        self._evento('SOLICITA_ACAO', acao=acao, detalhe=detalhe)
        if acao == POUSAR:
            self._pouso_pedido_s = agora

    def _ir(self, novo, agora, detalhe=''):
        self.estado = novo
        self.t_entrada = agora
        # o alvo muda antes do evento, para a transição já informar o vértice de destino
        if novo == 'deslocando':
            self.indice += 1
        elif novo == 'retornando':
            self.indice = PlanejadorTrajetoria.INDICE_RETORNO
        self._evento('TRANSICAO', detalhe=detalhe)
        # demais ações de entrada
        if novo == 'preparando':
            self._pedir(HABILITAR_CONTROLE_VIRTUAL, agora)
        elif novo == 'decolando':
            self._pedir(DECOLAR, agora)
        elif novo == 'pairando':
            self.cronometro.zerar()
        elif novo == 'estabilizandoEmA':
            self._estavel_desde = None
        elif novo == 'pousando':
            self._pouso_pedido_s = None
        elif novo == 'pousoSeguro':
            self._pedir(POUSAR, agora, 'pouso no local')
        elif novo == 'concluida':
            self._evento('TAREFA_CONCLUIDA', valor=self.vz_toque_mps, detalhe=self._resumo())
        elif novo == 'abortada':
            self._evento('TAREFA_ABORTADA', valor=self.vz_toque_mps, detalhe=detalhe or self._resumo())

    def _resumo(self):
        partes = [f'{n}={d:.1f}s/{i} reinícios' for n, d, i in self.permanencias]
        return f"permanências: {', '.join(partes) or 'nenhuma'}; |vz| no toque = {self.vz_toque_mps:.2f} m/s"

    def _problemas_preparacao(self, estado, tel):
        if tel is None:
            return ['sem telemetria']
        problemas = []
        if not tel.conectado:
            problemas.append('aeronave desconectada')
        if tel.bateria_pct < self.bateria_minima_pct:
            problemas.append(f'bateria {tel.bateria_pct:.0f} % < {self.bateria_minima_pct:.0f} %')
        if not tel.posicionamento_visual_ativo:
            problemas.append('posicionamento visual inativo')
        if tel.acao_perda_sinal != 'pousar':
            problemas.append(f'ação em perda de sinal = {tel.acao_perda_sinal} (exigido: pousar)')
        if not tel.controle_virtual_ativo:
            problemas.append('controle virtual não habilitado')
        if tel.em_voo or tel.motores_ligados:
            problemas.append('aeronave não está pousada com motores desligados')
        if estado is None or not estado.valido:
            problemas.append('estimativa de estado inválida')
        return problemas

    def _pousado(self, tel):
        return tel is not None and not tel.em_voo and not tel.motores_ligados

    # ------------------------------------------------------------------ passo (10 Hz)
    def passo(self, agora, ativa, estado, tel):
        """Avança a máquina. `ativa`: número da tarefa ativa; `estado`: EstadoEstimado; `tel`: telemetria atual
        (None se velha). Devolve (setpoint, eventos)."""
        self._eventos = []
        ativada = ativa == self.NUMERO and self._ativa_anterior != self.NUMERO
        desativada = ativa != self.NUMERO and self._ativa_anterior == self.NUMERO
        self._ativa_anterior = ativa
        if tel is not None and tel.em_voo and estado is not None and estado.valido:
            self._vz_em_voo = estado.vz_mps

        if self.estado in FINAIS:
            if ativada:
                self.indice, self.permanencias, self.vz_toque_mps = -1, [], math.nan
                self._ir('preparando', agora)
            return self._saida(INATIVO)

        if desativada:
            if self.estado == 'preparando':
                self._ir('aguardando', agora, 'interrompida na preparação')
                self._evento('TAREFA_ABORTADA', detalhe='interrompida na preparação')
                return self._saida(INATIVO)
            if self.estado in EM_VOO or self.estado == 'pousando':
                self._ir('pousoSeguro', agora, 'interrupção (operador ou falha)')

        return self._saida(getattr(self, '_em_' + self.estado)(agora, estado, tel))

    def _saida(self, setpoint):
        return setpoint, self._eventos

    # ------------------------------------------------------------------ estados
    def _em_preparando(self, agora, estado, tel):
        problemas = self._problemas_preparacao(estado, tel)
        if not problemas:
            self._ir('decolando', agora, 'PreparacaoConcluida')
        elif agora - self.t_entrada > self.cfg.tempo_max_preparacao_s:
            self._evento('PREPARACAO_FALHOU', detalhe='; '.join(problemas))
            self._ir('aguardando', agora, 'FalhaDetectada na preparação')
        return INATIVO

    def _em_decolando(self, agora, estado, tel):
        if (tel is not None and tel.em_voo and estado is not None and estado.valido
                and estado.z_m >= self.cfg.altura_min_decolagem_m
                and abs(estado.vz_mps) <= self.cfg.v_pairado_max_mps):
            self._ir('subindo', agora, 'DecolagemConcluida')
            return self._em_subindo(agora, estado, tel)
        if agora - self.t_entrada > self.cfg.tempo_max_decolagem_s:
            self._ir('pousoSeguro', agora, 'decolagem não concluída no prazo')
        return INATIVO

    def _em_subindo(self, agora, estado, tel):
        setpoint = self.planejador.setpoint(0)
        if (estado is not None and estado.valido
                and abs(estado.z_m - self.cfg.altura_alvo_m) <= self.cfg.tol_vertical_m
                and math.sqrt(estado.vx_mps ** 2 + estado.vy_mps ** 2 + estado.vz_mps ** 2)
                <= self.cfg.v_pairado_max_mps):
            self.indice = 0
            self._ir('pairando', agora, 'AlturaAtingida')
        return setpoint

    def _em_pairando(self, agora, estado, tel):
        setpoint = self.planejador.setpoint(self.indice)
        self.veredito = self.verificador.avaliar(estado, setpoint)
        resultado = self.cronometro.atualizar(self.veredito.dentro, agora)
        if resultado == INICIADA:
            self._evento('PERMANENCIA_INICIADA')
        elif resultado == INTERROMPIDA:
            v = self.veredito
            self._evento('PERMANENCIA_INTERROMPIDA', permanencia_s=self.cronometro.tentativas[-1].duracao_s,
                         detalhe=f'ToleranciaExcedida: erro_h={v.erro_horizontal_m:.2f} m, '
                                 f'erro_v={v.erro_vertical_m:.2f} m, |v|={v.velocidade_mps:.2f} m/s')
        elif resultado == CONCLUIDA:
            duracao = self.cronometro.tentativas[-1].duracao_s
            self.permanencias.append((self._nome_vertice(), duracao, self.cronometro.interrupcoes))
            self._evento('PERMANENCIA_CONCLUIDA', permanencia_s=duracao,
                         detalhe=f'{self.cronometro.interrupcoes} reinícios da contagem')
            if self.indice < PlanejadorTrajetoria.ULTIMO_INDICE_PERMANENCIA:
                self._ir('deslocando', agora, 'PermanenciaConcluida')
                return self.planejador.setpoint(self.indice)
            self._ir('retornando', agora, 'PermanenciaConcluida (último vértice)')
            return self.planejador.setpoint(self.indice)
        return setpoint

    def _em_deslocando(self, agora, estado, tel):
        setpoint = self.planejador.setpoint(self.indice)
        if self.verificador.avaliar(estado, setpoint).dentro:
            self._ir('pairando', agora, 'VerticeAtingido')
        return setpoint

    def _em_retornando(self, agora, estado, tel):
        setpoint = self.planejador.setpoint(self.indice)
        if self.verificador.avaliar(estado, setpoint).dentro:
            self._ir('estabilizandoEmA', agora, 'VerticeAtingido (retorno)')
        return setpoint

    def _em_estabilizandoEmA(self, agora, estado, tel):
        setpoint = self.planejador.setpoint(self.indice)
        if self.verificador.avaliar(estado, setpoint).dentro:
            if self._estavel_desde is None:
                self._estavel_desde = agora
            elif agora - self._estavel_desde >= self.cfg.tempo_estabilizacao_s:
                self._ir('pousando', agora, 'Estabilizado')
                return self._em_pousando(agora, estado, tel)
        else:
            self._estavel_desde = None
        return setpoint

    def _em_pousando(self, agora, estado, tel):
        if self._pousado(tel):
            return self._confirmar_pouso(agora, 'concluida')
        if self._pouso_pedido_s is None:
            ax, ay, _ = self.planejador.pontos[0]
            altura = self.cfg.altura_inicio_pouso_m
            if estado is not None and estado.valido and estado.z_m <= altura + self.cfg.tol_vertical_m:
                self._pedir(POUSAR, agora, 'pouso automático a partir de %.2f m' % estado.z_m)
                return INATIVO
            return Setpoint(ativo=True, x_m=ax, y_m=ay, z_m=altura, indice=self.indice, nome='pouso')
        if agora - self._pouso_pedido_s > REPETICAO_POUSO_S:
            self._pedir(POUSAR, agora, 'pouso ainda não confirmado: pedido repetido')
        return INATIVO

    def _em_pousoSeguro(self, agora, estado, tel):
        if self._pousado(tel):
            return self._confirmar_pouso(agora, 'abortada')
        if self._pouso_pedido_s is None or agora - self._pouso_pedido_s > REPETICAO_POUSO_S:
            self._pedir(POUSAR, agora, 'pouso ainda não confirmado: pedido repetido')
        return INATIVO

    def _confirmar_pouso(self, agora, destino):
        self.vz_toque_mps = abs(self._vz_em_voo)
        limite = self.cfg.v_toque_max_mps
        situacao = 'dentro do limite' if self.vz_toque_mps <= limite else 'ACIMA do limite'
        self._evento('POUSO_CONFIRMADO', valor=self.vz_toque_mps,
                     detalhe=f'|vz| no toque = {self.vz_toque_mps:.2f} m/s ({situacao} de {limite:.2f} m/s)')
        self._ir(destino, agora, 'PousoConfirmado')
        return INATIVO


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import EstadoEstimado, EventoTarefa, Setpoint as SetpointMsg, TarefaAtiva
    from psi3442_interfaces.msg import Telemetria as TelemetriaMsg

    from . import ros_util
    from .tipos import Estado, Telemetria, copiar_campos, de_mensagem

    class NoTarefa1(Node):
        def __init__(self):
            super().__init__('tarefa1')
            cfg = ros_util.carregar_config(self)
            self.prazo_telemetria_s = cfg.seguranca.prazo_telemetria_s
            self.prazo_estado_s = cfg.estimacao.idade_max_amostra_s
            self.maquina = MaquinaTarefa1(cfg.tarefa1, cfg.seguranca.bateria_minima_pct)
            self.ativa = 0
            self.estado, self.t_estado = None, None
            self.tel, self.t_tel = None, None
            self.pub_setpoint = self.create_publisher(SetpointMsg, '/setpoint', ros_util.QOS_FLUXO)
            self.pub_evento = self.create_publisher(EventoTarefa, '/tarefa/evento', ros_util.QOS_CONFIAVEL)
            self.create_subscription(TarefaAtiva, '/tarefa/ativa', self.ao_ativa, ros_util.QOS_LATCHED)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_subscription(TelemetriaMsg, '/dji/telemetria', self.ao_telemetria, ros_util.QOS_FLUXO)
            self.create_timer(0.1, self.ao_temporizar)

        def ao_ativa(self, msg):
            self.ativa = msg.numero

        def ao_estado(self, msg):
            self.estado, self.t_estado = de_mensagem(Estado, msg), ros_util.agora()

        def ao_telemetria(self, msg):
            self.tel, self.t_tel = de_mensagem(Telemetria, msg), ros_util.agora()

        def ao_temporizar(self):
            agora = ros_util.agora()
            tel = self.tel if self.t_tel is not None and agora - self.t_tel <= self.prazo_telemetria_s else None
            estado = self.estado
            if estado is not None and agora - self.t_estado > self.prazo_estado_s:
                estado = None
            setpoint, eventos = self.maquina.passo(agora, self.ativa, estado, tel)
            # só a tarefa ativa publica /setpoint (a Tarefa 2 também publica nele)
            if self.ativa == MaquinaTarefa1.NUMERO or setpoint.ativo:
                self.pub_setpoint.publish(ros_util.carimbar(self, copiar_campos(setpoint, SetpointMsg())))
            for ev in eventos:
                msg = copiar_campos(ev, EventoTarefa())
                msg.valor = float(ev.valor) if math.isfinite(ev.valor) else -1.0
                self.pub_evento.publish(ros_util.carimbar(self, msg))
                self.get_logger().info(f'{ev.tipo} [{ev.estado} {ev.nome_vertice}] {ev.detalhe}')

    rclpy.init(args=args)
    ros_util.executar(NoTarefa1())


if __name__ == '__main__':
    main()
