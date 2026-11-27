package br.usp.psi3442.ponte

import java.util.Random
import kotlin.math.abs
import kotlin.math.min

/**
 * Drone falso para o emulador e para testes: a mesma dinâmica do DroneCinematico de simulador_cinematico.py
 * (velocidade de 1ª ordem rumo ao alvo, decolagem e pouso automáticos, consumo de bateria, ruído com semente fixa).
 * Os watchdogs não ficam aqui: são do app ponte ([EmissorComandos]), como no app real.
 */
class DroneFalso(
    private val guinadaInicialGraus: Double = 30.0,
    private val alturaDecolagemM: Double = 1.2,
    private val vDecolagemMps: Double = 0.8,
    private val vPousoMps: Double = 0.4,
    private val tauS: Double = 0.3,
    bateriaInicialPct: Double = 80.0,
    private val consumoPctPorS: Double = 0.06,
    private val ruidoMps: Double = 0.01,
    semente: Long = 1,
    private val rejeitar: Set<String> = emptySet(),
) : Drone {
    override val descricao = "drone falso (cinemático)"

    private val rng = Random(semente)
    private var norte = 0.0
    private var leste = 0.0
    var altura = 0.0
        private set
    private var vNorte = 0.0
    private var vLeste = 0.0
    private var vBaixo = 0.0
    private var alvo = Triple(0.0, 0.0, 0.0)
    private var emVoo = false
    private var motores = false
    private var controleVirtual = false
    private var manobra: String? = null
    private var bateria = bateriaInicialPct
    private var acaoPerdaSinal = "retornar_ao_ponto"
    var vToqueMps = Double.NaN
        private set

    override fun iniciar(log: (String) -> Unit) = log("usando $descricao")

    @Synchronized
    override fun telemetria(agoraS: Double): Telemetria {
        val ruido = { if (motores && ruidoMps > 0) rng.nextGaussian() * ruidoMps else 0.0 }
        return Telemetria(
            instanteS = agoraS,
            vNorteMps = vNorte + ruido(),
            vLesteMps = vLeste + ruido(),
            vBaixoMps = vBaixo + ruido(),
            altitudeM = altura,
            alturaTofM = altura,
            guinadaGraus = guinadaInicialGraus,
            emVoo = emVoo,
            motoresLigados = motores,
            modoVoo = when (manobra) {
                "decolagem" -> "AUTO_TAKE_OFF"
                "pouso" -> "AUTO_LANDING"
                else -> if (controleVirtual && emVoo) "VIRTUAL_STICK" else "GPS_NORMAL"
            },
            bateriaPct = bateria,
            conectado = true,
            posicionamentoVisualAtivo = true,
            controleVirtualAtivo = controleVirtual,
            acaoPerdaSinal = acaoPerdaSinal,
            emManobraAutomatica = manobra != null,
        )
    }

    @Synchronized
    override fun decolar(aoConcluir: AoConcluir) = aoConcluir(
        when {
            "decolar" in rejeitar -> "rejeitado (falha injetada)"
            motores || emVoo -> "aeronave já em voo"
            else -> { motores = true; manobra = "decolagem"; null }
        }
    )

    @Synchronized
    override fun pousar(aoConcluir: AoConcluir) = aoConcluir(
        when {
            "pousar" in rejeitar -> "rejeitado (falha injetada)"
            !emVoo -> "aeronave não está em voo"
            else -> { manobra = "pouso"; null }
        }
    )

    @Synchronized
    override fun habilitarControleVirtual(aoConcluir: AoConcluir) {
        controleVirtual = true
        aoConcluir(null)
    }

    @Synchronized
    override fun desabilitarControleVirtual(aoConcluir: AoConcluir) {
        controleVirtual = false
        aoConcluir(null)
    }

    @Synchronized
    override fun definirAcaoPerdaSinalPousar(aoConcluir: AoConcluir) {
        acaoPerdaSinal = "pousar"
        aoConcluir(null)
    }

    @Synchronized
    override fun enviarVelocidade(vNorteMps: Double, vLesteMps: Double, vBaixoMps: Double, taxaGuinadaGrausS: Double) {
        if (controleVirtual && emVoo && manobra == null) alvo = Triple(vNorteMps, vLesteMps, vBaixoMps)
    }

    @Synchronized
    override fun passo(dtS: Double, agoraS: Double) {
        when (manobra) {
            "decolagem" -> {
                alvo = Triple(0.0, 0.0, -vDecolagemMps)
                if (altura >= alturaDecolagemM) {
                    manobra = null
                    alvo = Triple(0.0, 0.0, 0.0)
                }
            }
            "pouso" -> alvo = Triple(0.0, 0.0, vPousoMps)
        }
        val fator = min(1.0, dtS / tauS)
        vNorte += (alvo.first - vNorte) * fator
        vLeste += (alvo.second - vLeste) * fator
        vBaixo += (alvo.third - vBaixo) * fator
        if (motores) {
            norte += vNorte * dtS
            leste += vLeste * dtS
            altura -= vBaixo * dtS
            bateria = (bateria - consumoPctPorS * dtS).coerceAtLeast(0.0)
        }
        if (altura > 0.02 && motores) emVoo = true
        if (altura <= 0.0) {
            if (emVoo) {
                vToqueMps = abs(vBaixo)
                emVoo = false
                motores = false
                manobra = null
                alvo = Triple(0.0, 0.0, 0.0)
            }
            altura = 0.0
            if (!motores) { vNorte = 0.0; vLeste = 0.0; vBaixo = 0.0 }
        }
    }

    /** Posição (norte, leste, altura) para testes. */
    @Synchronized
    fun posicao() = Triple(norte, leste, altura)
}
