package br.usp.psi3442.ponte

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan

/** Balão da cena falsa, no ReferencialLocal (origem no ponto de decolagem, x à frente do nariz, y à esquerda). */
data class BalaoFalso(val cor: Int, val x: Double, val y: Double, val z: Double, val raio: Double = 0.13)

/**
 * Cena do drone falso para testar a Tarefa 2 sem aeronave (emulador ou celular em modo "falso"): sala retangular
 * com piso xadrez e balões esféricos sombreados. A imagem é traçada por raios a partir da câmera (pinhole, campo de
 * visão horizontal [hfovGraus], 0,10 m à frente e 0,03 m acima do centro, como em no_mapeamento_local); as
 * distâncias imitam a percepção de obstáculos (plano horizontal, sentido horário a partir do nariz).
 */
class CenaFalsa(
    val baloes: List<BalaoFalso>,
    private val xMin: Double, private val xMax: Double, private val yMin: Double, private val yMax: Double,
    private val alturaSala: Double = 3.0,
    val hfovGraus: Double = 82.1,
    val largura: Int = 640,
    val altura: Int = 480,
) {
    companion object {
        const val VERMELHO = 0xFFD91414.toInt()
        const val AZUL = 0xFF1A40D9.toInt()
        const val VERDE = 0xFF1AB333.toInt()
        const val AMARELO = 0xFFF2CC1A.toInt()
        const val ROXO = 0xFF8C26BF.toInt()
        private val LUZ = normalizar(doubleArrayOf(0.3, 0.2, 0.93))

        /** Cena de referência (a mesma de test_tarefa2.py): dois alvos e duas cores não alvo. */
        fun padrao() = CenaFalsa(
            listOf(BalaoFalso(VERMELHO, 3.0, 1.0, 1.6), BalaoFalso(AZUL, 1.0, 3.0, 1.1),
                BalaoFalso(VERDE, 2.0, 2.0, 1.5), BalaoFalso(AMARELO, 3.8, 3.0, 1.2)),
            -1.0, 5.4, -1.0, 4.4)

        private fun normalizar(v: DoubleArray): DoubleArray {
            val n = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
            return doubleArrayOf(v[0] / n, v[1] / n, v[2] / n)
        }

        private fun escalar(cor: Int, k: Double, brilho: Double): Int {
            fun canal(c: Int) = min(255.0, ((cor shr c) and 0xFF) * k + 255 * brilho).toInt()
            return (0xFF shl 24) or (canal(16) shl 16) or (canal(8) shl 8) or canal(0)
        }
    }

    private val f = (largura / 2.0) / tan(Math.toRadians(hfovGraus) / 2.0)

    /** Imagem ARGB (largura x altura) vista da pose (x, y, z do centro da aeronave; guinada local em graus). */
    fun renderizar(x: Double, y: Double, z: Double, guinadaLocalGraus: Double): IntArray {
        val g = Math.toRadians(guinadaLocalGraus)
        val fx = cos(g); val fy = sin(g)                 // frente
        val lx = -fy; val ly = fx                        // esquerda
        val cx = x + 0.10 * fx; val cy = y + 0.10 * fy; val cz = z + 0.03
        val pixels = IntArray(largura * altura)
        for (v in 0 until altura) {
            val dzCam = altura / 2.0 - v
            for (u in 0 until largura) {
                val dyCam = largura / 2.0 - u
                val n = sqrt(f * f + dyCam * dyCam + dzCam * dzCam)
                val dx = (f * fx + dyCam * lx) / n
                val dy = (f * fy + dyCam * ly) / n
                val dz = dzCam / n
                pixels[v * largura + u] = cor(cx, cy, cz, dx, dy, dz)
            }
        }
        return pixels
    }

    private fun cor(cx: Double, cy: Double, cz: Double, dx: Double, dy: Double, dz: Double): Int {
        var tMelhor = Double.MAX_VALUE
        var balao: BalaoFalso? = null
        for (b in baloes) {
            val ox = cx - b.x; val oy = cy - b.y; val oz = cz - b.z
            val bb = ox * dx + oy * dy + oz * dz
            val c = ox * ox + oy * oy + oz * oz - b.raio * b.raio
            val disc = bb * bb - c
            if (disc < 0) continue
            val t = -bb - sqrt(disc)
            if (t > 1e-3 && t < tMelhor) { tMelhor = t; balao = b }
        }
        val tFundo = fundo(cx, cy, cz, dx, dy, dz)
        if (balao != null && tMelhor < tFundo.first) {
            val px = cx + tMelhor * dx - balao.x; val py = cy + tMelhor * dy - balao.y; val pz = cz + tMelhor * dz - balao.z
            val nx = px / balao.raio; val ny = py / balao.raio; val nz = pz / balao.raio
            val difusa = max(0.0, nx * LUZ[0] + ny * LUZ[1] + nz * LUZ[2])
            val dn = nx * dx + ny * dy + nz * dz                           // reflexo do raio na superfície
            val refletido = (dx - 2 * dn * nx) * LUZ[0] + (dy - 2 * dn * ny) * LUZ[1] + (dz - 2 * dn * nz) * LUZ[2]
            val especular = 0.5 * max(0.0, refletido).pow(30)
            return escalar(balao.cor, 0.6 + 0.4 * difusa, especular)
        }
        return tFundo.second
    }

    /** (distância, cor) do piso, teto ou parede atingido. */
    private fun fundo(cx: Double, cy: Double, cz: Double, dx: Double, dy: Double, dz: Double): Pair<Double, Int> {
        var t = Double.MAX_VALUE
        var cor = 0xFFE0E0DC.toInt()
        if (dz < -1e-9) {
            val tp = -cz / dz
            if (tp < t) {
                t = tp
                val px = cx + tp * dx; val py = cy + tp * dy
                val xadrez = (floor(px / 0.5) + floor(py / 0.5)).toInt() and 1
                cor = if (xadrez == 0) 0xFF8C806B.toInt() else 0xFF7A6F5C.toInt()
            }
        } else if (dz > 1e-9) {
            val tt = (alturaSala - cz) / dz
            if (tt < t) { t = tt; cor = 0xFFF0F0F0.toInt() }
        }
        val tParede = paredeHorizontal(cx, cy, dx, dy)
        if (tParede.first < t) {
            t = tParede.first
            val sombra = 0.85 + 0.15 * ((cz + t * dz) / alturaSala)
            cor = escalar(tParede.second, sombra, 0.0)
        }
        return t to cor
    }

    private fun paredeHorizontal(cx: Double, cy: Double, dx: Double, dy: Double): Pair<Double, Int> {
        var t = Double.MAX_VALUE
        var cor = 0
        if (dx > 1e-9) { val tt = (xMax - cx) / dx; if (tt < t) { t = tt; cor = 0xFFEBEBE0.toInt() } }
        if (dx < -1e-9) { val tt = (xMin - cx) / dx; if (tt < t) { t = tt; cor = 0xFFE6E0D6.toInt() } }
        if (dy > 1e-9) { val tt = (yMax - cy) / dy; if (tt < t) { t = tt; cor = 0xFFE0E6EB.toInt() } }
        if (dy < -1e-9) { val tt = (yMin - cy) / dy; if (tt < t) { t = tt; cor = 0xFFDCE6DC.toInt() } }
        return t to cor
    }

    /** Distâncias horizontais (m) no plano da aeronave, sentido horário a partir do nariz, até paredes e balões. */
    fun distancias(x: Double, y: Double, z: Double, guinadaLocalGraus: Double, passoGraus: Double = 5.0,
                   alcanceM: Double = 8.0): List<Double> {
        val n = (360.0 / passoGraus).toInt()
        return List(n) { k ->
            val a = Math.toRadians(guinadaLocalGraus - k * passoGraus)
            val dx = cos(a); val dy = sin(a)
            var t = paredeHorizontal(x, y, dx, dy).first
            for (b in baloes) {
                val dzB = z - b.z
                if (kotlin.math.abs(dzB) >= b.raio) continue
                val r = sqrt(b.raio * b.raio - dzB * dzB)
                val ox = x - b.x; val oy = y - b.y
                val bb = ox * dx + oy * dy
                val disc = bb * bb - (ox * ox + oy * oy - r * r)
                if (disc < 0) continue
                val tt = -bb - sqrt(disc)
                if (tt > 0 && tt < t) t = tt
            }
            if (t <= alcanceM) t else Double.NaN
        }
    }

    /** Azimute (graus, local) do balão visto da posição (x, y), para testes. */
    fun azimute(b: BalaoFalso, x: Double, y: Double) = Math.toDegrees(atan2(b.y - y, b.x - x))
}
