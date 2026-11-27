package br.usp.psi3442.ponte

import kotlin.math.cos
import kotlin.math.sin

/** (x, y) do ReferencialLocal para (norte, leste); igual a solo_de_local em no_estimacao_estado.py. */
fun soloDeLocal(vx: Double, vy: Double, psi0Graus: Double): Pair<Double, Double> {
    val psi0 = Math.toRadians(psi0Graus)
    return Pair(vx * cos(psi0) + vy * sin(psi0), vx * sin(psi0) - vy * cos(psi0))
}

/**
 * EmissorComandos (nível n), sem dependência de Android: decide, a cada ciclo de 20 Hz, o que enviar à aeronave.
 * - cmd_vel no ReferencialLocal convertido para norte/leste/baixo com psi0;
 * - watchdog: sem cmd_vel por [prazoWatchdogS] com o controle virtual ativo, velocidade zero;
 * - sem heartbeat do nó ponte por [prazoPerdaPonteS] em voo: pouso automático (perdaPonte), uma vez por voo.
 */
class EmissorComandos(
    private val prazoWatchdogS: Double = 0.2,
    private val prazoPerdaPonteS: Double = 2.0,
) {
    sealed class Decisao {
        object Nenhuma : Decisao()
        object Pousar : Decisao()
        data class Velocidade(val vNorte: Double, val vLeste: Double, val vBaixo: Double, val taxaGuinada: Double) :
            Decisao()
    }

    private var comando: Protocolo.ComandoLocal? = null
    private var tComando: Double? = null
    private var tHeartbeat: Double? = null
    private var pousoPorPerdaPonte = false

    @Synchronized
    fun aoCmdVel(c: Protocolo.ComandoLocal, agoraS: Double) {
        comando = c
        tComando = agoraS
    }

    @Synchronized
    fun aoHeartbeat(agoraS: Double) {
        tHeartbeat = agoraS
    }

    @Synchronized
    fun pararEPairar() {
        comando = null
        tComando = null
    }

    @Synchronized
    fun passo(agoraS: Double, tel: Telemetria): Decisao {
        if (!tel.emVoo) {
            pousoPorPerdaPonte = false
            return Decisao.Nenhuma
        }
        if (tel.emManobraAutomatica) return Decisao.Nenhuma
        val hb = tHeartbeat
        if (hb != null && agoraS - hb > prazoPerdaPonteS) {
            if (pousoPorPerdaPonte) return Decisao.Nenhuma
            pousoPorPerdaPonte = true
            return Decisao.Pousar
        }
        if (!tel.controleVirtualAtivo) return Decisao.Nenhuma
        val c = comando
        val t = tComando
        if (c == null || t == null || agoraS - t > prazoWatchdogS) return Decisao.Velocidade(0.0, 0.0, 0.0, 0.0)
        val (norte, leste) = soloDeLocal(c.vxMps, c.vyMps, c.psi0Graus)
        return Decisao.Velocidade(norte, leste, -c.vzMps, c.taxaGuinadaGrausS)
    }
}
