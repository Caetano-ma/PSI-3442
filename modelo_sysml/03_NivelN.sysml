package NivelN {
    doc /* Nível n — implementação da Questão 1.
           (A) Drone: os blocos do nível 1 são produtos DJI fechados. Não são decompostos internamente; são
               "explorados" pela interface do DJI Mobile SDK v5: o que podemos ler, o que podemos comandar e quais
               limites conhecemos. Nomes de chaves/APIs do SDK e valores numéricos marcados "verificar" devem ser
               confirmados na documentação oficial e na versão do SDK efetivamente usada.
           (B) App de Missão: decomposta até módulos implementáveis e verificáveis, com ciclo de controle,
               máquina de estados, contratos de interface e tratamento de falhas.

           Justificativa da profundidade adotada:
           - Drone: a decomposição para no bloco do nível 1, porque abaixo dele nada é observável nem alterável;
             o que importa para a missão é o contrato do SDK de cada bloco (entradas, saídas, limites).
           - Aplicação: a decomposição para quando cada folha (i) corresponde a um único arquivo/classe Kotlin,
             (ii) tem entradas e saídas tipadas com unidades e referencial definidos e (iii) pode ser verificada
             isoladamente por um teste unitário ou por um ensaio em voo listado em 04_Verificacao.sysml. */

    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import Comum::*;
    private import Nivel1::EstadoEstimado;
    private import Nivel1::VereditoTolerancia;

    // =========================================================================================== (A) caixas-pretas
    enum def AcaoPerdaSinal {
        enum pairar;
        enum pousar;
        enum retornarAoPonto;   // RTH depende de GNSS: inválido em ambiente interno (R07)
    }

    port def SdkControladorVoo {
        doc /* Recursos do controlador de voo expostos pelo SDK (chaves FlightControllerKey e VirtualStickManager — verificar nomes). */
        out attribute velocidadeNorte : SpeedValue;     // KeyAircraftVelocity
        out attribute velocidadeLeste : SpeedValue;     // KeyAircraftVelocity
        out attribute velocidadeBaixo : SpeedValue;     // KeyAircraftVelocity
        out attribute altitude : LengthValue;           // KeyAltitude (relativa à decolagem)
        out attribute alturaToF : LengthValue;          // KeyUltrasonicHeight (sensor inferior)
        out attribute guinada : Real;                   // KeyAircraftAttitude (graus)
        out attribute emVoo : Boolean;                  // KeyIsFlying
        out attribute motoresLigados : Boolean;         // KeyAreMotorsOn
        out attribute modoVoo : String;                 // KeyFlightMode
        in item decolar : ComandoDiscreto;              // KeyStartTakeoff
        in item pousar : ComandoDiscreto;               // KeyStartAutoLanding
        in item controleVirtual : ComandoVelocidade;    // VirtualStickManager: modo velocidade, referencial do solo
        in attribute acaoPerdaSinal : AcaoPerdaSinal;   // KeyFailsafeAction
    }

    port def SdkBateria {
        out attribute cargaPercentual : Real;           // BatteryKey.KeyChargeRemainingInPercent
    }

    port def SdkPercepcao {
        doc /* Sensores de visão e ToF (verificar disponibilidade no Mini 4 Pro pelo SDK). */
        out attribute distanciasObstaculos : LengthValue[*];  // PerceptionManager: distâncias em 360°
        out attribute posicionamentoVisualAtivo : Boolean;    // estado do posicionamento visual — verificar chave
    }

    port def SdkEnlace {
        out attribute conectado : Boolean;              // FlightControllerKey.KeyConnection
        out attribute qualidadeSinal : Real;            // AirLinkKey.KeySignalQuality
    }

    port def SdkCamera {
        doc /* Usado apenas na Questão 2. */
        out item video : Imagem;                        // fluxo de vídeo da câmera principal
        in attribute anguloGimbal : Real;               // GimbalKey: rotação do gimbal
    }

    part def UceCaixaPreta :> Nivel1::UnidadeComputacaoEmbarcada {
        doc /* Estabilização, estimativa de pose e execução de decolagem/pouso automáticos ficam no firmware DJI.
               Exploramos: leitura de velocidade/altura/estado, decolagem e pouso automáticos, controle virtual em
               velocidade e configuração da ação em perda de sinal. */
        port sdk : SdkControladorVoo;
        attribute precisaoPairadoHorizontal : LengthValue = 0.3 [m];   // especificação DJI com posicionamento visual — verificar
        attribute precisaoPairadoVertical : LengthValue = 0.1 [m];     // idem — verificar
        attribute taxaControleVirtualMin : Real = 5.0;                   // Hz — verificar
        attribute taxaControleVirtualMax : Real = 25.0;                  // Hz — verificar
    }

    part def SensoriamentoCaixaPreta :> Nivel1::Sensoriamento {
        doc /* O posicionamento visual exige piso texturizado e iluminação adequada: condição do ambiente a garantir
               no ensaio (fita/tapete com textura sob a trajetória). */
        port sdk : SdkPercepcao;
        attribute exigePisoTexturizado : Boolean = true;
    }

    part def EnergiaCaixaPreta :> Nivel1::Energia {
        port sdk : SdkBateria;
    }

    part def ComunicacaoCaixaPreta :> Nivel1::Comunicacao {
        port sdk : SdkEnlace;
    }

    part def AtuadoresCaixaPreta :> Nivel1::Atuadores {
        doc /* Sem acesso direto aos motores: só são comandados através da UCE. Gimbal acessível pelo SDK (Questão 2). */
        port sdk : SdkCamera;
    }

    part def EstruturaCaixaPreta :> Nivel1::EstruturaFisica {
        doc /* Envelope externo com hélices (necessário para a Questão 2 e para o ponto de referência de P01). */
        attribute comprimentoComHelices : LengthValue = 0.298 [m];   // verificar no manual
        attribute larguraComHelices : LengthValue = 0.373 [m];       // verificar no manual
        attribute alturaTotal : LengthValue = 0.101 [m];             // verificar no manual
    }

    part def DroneN :> Nivel1::DroneN1 {
        part :>> uce : UceCaixaPreta;
        part :>> sensoriamento : SensoriamentoCaixaPreta;
        part :>> energia : EnergiaCaixaPreta;
        part :>> comunicacao : ComunicacaoCaixaPreta;
        part :>> atuadores : AtuadoresCaixaPreta;
        part :>> estrutura : EstruturaCaixaPreta;
    }

    // =========================================================================================== contratos de interface
    interface def ContratoSdkControladorVoo {
        doc /* Aplicação <-> controlador de voo, pelo caminho USB -> controle remoto -> enlace O4.
               Pré: aeronave conectada; controle virtual habilitado antes de enviar velocidades.
               Comandos de velocidade no referencial do solo (norte, leste, baixo), m/s.
               Latência do caminho não é especificada pela DJI: medir em ensaio (instante do comando x resposta na
               telemetria) e registrar. Perda de enlace: a própria aeronave executa acaoPerdaSinal = pousar. */
        end aplicacao : ~SdkControladorVoo;
        end aeronave : SdkControladorVoo;
    }

    interface def ContratoTelemetria {
        doc /* Adaptador -> lógica. Amostras em unidades SI, velocidades no referencial do solo (norte, leste, baixo),
               instante do relógio monotônico do Android. Pós: amostras em ordem crescente de instante. */
        end produtor : PortaTelemetria;
        end consumidor : ~PortaTelemetria;
        attribute taxa : Real = 10.0;                        // Hz
        attribute idadeMaxima : DurationValue = 0.3 [s];
    }

    interface def ContratoComandos {
        doc /* Lógica -> adaptador. Velocidades no ReferencialLocal (x, y, z para cima), m/s; o adaptador converte
               para norte/leste/baixo com psi0. Pré: módulo |v| dentro dos limites abaixo (saturado pela lógica).
               Pós: o adaptador reenvia o último comando à taxa do emissor; sem comando novo dentro do prazo do
               watchdog, envia velocidade zero. Comandos discretos rejeitados pelo SDK geram FalhaDetectada(comandoRejeitado). */
        end emissor : ~PortaComandos;
        end receptor : PortaComandos;
        attribute vMaxHorizontal : SpeedValue = 0.3 [m/s];
        attribute vMaxVertical : SpeedValue = 0.3 [m/s];
        attribute prazoWatchdog : DurationValue = 0.2 [s];
    }

    // =========================================================================================== (B) módulos da aplicação
    part def ModuloSoftware {
        attribute arquivoCodigo : String;
    }

    // ---------------------------------------------------------------- adaptador DJI (Kotlin)
    part def GerenciadorConexaoSdk :> ModuloSoftware {
        doc /* Registra o app no SDK, detecta a aeronave conectada e publica o estado do enlace. */
        attribute :>> arquivoCodigo = "app/adapter/ConexaoSdk.kt";
    }

    part def LeitorTelemetria :> ModuloSoftware {
        doc /* Assina as chaves do SDK e monta amostras Telemetria com instante do relógio monotônico do Android. */
        attribute :>> arquivoCodigo = "app/adapter/LeitorTelemetria.kt";
        attribute taxaAmostragem : Real = 10.0;   // Hz
    }

    part def EmissorComandos :> ModuloSoftware {
        doc /* Envia decolagem/pouso e o último ComandoVelocidade a taxa fixa, convertendo do ReferencialLocal para
               norte/leste/baixo. Watchdog: sem atualização da lógica dentro do prazo, envia velocidade zero. */
        attribute :>> arquivoCodigo = "app/adapter/EmissorComandos.kt";
        attribute taxaEnvio : Real = 20.0;        // Hz
        attribute prazoWatchdog : DurationValue = 0.2 [s];
    }

    part def ConfiguradorSeguranca :> ModuloSoftware {
        doc /* Antes da decolagem: ação em perda de sinal = pousar; desabilita retorno automático por GNSS;
               define limite de altura. Confirma por leitura das chaves. */
        attribute :>> arquivoCodigo = "app/adapter/ConfiguradorSeguranca.kt";
        attribute acaoPerdaSinal : AcaoPerdaSinal = AcaoPerdaSinal::pousar;
    }

    part def AdaptadorDJIN :> Nivel1::AdaptadorDJI {
        port fc : ~SdkControladorVoo;
        port bateria : ~SdkBateria;
        port enlace : ~SdkEnlace;
        port percepcao : ~SdkPercepcao;
        part gerenciadorConexao : GerenciadorConexaoSdk;
        part leitorTelemetria : LeitorTelemetria;
        part emissorComandos : EmissorComandos;
        part configuradorSeguranca : ConfiguradorSeguranca;
    }

    // ---------------------------------------------------------------- lógica de missão
    part def CarregadorConfig :> ModuloSoftware {
        doc /* Lê e valida o JSON (unidades SI, tolerâncias presentes, vértices coerentes com aresta e altura). */
        attribute :>> arquivoCodigo = "app/missao/CarregadorConfig.kt";
    }

    part def EstimadorEstado :> ModuloSoftware {
        doc /* Algoritmo: x, y por integração trapezoidal das velocidades norte/leste do posicionamento visual da DJI,
               a partir de A, convertidas ao ReferencialLocal com psi0. z: altura ToF inferior (reserva: altitude
               relativa). Estado inválido se a amostra estiver mais velha que idadeMaxAmostra ou se o posicionamento
               visual estiver inativo. A deriva da integração é o principal risco: validar com medição externa. */
        attribute :>> arquivoCodigo = "app/missao/EstimadorEstado.kt";
        attribute idadeMaxAmostra : DurationValue = 0.3 [s];
    }

    part def VerificadorTolerancia :> ModuloSoftware {
        doc /* dentro = |erro horizontal| <= tolHorizontal e |erro vertical| <= tolVertical e |v| <= vPairadoMax. */
        attribute :>> arquivoCodigo = "app/missao/VerificadorTolerancia.kt";
    }

    part def PlanejadorTrajetoria :> ModuloSoftware {
        doc /* Sequência de setpoints [A, B, C, D, A] (abcd) ou [A, D, C, B, A] (adcb); fornece o setpoint do índice atual. */
        attribute :>> arquivoCodigo = "app/missao/PlanejadorTrajetoria.kt";
    }

    part def ControladorPosicao :> ModuloSoftware {
        doc /* Algoritmo: por eixo, v = saturacao(kp * erro, vMax). Pouso: descida em rampa até alturaInicioPouso,
               depois pouso automático da DJI; a velocidade de toque é lida da telemetria e registrada. */
        attribute :>> arquivoCodigo = "app/missao/ControladorPosicao.kt";
        attribute kp : Real = 0.8;                                  // 1/s — ajustar em ensaio
        attribute vMaxHorizontal : SpeedValue = 0.3 [m/s];
        attribute vMaxVertical : SpeedValue = 0.3 [m/s];
        attribute alturaInicioPouso : LengthValue = 0.3 [m];
    }

    part def CronometroPermanencia :> ModuloSoftware {
        doc /* Relógio monotônico (tempo real). Conta enquanto o veredito é "dentro"; zera quando sai; emite
               PermanenciaConcluida aos 60 s contínuos. Registra início, interrupções e duração de cada tentativa. */
        attribute :>> arquivoCodigo = "app/missao/CronometroPermanencia.kt";
        attribute duracaoAlvo : DurationValue = 60 [s];
    }

    part def MonitorFalhas :> ModuloSoftware {
        doc /* Tratamento de erros (tipo de falha -> detecção -> reação):
               perdaEnlace                  -> conectado = false             -> aeronave pousa sozinha (failsafe); app registra
               telemetriaAtrasada           -> amostra > prazoTelemetria      -> watchdog zera velocidade; persistindo, pousoSeguro
               bateriaBaixa                 -> carga < bateriaMinima          -> pousoSeguro
               estimativaInvalida           -> estimador marca inválido       -> velocidade zero (paira); persistindo, pousoSeguro
               posicionamentoVisualInativo  -> chave do SDK = false           -> pousoSeguro
               desvioExcessivo              -> erro > desvioMaximo            -> pousoSeguro
               tempoMissaoExcedido          -> tempo > tempoMaxMissao         -> pousoSeguro
               comandoRejeitado             -> callback de erro do SDK        -> antes do voo: volta a ocioso; em voo: pousoSeguro
               Em todos os casos: evento registrado com tipo, instante e estado. */
        attribute :>> arquivoCodigo = "app/missao/MonitorFalhas.kt";
        attribute prazoTelemetria : DurationValue = 0.5 [s];
        attribute desvioMaximo : LengthValue = 0.6 [m];
    }

    part def SupervisorMissao :> ModuloSoftware {
        attribute :>> arquivoCodigo = "app/missao/SupervisorMissao.kt";
        exhibit state maquina : MaquinaEstadosQ1;
    }

    part def LogicaMissaoN :> Nivel1::LogicaMissao {
        part carregadorConfig : CarregadorConfig;
        part estimador : EstimadorEstado;
        part verificador : VerificadorTolerancia;
        part planejador : PlanejadorTrajetoria;
        part controlador : ControladorPosicao;
        part cronometro : CronometroPermanencia;
        part monitorFalhas : MonitorFalhas;
        part supervisor : SupervisorMissao;
    }

    // ---------------------------------------------------------------- painel e registro
    part def TelaMissao :> ModuloSoftware {
        doc /* Botões Iniciar e Interromper; mostra estado, vértice, cronômetro, x/y/z, velocidades, bateria e falhas. */
        attribute :>> arquivoCodigo = "app/ui/TelaMissao.kt";
    }

    part def RegistradorCsv :> ModuloSoftware {
        doc /* Estrutura de dados: um arquivo por missão; uma linha por ciclo (10 Hz) e uma por evento, com colunas
               instante_s, estado, vertice, x_m, y_m, z_m, vx_mps, vy_mps, vz_mps, dentro, permanencia_s,
               cmd_vx_mps, cmd_vy_mps, cmd_vz_mps, bateria_pct, evento, tipo_falha. */
        attribute :>> arquivoCodigo = "app/registro/RegistradorCsv.kt";
    }

    part def InterfacePainelN :> Nivel1::InterfacePainel {
        part tela : TelaMissao;
    }

    part def RegistroN :> Nivel1::Registro {
        part registradorCsv : RegistradorCsv;
    }

    part def AplicacaoMissaoN :> Nivel1::AplicacaoMissaoN1 {
        part :>> adaptador : AdaptadorDJIN;
        part :>> logica : LogicaMissaoN;
        part :>> painel : InterfacePainelN;
        part :>> registro : RegistroN;
        interface contratoTelemetria : ContratoTelemetria connect adaptador.telemetria to logica.telemetria;
        interface contratoComandos : ContratoComandos connect logica.comandos to adaptador.comandos;
    }

    part def CelularAndroidN :> Nivel1::CelularAndroidN1 {
        part :>> app : AplicacaoMissaoN;
    }

    part def EstacaoSoloN :> Nivel1::EstacaoSoloN1 {
        part :>> celular : CelularAndroidN;
    }

    part def SistemaVooAutonomoN :> Nivel1::SistemaVooAutonomoN1 {
        doc /* As conexões abaixo são lógicas (SDK); fisicamente passam por USB, controle remoto e enlace O4. */
        part :>> drone : DroneN;
        part :>> estacao : EstacaoSoloN;
        interface contratoSdk : ContratoSdkControladorVoo connect estacao.celular.app.adaptador.fc to drone.uce.sdk;
        connect estacao.celular.app.adaptador.bateria to drone.energia.sdk;
        connect estacao.celular.app.adaptador.enlace to drone.comunicacao.sdk;
        connect estacao.celular.app.adaptador.percepcao to drone.sensoriamento.sdk;
    }

    // =========================================================================================== configuração proposta
    item configQ1 : ConfiguracaoMissao {
        doc /* Valores de P05 são PROPOSTA a justificar e submeter na entrega intermediária (27/11/2026). */
        attribute verticeA : Ponto3D { :>> x = 0 [m];    :>> y = 0 [m];    :>> z = 1.80 [m]; }
        attribute verticeB : Ponto3D { :>> x = 1.50 [m]; :>> y = 0 [m];    :>> z = 1.80 [m]; }
        attribute verticeC : Ponto3D { :>> x = 1.50 [m]; :>> y = 1.50 [m]; :>> z = 1.80 [m]; }
        attribute verticeD : Ponto3D { :>> x = 0 [m];    :>> y = 1.50 [m]; :>> z = 1.80 [m]; }
        :>> vertices = (verticeA, verticeB, verticeC, verticeD);
        :>> sentido = SentidoPercurso::abcd;
        :>> alturaAlvo = 1.80 [m];
        :>> aresta = 1.50 [m];
        :>> tempoPermanencia = 60 [s];
        :>> tolHorizontal = 0.30 [m];
        :>> tolVertical = 0.10 [m];
        :>> vPairadoMax = 0.15 [m/s];
        :>> vToqueMax = 0.40 [m/s];
        :>> vDeslocamentoMax = 0.30 [m/s];
        :>> bateriaMinimaPercentual = 30.0;
        :>> tempoMaxMissao = 600 [s];
        :>> tempoEstabilizacao = 2 [s];
    }

    // =========================================================================================== ações folha e ciclo
    action def LerAmostra { out tel : Telemetria; }
    action def AtualizarEstimativa { in tel : Telemetria; out estado : EstadoEstimado; }
    action def ObterSetpoint { out setpoint : Ponto3D; }
    action def AvaliarTolerancia { in estado : EstadoEstimado; in setpoint : Ponto3D; out veredito : VereditoTolerancia; }
    action def AtualizarCronometro { in veredito : VereditoTolerancia; out concluido : Boolean; }
    action def DetectarFalhas { in tel : Telemetria; in estado : EstadoEstimado; out falha : Boolean; }
    action def AvancarMaquinaEstados {
        in veredito : VereditoTolerancia;
        in concluido : Boolean;
        in falha : Boolean;
        out discreto : ComandoDiscreto;
    }
    action def CalcularVelocidade { in estado : EstadoEstimado; in setpoint : Ponto3D; out comando : ComandoVelocidade; }
    action def EnviarComandos { in comando : ComandoVelocidade; in discreto : ComandoDiscreto; }
    action def GravarLinha { in tel : Telemetria; in estado : EstadoEstimado; in veredito : VereditoTolerancia; }

    action def CicloControle {
        doc /* Executado a cada 100 ms (10 Hz), em tempo real. O índice do vértice atual é lido do estado do supervisor. */
        action ler : LerAmostra;
        action estimar : AtualizarEstimativa;
        action setpoint : ObterSetpoint;
        action avaliar : AvaliarTolerancia;
        action cronometrar : AtualizarCronometro;
        action detectar : DetectarFalhas;
        action avancar : AvancarMaquinaEstados;
        action calcular : CalcularVelocidade;
        action enviar : EnviarComandos;
        action gravar : GravarLinha;

        first start then ler;
        first ler then estimar;
        first estimar then setpoint;
        first setpoint then avaliar;
        first avaliar then cronometrar;
        first cronometrar then detectar;
        first detectar then avancar;
        first avancar then calcular;
        first calcular then enviar;
        first enviar then gravar;
        first gravar then done;

        flow from ler.tel to estimar.tel;
        flow from ler.tel to detectar.tel;
        flow from ler.tel to gravar.tel;
        flow from estimar.estado to avaliar.estado;
        flow from estimar.estado to detectar.estado;
        flow from estimar.estado to calcular.estado;
        flow from estimar.estado to gravar.estado;
        flow from setpoint.setpoint to avaliar.setpoint;
        flow from setpoint.setpoint to calcular.setpoint;
        flow from avaliar.veredito to cronometrar.veredito;
        flow from avaliar.veredito to avancar.veredito;
        flow from avaliar.veredito to gravar.veredito;
        flow from cronometrar.concluido to avancar.concluido;
        flow from detectar.falha to avancar.falha;
        flow from avancar.discreto to enviar.discreto;
        flow from calcular.comando to enviar.comando;
    }

    // =========================================================================================== máquina de estados (P06)
    state def MaquinaEstadosQ1 {
        doc /* Refina Nivel1::ModosOperacao para a Questão 1 (missaoAutonoma = emVoo).
               Estados exigidos por P06: decolagem, deslocamento, permanência, retorno, pouso e falha.
               As condições de disparo de cada evento estão nas definições dos sinais (Comum). */
        attribute indiceVertice : Integer;     // 0=A, 1=B, 2=C, 3=D
        attribute ultimoIndice : Integer = 3;

        entry; then ocioso;

        state ocioso;
        transition iniciar first ocioso accept IniciarMissao then preparando;

        state preparando { entry action verificarConexaoBateriaEConfigurarSeguranca; }
        transition preparado first preparando accept PreparacaoConcluida then emVoo;
        transition desistir first preparando accept FalhaDetectada then ocioso;

        state emVoo {
            entry; then decolando;

            state decolando { entry action enviarDecolagem; }
            transition decolou first decolando accept DecolagemConcluida then subindo;

            state subindo { do action subirAte180; }
            transition chegouEmA first subindo accept AlturaAtingida then pairando;

            state pairando {
                entry action zerarCronometro;
                do action manterVertice;
            }
            transition reiniciarContagem first pairando accept ToleranciaExcedida then pairando;
            transition proximoVertice first pairando accept PermanenciaConcluida if indiceVertice < ultimoIndice then deslocando;
            transition ultimoVertice first pairando accept PermanenciaConcluida if indiceVertice >= ultimoIndice then retornando;

            state deslocando {
                entry action incrementarIndice;
                do action seguirSetpoint;
            }
            transition chegouNoVertice first deslocando accept VerticeAtingido then pairando;

            state retornando { do action seguirAteA; }
            transition chegouEmARetorno first retornando accept VerticeAtingido then estabilizandoEmA;

            state estabilizandoEmA { do action manterA; }
        }
        transition iniciarPouso first emVoo accept Estabilizado then pousando;
        transition falhaEmVoo first emVoo accept FalhaDetectada then pousoSeguro;
        transition interrompido first emVoo accept InterromperMissao then pousoSeguro;

        state pousando {
            entry action descerEmRampa;
            do action monitorarToque;
        }
        transition pousou first pousando accept PousoConfirmado then concluido;

        state pousoSeguro {
            doc /* Falha ou interrupção: pouso no local (nunca retorno por GNSS). */
            entry action pousarNoLocal;
        }
        transition pousouEmFalha first pousoSeguro accept PousoConfirmado then abortado;

        state concluido { entry action fecharRegistro; }
        state abortado { entry action fecharRegistroComFalha; }
    }

    // =========================================================================================== instâncias e rastreabilidade
    part sistemaN : SistemaVooAutonomoN;
    action ciclo : CicloControle;

    allocate ciclo.ler to sistemaN.estacao.celular.app.adaptador.leitorTelemetria;
    allocate ciclo.estimar to sistemaN.estacao.celular.app.logica.estimador;
    allocate ciclo.setpoint to sistemaN.estacao.celular.app.logica.planejador;
    allocate ciclo.avaliar to sistemaN.estacao.celular.app.logica.verificador;
    allocate ciclo.cronometrar to sistemaN.estacao.celular.app.logica.cronometro;
    allocate ciclo.detectar to sistemaN.estacao.celular.app.logica.monitorFalhas;
    allocate ciclo.avancar to sistemaN.estacao.celular.app.logica.supervisor;
    allocate ciclo.calcular to sistemaN.estacao.celular.app.logica.controlador;
    allocate ciclo.enviar to sistemaN.estacao.celular.app.adaptador.emissorComandos;
    allocate ciclo.gravar to sistemaN.estacao.celular.app.registro.registradorCsv;

    // refinamento nível 1 -> nível n
    allocate Nivel1::funcaoGlobal.configurar to sistemaN.estacao.celular.app.logica.carregadorConfig;
    allocate Nivel1::funcaoGlobal.estimar to sistemaN.estacao.celular.app.logica.estimador;
    allocate Nivel1::funcaoGlobal.estimar to sistemaN.estacao.celular.app.logica.verificador;
    allocate Nivel1::funcaoGlobal.planejar to sistemaN.estacao.celular.app.logica.planejador;
    allocate Nivel1::funcaoGlobal.supervisionar to sistemaN.estacao.celular.app.logica.supervisor;
    allocate Nivel1::funcaoGlobal.supervisionar to sistemaN.estacao.celular.app.logica.cronometro;
    allocate Nivel1::funcaoGlobal.supervisionar to sistemaN.estacao.celular.app.logica.monitorFalhas;
    allocate Nivel1::funcaoGlobal.controlar to sistemaN.estacao.celular.app.logica.controlador;
    allocate Nivel1::funcaoGlobal.interagir to sistemaN.estacao.celular.app.painel.tela;
    allocate Nivel1::funcaoGlobal.registrar to sistemaN.estacao.celular.app.registro.registradorCsv;
    allocate Nivel1::funcaoGlobal.adquirirTelemetria to sistemaN.estacao.celular.app.adaptador.leitorTelemetria;
    allocate Nivel1::funcaoGlobal.emitirComandos to sistemaN.estacao.celular.app.adaptador.emissorComandos;
    allocate Nivel1::funcaoGlobal.emitirComandos to sistemaN.estacao.celular.app.adaptador.configuradorSeguranca;

    // requisito -> módulo
    satisfy Nivel0::p01 by sistemaN.estacao.celular.app.logica.controlador;
    satisfy Nivel0::p01 by sistemaN.estacao.celular.app.logica.estimador;
    satisfy Nivel0::p02 by sistemaN.estacao.celular.app.logica.planejador;
    satisfy Nivel0::p02 by sistemaN.estacao.celular.app.logica.controlador;
    satisfy Nivel0::p03 by sistemaN.estacao.celular.app.logica.cronometro;
    satisfy Nivel0::p03 by sistemaN.estacao.celular.app.logica.supervisor;
    satisfy Nivel0::p04 by sistemaN.estacao.celular.app.logica.controlador;
    satisfy Nivel0::p04 by sistemaN.estacao.celular.app.logica.supervisor;
    satisfy Nivel0::p05 by sistemaN.estacao.celular.app.logica.verificador;
    satisfy Nivel0::p05 by sistemaN.estacao.celular.app.logica.cronometro;
    satisfy Nivel0::p06 by sistemaN.estacao.celular.app.registro.registradorCsv;
    satisfy Nivel0::p06 by sistemaN.estacao.celular.app.logica.supervisor;
    satisfy Nivel0::r07 by sistemaN.estacao.celular.app.logica.monitorFalhas;
    satisfy Nivel0::r07 by sistemaN.estacao.celular.app.adaptador.configuradorSeguranca;
}
