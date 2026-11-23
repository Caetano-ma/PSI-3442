package Nivel1 {
    doc /* Nível 1 — decomposição funcional do Sistema de Missões Autônomas (diagramas/nivel_1.png).
           Alvo da decomposição: as tarefas e os serviços ROS 2 que elas usam. Android emulado, rádio DJI e drone
           permanecem componentes caixa-preta de comunicação e execução.
           Reuso entre as tarefas: gerenciador, estimação, controle, supervisão, registro e ponte DJI são comuns;
           só a Tarefa 2 usa a percepção visual. */

    private import ScalarValues::*;
    private import Comum::*;
    private import Nivel0::*;

    // ------------------------------------------------------------------ nós ROS 2
    part def InterfaceOperador {
        doc /* Recebe "executar tarefa 1", "executar tarefa 2" ou "interromper" e mostra o painel. */
        port operador : PortaOperador;
        port painel : PortaPainel;
        port pubComando : TopicoComandoOperador;
        port subStatus : ~TopicoTarefaStatus;
        port subFalhas : ~TopicoFalhas;
    }

    part def GerenciadorTarefas {
        doc /* Carrega a configuração, ativa a tarefa pedida, mantém os modos globais e envia decolar/pousar. */
        port config : PortaConfiguracao;
        port subComando : ~TopicoComandoOperador;
        port subEvento : ~TopicoTarefaEvento;
        port subFalhas : ~TopicoFalhas;
        port pubAtiva : TopicoTarefaAtiva;
        port pubStatus : TopicoTarefaStatus;
        port pubAcao : TopicoAcaoDJI;
        exhibit state modos : ModosOperacao;
    }

    part def Tarefa1VooFamiliarizacao {
        doc /* Questão 1: quadrado A-B-C-D a 1,80 m, quatro permanências de 60 s, retorno e pouso. */
        port subAtiva : ~TopicoTarefaAtiva;
        port subEstado : ~TopicoEstado;
        port pubSetpoint : TopicoSetpoint;
        port pubEvento : TopicoTarefaEvento;
    }

    part def Tarefa2Baloes {
        doc /* Questão 2: busca, seleção, aproximação a 0 < d <= 5 cm por 60 s, afastamento, próximo alvo. */
        port subAtiva : ~TopicoTarefaAtiva;
        port subEstado : ~TopicoEstado;
        port subAlvos : ~TopicoAlvos;
        port pubSetpoint : TopicoSetpoint;
        port pubEvento : TopicoTarefaEvento;
    }

    part def Registro {
        doc /* rosbag2 grava todos os tópicos; exportador gera o CSV de evidência. */
        port logs : PortaLogs;
        port subStatus : ~TopicoTarefaStatus;
        port subEvento : ~TopicoTarefaEvento;
        port subEstado : ~TopicoEstado;
        port subFalhas : ~TopicoFalhas;
    }

    part def EstimacaoEstado {
        port subTelemetria : ~TopicoTelemetria;
        port pubEstado : TopicoEstado;
    }

    part def ControleVoo {
        port subSetpoint : ~TopicoSetpoint;
        port subEstado : ~TopicoEstado;
        port pubCmdVel : TopicoCmdVel;
    }

    part def PercepcaoVisual {
        doc /* Só na Tarefa 2. */
        port subCamera : ~TopicoCamera;
        port pubAlvos : TopicoAlvos;
    }

    part def SupervisaoSeguranca {
        port subTelemetria : ~TopicoTelemetria;
        port subEstado : ~TopicoEstado;
        port pubFalhas : TopicoFalhas;
    }

    part def NoPonteDJI {
        doc /* Converte tópicos ROS 2 em mensagens do socket do app ponte e vice-versa. */
        port socket : PortaSocket;
        port subCmdVel : ~TopicoCmdVel;
        port subAcao : ~TopicoAcaoDJI;
        port pubTelemetria : TopicoTelemetria;
        port pubCamera : TopicoCamera;
    }

    part def AplicacaoROS2N1 :> AplicacaoROS2 {
        part interfaceOperador : InterfaceOperador;
        part gerenciador : GerenciadorTarefas;
        part tarefa1 : Tarefa1VooFamiliarizacao;
        part tarefa2 : Tarefa2Baloes;
        part registro : Registro;
        part estimacao : EstimacaoEstado;
        part controle : ControleVoo;
        part percepcao : PercepcaoVisual;
        part supervisao : SupervisaoSeguranca;
        part noPonte : NoPonteDJI;

        // fronteira
        connect comandosOperador to interfaceOperador.operador;
        connect interfaceOperador.painel to painel;
        connect config to gerenciador.config;
        connect registro.logs to logs;
        connect noPonte.socket to socketPonte;

        // tópicos: publicador -> assinantes
        connect interfaceOperador.pubComando to gerenciador.subComando;
        connect gerenciador.pubStatus to interfaceOperador.subStatus;
        connect gerenciador.pubStatus to registro.subStatus;
        connect gerenciador.pubAtiva to tarefa1.subAtiva;
        connect gerenciador.pubAtiva to tarefa2.subAtiva;
        connect gerenciador.pubAcao to noPonte.subAcao;
        connect tarefa1.pubSetpoint to controle.subSetpoint;
        connect tarefa2.pubSetpoint to controle.subSetpoint;
        connect tarefa1.pubEvento to gerenciador.subEvento;
        connect tarefa2.pubEvento to gerenciador.subEvento;
        connect tarefa1.pubEvento to registro.subEvento;
        connect tarefa2.pubEvento to registro.subEvento;
        connect estimacao.pubEstado to tarefa1.subEstado;
        connect estimacao.pubEstado to tarefa2.subEstado;
        connect estimacao.pubEstado to controle.subEstado;
        connect estimacao.pubEstado to supervisao.subEstado;
        connect estimacao.pubEstado to registro.subEstado;
        connect percepcao.pubAlvos to tarefa2.subAlvos;
        connect controle.pubCmdVel to noPonte.subCmdVel;
        connect supervisao.pubFalhas to gerenciador.subFalhas;
        connect supervisao.pubFalhas to interfaceOperador.subFalhas;
        connect supervisao.pubFalhas to registro.subFalhas;
        connect noPonte.pubTelemetria to estimacao.subTelemetria;
        connect noPonte.pubTelemetria to supervisao.subTelemetria;
        connect noPonte.pubCamera to percepcao.subCamera;
    }

    // ------------------------------------------------------------------ Android emulado
    part def AppPonteDJI {
        doc /* App Android (Kotlin) com o DJI Mobile SDK v5: única parte que conhece o SDK. */
        port socket : PortaSocket;
        port usb : PortaUSB;
    }

    part def AndroidEmuladoN1 :> AndroidEmulado {
        part appPonte : AppPonteDJI;
        connect socketPonte to appPonte.socket;
        connect appPonte.usb to usb;
    }

    part def NotebookLinuxN1 :> NotebookLinux {
        part :>> ros2 : AplicacaoROS2N1;
        part :>> android : AndroidEmuladoN1;
    }

    part def SistemaMissoesAutonomasN1 :> SistemaMissoesAutonomas {
        part :>> notebook : NotebookLinuxN1;
    }

    // ------------------------------------------------------------------ modos de operação
    state def ModosOperacao {
        doc /* Modos globais, comuns às duas tarefas. Cada tarefa é refinada no nível n
               (Tarefa 1: NivelN::MaquinaEstadosTarefa1). Critério de progressão do enunciado: a Tarefa 2 só é aceita
               em voo real depois de a Tarefa 1 ter sido concluída em voo real. */
        attribute tarefa1ConcluidaEmVooReal : Boolean;

        entry; then ocioso;
        state ocioso;
        transition first ocioso accept ExecutarTarefa1 then tarefa1;
        transition first ocioso accept ExecutarTarefa2 if tarefa1ConcluidaEmVooReal then tarefa2;

        state tarefa1;
        transition first tarefa1 accept TarefaConcluida then ocioso;
        transition first tarefa1 accept FalhaDetectada then terminoSeguro;
        transition first tarefa1 accept InterromperTarefa then terminoSeguro;

        state tarefa2;
        transition first tarefa2 accept TarefaConcluida then ocioso;
        transition first tarefa2 accept FalhaDetectada then terminoSeguro;
        transition first tarefa2 accept InterromperTarefa then terminoSeguro;

        state terminoSeguro { doc /* Pouso no local; nunca retorno por GNSS. */ }
        transition first terminoSeguro accept PousoConfirmado then ocioso;
    }

    // ------------------------------------------------------------------ decomposição funcional
    action def InterpretarComandoOperador {
        in comando : ComandoOperador;
        in status : StatusTarefa;
        out pedido : ComandoOperador;
        out painel : StatusTarefa;
    }
    action def GerenciarTarefas {
        in arquivo : ConfiguracaoTarefas;
        in pedido : ComandoOperador;
        in evento : EventoTarefa;
        in falha : Falha;
        out ativa : TarefaAtiva;
        out status : StatusTarefa;
        out acao : ComandoDiscreto;
        out registro : RegistroLog;
    }
    action def ConduzirTarefa1 {
        in ativa : TarefaAtiva;
        in estado : EstadoEstimado;
        out setpoint : Setpoint;
        out evento : EventoTarefa;
    }
    action def ConduzirTarefa2 {
        in ativa : TarefaAtiva;
        in estado : EstadoEstimado;
        in alvos : Alvos;
        out setpoint : Setpoint;
        out evento : EventoTarefa;
    }
    action def EstimarEstado {
        in telemetria : Telemetria;
        out estado : EstadoEstimado;
    }
    action def PerceberAlvos {
        in quadro : QuadroCamera;
        out alvos : Alvos;
    }
    action def ControlarVoo {
        in setpoint : Setpoint;
        in estado : EstadoEstimado;
        out cmdVel : ComandoVelocidade;
    }
    action def SupervisionarSeguranca {
        in telemetria : Telemetria;
        in estado : EstadoEstimado;
        out falha : Falha;
    }
    action def Registrar {
        in estado : EstadoEstimado;
        in evento : RegistroLog;
        in falha : Falha;
        out registro : RegistroLog;
    }
    action def TraduzirRos2Dji {
        in cmdVel : ComandoVelocidade;
        in acao : ComandoDiscreto;
        in socketEntrada : PacoteDados;
        out socketSaida : PacoteDados;
        out telemetria : Telemetria;
        out quadro : QuadroCamera;
    }
    action def AcionarSdkDji {
        in socketEntrada : PacoteDados;
        out socketSaida : PacoteDados;
        in usbEntrada : PacoteDados;
        out usbSaida : PacoteDados;
    }
    action def TransmitirRadio {
        doc /* Caixa-preta (rádio DJI). */
        in subidaEntrada : PacoteDados;
        out subidaSaida : PacoteDados;
        in descidaEntrada : PacoteDados;
        out descidaSaida : PacoteDados;
    }
    action def VoarAeronave {
        doc /* Caixa-preta (drone): estabiliza, sente o ambiente, executa comandos e publica telemetria. */
        in comandos : PacoteDados;
        in grandezas : GrandezaFisica;
        out telemetria : PacoteDados;
        out empuxo : Empuxo;
    }

    action def ExecutarTarefaAutonoma {
        doc /* Função global: ao receber "executar tarefa N", realizar a tarefa N de forma autônoma. */
        in arquivoConfig : ConfiguracaoTarefas;
        in comandoOperador : ComandoOperador;
        in grandezas : GrandezaFisica;
        out painel : StatusTarefa;
        out registros : RegistroLog;
        out empuxo : Empuxo;

        action interpretarComando : InterpretarComandoOperador;
        action gerenciarTarefas : GerenciarTarefas;
        action executarTarefa1 : ConduzirTarefa1;
        action executarTarefa2 : ConduzirTarefa2;
        action estimarEstado : EstimarEstado;
        action perceberAlvos : PerceberAlvos;
        action controlarVoo : ControlarVoo;
        action supervisionar : SupervisionarSeguranca;
        action registrar : Registrar;
        action traduzirParaDji : TraduzirRos2Dji;
        action acionarSdk : AcionarSdkDji;
        action transmitirRadio : TransmitirRadio;
        action voar : VoarAeronave;

        bind interpretarComando.comando = comandoOperador;
        bind painel = interpretarComando.painel;
        bind gerenciarTarefas.arquivo = arquivoConfig;
        bind voar.grandezas = grandezas;
        bind empuxo = voar.empuxo;
        bind registros = registrar.registro;

        flow from interpretarComando.pedido to gerenciarTarefas.pedido;
        flow from gerenciarTarefas.status to interpretarComando.status;
        flow from gerenciarTarefas.ativa to executarTarefa1.ativa;
        flow from gerenciarTarefas.ativa to executarTarefa2.ativa;
        flow from gerenciarTarefas.acao to traduzirParaDji.acao;
        flow from gerenciarTarefas.registro to registrar.evento;
        flow from executarTarefa1.evento to gerenciarTarefas.evento;
        flow from executarTarefa2.evento to gerenciarTarefas.evento;
        flow from executarTarefa1.setpoint to controlarVoo.setpoint;
        flow from executarTarefa2.setpoint to controlarVoo.setpoint;
        flow from estimarEstado.estado to executarTarefa1.estado;
        flow from estimarEstado.estado to executarTarefa2.estado;
        flow from estimarEstado.estado to controlarVoo.estado;
        flow from estimarEstado.estado to supervisionar.estado;
        flow from estimarEstado.estado to registrar.estado;
        flow from perceberAlvos.alvos to executarTarefa2.alvos;
        flow from controlarVoo.cmdVel to traduzirParaDji.cmdVel;
        flow from supervisionar.falha to gerenciarTarefas.falha;
        flow from supervisionar.falha to registrar.falha;
        flow from traduzirParaDji.socketSaida to acionarSdk.socketEntrada;
        flow from acionarSdk.socketSaida to traduzirParaDji.socketEntrada;
        flow from acionarSdk.usbSaida to transmitirRadio.subidaEntrada;
        flow from transmitirRadio.descidaSaida to acionarSdk.usbEntrada;
        flow from transmitirRadio.subidaSaida to voar.comandos;
        flow from voar.telemetria to transmitirRadio.descidaEntrada;
        flow from traduzirParaDji.telemetria to estimarEstado.telemetria;
        flow from traduzirParaDji.telemetria to supervisionar.telemetria;
        flow from traduzirParaDji.quadro to perceberAlvos.quadro;
    }

    // ------------------------------------------------------------------ instâncias e alocação função -> componente
    part sistema : SistemaMissoesAutonomasN1;
    action funcaoGlobal : ExecutarTarefaAutonoma;

    allocate funcaoGlobal.interpretarComando to sistema.notebook.ros2.interfaceOperador;
    allocate funcaoGlobal.gerenciarTarefas to sistema.notebook.ros2.gerenciador;
    allocate funcaoGlobal.executarTarefa1 to sistema.notebook.ros2.tarefa1;
    allocate funcaoGlobal.executarTarefa2 to sistema.notebook.ros2.tarefa2;
    allocate funcaoGlobal.estimarEstado to sistema.notebook.ros2.estimacao;
    allocate funcaoGlobal.perceberAlvos to sistema.notebook.ros2.percepcao;
    allocate funcaoGlobal.controlarVoo to sistema.notebook.ros2.controle;
    allocate funcaoGlobal.supervisionar to sistema.notebook.ros2.supervisao;
    allocate funcaoGlobal.registrar to sistema.notebook.ros2.registro;
    allocate funcaoGlobal.traduzirParaDji to sistema.notebook.ros2.noPonte;
    allocate funcaoGlobal.acionarSdk to sistema.notebook.android.appPonte;
    allocate funcaoGlobal.transmitirRadio to sistema.radio;
    allocate funcaoGlobal.voar to sistema.drone;

    // ------------------------------------------------------------------ requisito -> função (matriz de rastreabilidade)
    satisfy Nivel0::p01 by funcaoGlobal.estimarEstado;
    satisfy Nivel0::p01 by funcaoGlobal.controlarVoo;
    satisfy Nivel0::p01 by funcaoGlobal.acionarSdk;
    satisfy Nivel0::p02 by funcaoGlobal.executarTarefa1;
    satisfy Nivel0::p02 by funcaoGlobal.estimarEstado;
    satisfy Nivel0::p02 by funcaoGlobal.controlarVoo;
    satisfy Nivel0::p03 by funcaoGlobal.executarTarefa1;
    satisfy Nivel0::p03 by funcaoGlobal.estimarEstado;
    satisfy Nivel0::p04 by funcaoGlobal.executarTarefa1;
    satisfy Nivel0::p04 by funcaoGlobal.controlarVoo;
    satisfy Nivel0::p04 by funcaoGlobal.gerenciarTarefas;
    satisfy Nivel0::p04 by funcaoGlobal.acionarSdk;
    satisfy Nivel0::p05 by funcaoGlobal.gerenciarTarefas;
    satisfy Nivel0::p05 by funcaoGlobal.estimarEstado;
    satisfy Nivel0::p05 by funcaoGlobal.executarTarefa1;
    satisfy Nivel0::p06 by funcaoGlobal.registrar;
    satisfy Nivel0::p06 by funcaoGlobal.gerenciarTarefas;
    satisfy Nivel0::p06 by funcaoGlobal.interpretarComando;
    satisfy Nivel0::p06 by funcaoGlobal.executarTarefa1;
    satisfy Nivel0::r07 by funcaoGlobal.supervisionar;
    satisfy Nivel0::r07 by funcaoGlobal.gerenciarTarefas;
    satisfy Nivel0::r07 by funcaoGlobal.acionarSdk;
    satisfy Nivel0::r01 by funcaoGlobal.gerenciarTarefas;
    satisfy Nivel0::r02 by funcaoGlobal.perceberAlvos;
    satisfy Nivel0::r03 by funcaoGlobal.executarTarefa2;
    satisfy Nivel0::r03 by funcaoGlobal.interpretarComando;
    satisfy Nivel0::r04 by funcaoGlobal.executarTarefa2;
    satisfy Nivel0::r04 by funcaoGlobal.perceberAlvos;
    satisfy Nivel0::r04 by funcaoGlobal.controlarVoo;
    satisfy Nivel0::r05 by funcaoGlobal.perceberAlvos;
    satisfy Nivel0::r05 by funcaoGlobal.estimarEstado;
    satisfy Nivel0::r06 by funcaoGlobal.executarTarefa2;
    satisfy Nivel0::r06 by funcaoGlobal.supervisionar;
    satisfy Nivel0::r08 by funcaoGlobal.interpretarComando;
    satisfy Nivel0::r08 by funcaoGlobal.registrar;
    satisfy Nivel0::r09 by funcaoGlobal.gerenciarTarefas;
    satisfy Nivel0::r09 by funcaoGlobal.registrar;
}
