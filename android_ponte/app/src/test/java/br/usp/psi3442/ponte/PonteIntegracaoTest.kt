package br.usp.psi3442.ponte

import org.json.JSONObject
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.Socket
import java.nio.charset.StandardCharsets
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import kotlin.math.atan2

/**
 * Ponte completa com o drone falso, comandada por um cliente TCP que faz o papel do nó ponte ROS 2
 * (mesmas mensagens de no_ponte_dji.py). Tempo real: alguns segundos.
 */
class PonteIntegracaoTest {
    private lateinit var drone: DroneFalso
    private lateinit var ponte: Ponte
    private lateinit var socket: Socket
    private lateinit var saida: OutputStreamWriter
    private val recebidas = LinkedBlockingQueue<JSONObject>()

    @Before
    fun preparar() {
        drone = DroneFalso(ruidoMps = 0.0)
        ponte = Ponte(drone, porta = 0, log = {})
        ponte.iniciar()
        socket = Socket("127.0.0.1", ponte.porta)
        saida = OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8)
        Thread {
            val entrada = BufferedReader(InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8))
            try {
                while (true) recebidas.put(JSONObject(entrada.readLine() ?: break))
            } catch (_: Exception) {
            }
        }.apply { isDaemon = true }.start()
    }

    @After
    fun encerrar() {
        socket.close()
        ponte.parar()
    }

    private fun enviar(json: String) {
        saida.write(json + "\n")
        saida.flush()
    }

    private fun heartbeat() = enviar("""{"tipo":"heartbeat","instante_s":0}""")

    private fun esperarTelemetria(segundos: Double, condicao: (JSONObject) -> Boolean): JSONObject {
        val limite = System.nanoTime() + (segundos * 1e9).toLong()
        while (System.nanoTime() < limite) {
            val msg = recebidas.poll(50, TimeUnit.MILLISECONDS) ?: continue
            if (msg.getString("tipo") == "telemetria" && condicao(msg)) return msg
        }
        throw AssertionError("condição de telemetria não atingida em $segundos s")
    }

    @Test
    fun decolaSegueOCmdVelNoReferencialCertoEPousaSemHeartbeat() {
        heartbeat()
        val inicial = esperarTelemetria(2.0) { true }
        assertEquals("pousar", esperarTelemetria(2.0) { it.getString("acao_perda_sinal") == "pousar" }
            .getString("acao_perda_sinal"))
        assertTrue(!inicial.getBoolean("em_voo"))

        enviar("""{"tipo":"acao","comando":"habilitar_controle_virtual"}""")
        enviar("""{"tipo":"acao","comando":"decolar"}""")
        var t = 0
        while (drone.posicao().third < 1.15 && t++ < 60) { heartbeat(); Thread.sleep(100) }
        esperarTelemetria(3.0) { it.getBoolean("em_voo") && it.getString("modo_voo") == "VIRTUAL_STICK" }

        val antes = drone.posicao()
        repeat(20) {
            enviar("""{"tipo":"cmd_vel","vx_mps":0.3,"vy_mps":0.0,"vz_mps":0.0,"taxa_guinada_grausps":0.0,"psi0_graus":30.0}""")
            if (it % 10 == 0) heartbeat()
            Thread.sleep(50)
        }
        val depois = drone.posicao()
        val dn = depois.first - antes.first
        val de = depois.second - antes.second
        assertTrue("deslocamento pequeno demais: $dn, $de", dn * dn + de * de > 0.1 * 0.1)
        assertEquals("rumo do deslocamento = psi0", 30.0, Math.toDegrees(atan2(de, dn)), 3.0)

        val tPerda = System.nanoTime()
        esperarTelemetria(10.0) { !it.getBoolean("em_voo") }
        val segundos = (System.nanoTime() - tPerda) / 1e9
        assertTrue("pousou cedo demais: $segundos s", segundos > 2.0)
        assertTrue("toque suave", drone.vToqueMps <= 0.5)
    }

    @Test
    fun comandoRejeitadoVoltaComoErro() {
        enviar("""{"tipo":"acao","comando":"pousar"}""")
        val limite = System.nanoTime() + 2_000_000_000L
        while (System.nanoTime() < limite) {
            val msg = recebidas.poll(50, TimeUnit.MILLISECONDS) ?: continue
            if (msg.getString("tipo") == "erro") {
                assertEquals("pousar", msg.getString("comando"))
                return
            }
        }
        throw AssertionError("a ponte não devolveu erro para pousar no solo")
    }
}
