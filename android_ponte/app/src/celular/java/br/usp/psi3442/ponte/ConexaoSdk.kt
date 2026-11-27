package br.usp.psi3442.ponte

import android.content.Context
import dji.v5.common.error.IDJIError
import dji.v5.common.register.DJISDKInitEvent
import dji.v5.common.register.InitSettings
import dji.v5.common.register.SDKLinKMode
import dji.v5.manager.SDKManager
import dji.v5.manager.interfaces.SDKManagerCallback

/**
 * ConexaoSdk (nível n): inicializa o DJI Mobile SDK v5, registra o app com a App Key (exige internet na primeira
 * vez) e acompanha a conexão da aeronave. Segue o MSDKManagerVM do app de exemplo da DJI.
 */
object ConexaoSdk {
    @Volatile var inicializado = false
        private set
    @Volatile var registrado = false
        private set
    @Volatile var produtoConectado = false
        private set
    @Volatile var ultimoErro: String? = null
        private set
    private var iniciado = false

    @Synchronized
    fun iniciar(contexto: Context, log: (String) -> Unit) {
        if (iniciado) return
        iniciado = true
        SDKManager.getInstance().init(contexto.applicationContext, InitSettings(SDKLinKMode.LOCAL), object : SDKManagerCallback {
            override fun onRegisterSuccess() {
                registrado = true
                log("SDK registrado")
            }

            override fun onRegisterFailure(error: IDJIError) {
                registrado = false
                ultimoErro = error.toString()
                log("falha no registro do SDK: $error")
            }

            override fun onProductDisconnect(productId: Int) {
                produtoConectado = false
                log("aeronave desconectada ($productId)")
            }

            override fun onProductConnect(productId: Int) {
                produtoConectado = true
                log("aeronave conectada ($productId)")
            }

            override fun onProductChanged(productId: Int) {
                log("produto alterado ($productId)")
            }

            override fun onInitProcess(event: DJISDKInitEvent, totalProcess: Int) {
                if (event == DJISDKInitEvent.INITIALIZE_COMPLETE) {
                    inicializado = true
                    log("SDK inicializado; registrando o app")
                    SDKManager.getInstance().registerApp()
                }
            }

            @Deprecated("Deprecated")
            override fun onDatabaseDownloadProgress(current: Long, total: Long) {}
        })
    }

    fun resumo(): String = "SDK: inicializado=$inicializado registrado=$registrado aeronave=$produtoConectado" +
        (ultimoErro?.let { "\nÚltimo erro do SDK: $it" } ?: "")
}
