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

package VerificacaoQ2 {
    doc /* Casos de verificação da Tarefa 2 (Questão 2). Cenários exigidos na seção 7: único alvo (V03, V04),
           múltiplos alvos e cores não alvo (V03, V06), ausência de alvos (V07), iluminação/oclusão desfavorável (V02),
           alvo perto de obstáculo (V06), perda de detecção na permanência (V07) e perda de comunicação/tempo excedido
           (V07, mais T07/T09 da Q1, reutilizados). Ambientes identificados: "teste sem voo" (malha fechada sintética,
           pytest), "simulação" (Gazebo, relógio do simulador, avaliador com a verdade) e "voo real". */

    private import ScalarValues::*;

    verification def <V01> VerificarConfiguracaoT2 {
        doc /* Método: carregar config/tarefas.yaml e variações inválidas (cor-alvo fora das conhecidas, d_alvo >= d_max,
               volume vazio). Critério: configuração válida carrega; inválidas são rejeitadas com mensagem. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r01; }
        attribute ambiente : String = "teste sem voo (unitário)";
        attribute evidencia : String = "relatório do pytest";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_modulos.py";
    }

    verification def <V02> VerificarPercepcao {
        doc /* Método: avaliação do detector ONNX (mesmo código do voo) no conjunto de validação sintético com
               oclusão, cortes, desfoque, ruído e iluminação variados; depois nos quadros do Gazebo e do voo real.
               Critério: precisão e revocação >= 0,9 para diâmetro aparente >= 20 px; nenhuma troca de cor em alvo. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r02; }
        attribute ambiente : String = "teste sem voo (conjunto sintético) + simulação + voo real";
        attribute evidencia : String = "modelos/metricas_detector.json + resumo.yaml do Gazebo + bag do voo";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/ferramentas/treinar_yolo.py";
    }

    verification def <V03> VerificarAutonomiaT2 {
        doc /* Método: só "executar tarefa 2"; cenários com um alvo e com vários alvos e cores não alvo (sementes
               registradas). Critério: todos os alvos destruídos uma única vez, nenhum ALVO_SELECIONADO de cor não alvo,
               retorno e pouso no ponto de decolagem, sem falhas. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r03; }
        attribute ambiente : String = "teste sem voo (malha fechada sintética) + simulação + voo real";
        attribute evidencia : String = "pytest test_tarefa2 + resumo.yaml/CSV do Gazebo + bag do voo";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_tarefa2.py";
    }

    verification def <V04> VerificarDistanciaPermanencia {
        doc /* Método: durante a contagem, distância VERDADEIRA (avaliador/simulação; no voo real, câmera lateral fixa
               com escala, 30 quadros/s) comparada com 0 < d <= 5 cm; rajada e perda de visão para provar o reinício;
               balão em movimento (1 cm/s). Critério: d real na faixa em todas as amostras com contagem; 60 s contínuos
               por balão; reinício registrado após a interrupção. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r04; }
        attribute ambiente : String = "teste sem voo + simulação + voo real (validação por câmera lateral)";
        attribute evidencia : String = "pytest test_tarefa2 + avaliacao.csv do Gazebo + vídeo lateral e bag do voo";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_tarefa2.py";
    }

    verification def <V05> VerificarEstimacaoDistancia {
        doc /* Método: mesma missão com viés de velocidade (deriva da posição integrada) de 0,5 e 2 cm/s; a verdade só
               entra no avaliador. Critério: com 0,5 cm/s cumpre R04; com 2 cm/s pode não cumprir, mas nunca conta fora da
               faixa e termina pousada. Erro de estimação na aproximação registrado (d estimada x d real). */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r05; }
        attribute ambiente : String = "teste sem voo (malha fechada sintética) + simulação";
        attribute evidencia : String = "pytest test_tarefa2 (deriva) + avaliacao.csv";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_tarefa2.py";
    }

    verification def <V06> VerificarRestricoes {
        doc /* Método: folga mínima a balões não alvo e a paredes/móveis durante toda a missão (verdade do simulador);
               balão novo no caminho força replanejamento; alvo junto de obstáculo. Critério: folga > 0,15 m a não alvos,
               nenhuma colisão, nenhuma saída do volume. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r06; }
        attribute ambiente : String = "teste sem voo + simulação";
        attribute evidencia : String = "pytest test_tarefa2 + resumo.yaml (folga_min_nao_alvo_m, colisoes)";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_tarefa2.py";
    }

    verification def <V07> VerificarFalhasT2 {
        doc /* Método: ausência de alvos; perda de detecção de 3 s na permanência; interromper durante a aproximação;
               deriva extrema; perda da ponte e tempo excedido (reuso de T07/T09). Critério: varre e pousa sem alvos;
               contagem reinicia; pouso no local; nenhuma contagem fora da faixa. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r07; }
        attribute ambiente : String = "teste sem voo (malha fechada sintética)";
        attribute evidencia : String = "relatório do pytest";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/test/test_tarefa2.py";
    }

    verification def <V08> VerificarObservabilidade {
        doc /* Método: inspeção do painel (estado, alvo, distância estimada, cronômetro, eventos, falhas) e do CSV
               exportado (analisar_ensaio.py). Critério: todos os campos presentes; logs exportáveis. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r08; }
        attribute ambiente : String = "inspeção (simulação e voo real)";
        attribute evidencia : String = "CSV/metricas.md de cada ensaio";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_tarefas/ferramentas/analisar_ensaio.py";
    }

    verification def <V09> VerificarReprodutibilidade {
        doc /* Método: mesma semente gera a mesma sala; instalação em outra máquina pelo README (versões fixadas).
               Critério: salas idênticas; testes passam numa instalação limpa. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r09; }
        attribute ambiente : String = "teste sem voo";
        attribute evidencia : String = "pytest test_sala_t2 + README";
        attribute arquivoTeste : String = "ros2_ws/src/psi3442_gazebo/test/test_sala_t2.py";
    }

    verification def <V10> VerificarCanalVideoObstaculos {
        doc /* Método: testes JVM do app ponte (redução NV21, canal de vídeo, obstáculos, cena falsa) e do lado ROS 2
               (LeitorQuadros, LaserScan); no celular, modo "falso" com o ROS 2 pelo Wi-Fi; em solo com a aeronave,
               quadros e distâncias reais (anteparo a distância conhecida). Critério: quadros a ~5 Hz e distâncias
               coerentes com a medida de referência. */
        subject sistema : NivelN::SistemaMissoesN;
        objective { verify Nivel0::r02; }
        attribute ambiente : String = "teste sem voo (JVM e pytest) + teste em solo com a aeronave";
        attribute evidencia : String = "relatórios dos testes + log do app ponte";
        attribute arquivoTeste : String = "android_ponte/app/src/test/java/br/usp/psi3442/ponte/SensoresTest.kt";
    }

    verification v01 : VerificarConfiguracaoT2;
    verification v02 : VerificarPercepcao;
    verification v03 : VerificarAutonomiaT2;
    verification v04 : VerificarDistanciaPermanencia;
    verification v05 : VerificarEstimacaoDistancia;
    verification v06 : VerificarRestricoes;
    verification v07 : VerificarFalhasT2;
    verification v08 : VerificarObservabilidade;
    verification v09 : VerificarReprodutibilidade;
    verification v10 : VerificarCanalVideoObstaculos;
}
