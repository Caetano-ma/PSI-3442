package br.usp.psi3442.ponte

import org.json.JSONException
import org.json.JSONObject

/**
 * ContratoSocketPonte: JSON UTF-8, uma mensagem por linha, campo "tipo" em {telemetria, cmd_vel, acao, heartbeat,
 * erro}. Especificação no cabeçalho de ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_ponte_dji.py.
 */
object Protocolo {
    val TIPOS = setOf("telemetria", "cmd_vel", "acao", "heartbeat", "erro")
    const val TAMANHO_MAX_LINHA = 64 * 1024

    class ErroProtocolo(mensagem: String) : Exception(mensagem)

    fun decodificar(linha: String): JSONObject {
        val json = try {
            JSONObject(linha)
        } catch (e: JSONException) {
            throw ErroProtocolo("JSON inválido: ${e.message}")
        }
        if (json.optString("tipo") !in TIPOS) throw ErroProtocolo("mensagem sem campo \"tipo\" válido")
        return json
    }

    fun codificar(mensagem: JSONObject): String {
        require(mensagem.optString("tipo") in TIPOS) { "tipo inválido: ${mensagem.opt("tipo")}" }
        return mensagem.toString() + "\n"
    }

    fun telemetria(tel: Telemetria): JSONObject = JSONObject()
        .put("tipo", "telemetria")
        .put("instante_s", tel.instanteS)
        .put("v_norte_mps", tel.vNorteMps)
        .put("v_leste_mps", tel.vLesteMps)
        .put("v_baixo_mps", tel.vBaixoMps)
        .put("altitude_m", tel.altitudeM)
        .put("altura_tof_m", tel.alturaTofM?.takeIf { it.isFinite() } ?: JSONObject.NULL)
        .put("guinada_graus", tel.guinadaGraus)
        .put("em_voo", tel.emVoo)
        .put("motores_ligados", tel.motoresLigados)
        .put("modo_voo", tel.modoVoo)
        .put("bateria_pct", tel.bateriaPct)
        .put("conectado", tel.conectado)
        .put("posicionamento_visual_ativo", tel.posicionamentoVisualAtivo)
        .put("controle_virtual_ativo", tel.controleVirtualAtivo)
        .put("acao_perda_sinal", tel.acaoPerdaSinal)

    fun heartbeat(instanteS: Double): JSONObject = JSONObject().put("tipo", "heartbeat").put("instante_s", instanteS)

    fun erro(comando: String, mensagem: String): JSONObject =
        JSONObject().put("tipo", "erro").put("comando", comando).put("mensagem", mensagem)

    /** cmd_vel do nó ponte: velocidades no ReferencialLocal e psi0 para a conversão ao referencial do solo. */
    data class ComandoLocal(
        val vxMps: Double, val vyMps: Double, val vzMps: Double, val taxaGuinadaGrausS: Double, val psi0Graus: Double,
    )

    fun comandoLocal(json: JSONObject) = ComandoLocal(
        vxMps = json.getDouble("vx_mps"),
        vyMps = json.getDouble("vy_mps"),
        vzMps = json.getDouble("vz_mps"),
        taxaGuinadaGrausS = json.optDouble("taxa_guinada_grausps", 0.0),
        psi0Graus = json.getDouble("psi0_graus"),
    )
}

/** Acumula bytes recebidos e devolve as linhas completas (mesmo comportamento do LeitorLinhas em Python). */
class LeitorLinhas {
    private val buffer = StringBuilder()

    fun alimentar(texto: String): List<String> {
        buffer.append(texto)
        val linhas = mutableListOf<String>()
        while (true) {
            val fim = buffer.indexOf("\n")
            if (fim < 0) break
            val linha = buffer.substring(0, fim)
            buffer.delete(0, fim + 1)
            if (linha.isNotBlank()) linhas += linha
        }
        if (buffer.length > Protocolo.TAMANHO_MAX_LINHA) {
            buffer.setLength(0)
            throw Protocolo.ErroProtocolo("linha maior que o limite")
        }
        return linhas
    }
}
