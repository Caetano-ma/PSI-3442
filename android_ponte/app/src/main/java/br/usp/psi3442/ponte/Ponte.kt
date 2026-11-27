package br.usp.psi3442.ponte

import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

/**
 * App ponte (nível n): liga o socket do nó ponte ROS 2 à aeronave. Todo o estado é tratado num único executor:
 * mensagens recebidas, ciclo do emissor (20 Hz), telemetria (10 Hz), heartbeat (1 Hz) e a dinâmica do drone falso.
 */
class Ponte(
    private val drone: Drone,
    porta: Int = PORTA_PADRAO,
    private val log: (String) -> Unit,
    private val relogio: () -> Double = { System.nanoTime() / 1e9 },
) {
    companion object {
        const val PORTA_PADRAO = 5760
    }

    private val executor: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor { r ->
        Thread(r, "ponte").apply { isDaemon = true }
    }
    private val emissor = EmissorComandos()
    private val servidor = ServidorSocket(porta, ::aoReceber, ::aoMudarCliente, log)
    private val leitor = LeitorTelemetria(drone, servidor)
    private val configurador = ConfiguradorSeguranca(drone, log)
    private var tAnterior = 0.0

    @Volatile var cliente: String? = null
        private set
    val porta: Int get() = servidor.portaLocal
    val telemetria: Telemetria? get() = leitor.ultima
    val descricaoDrone: String get() = drone.descricao

    fun iniciar() {
        drone.iniciar(log)
        servidor.iniciar()
        tAnterior = relogio()
        agendar(20) { val t = relogio(); drone.passo(t - tAnterior, t); tAnterior = t }
        agendar(50, ::cicloEmissor)
        agendar(100) { val t = relogio(); leitor.publicar(t); configurador.verificar(leitor.ultima ?: return@agendar) }
        agendar(1000) { leitor.heartbeat(relogio()) }
    }

    fun parar() {
        executor.shutdownNow()
        servidor.parar()
        drone.encerrar()
    }

    private fun agendar(periodoMs: Long, tarefa: () -> Unit) {
        executor.scheduleAtFixedRate({
            try {
                tarefa()
            } catch (e: Exception) {
                log("erro no ciclo: $e")
            }
        }, 0, periodoMs, TimeUnit.MILLISECONDS)
    }

    private fun aoMudarCliente(origem: String?) {
        cliente = origem
    }

    /** Heartbeat e cmd_vel são carimbados na chegada (thread de leitura): um executor atrasado não pode simular
     *  perda da ponte nem envelhecer comandos. Ações vão para o executor. */
    private fun aoReceber(mensagem: JSONObject) {
        val agora = relogio()
        when (mensagem.getString("tipo")) {
            "heartbeat" -> emissor.aoHeartbeat(agora)
            "cmd_vel" -> emissor.aoCmdVel(Protocolo.comandoLocal(mensagem), agora)
            "acao" -> {
                val comando = mensagem.optString("comando")
                executor.execute { executarAcao(comando) }
            }
        }
    }

    private fun executarAcao(comando: String) {
        log("ação recebida: $comando")
        val aoConcluir: AoConcluir = { erro ->
            if (erro != null) {
                log("ação $comando rejeitada: $erro")
                servidor.enviar(Protocolo.erro(comando, erro))
            }
        }
        when (comando) {
            "decolar" -> drone.decolar(aoConcluir)
            "pousar" -> drone.pousar(aoConcluir)
            "habilitar_controle_virtual" -> drone.habilitarControleVirtual(aoConcluir)
            "desabilitar_controle_virtual" -> drone.desabilitarControleVirtual(aoConcluir)
            "parar_e_pairar" -> {
                emissor.pararEPairar()
                drone.enviarVelocidade(0.0, 0.0, 0.0, 0.0)
            }
            else -> aoConcluir("comando desconhecido: $comando")
        }
    }

    private fun cicloEmissor() {
        val tel = leitor.ultima ?: leitor.ler(relogio())
        when (val decisao = emissor.passo(relogio(), tel)) {
            is EmissorComandos.Decisao.Velocidade ->
                drone.enviarVelocidade(decisao.vNorte, decisao.vLeste, decisao.vBaixo, decisao.taxaGuinada)
            EmissorComandos.Decisao.Pousar -> {
                log("sem heartbeat do nó ponte: pouso automático (perda da ponte)")
                drone.pousar { erro -> if (erro != null) log("pouso por perda da ponte falhou: $erro") }
            }
            EmissorComandos.Decisao.Nenhuma -> {}
        }
    }
}
