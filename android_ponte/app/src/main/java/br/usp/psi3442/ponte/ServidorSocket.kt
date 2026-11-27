package br.usp.psi3442.ponte

import org.json.JSONObject
import java.io.IOException
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.charset.StandardCharsets

/**
 * ServidorSocket (nível n): servidor TCP do ContratoSocketPonte. Aceita um nó ponte por vez (uma nova conexão
 * substitui a anterior). Escuta em todas as interfaces: serve tanto ao `adb forward` (emulador, USB) quanto ao
 * Wi-Fi (celular ligado ao controle, notebook na mesma rede).
 */
class ServidorSocket(
    private val porta: Int,
    private val aoReceber: (JSONObject) -> Unit,
    private val aoMudarCliente: (String?) -> Unit,
    private val log: (String) -> Unit,
) {
    @Volatile private var servidor: ServerSocket? = null
    @Volatile private var cliente: Socket? = null
    private var saida: OutputStream? = null
    private val travaSaida = Any()

    val portaLocal: Int get() = servidor?.localPort ?: porta
    val clienteConectado: Boolean get() = cliente != null

    fun iniciar() {
        val s = ServerSocket()
        s.reuseAddress = true
        s.bind(InetSocketAddress(porta))
        servidor = s
        Thread({ aceitar(s) }, "ponte-aceitar").apply { isDaemon = true }.start()
        log("servidor escutando na porta ${s.localPort}")
    }

    fun parar() {
        try { servidor?.close() } catch (_: IOException) {}
        fecharCliente()
        servidor = null
    }

    /** Envia uma mensagem ao nó ponte; devolve false se não houver cliente. */
    fun enviar(mensagem: JSONObject): Boolean {
        val dados = Protocolo.codificar(mensagem).toByteArray(StandardCharsets.UTF_8)
        synchronized(travaSaida) {
            val out = saida ?: return false
            return try {
                out.write(dados)
                out.flush()
                true
            } catch (e: IOException) {
                log("falha ao enviar: ${e.message}")
                fecharCliente()
                false
            }
        }
    }

    private fun aceitar(s: ServerSocket) {
        while (!s.isClosed) {
            val conexao = try { s.accept() } catch (e: IOException) { break }
            conexao.tcpNoDelay = true
            fecharCliente()
            synchronized(travaSaida) {
                cliente = conexao
                saida = conexao.getOutputStream()
            }
            val origem = conexao.remoteSocketAddress.toString()
            log("nó ponte conectado de $origem")
            aoMudarCliente(origem)
            Thread({ atender(conexao) }, "ponte-cliente").apply { isDaemon = true }.start()
        }
    }

    private fun atender(conexao: Socket) {
        val leitor = LeitorLinhas()
        val entrada = InputStreamReader(conexao.getInputStream(), StandardCharsets.UTF_8)
        val buffer = CharArray(4096)
        try {
            while (cliente === conexao) {
                val n = entrada.read(buffer)
                if (n < 0) break
                val linhas = try {
                    leitor.alimentar(String(buffer, 0, n))
                } catch (e: Protocolo.ErroProtocolo) {
                    log("protocolo: ${e.message}")
                    continue
                }
                for (linha in linhas) {
                    try {
                        aoReceber(Protocolo.decodificar(linha))
                    } catch (e: Protocolo.ErroProtocolo) {
                        log("protocolo: ${e.message}")
                    }
                }
            }
        } catch (_: IOException) {
        }
        if (cliente === conexao) {
            fecharCliente()
            log("nó ponte desconectado")
        }
    }

    private fun fecharCliente() {
        val anterior: Socket?
        synchronized(travaSaida) {
            anterior = cliente
            cliente = null
            saida = null
        }
        if (anterior != null) {
            try { anterior.close() } catch (_: IOException) {}
            aoMudarCliente(null)
        }
    }
}
