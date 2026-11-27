package br.usp.psi3442.ponte

import android.graphics.Bitmap
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import java.io.ByteArrayOutputStream

/** Codificação JPEG com as classes do Android (não roda nos testes JVM). */
object JpegAndroid {
    const val QUALIDADE = 80

    fun deArgb(pixels: IntArray, largura: Int, altura: Int): ByteArray {
        val bitmap = Bitmap.createBitmap(pixels, largura, altura, Bitmap.Config.ARGB_8888)
        return ByteArrayOutputStream().also { bitmap.compress(Bitmap.CompressFormat.JPEG, QUALIDADE, it) }.toByteArray()
    }

    fun deNv21(dados: ByteArray, largura: Int, altura: Int): ByteArray {
        val saida = ByteArrayOutputStream()
        YuvImage(dados, ImageFormat.NV21, largura, altura, null).compressToJpeg(Rect(0, 0, largura, altura), QUALIDADE, saida)
        return saida.toByteArray()
    }
}
