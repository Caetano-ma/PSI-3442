package br.usp.psi3442.ponte

/** LeitorTelemetria (nível n): lê a aeronave a 10 Hz e publica no socket; heartbeat a 1 Hz. */
class LeitorTelemetria(private val drone: Drone, private val servidor: ServidorSocket) {
    @Volatile var ultima: Telemetria? = null
        private set
    @Volatile var amostrasEnviadas = 0L
        private set

    fun ler(agoraS: Double): Telemetria = drone.telemetria(agoraS).also { ultima = it }

    fun publicar(agoraS: Double) {
        if (servidor.enviar(Protocolo.telemetria(ler(agoraS)))) amostrasEnviadas++
    }

    fun heartbeat(agoraS: Double) {
        servidor.enviar(Protocolo.heartbeat(agoraS))
    }
}
