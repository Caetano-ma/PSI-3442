package br.usp.psi3442.ponte

import dji.sdk.keyvalue.key.BatteryKey
import dji.sdk.keyvalue.key.DJIActionKeyInfo
import dji.sdk.keyvalue.key.DJIKeyInfo
import dji.sdk.keyvalue.key.FlightAssistantKey
import dji.sdk.keyvalue.key.FlightControllerKey
import dji.sdk.keyvalue.key.KeyTools
import dji.sdk.keyvalue.value.common.Attitude
import dji.sdk.keyvalue.value.common.EmptyMsg
import dji.sdk.keyvalue.value.common.Velocity3D
import dji.sdk.keyvalue.value.flightcontroller.FailsafeAction
import dji.sdk.keyvalue.value.flightcontroller.FlightControlAuthorityChangeReason
import dji.sdk.keyvalue.value.flightcontroller.FlightCoordinateSystem
import dji.sdk.keyvalue.value.flightcontroller.FlightMode
import dji.sdk.keyvalue.value.flightcontroller.RollPitchControlMode
import dji.sdk.keyvalue.value.flightcontroller.VerticalControlMode
import dji.sdk.keyvalue.value.flightcontroller.VirtualStickFlightControlParam
import dji.sdk.keyvalue.value.flightcontroller.YawControlMode
import dji.v5.common.callback.CommonCallbacks
import dji.v5.common.error.IDJIError
import dji.v5.manager.KeyManager
import dji.v5.manager.aircraft.virtualstick.VirtualStickManager
import dji.v5.manager.aircraft.virtualstick.VirtualStickState
import dji.v5.manager.aircraft.virtualstick.VirtualStickStateListener

/**
 * DJI Mini 4 Pro pelo DJI Mobile SDK v5 (caixa-preta explorada só pelas chaves e gerenciadores do SDK).
 *
 * A verificar em ensaio antes do T01 (roteiro de voo, "teste de eixos"):
 * - [ROLL_E_NORTE]: no controle virtual em velocidade e referencial do solo, qual eixo (roll ou pitch) é o norte;
 * - o referencial de KeyAircraftVelocity (assumido norte, leste, baixo);
 * - a unidade de KeyUltrasonicHeight: enquanto não confirmada, a altura ToF não é publicada e a estimação usa a
 *   altitude relativa (KeyAltitude), como prevê o nível n.
 * O posicionamento visual é considerado ativo quando está habilitado e a aeronave não está em ATTI (sem
 * posicionamento a aeronave entra em ATTI).
 */
class DroneDji : Drone {
    companion object {
        const val ROLL_E_NORTE = true
        val FATOR_ULTRASSOM_PARA_METROS: Double? = null
    }

    override val descricao = "DJI Mini 4 Pro (Mobile SDK v5)"

    private val dono = Any()
    private var log: (String) -> Unit = {}
    @Volatile private var velocidade: Velocity3D? = null
    @Volatile private var altitude: Double? = null
    @Volatile private var ultrassom: Int? = null
    @Volatile private var atitude: Attitude? = null
    @Volatile private var emVoo: Boolean? = null
    @Volatile private var motores: Boolean? = null
    @Volatile private var modo: FlightMode? = null
    @Volatile private var bateria: Int? = null
    @Volatile private var conectado: Boolean? = null
    @Volatile private var visaoHabilitada: Boolean? = null
    @Volatile private var acaoPerdaSinal: FailsafeAction? = null
    @Volatile private var controleVirtual = false

    override fun iniciar(log: (String) -> Unit) {
        this.log = log
        log("usando $descricao")
        ouvir(FlightControllerKey.KeyAircraftVelocity) { velocidade = it }
        ouvir(FlightControllerKey.KeyAltitude) { altitude = it }
        ouvir(FlightControllerKey.KeyUltrasonicHeight) { ultrassom = it }
        ouvir(FlightControllerKey.KeyAircraftAttitude) { atitude = it }
        ouvir(FlightControllerKey.KeyIsFlying) { emVoo = it }
        ouvir(FlightControllerKey.KeyAreMotorsOn) { motores = it }
        ouvir(FlightControllerKey.KeyFlightMode) { modo = it }
        ouvir(FlightControllerKey.KeyConnection) { conectado = it }
        ouvir(FlightControllerKey.KeyFailsafeAction) { acaoPerdaSinal = it }
        ouvir(BatteryKey.KeyChargeRemainingInPercent) { bateria = it }
        ouvir(FlightAssistantKey.KeyVisionPositioningEnabled) { visaoHabilitada = it }
        VirtualStickManager.getInstance().setVirtualStickStateListener(object : VirtualStickStateListener {
            override fun onVirtualStickStateUpdate(stickState: VirtualStickState) {
                controleVirtual = stickState.isVirtualStickEnable
            }

            override fun onChangeReasonUpdate(reason: FlightControlAuthorityChangeReason) {
                log("autoridade de voo mudou: $reason")
            }
        })
    }

    private fun <T> ouvir(chave: DJIKeyInfo<T>, aoMudar: (T?) -> Unit) {
        KeyManager.getInstance().listen(KeyTools.createKey(chave), dono, true) { _, novo -> aoMudar(novo) }
    }

    override fun telemetria(agoraS: Double): Telemetria {
        val v = velocidade
        val modoAtual = modo
        val nomeModo = modoAtual?.name ?: "DESCONHECIDO"
        return Telemetria(
            instanteS = agoraS,
            vNorteMps = v?.x ?: 0.0,
            vLesteMps = v?.y ?: 0.0,
            vBaixoMps = v?.z ?: 0.0,
            altitudeM = altitude ?: 0.0,
            alturaTofM = FATOR_ULTRASSOM_PARA_METROS?.let { fator -> ultrassom?.let { it * fator } },
            guinadaGraus = atitude?.yaw ?: 0.0,
            emVoo = emVoo ?: false,
            motoresLigados = motores ?: false,
            modoVoo = nomeModo,
            bateriaPct = bateria?.toDouble() ?: 0.0,
            conectado = (conectado ?: false) && ConexaoSdk.produtoConectado,
            posicionamentoVisualAtivo = (visaoHabilitada ?: false) && modoAtual != FlightMode.ATTI,
            controleVirtualAtivo = controleVirtual,
            acaoPerdaSinal = when (acaoPerdaSinal) {
                FailsafeAction.LANDING -> "pousar"
                FailsafeAction.HOVER -> "pairar"
                FailsafeAction.GOHOME -> "retornar_ao_ponto"
                else -> "desconhecida"
            },
            emManobraAutomatica = modoAtual == FlightMode.AUTO_TAKE_OFF || modoAtual == FlightMode.AUTO_LANDING,
        )
    }

    private fun acao(chave: DJIActionKeyInfo<EmptyMsg, EmptyMsg>, aoConcluir: AoConcluir) {
        KeyManager.getInstance().performAction(KeyTools.createKey(chave),
            object : CommonCallbacks.CompletionCallbackWithParam<EmptyMsg> {
                override fun onSuccess(t: EmptyMsg?) = aoConcluir(null)
                override fun onFailure(error: IDJIError) = aoConcluir(error.toString())
            })
    }

    private fun callback(aoConcluir: AoConcluir) = object : CommonCallbacks.CompletionCallback {
        override fun onSuccess() = aoConcluir(null)
        override fun onFailure(error: IDJIError) = aoConcluir(error.toString())
    }

    override fun decolar(aoConcluir: AoConcluir) = acao(FlightControllerKey.KeyStartTakeoff, aoConcluir)

    override fun pousar(aoConcluir: AoConcluir) = acao(FlightControllerKey.KeyStartAutoLanding, aoConcluir)

    override fun habilitarControleVirtual(aoConcluir: AoConcluir) {
        VirtualStickManager.getInstance().enableVirtualStick(callback { erro ->
            if (erro == null) VirtualStickManager.getInstance().setVirtualStickAdvancedModeEnabled(true)
            aoConcluir(erro)
        })
    }

    override fun desabilitarControleVirtual(aoConcluir: AoConcluir) {
        VirtualStickManager.getInstance().setVirtualStickAdvancedModeEnabled(false)
        VirtualStickManager.getInstance().disableVirtualStick(callback(aoConcluir))
    }

    override fun definirAcaoPerdaSinalPousar(aoConcluir: AoConcluir) {
        KeyManager.getInstance().setValue(KeyTools.createKey(FlightControllerKey.KeyFailsafeAction),
            FailsafeAction.LANDING, callback(aoConcluir))
    }

    override fun enviarVelocidade(vNorteMps: Double, vLesteMps: Double, vBaixoMps: Double, taxaGuinadaGrausS: Double) {
        val param = VirtualStickFlightControlParam().apply {
            rollPitchCoordinateSystem = FlightCoordinateSystem.GROUND
            rollPitchControlMode = RollPitchControlMode.VELOCITY
            verticalControlMode = VerticalControlMode.VELOCITY
            yawControlMode = YawControlMode.ANGULAR_VELOCITY
            roll = if (ROLL_E_NORTE) vNorteMps else vLesteMps
            pitch = if (ROLL_E_NORTE) vLesteMps else vNorteMps
            verticalThrottle = -vBaixoMps
            yaw = taxaGuinadaGrausS
        }
        VirtualStickManager.getInstance().sendVirtualStickAdvancedParam(param)
    }

    override fun encerrar() {
        KeyManager.getInstance().cancelListen(dono)
    }
}
