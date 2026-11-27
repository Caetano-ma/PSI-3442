package br.usp.psi3442.ponte

import java.io.IOException
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.charset.StandardCharsets

/**
 * Canal de vídeo (Tarefa 2): servidor TCP na porta do ContratoSocketPonte + 1. Cada quadro é uma linha JSON de
 * cabeçalho ([Protocolo.cabecalhoQuadro]) seguida dos bytes do JPEG. Só o quadro mais recente é enviado: se a rede
 * atrasar, os intermediários são descartados (a visão quer o quadro atual, não a fila). Um cliente por vez.
 */
class ServidorVideo(private val porta: Int, private val log: (String) -> Unit) {
    @Volatile private var servidor: ServerSocket? = null
    @Volatile private var cliente: Socket? = null
    private val trava = Object()
    private var pendente: Quadro? = null
    @Volatile var enviados = 0L
        private set
    @Volatile var descartados = 0L
        private set

    val portaLocal: Int get() = servidor?.localPort ?: porta
    val clienteConectado: Boolean get() = cliente != null

    fun iniciar() {
        val s = ServerSocket()
        s.reuseAddress = true
        s.bind(InetSocketAddress(porta))
        servidor = s
        Thread({ aceitar(s) }, "video-aceitar").apply { isDaemon = true }.start()
        Thread(::escrever, "video-escrever").apply { isDaemon = true }.start()
        log("canal de vídeo na porta ${s.localPort}")
    }

    fun parar() {
        try { servidor?.close() } catch (_: IOException) {}
        fechar()
        servidor = null
        synchronized(trava) { trava.notifyAll() }
    }

    /** Entrega um quadro para envio (não bloqueia). */
    fun enviar(quadro: Quadro) {
        if (cliente == null) return
        synchronized(trava) {
            if (pendente != null) descartados++
            pendente = quadro
            trava.notifyAll()
        }
    }

    private fun aceitar(s: ServerSocket) {
        while (!s.isClosed) {
            val conexao = try { s.accept() } catch (e: IOException) { break }
            conexao.tcpNoDelay = true
            fechar()
            cliente = conexao
            log("cliente de vídeo conectado de ${conexao.remoteSocketAddress}")
        }
    }

    private fun proximo(): Quadro? = synchronized(trava) {
        while (pendente == null && servidor != null) trava.wait(500)
        val quadro = pendente
        pendente = null
        quadro
    }

    private fun escrever() {
        while (servidor != null) {
            val quadro = proximo() ?: continue
            val saida: OutputStream = try { cliente?.getOutputStream() } catch (_: IOException) { null } ?: continue
            try {
                saida.write(Protocolo.codificarCabecalho(quadro).toByteArray(StandardCharsets.UTF_8))
                saida.write(quadro.jpeg)
                saida.flush()
                enviados++
            } catch (e: IOException) {
                log("cliente de vídeo desconectado: ${e.message}")
                fechar()
            }
        }
    }

    private fun fechar() {
        val anterior = cliente
        cliente = null
        try { anterior?.close() } catch (_: IOException) {}
    }
}
