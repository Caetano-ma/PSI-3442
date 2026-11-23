package Comum {
    doc /* Tipos, sinais, portas e requisitos compartilhados pelos níveis 0, 1 e n.
           PSI3442 — P2 2026 — Questão 1 (voo de familiarização com DJI Mini 4 Pro). */

    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;

    // ------------------------------------------------------------------ grandezas físicas e energia
    item def Energia { doc /* Energia elétrica fornecida por bateria. */ }
    item def Empuxo { doc /* Força e torque aplicados ao ar pelas hélices. */ }
    item def SinalVisual { doc /* Indicação luminosa (LEDs de status). */ }
    item def AcaoManual { doc /* Ação física do operador: ligar/desligar, trocar bateria, posicionar. */ }
    item def GrandezaFisica { doc /* Grandeza do ambiente percebida por um sensor. */ }
    item def Distancia :> GrandezaFisica;
    item def Pressao :> GrandezaFisica;
    item def TexturaIluminacao :> GrandezaFisica { doc /* Textura do piso e iluminação: condição para o posicionamento visual. */ }
    item def Imagem :> GrandezaFisica;
    item def SinalGNSS :> GrandezaFisica { doc /* Indisponível em ambiente interno (R07): não utilizado pela missão. */ }

    // ------------------------------------------------------------------ dados
    attribute def ReferencialLocal {
        doc /* Referencial local da missão (P02), dextrogiro:
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

    enum def TipoFalha {
        enum perdaEnlace;
        enum telemetriaAtrasada;
        enum bateriaBaixa;
        enum estimativaInvalida;
        enum posicionamentoVisualInativo;
        enum desvioExcessivo;
        enum tempoMissaoExcedido;
        enum comandoRejeitado;
    }

    enum def TipoComando {
        enum decolar;
        enum pousar;
        enum habilitarControleVirtual;
        enum desabilitarControleVirtual;
        enum pararEPairar;
    }

    item def Telemetria {
        doc /* Amostra publicada pelo drone (caixa-preta) e lida via DJI Mobile SDK.
               Velocidades no referencial do solo (norte, leste, baixo); altura relativa ao ponto de decolagem. */
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
    }

    item def ComandoVelocidade {
        doc /* Comando de controle virtual em velocidade, referencial do solo. */
        attribute vx : SpeedValue;
        attribute vy : SpeedValue;
        attribute vz : SpeedValue;
        attribute taxaGuinada : Real;
    }

    item def ComandoDiscreto {
        attribute tipo : TipoComando;
    }

    item def ConfiguracaoMissao {
        doc /* Conteúdo do arquivo de configuração (JSON). */
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
        attribute bateriaMinimaPercentual : Real;
        attribute tempoMaxMissao : DurationValue;
        attribute tempoEstabilizacao : DurationValue;
    }

    item def ComandoOperador {
        doc /* O operador apenas inicia, interrompe ou aborta: não pilota continuamente (R03). */
    }
    item def DadosPainel { doc /* Estado da missão, vértice atual, cronômetro, telemetria e falhas. */ }
    item def RegistroLog { doc /* Linha de log: instante, estado, estimativa, comando, evento. */ }
    item def PacoteDados { doc /* Comandos, telemetria e vídeo trafegando entre aplicação, controle remoto e aeronave. */ }

    // ------------------------------------------------------------------ sinais da máquina de estados
    attribute def IniciarMissao { doc /* Operador pressiona Iniciar no painel. */ }
    attribute def InterromperMissao { doc /* Operador pressiona Interromper no painel. */ }
    attribute def PreparacaoConcluida {
        doc /* Aeronave conectada, bateria >= mínimo, posicionamento visual ativo, ação de perda de sinal = pousar
               confirmada por leitura, controle virtual habilitado e guinada psi0 registrada. */
    }
    attribute def DecolagemConcluida { doc /* emVoo = true e |vz| <= vPairadoMax após o comando de decolagem automática. */ }
    attribute def AlturaAtingida { doc /* |z - alturaAlvo| <= tolVertical e |v| <= vPairadoMax. */ }
    attribute def VerticeAtingido { doc /* Veredito "dentro" no setpoint atual (erro horizontal, vertical e velocidade). */ }
    attribute def ToleranciaExcedida { doc /* Veredito passa de "dentro" para "fora" durante a permanência: zera o cronômetro (P05). */ }
    attribute def PermanenciaConcluida { doc /* Cronômetro atinge tempoPermanencia contínuo em tempo real. */ }
    attribute def Estabilizado { doc /* Veredito "dentro" em A (retorno) mantido por tempoEstabilizacao. */ }
    attribute def PousoConfirmado { doc /* Telemetria: emVoo = false e motoresLigados = false. */ }
    attribute def FalhaDetectada {
        doc /* Emitido pelo monitor de falhas ou pelo adaptador (comando rejeitado pelo SDK). */
        attribute tipo : TipoFalha;
    }

    // ------------------------------------------------------------------ portas
    port def PortaEnergia { in item energia : Energia; }
    port def PortaAcaoManual { in item acao : AcaoManual; }
    port def PortaSensorial { in item grandeza : GrandezaFisica; }
    port def PortaEmpuxo { out item empuxo : Empuxo; }
    port def PortaSinalVisual { out item sinal : SinalVisual; }
    port def PortaRF { inout item pacote : PacoteDados; }
    port def PortaUSB { inout item pacote : PacoteDados; }
    port def PortaArmazenamento { inout item midia : PacoteDados; }
    port def PortaConfiguracao { in item config : ConfiguracaoMissao; }
    port def PortaLogs { out item registro : RegistroLog; }
    port def PortaPainel { out item dados : DadosPainel; }
    port def PortaOperador { in item comando : ComandoOperador; }
    port def PortaTelemetria { out item telemetria : Telemetria; }
    port def PortaComandos {
        in item velocidade : ComandoVelocidade;
        in item discreto : ComandoDiscreto;
    }

    // ------------------------------------------------------------------ requisitos da Questão 1
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
                   A=(0;0;1,80) B=(1,50;0;1,80) C=(1,50;1,50;1,80) D=(0;1,50;1,80), A acima do ponto de decolagem.
                   Sentido escolhido pela equipe. */
            subject sujeito;
            attribute aresta : LengthValue = 1.50 [m];
            attribute alturaAlvo : LengthValue = 1.80 [m];
        }

        requirement def <P03> PermanenciaNosVertices {
            doc /* Pairar pelo menos 60 s contínuos em A, B, C e D, nesta ordem (ou A, D, C, B);
                   sem segunda espera no retorno a A. */
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
            doc /* Tolerâncias de posição e altura, limite de velocidade de voo pairado e de velocidade vertical no toque,
                   definidos antes dos testes e aprovados na entrega intermediária. A contagem de permanência reinicia
                   se as tolerâncias forem excedidas. Não podem ser ampliados retrospectivamente. */
            subject sujeito;
        }

        requirement def <P06> EvidenciaEModelo {
            doc /* Modelo SysML 2.0 (níveis 0, 1 e n), implementação executável, configuração da trajetória, logs e
                   evidências em voo real; estados de decolagem, deslocamento, permanência, retorno, pouso e falha;
                   60 s medidos em tempo real. */
            subject sujeito;
        }

        requirement def <R07> FalhasEmAmbienteInterno {
            doc /* Tratar perda de comunicação, bateria insuficiente, estimativa inválida e tempo excedido com estados
                   de término seguro adequados a uma sala. Retorno automático por GNSS não é solução válida. */
            subject sujeito;
        }
    }
}
