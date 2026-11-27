package br.usp.psi3442.ponte

/** Redução de quadros NV21 (formato entregue pelo decodificador do SDK) sem passar por Bitmap. */
object Nv21 {
    /**
     * Amostra 1 a cada [fator] pixels nas duas direções e devolve (dados NV21, largura, altura), com dimensões
     * pares. Plano Y (largura x altura) seguido do plano VU intercalado em meia resolução.
     */
    fun reduzir(dados: ByteArray, deslocamento: Int, largura: Int, altura: Int, fator: Int): Triple<ByteArray, Int, Int> {
        require(fator >= 1)
        val l2 = (largura / fator) and 1.inv()
        val a2 = (altura / fator) and 1.inv()
        val saida = ByteArray(l2 * a2 * 3 / 2)
        for (y in 0 until a2) {
            val origem = deslocamento + (y * fator) * largura
            val destino = y * l2
            for (x in 0 until l2) saida[destino + x] = dados[origem + x * fator]
        }
        val inicioVu = deslocamento + largura * altura
        for (j in 0 until a2 / 2) {
            val origem = inicioVu + (j * fator) * largura
            val destino = l2 * a2 + j * l2
            for (i in 0 until l2 / 2) {
                saida[destino + 2 * i] = dados[origem + 2 * i * fator]
                saida[destino + 2 * i + 1] = dados[origem + 2 * i * fator + 1]
            }
        }
        return Triple(saida, l2, a2)
    }

    /** Fator inteiro que deixa a largura em no máximo [larguraMax]. */
    fun fatorPara(largura: Int, larguraMax: Int) = maxOf(1, (largura + larguraMax - 1) / larguraMax)
}
