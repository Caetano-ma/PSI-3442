package br.usp.psi3442.ponte

import android.app.Application
import android.content.Context

/** O DJI Mobile SDK v5 exige Helper.install na Application antes de qualquer uso (como no app de exemplo da DJI). */
class AplicacaoPonte : Application() {
    override fun attachBaseContext(base: Context?) {
        super.attachBaseContext(base)
        com.cySdkyc.clx.Helper.install(this)
    }
}
