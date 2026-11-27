package Comum {
    doc /* Tipos, tópicos ROS 2, sinais, portas e requisitos compartilhados pelos níveis 0, 1 e n.
           PSI3442 — P2 2026 — Sistema de Missões Autônomas com DJI Mini 4 Pro:
           Tarefa 1 = voo de familiarização (Questão 1); Tarefa 2 = balões (Questão 2). */

    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;

    // ------------------------------------------------------------------ grandezas físicas e energia
    item def Energia { doc /* Energia elétrica fornecida por bateria ou fonte. */ }
    item def Empuxo { doc /* Força e torque aplicados ao ar pelas hélices. */ }
    item def SinalVisual { doc /* Indicação luminosa (LEDs de status). */ }
    item def AcaoManual { doc /* Ação física do operador: ligar/desligar, trocar bateria, posicionar a aeronave. */ }
    item def GrandezaFisica { doc /* Grandeza do ambiente percebida por um sensor. */ }
    item def Distancia :> GrandezaFisica;
    item def Pressao :> GrandezaFisica;
    item def TexturaIluminacao :> GrandezaFisica { doc /* Textura do piso e iluminação: condição para o posicionamento visual. */ }
    item def Imagem :> GrandezaFisica;
    item def SinalGNSS :> GrandezaFisica { doc /* Indisponível em ambiente interno (R07): não utilizado. */ }

    // ------------------------------------------------------------------ referencial e dados
    attribute def ReferencialLocal {
        doc /* Referencial local da Tarefa 1 (P02), dextrogiro:
               origem = ponto de decolagem no piso (A projetado no piso);
               x = horizontal de A para B (direção do nariz da aeronave na decolagem, guinada psi0);
               y = horizontal de A para D (à esquerda do nariz);
               z = vertical para cima, medida do piso ao ponto de referência da aeronave (P01).
               Conversão a partir da telemetria (norte, leste, baixo):
               x =  N cos(psi0) + E sin(psi0);  y = N sin(psi0) - E cos(psi0);  vz = -vBaixo. */
        attribute guinadaDecolagem : Real;
    }

    attribute def Ponto3D {
        doc /* Coordenadas no ReferencialLocal. */
        attribute x : LengthValue;
        attribute y : LengthValue;
        attribute z : LengthValue;
    }

    enum def SentidoPercurso {
        doc /* Com x para B, y para D e z para cima, A-B-C-D é anti-horário visto de cima. */
        enum abcd;   // A -> B -> C -> D -> A
        enum adcb;   // A -> D -> C -> B -> A
    }

    enum def AcaoOperador {
        doc /* Únicos comandos do operador: não há pilotagem (R03). */
        enum executarTarefa1;
        enum executarTarefa2;
        enum interromper;
    }

    enum def TipoComando {
        enum decolar;
        enum pousar;
        enum habilitarControleVirtual;
        enum desabilitarControleVirtual;
        enum pararEPairar;
    }

    enum def TipoFalha {
        enum perdaEnlace;
        enum perdaPonte;
        enum telemetriaAtrasada;
        enum bateriaBaixa;
        enum estimativaInvalida;
        enum posicionamentoVisualInativo;
        enum desvioExcessivo;
        enum tempoTarefaExcedido;
        enum comandoRejeitado;
    }

    item def Telemetria {
        doc /* Amostra publicada pelo drone (caixa-preta), lida pelo app ponte via DJI Mobile SDK e republicada em
               /dji/telemetria. Velocidades no referencial do solo (norte, leste, baixo); altura relativa à decolagem. */
        attribute instante : DurationValue;
        attribute vNorte : SpeedValue;
        attribute vLeste : SpeedValue;
        attribute vBaixo : SpeedValue;
        attribute altitude : LengthValue;
        attribute alturaToF : LengthValue;
        attribute guinada : Real;
        attribute emVoo : Boolean;
        attribute motoresLigados : Boolean;
        attribute modoVoo : String;
        attribute bateriaPercentual : Real;
        attribute conectado : Boolean;
        attribute posicionamentoVisualAtivo : Boolean;
        attribute controleVirtualAtivo : Boolean;   // confirma a preparação por leitura
        attribute acaoPerdaSinal : String;          // idem: deve ser "pousar"
    }

    item def EstadoEstimado {
        doc /* Estado da aeronave no ReferencialLocal (tópico /estado). */
        attribute posicao : Ponto3D;
        attribute vx : SpeedValue;
        attribute vy : SpeedValue;
        attribute vz : SpeedValue;
        attribute valido : Boolean;
        attribute psi0 : Real;                      // guinada registrada na borda de subida de motoresLigados
        attribute motivoInvalido : String;
    }

    attribute def VereditoTolerancia {
        attribute dentroHorizontal : Boolean;
        attribute dentroVertical : Boolean;
        attribute dentroVelocidade : Boolean;
        attribute dentro : Boolean;
    }

    item def Setpoint {
        attribute ponto : Ponto3D;
        attribute ativo : Boolean;    // falso durante a decolagem e o pouso automáticos
    }

    item def ComandoVelocidade {
        doc /* Velocidade comandada (tópico /dji/cmd_vel) no ReferencialLocal; o app ponte converte para o solo. */
        attribute vx : SpeedValue;
        attribute vy : SpeedValue;
        attribute vz : SpeedValue;
        attribute taxaGuinada : Real;
        attribute psi0 : Real;        // para o app ponte converter ao referencial do solo
    }

    item def ComandoDiscreto { attribute tipo : TipoComando; }
    item def ComandoOperador { attribute acao : AcaoOperador; }
    item def TarefaAtiva { attribute numero : Integer; }
    item def StatusTarefa { doc /* Estado da tarefa, vértice/alvo atual, cronômetro, falhas, telemetria resumida:
                                   alimenta o painel e o CSV. */ }
    item def EventoTarefa {
        doc /* Início, permanência concluída, conclusão ou aborto de tarefa; também SOLICITA_ACAO: a tarefa pede
               decolar/pousar ao gerenciador, único que publica em /dji/acao. */
    }
    item def Falha { attribute tipo : TipoFalha; }
    item def Alvos { doc /* Questão 2: balões detectados, cor, posição na imagem e distância estimada. */ }
    item def Obstaculos {
        doc /* Distâncias aos obstáculos por setor em torno da aeronave, lidas pelo app ponte (PerceptionManager do SDK —
               verificar disponibilidade no Mini 4 Pro) e republicadas em /dji/obstaculos. */
        attribute distancias : LengthValue[*];
    }
    item def MapaLocal {
        doc /* Mapa grosseiro no ReferencialLocal (tópico /mapa): grade 2D de ocupação de baixa resolução e lista de
               balões com cor, posição estimada e incerteza. Serve para localizar os balões no espaço relativo à
               decolagem, não para navegação precisa. */
        attribute resolucao : LengthValue;
    }
    item def QuadroCamera :> Imagem { doc /* Quadro de vídeo da câmera principal (tópico /dji/camera). */ }
    item def RegistroLog { doc /* Registro: bag do rosbag2 e CSV exportado. */ }
    item def PacoteDados { doc /* Mensagem serializada trafegando por TCP, USB ou RF. */ }

    item def ConfiguracaoTarefa1 {
        doc /* Parâmetros da Tarefa 1 no arquivo de configuração (YAML). */
        attribute vertices : Ponto3D[4];
        attribute sentido : SentidoPercurso;
        attribute alturaAlvo : LengthValue;
        attribute aresta : LengthValue;
        attribute tempoPermanencia : DurationValue;
        attribute tolHorizontal : LengthValue;
        attribute tolVertical : LengthValue;
        attribute vPairadoMax : SpeedValue;
        attribute vToqueMax : SpeedValue;
        attribute vDeslocamentoMax : SpeedValue;
        attribute bateriaMinimaPercentual : Real;      // condição para iniciar
        attribute bateriaCriticaPercentual : Real;     // em voo: abaixo disto, término seguro
        attribute tempoMaxTarefa : DurationValue;
        attribute tempoEstabilizacao : DurationValue;
        attribute alturaMinDecolagem : LengthValue;    // DecolagemConcluida exige z acima disto
        attribute tempoMaxPreparacao : DurationValue;
        attribute tempoMaxDecolagem : DurationValue;
        attribute persistenciaFalha : DurationValue;   // telemetria atrasada ou estimativa inválida
    }

    item def ConfiguracaoTarefa2 {
        doc /* Parâmetros da Tarefa 2 (R01) — a detalhar. */
        attribute coresAlvo : String[*];
        attribute distanciaMaxima : LengthValue;
        attribute tempoPermanencia : DurationValue;
        attribute margemObstaculos : LengthValue;
    }

    item def ConfiguracaoTarefas {
        item tarefa1 : ConfiguracaoTarefa1;
        item tarefa2 : ConfiguracaoTarefa2;
    }

    // ------------------------------------------------------------------ sinais das máquinas de estados
    attribute def ExecutarTarefa1 { doc /* Operador envia "executar tarefa 1". */ }
    attribute def ExecutarTarefa2 { doc /* Operador envia "executar tarefa 2". */ }
    attribute def InterromperTarefa { doc /* Operador envia "interromper". */ }
    attribute def TarefaConcluida { doc /* Tarefa terminou e a aeronave está pousada. */ }
    attribute def PreparacaoConcluida {
        doc /* Ponte conectada, aeronave conectada, bateria >= mínimo, posicionamento visual ativo, ação de perda de
               sinal = pousar confirmada por leitura, controle virtual habilitado e guinada psi0 registrada. */
    }
    attribute def DecolagemConcluida { doc /* emVoo = true e |vz| <= vPairadoMax após o comando de decolagem automática. */ }
    attribute def AlturaAtingida { doc /* |z - alturaAlvo| <= tolVertical e |v| <= vPairadoMax. */ }
    attribute def VerticeAtingido { doc /* Veredito "dentro" no setpoint atual (erro horizontal, vertical e velocidade). */ }
    attribute def ToleranciaExcedida { doc /* Veredito passa de "dentro" para "fora" durante a permanência: zera o cronômetro (P05). */ }
    attribute def PermanenciaConcluida { doc /* Cronômetro atinge tempoPermanencia contínuo em tempo real. */ }
    attribute def Estabilizado { doc /* Veredito "dentro" em A (retorno) mantido por tempoEstabilizacao. */ }
    attribute def PousoConfirmado { doc /* Telemetria: emVoo = false e motoresLigados = false. */ }
    attribute def FalhaDetectada {
        doc /* Publicada em /falhas pela supervisão, ou pela ponte (comando rejeitado pelo SDK, perda da ponte). */
        attribute tipo : TipoFalha;
    }

    // ------------------------------------------------------------------ portas físicas e de comunicação
    port def PortaEnergia { in item energia : Energia; }
    port def PortaAcaoManual { in item acao : AcaoManual; }
    port def PortaSensorial { in item grandeza : GrandezaFisica; }
    port def PortaEmpuxo { out item empuxo : Empuxo; }
    port def PortaSinalVisual { out item sinal : SinalVisual; }
    port def PortaRF { inout item pacote : PacoteDados; }
    port def PortaUSB { inout item pacote : PacoteDados; }
    port def PortaSocket { doc /* TCP pelo Wi-Fi entre o notebook e o celular (nos testes sem drone: adb forward para o Android emulado). */ inout item pacote : PacoteDados; }
    port def PortaConfiguracao { in item config : ConfiguracaoTarefas; }
    port def PortaLogs { out item registro : RegistroLog; }
    port def PortaPainel { out item status : StatusTarefa; }
    port def PortaOperador { in item comando : ComandoOperador; }

    // ------------------------------------------------------------------ tópicos ROS 2 (quem publica usa a porta; quem assina, a conjugada)
    port def TopicoComandoOperador { attribute nome : String = "/operador/comando"; out item msg : ComandoOperador; }
    port def TopicoTarefaAtiva { attribute nome : String = "/tarefa/ativa"; out item msg : TarefaAtiva; }
    port def TopicoTarefaStatus { attribute nome : String = "/tarefa/status"; out item msg : StatusTarefa; }
    port def TopicoTarefaEvento { attribute nome : String = "/tarefa/evento"; out item msg : EventoTarefa; }
    port def TopicoAcaoDJI { attribute nome : String = "/dji/acao"; out item msg : ComandoDiscreto; }
    port def TopicoSetpoint { attribute nome : String = "/setpoint"; out item msg : Setpoint; }
    port def TopicoEstado { attribute nome : String = "/estado"; out item msg : EstadoEstimado; }
    port def TopicoAlvos { attribute nome : String = "/alvos"; out item msg : Alvos; }
    port def TopicoObstaculos { attribute nome : String = "/dji/obstaculos"; out item msg : Obstaculos; }
    port def TopicoMapa { attribute nome : String = "/mapa"; out item msg : MapaLocal; }
    port def TopicoCmdVel { attribute nome : String = "/dji/cmd_vel"; out item msg : ComandoVelocidade; }
    port def TopicoTelemetria { attribute nome : String = "/dji/telemetria"; out item msg : Telemetria; }
    port def TopicoCamera { attribute nome : String = "/dji/camera"; out item msg : QuadroCamera; }
    port def TopicoFalhas { attribute nome : String = "/falhas"; out item msg : Falha; }

    // ------------------------------------------------------------------ requisitos da Questão 1 (Tarefa 1)
    package RequisitosQ1 {
        requirement def <P01> Decolagem {
            doc /* Decolar verticalmente a partir do ponto inicial e atingir 1,80 m de altura em relação ao piso.
                   Ponto de referência geométrico declarado: plano inferior do corpo da aeronave (sensores inferiores),
                   mantido em todas as medições. */
            subject sujeito;
            attribute alturaAlvo : LengthValue = 1.80 [m];
            attribute alturaMedida : LengthValue;
            attribute tolVertical : LengthValue;
            require constraint { alturaMedida - alturaAlvo <= tolVertical and alturaAlvo - alturaMedida <= tolVertical }
        }

        requirement def <P02> QuadradoHorizontal {
            doc /* Percorrer um quadrado horizontal de aresta 1,50 m a 1,80 m de altura:
                   A=(0;0;1,80) B=(1,50;0;1,80) C=(1,50;1,50;1,80) D=(0;1,50;1,80), A acima do ponto de decolagem. */
            subject sujeito;
            attribute aresta : LengthValue = 1.50 [m];
            attribute alturaAlvo : LengthValue = 1.80 [m];
        }

        requirement def <P03> PermanenciaNosVertices {
            doc /* Pairar pelo menos 60 s contínuos em A, B, C e D, nesta ordem (ou A, D, C, B); sem segunda espera em A. */
            subject sujeito;
            attribute tempoPermanencia : DurationValue = 60 [s];
            attribute tempoMedido : DurationValue;
            require constraint { tempoMedido >= tempoPermanencia }
        }

        requirement def <P04> PousoSuave {
            doc /* Retornar ao ponto inicial e pousar com redução controlada da velocidade vertical;
                   encerrar após confirmar o pouso por telemetria. */
            subject sujeito;
            attribute vToqueMax : SpeedValue;
            attribute vToqueMedida : SpeedValue;
            require constraint { vToqueMedida <= vToqueMax }
        }

        requirement def <P05> ToleranciasDeclaradas {
            doc /* Tolerâncias de posição e altura, limites de velocidade de voo pairado e de toque, definidos antes dos
                   testes e aprovados na entrega intermediária; a contagem de permanência reinicia se forem excedidas. */
            subject sujeito;
        }

        requirement def <P06> EvidenciaEModelo {
            doc /* Modelo SysML 2.0 (níveis 0, 1 e n), implementação executável, configuração da trajetória, logs e
                   evidências em voo real; estados de decolagem, deslocamento, permanência, retorno, pouso e falha. */
            subject sujeito;
        }

        requirement def <R07> FalhasEmAmbienteInterno {
            doc /* Comum às duas tarefas. Tratar perda de comunicação, bateria insuficiente, estimativa inválida e tempo
                   excedido com término seguro adequado a uma sala. Retorno automático por GNSS não é solução válida. */
            subject sujeito;
        }
    }

    // ------------------------------------------------------------------ requisitos da Questão 2 (Tarefa 2)
    package RequisitosQ2 {
        requirement def <R01> Configuracao { doc /* Carregar cores-alvo, limites de tempo, condições iniciais e parâmetros de arquivo documentado. */ subject sujeito; }
        requirement def <R02> Percepcao { doc /* Detectar e classificar balões nas imagens da câmera do drone em voo real. */ subject sujeito; }
        requirement def <R03> Autonomia {
            doc /* Busca, seleção, aproximação, confirmação, afastamento e próximo alvo; o operador só inicia e interrompe. */
            subject sujeito;
        }
        requirement def <R04> DistanciaEPermanencia {
            doc /* 0 < d <= 0,05 m entre a bexiga e o envelope externo (com hélices) por 60 s contínuos, sem colisão;
                   método de medição e incerteza; contagem reinicia ao sair da faixa. */
            subject sujeito;
            attribute distanciaMaxima : LengthValue = 0.05 [m];
            attribute tempoPermanencia : DurationValue = 60 [s];
        }
        requirement def <R05> Estimacao { doc /* Estimar a distância com as observações disponíveis; referência independente não alimenta o algoritmo. */ subject sujeito; }
        requirement def <R06> Restricoes { doc /* Evitar paredes, teto, piso, mobiliário e bexigas não selecionadas, com margens definidas. */ subject sujeito; }
        requirement def <R08> Observabilidade { doc /* Painel com estado, alvo, distância, tempo, eventos e falhas; logs exportáveis. */ subject sujeito; }
        requirement def <R09> Reprodutibilidade { doc /* Execução documentada em outro computador, com dependências, versões, parâmetros e sementes. */ subject sujeito; }
    }
}
