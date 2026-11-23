package VerificacaoQ1 {
    doc /* Casos de verificação da Questão 1 (coluna "teste e evidência" da matriz de rastreabilidade).
           Ensaios que possam comprometer o equipamento são feitos sem voo ou em teste controlado (seção 7).
           Os critérios usam os valores de NivelN::configQ1 (P05), a aprovar na entrega intermediária. */

    private import ScalarValues::*;

    verification def <T01> VerificarAlturaDecolagem {
        doc /* Método: z (ToF) registrado após AlturaAtingida + medição externa com régua vertical de referência em A,
               filmada de lado. Critério: |z - 1,80 m| <= tolVertical, no registro e na medição externa. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p01; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "CSV da missão (z_m, estado) + vídeo lateral com régua";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_q1.md#T01";
    }

    verification def <T02> VerificarQuadrado {
        doc /* Método: x, y, z estimados em cada permanência comparados com A, B, C, D; marcas no piso e vídeo
               superior/lateral como validação externa. Critério: erro horizontal <= tolHorizontal e vertical
               <= tolVertical em cada vértice e durante os deslocamentos; erro de fechamento do quadrado registrado. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p02; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "CSV da missão (x_m, y_m, z_m) + vídeo com marcas no piso";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_q1.md#T02";
    }

    verification def <T03> VerificarPermanencias {
        doc /* Método: no CSV, intervalos contínuos com dentro = true por vértice, em tempo real. Critério: quatro
               intervalos >= 60 s, na ordem A, B, C, D (ou A, D, C, B), sem segunda espera em A. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p03; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "CSV da missão (permanencia_s, vertice, evento) + vídeo com cronômetro";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_q1.md#T03";
    }

    verification def <T04> VerificarPousoSuave {
        doc /* Método: vz da telemetria no instante em que emVoo passa a false. Critério: |vz| <= vToqueMax e
               evento PousoConfirmado registrado antes de encerrar a missão. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p04; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "CSV da missão (vz_mps, evento PousoConfirmado) + vídeo";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_q1.md#T04";
    }

    verification def <T05> VerificarReinicioContagem {
        doc /* Método: teste unitário do CronometroPermanencia com sequência sintética de vereditos
               (dentro 40 s, fora 1 amostra, dentro 60 s) e relógio injetado. Critério: PermanenciaConcluida só após
               60 s contínuos depois da interrupção; interrupção registrada. Em voo, conferir reinícios no CSV. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p05; }
        attribute ambiente : String = "teste sem voo (unitário) + conferência no CSV do voo";
        attribute evidencia : String = "relatório do teste unitário + CSV da missão";
        attribute arquivoTeste : String = "app/src/test/missao/CronometroPermanenciaTest.kt";
    }

    verification def <T06> VerificarModeloEEvidencias {
        doc /* Método: inspeção. executar_modelo.py sem erros; matriz de rastreabilidade gerada sem pendências;
               CSV exportado com transições de todos os estados exigidos. Critério: nenhum item ausente. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p06; }
        attribute ambiente : String = "inspeção";
        attribute evidencia : String = "saída de executar_modelo.py e gerar_matriz.py + CSV da missão";
        attribute arquivoTeste : String = "modelo_sysml/gerar_matriz.py";
    }

    verification def <T07> VerificarTratamentoFalhas {
        doc /* Método: testes unitários do MonitorFalhas com telemetria injetada para cada TipoFalha; teste controlado
               com motores desligados para comando rejeitado e bateria baixa; em voo, apenas Interromper (pouso no
               local). Critério: reação igual à tabela do MonitorFalhas e evento registrado. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::r07; }
        attribute ambiente : String = "teste sem voo + teste controlado + voo real (interrupção)";
        attribute evidencia : String = "relatório dos testes unitários + CSV do ensaio de interrupção";
        attribute arquivoTeste : String = "app/src/test/missao/MonitorFalhasTest.kt";
    }

    verification def <T08> VerificarConversaoReferencial {
        doc /* Método: teste unitário do EstimadorEstado com velocidades norte/leste constantes e psi0 conhecido.
               Critério: x, y integrados coincidem com a solução analítica (erro < 1 mm em 10 s). */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::p02; }
        attribute ambiente : String = "teste sem voo (unitário)";
        attribute evidencia : String = "relatório do teste unitário";
        attribute arquivoTeste : String = "app/src/test/missao/EstimadorEstadoTest.kt";
    }

    verification def <T09> VerificarWatchdog {
        doc /* Método: teste do EmissorComandos com SDK simulado (mock); a lógica para de enviar comandos.
               Critério: velocidade zero enviada em até prazoWatchdog. */
        subject sistema : NivelN::SistemaVooAutonomoN;
        objective { verify Nivel0::r07; }
        attribute ambiente : String = "teste sem voo (mock do SDK)";
        attribute evidencia : String = "relatório do teste unitário";
        attribute arquivoTeste : String = "app/src/test/adapter/EmissorComandosTest.kt";
    }

    verification t01 : VerificarAlturaDecolagem;
    verification t02 : VerificarQuadrado;
    verification t03 : VerificarPermanencias;
    verification t04 : VerificarPousoSuave;
    verification t05 : VerificarReinicioContagem;
    verification t06 : VerificarModeloEEvidencias;
    verification t07 : VerificarTratamentoFalhas;
    verification t08 : VerificarConversaoReferencial;
    verification t09 : VerificarWatchdog;
}
