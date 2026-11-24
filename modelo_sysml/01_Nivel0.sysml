package Nivel0 {
    doc /* Nível 0 — Sistema de Missões Autônomas: sistema de interesse, atores externos, cenário de operação,
           fronteiras, entradas, saídas e fluxos de informação e energia. Corresponde a diagramas/nivel_0.png.

           Paradigma: o drone é um produto dado; o trabalho é de software. A lógica das tarefas roda em nós ROS 2 num
           notebook Linux; um Android emulado no mesmo notebook executa o app ponte com o DJI Mobile SDK v5; o rádio
           DJI (RC-N2) é apenas o enlace exigido pelo SDK (seção 6 do enunciado), sem pilotagem; o drone é um
           componente caixa-preta. O operador só comanda "executar tarefa 1", "executar tarefa 2" ou "interromper".

           Diferenças em relação aos modelos anteriores (P1 e primeira versão desta prova, com celular):
           - estação de solo substituída por notebook Linux + ROS 2; celular substituído por Android emulado;
           - controle remoto rebaixado a rádio-enlace; nenhuma entrada de pilotagem;
           - drone deixa de ser decomposto em blocos internos: é tratado só pelas entradas e saídas;
           - GPS mantido só como entrada indisponível (R07); textura do piso e iluminação como entrada do ambiente;
           - botão Reset removido (não existe no Mini 4 Pro); USB e cartão de memória da aeronave não participam
             das tarefas e saíram da fronteira. */

    private import Comum::*;
    private import Comum::RequisitosQ1::*;
    private import Comum::RequisitosQ2::*;

    // ------------------------------------------------------------------ elementos externos
    part def Operador {
        doc /* Ator externo: comanda tarefas; não pilota. */
        port comando : ~PortaOperador;
        port painel : ~PortaPainel;
        port acaoManual : ~PortaAcaoManual;
        port leds : ~PortaSinalVisual;
    }

    part def AmbienteFisico {
        doc /* Sala de aula: piso (textura), paredes, teto, mobiliário, iluminação, ar e balões estáticos (Tarefa 2). */
        port distancia : ~PortaSensorial;
        port pressao : ~PortaSensorial;
        port texturaIluminacao : ~PortaSensorial;
        port imagem : ~PortaSensorial;
        port empuxo : ~PortaEmpuxo;
    }

    part def FonteEnergia {
        doc /* Alimentação do notebook e baterias carregadas do rádio e da aeronave. */
        port notebook : ~PortaEnergia;
        port radio : ~PortaEnergia;
        port aeronave : ~PortaEnergia;
    }

    part def ArquivoConfiguracao {
        doc /* YAML com os parâmetros das tarefas (P05, R01). */
        port saida : ~PortaConfiguracao;
    }

    part def RepositorioLogs {
        doc /* Destino dos logs exportáveis (rosbag2 e CSV) usados como evidência (P06, R08). */
        port entrada : ~PortaLogs;
    }

    part def SatelitesGNSS {
        doc /* Indisponíveis em ambiente interno: representados para registrar que não são usados (R07). */
        port sinal : ~PortaSensorial;
    }

    part def Simulador {
        doc /* Opcional — ambiente de teste. Substitui ponte, rádio e drone publicando e assinando os mesmos tópicos
               /dji/* do nó ponte; a lógica das tarefas roda sem alteração. Resultados identificados separadamente,
               com a escala de tempo usada (P06). Uso a decidir pela equipe. */
        port socket : PortaSocket;
    }

    // ------------------------------------------------------------------ componentes do sistema
    part def AplicacaoROS2 {
        doc /* Nós ROS 2 com toda a lógica das tarefas (decomposta no nível 1). */
        port comandosOperador : PortaOperador;
        port painel : PortaPainel;
        port config : PortaConfiguracao;
        port logs : PortaLogs;
        port socketPonte : PortaSocket;
    }

    part def AndroidEmulado {
        doc /* Android emulado no notebook, executando o app ponte com o DJI Mobile SDK v5.
               Riscos a testar cedo: tradução de bibliotecas ARM do SDK, repasse USB do rádio ao emulador,
               ativação da chave do SDK pela internet. */
        port socketPonte : PortaSocket;
        port usb : PortaUSB;
    }

    part def NotebookLinux {
        port comandosOperador : PortaOperador;
        port painel : PortaPainel;
        port config : PortaConfiguracao;
        port logs : PortaLogs;
        port usb : PortaUSB;
        port energia : PortaEnergia;

        part ros2 : AplicacaoROS2;
        part android : AndroidEmulado;

        connect ros2.socketPonte to android.socketPonte;
        connect android.usb to usb;
        connect comandosOperador to ros2.comandosOperador;
        connect ros2.painel to painel;
        connect config to ros2.config;
        connect ros2.logs to logs;
    }

    part def RadioDJI {
        doc /* Controle remoto compatível com o Mobile SDK v5 para o Mini 4 Pro: DJI RC N2 ou RC N3 (SDK >= 5.13.0;
               DJI RC 2 não suportado). Indispensável: não há conexão direta celular-aeronave documentada para este
               modelo. Usado só como rádio-enlace: nenhum comando de pilotagem sai dele. */
        port usb : PortaUSB;
        port rf : PortaRF;
        port bateria : PortaEnergia;
    }

    part def Drone {
        doc /* DJI Mini 4 Pro — produto comercial tratado como caixa-preta: estabilização, sensores, atuadores e
               energia ficam no firmware DJI. */
        port bateria : PortaEnergia;
        port botaoOnOff : PortaAcaoManual;
        port distancia : PortaSensorial;
        port pressao : PortaSensorial;
        port texturaIluminacao : PortaSensorial;
        port imagem : PortaSensorial;
        port gps : PortaSensorial { doc /* Indisponível indoor. */ }
        port empuxo : PortaEmpuxo;
        port ledReady : PortaSinalVisual;
        port rf : PortaRF;
    }

    part def SistemaMissoesAutonomas {
        doc /* Função global: ao receber "executar tarefa N", realizar a tarefa N de forma autônoma até o pouso
               (Tarefa 1: quadrado de 1,50 m a 1,80 m com quatro permanências de 60 s; Tarefa 2: balões), respeitando
               tolerâncias e restrições e registrando evidências; interromper com segurança quando comandado. */
        part notebook : NotebookLinux;
        part radio : RadioDJI;
        part drone : Drone;
        flow of PacoteDados from notebook.usb.pacote to radio.usb.pacote;
        flow of PacoteDados from radio.usb.pacote to notebook.usb.pacote;
        flow of PacoteDados from radio.rf.pacote to drone.rf.pacote;
        flow of PacoteDados from drone.rf.pacote to radio.rf.pacote;
    }

    part def ContextoOperacional {
        part operador : Operador;
        part ambiente : AmbienteFisico;
        part energia : FonteEnergia;
        part arquivoConfig : ArquivoConfiguracao;
        part repositorioLogs : RepositorioLogs;
        part gnss : SatelitesGNSS;
        part sistema : SistemaMissoesAutonomas;

        // informação
        flow of ComandoOperador from operador.comando.comando to sistema.notebook.comandosOperador.comando;
        flow of StatusTarefa from sistema.notebook.painel.status to operador.painel.status;
        flow of ConfiguracaoTarefas from arquivoConfig.saida.config to sistema.notebook.config.config;
        flow of RegistroLog from sistema.notebook.logs.registro to repositorioLogs.entrada.registro;
        flow of SinalVisual from sistema.drone.ledReady.sinal to operador.leds.sinal;
        flow of AcaoManual from operador.acaoManual.acao to sistema.drone.botaoOnOff.acao;

        // grandezas físicas sensoriadas
        flow of Distancia from ambiente.distancia.grandeza to sistema.drone.distancia.grandeza;
        flow of Pressao from ambiente.pressao.grandeza to sistema.drone.pressao.grandeza;
        flow of TexturaIluminacao from ambiente.texturaIluminacao.grandeza to sistema.drone.texturaIluminacao.grandeza;
        flow of Imagem from ambiente.imagem.grandeza to sistema.drone.imagem.grandeza;
        flow of SinalGNSS from gnss.sinal.grandeza to sistema.drone.gps.grandeza;

        // energia e força
        flow of Energia from energia.notebook.energia to sistema.notebook.energia.energia;
        flow of Energia from energia.radio.energia to sistema.radio.bateria.energia;
        flow of Energia from energia.aeronave.energia to sistema.drone.bateria.energia;
        flow of Empuxo from sistema.drone.empuxo.empuxo to ambiente.empuxo.empuxo;
    }

    part contexto : ContextoOperacional;

    // ------------------------------------------------------------------ cenário de operação
    use case def CenarioOperacao {
        doc /* Cenário de operação de uma tarefa na sala de aula. */
        subject sistema : SistemaMissoesAutonomas;
        actor operador : Operador;
        objective { doc /* Executar a tarefa pedida de forma autônoma, com o operador apenas comandando a tarefa. */ }

        action prepararAmbiente {
            doc /* Tarefa 1: marcar A, B, C e D no piso; Tarefa 2: posicionar os balões. Piso texturizado, iluminação
                   e volume livre com margem de segurança (hipótese: 2,5 m x 2,5 m x 2,5 m para a Tarefa 1). */
        }
        action posicionarAeronave { doc /* Aeronave sobre A, nariz apontado para B (define psi0). */ }
        action ligarEquipamentos {
            doc /* Ligar aeronave e rádio; no notebook, iniciar o Android emulado com o app ponte (rádio repassado por
                   USB) e lançar os nós ROS 2. */
        }
        action carregarConfiguracao { doc /* Gerenciador carrega o YAML aprovado; o painel exibe os parâmetros. */ }
        action comandarTarefa { doc /* Operador envia "executar tarefa 1" (ou 2). A partir daqui nada é pilotado. */ }
        action executarTarefa {
            doc /* Execução autônoma até o pouso. O operador pode enviar "interromper" (pouso no local). */
        }
        action exportarEvidencias { doc /* Exportar o rosbag2/CSV da tarefa e o vídeo da demonstração. */ }

        first start then prepararAmbiente;
        first prepararAmbiente then posicionarAeronave;
        first posicionarAeronave then ligarEquipamentos;
        first ligarEquipamentos then carregarConfiguracao;
        first carregarConfiguracao then comandarTarefa;
        first comandarTarefa then executarTarefa;
        first executarTarefa then exportarEvidencias;
        first exportarEvidencias then done;
    }

    // ------------------------------------------------------------------ requisitos alocados ao sistema
    requirement p01 : Decolagem;
    requirement p02 : QuadradoHorizontal;
    requirement p03 : PermanenciaNosVertices;
    requirement p04 : PousoSuave;
    requirement p05 : ToleranciasDeclaradas;
    requirement p06 : EvidenciaEModelo;
    requirement r07 : FalhasEmAmbienteInterno;
    requirement r01 : Configuracao;
    requirement r02 : Percepcao;
    requirement r03 : Autonomia;
    requirement r04 : DistanciaEPermanencia;
    requirement r05 : Estimacao;
    requirement r06 : Restricoes;
    requirement r08 : Observabilidade;
    requirement r09 : Reprodutibilidade;

    satisfy p01 by contexto.sistema;
    satisfy p02 by contexto.sistema;
    satisfy p03 by contexto.sistema;
    satisfy p04 by contexto.sistema;
    satisfy p05 by contexto.sistema;
    satisfy p06 by contexto.sistema;
    satisfy r07 by contexto.sistema;
    satisfy r01 by contexto.sistema;
    satisfy r02 by contexto.sistema;
    satisfy r03 by contexto.sistema;
    satisfy r04 by contexto.sistema;
    satisfy r05 by contexto.sistema;
    satisfy r06 by contexto.sistema;
    satisfy r08 by contexto.sistema;
    satisfy r09 by contexto.sistema;
}
