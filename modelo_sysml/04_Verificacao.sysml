package VerificacaoQ1 {
    doc /* Casos de verificação da Tarefa 1 (Questão 1) (coluna "teste e evidência" da matriz de rastreabilidade).
           Ensaios que possam comprometer o equipamento são feitos sem voo ou em teste controlado (seção 7).
           Os critérios usam os valores de NivelN::configTarefa1 (P05), a aprovar na entrega intermediária. */

    private import ScalarValues::*;

    verification def <T01> VerificarAlturaDecolagem {
        doc /* Método: z (ToF) registrado após AlturaAtingida + medição externa com régua vertical de referência em A,
               filmada de lado. Critério: |z - 1,80 m| <= tolVertical, no registro e na medição externa. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p01; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "bag/CSV da tarefa (z_m, estado) + vídeo lateral com régua";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_tarefa1.md#T01";
    }

    verification def <T02> VerificarQuadrado {
        doc /* Método: x, y, z estimados em cada permanência comparados com A, B, C, D; marcas no piso e vídeo
               superior/lateral como validação externa. Critério: erro horizontal <= tolHorizontal e vertical
               <= tolVertical em cada vértice e durante os deslocamentos; erro de fechamento do quadrado registrado. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p02; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "bag/CSV da tarefa (x_m, y_m, z_m) + vídeo com marcas no piso";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_tarefa1.md#T02";
    }

    verification def <T03> VerificarPermanencias {
        doc /* Método: no CSV, intervalos contínuos com dentro = true por vértice, em tempo real. Critério: quatro
               intervalos >= 60 s, na ordem A, B, C, D (ou A, D, C, B), sem segunda espera em A. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p03; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "bag/CSV da tarefa (permanencia_s, vertice, evento) + vídeo com cronômetro";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_tarefa1.md#T03";
    }

    verification def <T04> VerificarPousoSuave {
        doc /* Método: vz da telemetria no instante em que emVoo passa a false. Critério: |vz| <= vToqueMax e
               evento PousoConfirmado registrado antes de encerrar a missão. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p04; }
        attribute ambiente : String = "voo real";
        attribute evidencia : String = "bag/CSV da tarefa (vz_mps, evento PousoConfirmado) + vídeo";
        attribute arquivoTeste : String = "ensaios/roteiro_voo_tarefa1.md#T04";
    }

    verification def <T05> VerificarReinicioContagem {
        doc /* Método: teste unitário do CronometroPermanencia com sequência sintética de vereditos
               (dentro 40 s, fora 1 amostra, dentro 60 s) e relógio injetado. Critério: PermanenciaConcluida só após
               60 s contínuos depois da interrupção; interrupção registrada. Em voo, conferir reinícios no CSV. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p05; }
        attribute ambiente : String = "teste sem voo (unitário) + conferência no CSV do voo";
        attribute evidencia : String = "relatório do teste unitário + bag/CSV da tarefa";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_cronometro_permanencia.py";
    }

    verification def <T06> VerificarModeloEEvidencias {
        doc /* Método: inspeção. executar_modelo.py sem erros; matriz de rastreabilidade gerada sem pendências;
               CSV exportado com transições de todos os estados exigidos. Critério: nenhum item ausente. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p06; }
        attribute ambiente : String = "inspeção";
        attribute evidencia : String = "saída de executar_modelo.py e gerar_matriz.py + bag/CSV da tarefa";
        attribute arquivoTeste : String = "modelo_sysml/gerar_matriz.py";
    }

    verification def <T07> VerificarTratamentoFalhas {
        doc /* Método: testes unitários do MonitorFalhas com telemetria injetada para cada TipoFalha; teste controlado
               com motores desligados para comando rejeitado, bateria baixa e perda da ponte (socket derrubado); em voo, apenas Interromper (pouso no
               local). Critério: reação igual à tabela do MonitorFalhas e evento registrado. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r07; }
        attribute ambiente : String = "teste sem voo + teste controlado + voo real (interrupção)";
        attribute evidencia : String = "relatório dos testes unitários + CSV do ensaio de interrupção";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_monitor_falhas.py";
    }

    verification def <T08> VerificarConversaoReferencial {
        doc /* Método: teste unitário do EstimadorEstado com velocidades norte/leste constantes e psi0 conhecido.
               Critério: x, y integrados coincidem com a solução analítica (erro < 1 mm em 10 s). */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::p02; }
        attribute ambiente : String = "teste sem voo (unitário)";
        attribute evidencia : String = "relatório do teste unitário";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_estimacao_estado.py";
    }

    verification def <T09> VerificarWatchdog {
        doc /* Método: teste do EmissorComandos do app ponte com SDK simulado (mock); o nó ponte para de enviar
               comandos e depois o heartbeat. Critério: velocidade zero em até prazoWatchdog e pouso automático em até
               prazoPerdaPonte. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r07; }
        attribute ambiente : String = "teste sem voo (mock do SDK)";
        attribute evidencia : String = "relatório do teste unitário";
        attribute arquivoTeste : String = "android_ponte/app/src/test/java/br/usp/psi3442/ponte/EmissorComandosTest.kt";
    }

    verification def <T10> VerificarComandoDeTarefa {
        doc /* Método: com o simulador ou com a ponte em modo de teste, enviar só "executar tarefa 1" e nenhum outro
               comando. Critério: a tarefa percorre todos os estados até concluida sem nova entrada do operador; e
               "executar tarefa 2" é recusado enquanto a Tarefa 1 não tiver sido concluída em voo real. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r03; }
        attribute ambiente : String = "teste sem voo (simulador ou ponte de teste) + voo real";
        attribute evidencia : String = "bag da tarefa com /operador/comando e /tarefa/evento";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_gerenciador_tarefas.py";
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
    verification t10 : VerificarComandoDeTarefa;
}
