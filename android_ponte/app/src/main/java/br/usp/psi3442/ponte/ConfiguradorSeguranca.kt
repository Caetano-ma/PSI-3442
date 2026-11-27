package br.usp.psi3442.ponte

/**
 * ConfiguradorSeguranca (nível n): assim que a aeronave aparece conectada, define a ação em perda de sinal como
 * pousar (retorno por GNSS é inválido em sala, R07). A confirmação é feita por leitura: a telemetria publica
 * `acao_perda_sinal`, que o gerenciador de tarefas exige igual a "pousar" na preparação.
 */
class ConfiguradorSeguranca(private val drone: Drone, private val log: (String) -> Unit) {
    @Volatile var configurado = false
        private set
    @Volatile private var tentando = false

    fun verificar(tel: Telemetria) {
        if (!tel.conectado) {
            configurado = false
            return
        }
        if (configurado || tentando) return
        if (tel.acaoPerdaSinal == "pousar") {
            configurado = true
            return
        }
        tentando = true
        drone.definirAcaoPerdaSinalPousar { erro ->
            tentando = false
            if (erro == null) {
                configurado = true
                log("ação em perda de sinal definida: pousar")
            } else {
                log("falha ao definir ação em perda de sinal: $erro")
            }
        }
    }
}
