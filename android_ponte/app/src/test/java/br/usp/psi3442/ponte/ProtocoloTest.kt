package br.usp.psi3442.ponte

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtocoloTest {
    /** As mesmas chaves de CAMPOS_TELEMETRIA em no_ponte_dji.py (o nó ROS 2 lê exatamente estas). */
    private val chavesPython = setOf(
        "instante_s", "v_norte_mps", "v_leste_mps", "v_baixo_mps", "altitude_m", "altura_tof_m", "guinada_graus",
        "em_voo", "motores_ligados", "modo_voo", "bateria_pct", "conectado", "posicionamento_visual_ativo",
        "controle_virtual_ativo", "acao_perda_sinal",
    )

    private fun telemetria(alturaTof: Double?) = Telemetria(
        1.5, 0.1, -0.2, 0.05, 1.8, alturaTof, 30.0, true, true, "VIRTUAL_STICK", 77.0, true, true, true,
        "pousar", false,
    )

    @Test
    fun telemetriaTemExatamenteOsCamposDoNoPonte() {
        val json = Protocolo.telemetria(telemetria(1.79))
        assertEquals("telemetria", json.getString("tipo"))
        assertEquals(chavesPython + "tipo", json.keySet())
        assertEquals(-0.2, json.getDouble("v_leste_mps"), 1e-12)
        assertEquals("pousar", json.getString("acao_perda_sinal"))
    }

    @Test
    fun alturaTofAusenteViraNull() {
        val json = Protocolo.telemetria(telemetria(null))
        assertTrue(json.isNull("altura_tof_m"))
        val linha = Protocolo.codificar(json)
        assertTrue(linha.endsWith("\n"))
        assertTrue(linha.contains("\"altura_tof_m\":null"))
    }

    @Test
    fun decodificaCmdVelComoONoPonteEnvia() {
        val linha = """{"tipo":"cmd_vel","vx_mps":0.3,"vy_mps":-0.1,"vz_mps":0.05,"taxa_guinada_grausps":0.0,"psi0_graus":30.0}"""
        val c = Protocolo.comandoLocal(Protocolo.decodificar(linha))
        assertEquals(Protocolo.ComandoLocal(0.3, -0.1, 0.05, 0.0, 30.0), c)
    }

    @Test(expected = Protocolo.ErroProtocolo::class)
    fun rejeitaTipoDesconhecido() {
        Protocolo.decodificar("""{"tipo":"outro"}""")
    }

    @Test(expected = Protocolo.ErroProtocolo::class)
    fun rejeitaJsonInvalido() {
        Protocolo.decodificar("{nao é json")
    }

    @Test
    fun leitorDeLinhasJuntaFragmentos() {
        val leitor = LeitorLinhas()
        assertEquals(emptyList<String>(), leitor.alimentar("""{"tipo":"heart"""))
        assertEquals(listOf("""{"tipo":"heartbeat"}""", """{"tipo":"acao"}"""),
            leitor.alimentar("beat\"}\n\n{\"tipo\":\"acao\"}\n{\"ti"))
        assertEquals(listOf("""{"tipo":"erro"}"""), leitor.alimentar("po\":\"erro\"}\n"))
    }

    @Test
    fun erroTemOsCamposQueONoPonteLe() {
        val json: JSONObject = Protocolo.erro("decolar", "motores bloqueados")
        assertEquals(setOf("tipo", "comando", "mensagem"), json.keySet())
        assertFalse(json.isNull("mensagem"))
    }
}
