package Nivel1 {
    doc /* Nível 1 — decomposição dos elementos do nível 0 (diagramas/nivel_1.png) e decomposição funcional da
           função global, com alocação das funções aos blocos. Os blocos internos do drone são caixas-pretas:
           conhecemos suas entradas e saídas, mas não podemos alterá-los. */

    private import ScalarValues::*;
    private import ISQ::*;
    private import Comum::*;
    private import Nivel0::*;

    // ------------------------------------------------------------------ itens e portas internos do drone
    item def InformacaoSensores;
    item def Trigger;
    item def SinalPWM;
    item def FixacaoMecanica;

    port def PortaInfoSensores {
        out item info : InformacaoSensores;
        in item trigger : Trigger;
    }
    port def PortaPWM { in item pwm : SinalPWM; }
    port def PortaFixacao { in item fixacao : FixacaoMecanica; }
    port def PortaPacotes { inout item pacote : PacoteDados; }

    // ------------------------------------------------------------------ dados internos da aplicação
    attribute def EstadoEstimado {
        doc /* Estado da aeronave no referencial local da missão (origem em A projetado no piso). */
        attribute posicao : Ponto3D;
        attribute vx : SpeedValue;
        attribute vy : SpeedValue;
        attribute vz : SpeedValue;
        attribute valido : Boolean;
    }

    attribute def VereditoTolerancia {
        attribute dentroHorizontal : Boolean;
        attribute dentroVertical : Boolean;
        attribute dentroVelocidade : Boolean;
        attribute dentro : Boolean;
    }

    port def PortaEstadoMissao {
        out item estado : DadosPainel;
        in item comando : ComandoOperador;
    }

    // ------------------------------------------------------------------ blocos do drone (caixas-pretas)
    part def Energia {
        doc /* Bateria inteligente de voo: armazena e distribui energia. */
        port bateria : PortaEnergia;
        port alimentacao : ~PortaEnergia;
    }

    part def UnidadeComputacaoEmbarcada {
        doc /* Controlador de voo DJI (firmware fechado): estima a pose, estabiliza e executa comandos do SDK. */
        port alimentacao : PortaEnergia;
        port botaoOnOff : PortaAcaoManual;
        port cartaoMemoria : PortaArmazenamento;
        port ledReady : PortaSinalVisual;
        port sensores : ~PortaInfoSensores;
        port pwm : ~PortaPWM;
        port pacotes : PortaPacotes;
    }

    part def Sensoriamento {
        doc /* IMU, barômetro, ToF inferior, visão inferior e omnidirecional, câmera. */
        port alimentacao : PortaEnergia;
        port distancia : PortaSensorial;
        port pressao : PortaSensorial;
        port texturaIluminacao : PortaSensorial;
        port imagem : PortaSensorial;
        port gps : PortaSensorial;
        port info : PortaInfoSensores;
        port fixacao : PortaFixacao;
    }

    part def Atuadores {
        doc /* Motores, ESCs e hélices; gimbal de 3 eixos da câmera. */
        port alimentacao : PortaEnergia;
        port pwm : PortaPWM;
        port empuxo : PortaEmpuxo;
        port fixacao : PortaFixacao;
    }

    part def Comunicacao {
        doc /* Transceptor DJI O4 e porta USB-C. */
        port alimentacao : PortaEnergia;
        port rf : PortaRF;
        port usb : PortaUSB;
        port pacotes : ~PortaPacotes;
    }

    part def EstruturaFisica {
        doc /* Corpo, braços dobráveis e fixações. */
        port fixacao : ~PortaFixacao;
    }

    part def DroneN1 :> Drone {
        part energia : Energia;
        part uce : UnidadeComputacaoEmbarcada;
        part sensoriamento : Sensoriamento;
        part atuadores : Atuadores;
        part comunicacao : Comunicacao;
        part estrutura : EstruturaFisica;

        // fluxos internos
        connect energia.alimentacao to uce.alimentacao;
        connect energia.alimentacao to sensoriamento.alimentacao;
        connect energia.alimentacao to atuadores.alimentacao;
        connect energia.alimentacao to comunicacao.alimentacao;
        connect sensoriamento.info to uce.sensores;
        connect uce.pwm to atuadores.pwm;
        connect uce.pacotes to comunicacao.pacotes;
        connect estrutura.fixacao to atuadores.fixacao;
        connect estrutura.fixacao to sensoriamento.fixacao;

        // fronteira do nível 0 delegada aos blocos
        connect bateria to energia.bateria;
        connect botaoOnOff to uce.botaoOnOff;
        connect cartaoMemoria to uce.cartaoMemoria;
        connect uce.ledReady to ledReady;
        connect distancia to sensoriamento.distancia;
        connect pressao to sensoriamento.pressao;
        connect texturaIluminacao to sensoriamento.texturaIluminacao;
        connect imagem to sensoriamento.imagem;
        connect gps to sensoriamento.gps;
        connect conexaoUSB to comunicacao.usb;
        connect rf to comunicacao.rf;
        connect atuadores.empuxo to empuxo;
    }

    // ------------------------------------------------------------------ blocos da aplicação de missão
    part def AdaptadorDJI {
        doc /* Única parte que conhece o DJI Mobile SDK v5 (Kotlin). Traduz telemetria e comandos. */
        port sdk : PortaUSB;
        port telemetria : PortaTelemetria;
        port comandos : PortaComandos;
    }

    part def LogicaMissao {
        doc /* Independente de plataforma: máquina de estados, cronômetro de 60 s, controle de posição e
               supervisão de falhas. A mesma lógica roda contra o simulador. */
        port telemetria : ~PortaTelemetria;
        port comandos : ~PortaComandos;
        port config : PortaConfiguracao;
        port estadoMissao : PortaEstadoMissao;
        port log : PortaLogs;
        exhibit state modos : ModosOperacao;
    }

    state def ModosOperacao {
        doc /* Estados de nível 1, comuns às Questões 1 e 2. Refinados no nível n por NivelN::MaquinaEstadosQ1
               (missaoAutonoma = decolagem, deslocamento, permanência e retorno). */
        entry; then ocioso;
        state ocioso;
        transition first ocioso accept IniciarMissao then preparacao;
        state preparacao;
        transition first preparacao accept PreparacaoConcluida then missaoAutonoma;
        transition first preparacao accept FalhaDetectada then ocioso;
        state missaoAutonoma;
        transition first missaoAutonoma accept Estabilizado then pousoNormal;
        transition first missaoAutonoma accept FalhaDetectada then terminoSeguro;
        transition first missaoAutonoma accept InterromperMissao then terminoSeguro;
        state pousoNormal;
        transition first pousoNormal accept PousoConfirmado then encerrada;
        state terminoSeguro { doc /* Pouso no local; nunca retorno por GNSS. */ }
        transition first terminoSeguro accept PousoConfirmado then encerrada;
        state encerrada;
    }

    part def InterfacePainel {
        port estadoMissao : ~PortaEstadoMissao;
        port display : PortaPainel;
        port operador : PortaOperador;
    }

    part def Registro {
        port entrada : ~PortaLogs;
        port saida : PortaLogs;
    }

    part def AplicacaoMissaoN1 :> AplicacaoMissao {
        part adaptador : AdaptadorDJI;
        part logica : LogicaMissao;
        part painel : InterfacePainel;
        part registro : Registro;

        connect sdk to adaptador.sdk;
        connect adaptador.telemetria to logica.telemetria;
        connect logica.comandos to adaptador.comandos;
        connect config to logica.config;
        connect logica.estadoMissao to painel.estadoMissao;
        connect comandosOperador to painel.operador;
        connect painel.display to display;
        connect logica.log to registro.entrada;
        connect registro.saida to logs;
    }

    part def CelularAndroidN1 :> CelularAndroid {
        part :>> app : AplicacaoMissaoN1;
    }

    part def EstacaoSoloN1 :> EstacaoSolo {
        part :>> celular : CelularAndroidN1;
    }

    part def SistemaVooAutonomoN1 :> SistemaVooAutonomo {
        part :>> drone : DroneN1;
        part :>> estacao : EstacaoSoloN1;
    }

    // ------------------------------------------------------------------ decomposição funcional
    action def ConfigurarMissao {
        in arquivo : ConfiguracaoMissao;
        out config : ConfiguracaoMissao;
    }
    action def InteragirComOperador {
        in comando : ComandoOperador;
        in estadoMissao : DadosPainel;
        out painel : DadosPainel;
        out comandoMissao : ComandoOperador;
    }
    action def AdquirirTelemetria {
        in pacote : PacoteDados;
        out telemetria : Telemetria;
    }
    action def EstimarEstadoEVerificarTolerancias {
        in telemetria : Telemetria;
        in config : ConfiguracaoMissao;
        out estado : EstadoEstimado;
        out veredito : VereditoTolerancia;
    }
    action def PlanejarTrajetoria {
        in config : ConfiguracaoMissao;
        in indiceVertice : Integer;
        out setpoint : Ponto3D;
    }
    action def SupervisionarMissao {
        in estado : EstadoEstimado;
        in veredito : VereditoTolerancia;
        in comandoOperador : ComandoOperador;
        in config : ConfiguracaoMissao;
        out indiceVertice : Integer;
        out comandoDiscreto : ComandoDiscreto;
        out estadoMissao : DadosPainel;
        out evento : RegistroLog;
    }
    action def ControlarPosicao {
        in estado : EstadoEstimado;
        in setpoint : Ponto3D;
        out comando : ComandoVelocidade;
    }
    action def EmitirComandosVoo {
        in velocidade : ComandoVelocidade;
        in discreto : ComandoDiscreto;
        out pacote : PacoteDados;
    }
    action def Registrar {
        in evento : RegistroLog;
        in estado : EstadoEstimado;
        out registro : RegistroLog;
    }
    action def RetransmitirRF {
        in subidaEntrada : PacoteDados;
        out subidaSaida : PacoteDados;
        in descidaEntrada : PacoteDados;
        out descidaSaida : PacoteDados;
    }
    action def EstimarPoseEEstabilizar {
        doc /* Caixa-preta: executada pelo firmware DJI. */
        in comandos : PacoteDados;
        in info : InformacaoSensores;
        out pwm : SinalPWM;
        out telemetria : PacoteDados;
    }
    action def Sensoriar {
        doc /* Caixa-preta. */
        in grandeza : GrandezaFisica;
        out info : InformacaoSensores;
    }
    action def GerarEmpuxo {
        doc /* Caixa-preta. */
        in pwm : SinalPWM;
        in energia : Comum::Energia;
        out empuxo : Empuxo;
    }
    action def ArmazenarDistribuirEnergia {
        doc /* Caixa-preta. */
        in recarga : Comum::Energia;
        out energia : Comum::Energia;
    }

    action def ExecutarMissaoAutonoma {
        doc /* Função global do sistema, decomposta em funções de nível 1. */
        in arquivoConfig : ConfiguracaoMissao;
        in comandoOperador : ComandoOperador;
        in grandezas : GrandezaFisica;
        out painel : DadosPainel;
        out registros : RegistroLog;
        out empuxo : Empuxo;

        action configurar : ConfigurarMissao;
        action interagir : InteragirComOperador;
        action adquirirTelemetria : AdquirirTelemetria;
        action estimar : EstimarEstadoEVerificarTolerancias;
        action planejar : PlanejarTrajetoria;
        action supervisionar : SupervisionarMissao;
        action controlar : ControlarPosicao;
        action emitirComandos : EmitirComandosVoo;
        action registrar : Registrar;
        action retransmitir : RetransmitirRF;
        action estabilizar : EstimarPoseEEstabilizar;
        action sensoriar : Sensoriar;
        action gerarEmpuxo : GerarEmpuxo;
        action distribuirEnergia : ArmazenarDistribuirEnergia;

        bind configurar.arquivo = arquivoConfig;
        bind interagir.comando = comandoOperador;
        bind sensoriar.grandeza = grandezas;
        flow from configurar.config to estimar.config;
        flow from configurar.config to planejar.config;
        flow from configurar.config to supervisionar.config;
        flow from interagir.comandoMissao to supervisionar.comandoOperador;
        flow from supervisionar.estadoMissao to interagir.estadoMissao;
        bind painel = interagir.painel;
        flow from adquirirTelemetria.telemetria to estimar.telemetria;
        flow from estimar.estado to supervisionar.estado;
        flow from estimar.veredito to supervisionar.veredito;
        flow from estimar.estado to controlar.estado;
        flow from estimar.estado to registrar.estado;
        flow from supervisionar.indiceVertice to planejar.indiceVertice;
        flow from planejar.setpoint to controlar.setpoint;
        flow from controlar.comando to emitirComandos.velocidade;
        flow from supervisionar.comandoDiscreto to emitirComandos.discreto;
        flow from supervisionar.evento to registrar.evento;
        bind registros = registrar.registro;
        flow from emitirComandos.pacote to retransmitir.subidaEntrada;
        flow from retransmitir.subidaSaida to estabilizar.comandos;
        flow from estabilizar.telemetria to retransmitir.descidaEntrada;
        flow from retransmitir.descidaSaida to adquirirTelemetria.pacote;
        flow from sensoriar.info to estabilizar.info;
        flow from estabilizar.pwm to gerarEmpuxo.pwm;
        flow from distribuirEnergia.energia to gerarEmpuxo.energia;
        bind empuxo = gerarEmpuxo.empuxo;
    }

    // ------------------------------------------------------------------ instâncias e alocação função -> bloco
    part sistema : SistemaVooAutonomoN1;
    action funcaoGlobal : ExecutarMissaoAutonoma;

    allocate funcaoGlobal.configurar to sistema.estacao.celular.app.logica;
    allocate funcaoGlobal.estimar to sistema.estacao.celular.app.logica;
    allocate funcaoGlobal.planejar to sistema.estacao.celular.app.logica;
    allocate funcaoGlobal.supervisionar to sistema.estacao.celular.app.logica;
    allocate funcaoGlobal.controlar to sistema.estacao.celular.app.logica;
    allocate funcaoGlobal.interagir to sistema.estacao.celular.app.painel;
    allocate funcaoGlobal.registrar to sistema.estacao.celular.app.registro;
    allocate funcaoGlobal.adquirirTelemetria to sistema.estacao.celular.app.adaptador;
    allocate funcaoGlobal.emitirComandos to sistema.estacao.celular.app.adaptador;
    allocate funcaoGlobal.retransmitir to sistema.estacao.controleRemoto;
    allocate funcaoGlobal.retransmitir to sistema.drone.comunicacao;
    allocate funcaoGlobal.estabilizar to sistema.drone.uce;
    allocate funcaoGlobal.sensoriar to sistema.drone.sensoriamento;
    allocate funcaoGlobal.gerarEmpuxo to sistema.drone.atuadores;
    allocate funcaoGlobal.distribuirEnergia to sistema.drone.energia;

    // ------------------------------------------------------------------ requisitos refinados para os blocos
    satisfy Nivel0::p01 by sistema.estacao.celular.app.logica;
    satisfy Nivel0::p02 by sistema.estacao.celular.app.logica;
    satisfy Nivel0::p03 by sistema.estacao.celular.app.logica;
    satisfy Nivel0::p04 by sistema.estacao.celular.app.logica;
    satisfy Nivel0::p05 by sistema.estacao.celular.app.logica;
    satisfy Nivel0::p06 by sistema.estacao.celular.app.registro;
    satisfy Nivel0::r07 by sistema.estacao.celular.app.logica;
    satisfy Nivel0::r07 by sistema.estacao.celular.app.adaptador;

    // ------------------------------------------------------------------ requisito -> função (matriz de rastreabilidade)
    satisfy Nivel0::p01 by funcaoGlobal.estimar;
    satisfy Nivel0::p01 by funcaoGlobal.controlar;
    satisfy Nivel0::p01 by funcaoGlobal.emitirComandos;
    satisfy Nivel0::p02 by funcaoGlobal.planejar;
    satisfy Nivel0::p02 by funcaoGlobal.estimar;
    satisfy Nivel0::p02 by funcaoGlobal.controlar;
    satisfy Nivel0::p03 by funcaoGlobal.estimar;
    satisfy Nivel0::p03 by funcaoGlobal.supervisionar;
    satisfy Nivel0::p04 by funcaoGlobal.controlar;
    satisfy Nivel0::p04 by funcaoGlobal.supervisionar;
    satisfy Nivel0::p04 by funcaoGlobal.emitirComandos;
    satisfy Nivel0::p05 by funcaoGlobal.configurar;
    satisfy Nivel0::p05 by funcaoGlobal.estimar;
    satisfy Nivel0::p05 by funcaoGlobal.supervisionar;
    satisfy Nivel0::p06 by funcaoGlobal.supervisionar;
    satisfy Nivel0::p06 by funcaoGlobal.registrar;
    satisfy Nivel0::p06 by funcaoGlobal.interagir;
    satisfy Nivel0::r07 by funcaoGlobal.supervisionar;
    satisfy Nivel0::r07 by funcaoGlobal.adquirirTelemetria;
    satisfy Nivel0::r07 by funcaoGlobal.emitirComandos;
}
