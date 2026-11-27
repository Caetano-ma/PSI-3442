package br.usp.psi3442.ponte

import android.content.Context

/** Variante "celular": drone DJI pelo SDK, ou o drone falso para testar o celular sem a aeronave. */
object FabricaDrone {
    val modos = listOf("dji", "falso")

    fun preparar(contexto: Context, log: (String) -> Unit) = ConexaoSdk.iniciar(contexto, log)

    fun estado(): String = ConexaoSdk.resumo()

    fun criar(contexto: Context, modo: String): Drone = if (modo == "dji") DroneDji() else DroneFalso()
}
