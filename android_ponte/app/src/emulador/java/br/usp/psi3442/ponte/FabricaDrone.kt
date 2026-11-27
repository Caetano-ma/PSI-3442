package br.usp.psi3442.ponte

import android.content.Context

/** Variante "emulador": sem o SDK da DJI; só o drone falso. */
object FabricaDrone {
    val modos = listOf("falso")

    fun preparar(contexto: Context, log: (String) -> Unit) {}

    fun estado(): String = "Variante emulador: sem DJI SDK."

    fun criar(contexto: Context, modo: String): Drone =
        DroneFalso(cena = CenaFalsa.padrao(), codificarJpeg = JpegAndroid::deArgb)
}
