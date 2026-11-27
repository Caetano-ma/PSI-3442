package br.usp.psi3442.ponte

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.net.Socket
import java.nio.charset.StandardCharsets
import kotlin.math.abs

/** Tarefa 2 no app ponte: redução NV21, cena falsa, canal de vídeo, obstáculos e guinada do drone falso. */
class SensoresTest {
    /** Nos testes JVM não há codificador JPEG (o android.jar só tem stubs): bytes que identificam a imagem. */
    private fun jpegJvm(pixels: IntArray, l: Int, a: Int): ByteArray =
        ByteArray(l * 8) { i -> (pixels[(a / 2) * l + i / 8] shr (i % 4 * 8)).toByte() }

    @Test
    fun reducaoNv21PreservaPlanosEDimensoesPares() {
        val l = 12; val a = 8
        val dados = ByteArray(l * a * 3 / 2) { i -> if (i < l * a) (i % l).toByte() else (100 + (i - l * a) % l).toByte() }
        val (saida, l2, a2) = Nv21.reduzir(dados, 0, l, a, 3)
        assertEquals(4, l2); assertEquals(2, a2)
        assertEquals(l2 * a2 * 3 / 2, saida.size)
        assertEquals(listOf(0, 3, 6, 9), (0 until 4).map { saida[it].toInt() })     // colunas 0, 3, 6, 9
        assertEquals(100, saida[l2 * a2].toInt())                                    // V da 1ª coluna
        assertEquals(106, saida[l2 * a2 + 2].toInt())                                // V da coluna de croma 3 (bytes 6..7)
        assertEquals(3, Nv21.fatorPara(1920, 640))
        assertEquals(1, Nv21.fatorPara(640, 640))
    }

    @Test
    fun cenaFalsaMostraOBalaoDeFrenteNoCentroDaImagem() {
        val cena = CenaFalsa.padrao()
        val vermelho = cena.baloes.first()
        // 0,5 m antes do balão, olhando para ele, à mesma altura (câmera 3 cm acima do centro)
        val g = 0.0
        val pixels = cena.renderizar(vermelho.x - 0.5, vermelho.y, vermelho.z - 0.03, g)
        val centro = pixels[(cena.altura / 2) * cena.largura + cena.largura / 2]
        val r = (centro shr 16) and 0xFF; val gg = (centro shr 8) and 0xFF; val b = centro and 0xFF
        assertTrue("centro deveria ser vermelho: $r $gg $b", r > 120 && gg < 80 && b < 80)
        // canto superior: fundo (parede), não vermelho
        val canto = pixels[5 * cena.largura + 5]
        assertTrue(((canto shr 16) and 0xFF) - (canto and 0xFF) < 60)
    }

    @Test
    fun distanciasDaCenaFalsaVaoAteParedesEBaloes() {
        val cena = CenaFalsa.padrao()
        val d = cena.distancias(0.0, 0.0, 1.4, 0.0)
        assertEquals(72, d.size)
        assertEquals(5.4, d[0], 1e-6)            // nariz (+x) até a parede x = 5,4
        assertEquals(1.0, d[18], 1e-6)           // 90° horário = -y: parede y = -1
        assertEquals(4.4, d[54], 1e-6)           // 270° horário = +y: parede y = 4,4
        val dBalao = cena.distancias(2.0, 1.0, 1.6, 0.0)
        assertEquals(1.0 - 0.13, dBalao[0], 1e-6)  // balão vermelho em (3, 1, 1,6) à frente
    }

    @Test
    fun guinadaDoDroneFalsoSegueATaxaComandada() {
        val drone = DroneFalso(guinadaInicialGraus = 30.0, ruidoMps = 0.0)
        drone.habilitarControleVirtual {}
        drone.decolar {}
        var t = 0.0
        while (drone.altura < 1.2) { drone.passo(0.02, t); t += 0.02 }
        repeat(150) { drone.enviarVelocidade(0.0, 0.0, 0.0, 20.0); drone.passo(0.02, t); t += 0.02 }  // 3 s
        val bussola = drone.telemetria(t).guinadaGraus
        assertTrue("guinada $bussola", abs(bussola - (30.0 + 60.0 - 20.0 * 0.3)) < 3.0)
        // horária na bússola = anti-horária negativa no local
        assertTrue(drone.poseLocal()[3] < -40.0)
    }

    @Test
    fun canalDeVideoEnviaCabecalhoEJpeg() {
        val servidor = ServidorVideo(0) {}
        servidor.iniciar()
        Socket("127.0.0.1", servidor.portaLocal).use { cliente ->
            val inicio = System.currentTimeMillis()
            while (!servidor.clienteConectado && System.currentTimeMillis() - inicio < 2000) Thread.sleep(10)
            val cena = CenaFalsa.padrao()
            val jpeg = jpegJvm(cena.renderizar(0.0, 0.0, 1.4, 0.0), cena.largura, cena.altura)
            servidor.enviar(Quadro(12.5, cena.largura, cena.altura, jpeg, 0.0))
            val entrada = DataInputStream(cliente.getInputStream())
            val linha = ByteArrayOutputStream()
            while (true) { val b = entrada.read(); if (b == '\n'.code) break; linha.write(b) }
            val cabecalho = JSONObject(String(linha.toByteArray(), StandardCharsets.UTF_8))
            assertEquals("quadro", cabecalho.getString("tipo"))
            assertEquals(jpeg.size, cabecalho.getInt("bytes"))
            assertEquals(640, cabecalho.getInt("largura"))
            val corpo = ByteArray(jpeg.size).also { entrada.readFully(it) }
            assertTrue(corpo.contentEquals(jpeg))
        }
        servidor.parar()
    }

    @Test
    fun obstaculosViramJsonComNulos() {
        val json = Protocolo.decodificar(Protocolo.codificar(Protocolo.obstaculos(
            Obstaculos(1.0, 5.0, listOf(1.5, Double.NaN, 3.0)))).trim())
        assertEquals("obstaculos", json.getString("tipo"))
        assertTrue(json.getJSONArray("distancias_m").isNull(1))
        assertEquals(3.0, json.getJSONArray("distancias_m").getDouble(2), 1e-9)
    }
}
