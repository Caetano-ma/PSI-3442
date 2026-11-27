package br.usp.psi3442.ponte

/** Resposta de um comando: null em caso de sucesso, ou a mensagem de erro devolvida pelo SDK. */
typealias AoConcluir = (erro: String?) -> Unit

/** Amostra de telemetria no formato do ContratoSocketPonte (unidades SI; velocidades norte/leste/baixo). */
data class Telemetria(
    val instanteS: Double,
    val vNorteMps: Double,
    val vLesteMps: Double,
    val vBaixoMps: Double,
    val altitudeM: Double,
    val alturaTofM: Double?,
    val guinadaGraus: Double,
    val emVoo: Boolean,
    val motoresLigados: Boolean,
    val modoVoo: String,
    val bateriaPct: Double,
    val conectado: Boolean,
    val posicionamentoVisualAtivo: Boolean,
    val controleVirtualAtivo: Boolean,
    val acaoPerdaSinal: String,
    /** Decolagem ou pouso automático em andamento: comandos de velocidade são ignorados. */
    val emManobraAutomatica: Boolean,
)

/**
 * Aeronave vista pelo app ponte (caixa-preta). Implementações: [DroneFalso] (cinemático, para o emulador e para
 * testes) e DroneDji (DJI Mobile SDK v5, só na variante "celular").
 */
interface Drone {
    val descricao: String

    fun iniciar(log: (String) -> Unit)

    fun telemetria(agoraS: Double): Telemetria

    fun decolar(aoConcluir: AoConcluir)

    fun pousar(aoConcluir: AoConcluir)

    fun habilitarControleVirtual(aoConcluir: AoConcluir)

    fun desabilitarControleVirtual(aoConcluir: AoConcluir)

    fun definirAcaoPerdaSinalPousar(aoConcluir: AoConcluir)

    /** Velocidades no referencial do solo (m/s, "baixo" positivo para baixo) e taxa de guinada (graus/s). */
    fun enviarVelocidade(vNorteMps: Double, vLesteMps: Double, vBaixoMps: Double, taxaGuinadaGrausS: Double)

    /** Avança a dinâmica; só o drone falso precisa. */
    fun passo(dtS: Double, agoraS: Double) {}

    fun encerrar() {}
}
