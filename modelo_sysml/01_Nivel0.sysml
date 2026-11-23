package Nivel0 {
    doc /* Nível 0 — sistema de interesse, atores externos, cenário de operação, fronteiras, entradas, saídas e
           fluxos de informação e energia. Corresponde ao diagrama diagramas/nivel_0.png.

           Diferenças em relação ao modelo da primeira prova (outro drone), justificadas pelo Mini 4 Pro e pela sala:
           - GPS mantido apenas como entrada indisponível: em ambiente interno não há GNSS confiável (R07);
             a posição vem do posicionamento visual (câmeras inferiores) e do sensor ToF.
           - Entrada "textura do piso / iluminação" acrescentada: condição de funcionamento do posicionamento visual.
           - Botão Reset removido: não existe no Mini 4 Pro.
           - Cartão de memória passa a ser bidirecional (armazenamento) e ligado à computação embarcada.
           - Estação de solo decomposta em controle remoto e celular Android com a aplicação de missão: o Mobile SDK
             roda no celular; nenhum código da missão é instalado no controlador de voo.
           - Entradas/saídas acrescentadas: arquivo de configuração, logs exportáveis, comandos do operador limitados
             a iniciar/interromper, energia da estação de solo. */

    private import Comum::*;
    private import Comum::RequisitosQ1::*;

    // ------------------------------------------------------------------ elementos externos
    part def Operador {
        doc /* Ator externo: inicia e interrompe a missão; não pilota continuamente. */
        port comando : ~PortaOperador;
        port painel : ~PortaPainel;
        port acaoManual : ~PortaAcaoManual;
        port leds : ~PortaSinalVisual;
    }

    part def AmbienteFisico {
        doc /* Sala de aula: piso (textura), paredes, teto, mobiliário, iluminação e ar. */
        port distancia : ~PortaSensorial;
        port pressao : ~PortaSensorial;
        port texturaIluminacao : ~PortaSensorial;
        port imagem : ~PortaSensorial;
        port empuxo : ~PortaEmpuxo;
    }

    part def FonteEnergia {
        doc /* Baterias carregadas: aeronave, controle remoto e celular. */
        port aeronave : ~PortaEnergia;
        port estacao : ~PortaEnergia;
    }

    part def ArquivoConfiguracao {
        doc /* Arquivo JSON com vértices, tolerâncias e tempos da missão (R01, P05). */
        port saida : ~PortaConfiguracao;
    }

    part def RepositorioLogs {
        doc /* Destino dos logs exportáveis (CSV) usados como evidência (P06). */
        port entrada : ~PortaLogs;
    }

    part def SatelitesGNSS {
        doc /* Indisponíveis em ambiente interno: representados apenas para registrar que não são usados (R07). */
        port sinal : ~PortaSensorial;
    }

    part def Simulador {
        doc /* Opcional — ambiente de teste. Substitui controle remoto + aeronave e oferece à aplicação a mesma
               interface do adaptador DJI. Resultados identificados separadamente dos de voo real, com a escala de
               tempo usada (P06). Uso ainda a decidir pela equipe. */
        port interfaceAdaptador : PortaUSB;
    }

    // ------------------------------------------------------------------ sistema de interesse
    part def Drone {
        doc /* DJI Mini 4 Pro — produto comercial tratado como caixa-preta. */
        port bateria : PortaEnergia;
        port botaoOnOff : PortaAcaoManual;
        port distancia : PortaSensorial;
        port pressao : PortaSensorial;
        port texturaIluminacao : PortaSensorial;
        port imagem : PortaSensorial;
        port gps : PortaSensorial { doc /* Indisponível indoor. */ }
        port conexaoUSB : PortaUSB;
        port cartaoMemoria : PortaArmazenamento;
        port empuxo : PortaEmpuxo;
        port ledReady : PortaSinalVisual;
        port rf : PortaRF;
    }

    part def ControleRemoto {
        doc /* Controle remoto compatível com o Mobile SDK (RC-N2 — verificar). */
        port rf : PortaRF;
        port usb : PortaUSB;
        port bateria : PortaEnergia;
    }

    part def AplicacaoMissao {
        doc /* Software da missão (Kotlin, DJI Mobile SDK v5). Comum às Questões 1 e 2: comando, supervisão e registro. */
        port sdk : PortaUSB;
        port config : PortaConfiguracao;
        port logs : PortaLogs;
        port display : PortaPainel;
        port comandosOperador : PortaOperador;
    }

    part def CelularAndroid {
        doc /* Hardware que executa a aplicação de missão. */
        port usb : PortaUSB;
        port config : PortaConfiguracao;
        port logs : PortaLogs;
        port display : PortaPainel;
        port comandosOperador : PortaOperador;
        port bateria : PortaEnergia;

        part app : AplicacaoMissao;

        connect usb to app.sdk;
        connect config to app.config;
        connect app.logs to logs;
        connect app.display to display;
        connect comandosOperador to app.comandosOperador;
    }

    part def EstacaoSolo {
        port rf : PortaRF;
        port bateria : PortaEnergia;
        port config : PortaConfiguracao;
        port logs : PortaLogs;
        port display : PortaPainel;
        port comandosOperador : PortaOperador;

        part controleRemoto : ControleRemoto;
        part celular : CelularAndroid;

        connect controleRemoto.usb to celular.usb;
        connect rf to controleRemoto.rf;
        connect bateria to controleRemoto.bateria;
        connect bateria to celular.bateria;
        connect config to celular.config;
        connect celular.logs to logs;
        connect celular.display to display;
        connect comandosOperador to celular.comandosOperador;
    }

    part def SistemaVooAutonomo {
        doc /* Função global: executar autonomamente decolagem, quadrado de 1,50 m a 1,80 m, permanências de 60 s
               nos quatro vértices, retorno e pouso suave, respeitando as tolerâncias declaradas e registrando evidências. */
        part drone : Drone;
        part estacao : EstacaoSolo;
        flow of PacoteDados from estacao.rf.pacote to drone.rf.pacote;
        flow of PacoteDados from drone.rf.pacote to estacao.rf.pacote;
    }

    part def ContextoOperacional {
        part operador : Operador;
        part ambiente : AmbienteFisico;
        part energia : FonteEnergia;
        part arquivoConfig : ArquivoConfiguracao;
        part repositorioLogs : RepositorioLogs;
        part gnss : SatelitesGNSS;
        part sistema : SistemaVooAutonomo;

        // informação
        flow of ComandoOperador from operador.comando.comando to sistema.estacao.comandosOperador.comando;
        flow of DadosPainel from sistema.estacao.display.dados to operador.painel.dados;
        flow of ConfiguracaoMissao from arquivoConfig.saida.config to sistema.estacao.config.config;
        flow of RegistroLog from sistema.estacao.logs.registro to repositorioLogs.entrada.registro;
        flow of SinalVisual from sistema.drone.ledReady.sinal to operador.leds.sinal;
        flow of AcaoManual from operador.acaoManual.acao to sistema.drone.botaoOnOff.acao;

        // grandezas físicas sensoriadas
        flow of Distancia from ambiente.distancia.grandeza to sistema.drone.distancia.grandeza;
        flow of Pressao from ambiente.pressao.grandeza to sistema.drone.pressao.grandeza;
        flow of TexturaIluminacao from ambiente.texturaIluminacao.grandeza to sistema.drone.texturaIluminacao.grandeza;
        flow of Imagem from ambiente.imagem.grandeza to sistema.drone.imagem.grandeza;
        flow of SinalGNSS from gnss.sinal.grandeza to sistema.drone.gps.grandeza;

        // energia e força
        flow of Energia from energia.aeronave.energia to sistema.drone.bateria.energia;
        flow of Energia from energia.estacao.energia to sistema.estacao.bateria.energia;
        flow of Empuxo from sistema.drone.empuxo.empuxo to ambiente.empuxo.empuxo;
    }

    part contexto : ContextoOperacional;

    // ------------------------------------------------------------------ cenário de operação
    use case def CenarioOperacaoQ1 {
        doc /* Cenário de operação do voo de familiarização na sala de aula. */
        subject sistema : SistemaVooAutonomo;
        actor operador : Operador;
        objective { doc /* Demonstrar P01 a P06 em voo real, com o operador apenas iniciando ou interrompendo. */ }

        action prepararAmbiente {
            doc /* Marcar A, B, C e D no piso; garantir piso texturizado e iluminação; volume livre em torno do
                   quadrado com margem de segurança (hipótese: 2,5 m x 2,5 m x 2,5 m). */
        }
        action posicionarAeronave { doc /* Aeronave sobre a marca de A, nariz apontado para B (define psi0). */ }
        action ligarEquipamentos { doc /* Ligar aeronave, controle remoto e celular; conectar USB; abrir a aplicação. */ }
        action carregarConfiguracao { doc /* Selecionar o JSON aprovado; o painel exibe tolerâncias e sentido. */ }
        action iniciarMissao { doc /* Operador pressiona Iniciar; a partir daqui não pilota. */ }
        action executarMissao {
            doc /* Decolagem, quadrado com quatro permanências de 60 s, retorno e pouso. O operador pode Interromper
                   a qualquer momento (pouso no local). */
        }
        action exportarEvidencias { doc /* Exportar o CSV da missão e o vídeo da demonstração. */ }

        first start then prepararAmbiente;
        first prepararAmbiente then posicionarAeronave;
        first posicionarAeronave then ligarEquipamentos;
        first ligarEquipamentos then carregarConfiguracao;
        first carregarConfiguracao then iniciarMissao;
        first iniciarMissao then executarMissao;
        first executarMissao then exportarEvidencias;
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

    satisfy p01 by contexto.sistema;
    satisfy p02 by contexto.sistema;
    satisfy p03 by contexto.sistema;
    satisfy p04 by contexto.sistema;
    satisfy p05 by contexto.sistema;
    satisfy p06 by contexto.sistema;
    satisfy r07 by contexto.sistema;
}
