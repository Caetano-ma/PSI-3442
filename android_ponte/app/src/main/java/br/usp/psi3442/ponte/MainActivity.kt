package br.usp.psi3442.ponte

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.net.Inet4Address
import java.net.NetworkInterface
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Tela do app ponte: escolhe o drone (DJI ou falso), inicia a ponte e mostra conexão, telemetria e log. */
class MainActivity : Activity() {
    private var ponte: Ponte? = null
    private val linhasLog = ArrayDeque<String>()
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var estado: TextView
    private lateinit var registro: TextView
    private lateinit var botoes: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        FabricaDrone.preparar(this, ::registrar)

        estado = TextView(this).apply { typeface = Typeface.MONOSPACE; textSize = 13f }
        registro = TextView(this).apply { typeface = Typeface.MONOSPACE; textSize = 11f }
        botoes = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        for (modo in FabricaDrone.modos) {
            botoes.addView(Button(this).apply {
                text = "Iniciar ($modo)"
                setOnClickListener { iniciar(modo) }
            })
        }
        botoes.addView(Button(this).apply { text = "Parar"; setOnClickListener { parar() } })

        val raiz = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 24, 24, 24)
            addView(TextView(context).apply { text = "PSI3442 — app ponte DJI"; textSize = 18f })
            addView(botoes)
            addView(estado)
            addView(registro)
        }
        setContentView(ScrollView(this).apply { addView(raiz) })
        handler.post(object : Runnable {
            override fun run() {
                atualizarTela()
                handler.postDelayed(this, 500)
            }
        })
        intent?.getStringExtra("modo")?.takeIf { it in FabricaDrone.modos }?.let(::iniciar)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        parar()
        super.onDestroy()
    }

    private fun iniciar(modo: String) {
        if (ponte != null) return
        try {
            ponte = Ponte(FabricaDrone.criar(this, modo), log = ::registrar).also { it.iniciar() }
        } catch (e: Exception) {
            registrar("não foi possível iniciar: $e")
            ponte = null
        }
    }

    private fun parar() {
        ponte?.parar()
        ponte = null
    }

    private fun registrar(texto: String) {
        val hora = SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())
        synchronized(linhasLog) {
            linhasLog.addFirst("$hora $texto")
            while (linhasLog.size > 40) linhasLog.removeLast()
        }
    }

    private fun atualizarTela() {
        val p = ponte
        val texto = StringBuilder()
        texto.append(FabricaDrone.estado()).append('\n')
        if (p == null) {
            texto.append("Ponte parada.\n")
        } else {
            texto.append("Drone: ${p.descricaoDrone}\n")
            texto.append("Porta: ${p.porta}   IPs: ${enderecos().joinToString()}\n")
            texto.append("Nó ponte ROS 2: ${p.cliente ?: "desconectado"}\n")
            p.telemetria?.let { t ->
                texto.append(
                    String.format(
                        Locale.US,
                        "Telemetria: conectado=%s em_voo=%s motores=%s modo=%s\n" +
                            "  v N/L/B = %+.2f %+.2f %+.2f m/s  alt = %.2f m  guinada = %.1f°\n" +
                            "  bateria = %.0f%%  PV=%s  controle virtual=%s  perda de sinal=%s\n",
                        t.conectado, t.emVoo, t.motoresLigados, t.modoVoo, t.vNorteMps, t.vLesteMps, t.vBaixoMps,
                        t.altitudeM, t.guinadaGraus, t.bateriaPct, t.posicionamentoVisualAtivo,
                        t.controleVirtualAtivo, t.acaoPerdaSinal,
                    )
                )
            }
        }
        estado.text = texto
        registro.text = synchronized(linhasLog) { linhasLog.joinToString("\n") }
    }

    private fun enderecos(): List<String> = try {
        NetworkInterface.getNetworkInterfaces().toList()
            .flatMap { it.inetAddresses.toList() }
            .filter { it is Inet4Address && !it.isLoopbackAddress }
            .map { it.hostAddress ?: "?" }
    } catch (e: Exception) {
        emptyList()
    }
}
