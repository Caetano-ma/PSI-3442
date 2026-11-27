package br.usp.psi3442.ponte

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin

/** T09 (R07): watchdog de 0,2 s e pouso após 2 s sem heartbeat, e a conversão de referencial. */
class EmissorComandosTest {
    private fun tel(emVoo: Boolean = true, controleVirtual: Boolean = true, manobra: Boolean = false) = Telemetria(
        0.0, 0.0, 0.0, 0.0, 1.8, 1.8, 30.0, emVoo, emVoo, "VIRTUAL_STICK", 80.0, true, true, controleVirtual,
        "pousar", manobra,
    )

    private val cmd = Protocolo.ComandoLocal(0.3, 0.1, 0.05, 0.0, 30.0)

    @Test
    fun conversaoIgualAoPython() {
        for (psi0 in listOf(0.0, 30.0, 90.0, -135.0)) {
            val r = Math.toRadians(psi0)
            val (n, e) = soloDeLocal(0.3, 0.1, psi0)
            assertEquals(0.3 * cos(r) + 0.1 * sin(r), n, 1e-12)
            assertEquals(0.3 * sin(r) - 0.1 * cos(r), e, 1e-12)
        }
        val (n, e) = soloDeLocal(1.0, 0.0, 90.0)
        assertEquals(0.0, n, 1e-12)
        assertEquals(1.0, e, 1e-12)
    }

    @Test
    fun comandoRecenteEhConvertidoParaOSolo() {
        val em = EmissorComandos()
        em.aoHeartbeat(0.0)
        em.aoCmdVel(cmd, 0.0)
        val d = em.passo(0.1, tel()) as EmissorComandos.Decisao.Velocidade
        val (n, e) = soloDeLocal(0.3, 0.1, 30.0)
        assertEquals(n, d.vNorte, 1e-12)
        assertEquals(e, d.vLeste, 1e-12)
        assertEquals(-0.05, d.vBaixo, 1e-12)
    }

    @Test
    fun watchdogZeraAVelocidadeDepoisDe200ms() {
        val em = EmissorComandos()
        em.aoHeartbeat(0.0)
        em.aoCmdVel(cmd, 0.0)
        assertTrue((em.passo(0.19, tel()) as EmissorComandos.Decisao.Velocidade).vNorte != 0.0)
        assertEquals(EmissorComandos.Decisao.Velocidade(0.0, 0.0, 0.0, 0.0), em.passo(0.21, tel()))
    }

    @Test
    fun semComandoNenhumComControleVirtualMandaZero() {
        assertEquals(EmissorComandos.Decisao.Velocidade(0.0, 0.0, 0.0, 0.0), EmissorComandos().passo(1.0, tel()))
    }

    @Test
    fun perdaDaPonteDisparaUmPousoPorVoo() {
        val em = EmissorComandos()
        em.aoHeartbeat(0.0)
        em.aoCmdVel(cmd, 1.9)
        assertTrue(em.passo(2.0, tel()) is EmissorComandos.Decisao.Velocidade)
        assertEquals(EmissorComandos.Decisao.Pousar, em.passo(2.01, tel()))
        assertEquals(EmissorComandos.Decisao.Nenhuma, em.passo(2.5, tel()))
        assertEquals(EmissorComandos.Decisao.Nenhuma, em.passo(3.0, tel(emVoo = false)))
        assertEquals(EmissorComandos.Decisao.Pousar, em.passo(10.0, tel()))
    }

    @Test
    fun nadaDuranteManobraAutomaticaOuNoSolo() {
        val em = EmissorComandos()
        em.aoCmdVel(cmd, 0.0)
        assertEquals(EmissorComandos.Decisao.Nenhuma, em.passo(0.1, tel(manobra = true)))
        assertEquals(EmissorComandos.Decisao.Nenhuma, em.passo(0.1, tel(emVoo = false)))
        assertEquals(EmissorComandos.Decisao.Nenhuma, em.passo(0.1, tel(controleVirtual = false)))
    }

    @Test
    fun pararEPairarDescartaOComando() {
        val em = EmissorComandos()
        em.aoCmdVel(cmd, 0.0)
        em.pararEPairar()
        assertEquals(EmissorComandos.Decisao.Velocidade(0.0, 0.0, 0.0, 0.0), em.passo(0.05, tel()))
    }
}
