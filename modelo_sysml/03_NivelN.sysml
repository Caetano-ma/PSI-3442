package NivelN {
    doc /* Nível n — implementação. Detalha a Tarefa 1 (Questão 1), os serviços comuns às duas tarefas e a ponte DJI.
           A Tarefa 2 (Questão 2), a visão computacional e o mapeamento local estão detalhados na segunda parte deste
           pacote ("Tarefa 2"); funções e módulos reutilizados entre as duas tarefas estão marcados com "reuso".

           Componentes caixa-preta (drone e rádio): não são decompostos; o drone é "explorado" pela interface do
           DJI Mobile SDK v5 (o que se lê, o que se comanda e os limites conhecidos). Nomes de chaves/APIs e valores
           marcados "verificar" devem ser confirmados na documentação oficial e na versão do SDK usada.

           Linguagens: nós ROS 2 em Python (rclpy), pacote ros2_ws/src/psi3442_tarefas, mensagens próprias em
           ros2_ws/src/psi3442_interfaces/msg; app ponte em Kotlin, android_ponte/.

           Justificativa da profundidade adotada: a decomposição para quando cada folha (i) corresponde a um único
           arquivo/classe, (ii) tem entradas e saídas tipadas com unidades e referencial definidos e (iii) pode ser
           verificada isoladamente por teste unitário ou ensaio listado em 04_Verificacao.sysml. Drone e rádio param
           no próprio componente, porque abaixo dele nada é observável nem alterável. */

    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import Comum::*;

    // =========================================================================================== caixas-pretas
    enum def AcaoPerdaSinal {
        enum pairar;
        enum pousar;
        enum retornarAoPonto;   // RTH depende de GNSS: inválido em ambiente interno (R07)
    }

    port def SdkControladorVoo {
        doc /* Recursos do controlador de voo expostos pelo SDK (FlightControllerKey e VirtualStickManager — verificar nomes). */
        out attribute velocidadeNorte : SpeedValue;     // KeyAircraftVelocity
        out attribute velocidadeLeste : SpeedValue;     // KeyAircraftVelocity
        out attribute velocidadeBaixo : SpeedValue;     // KeyAircraftVelocity
        out attribute altitude : LengthValue;           // KeyAltitude (relativa à decolagem)
        out attribute alturaToF : LengthValue;          // KeyUltrasonicHeight (sensor inferior)
        out attribute guinada : Real;                   // KeyAircraftAttitude (graus, bússola + IMU)
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
        doc /* Usado pela Tarefa 2. */
        out item video : QuadroCamera;                  // fluxo de vídeo da câmera principal
        in attribute anguloGimbal : Real;               // GimbalKey: rotação do gimbal
    }

    part def DroneN :> Nivel0::Drone {
        doc /* Exploração da caixa-preta: estabilização, estimativa de pose, decolagem e pouso automáticos ficam no
               firmware DJI; usamos leitura de velocidade/altura/guinada/estado, decolagem e pouso automáticos,
               controle virtual em velocidade e a ação em perda de sinal. O SDK não fornece posição local em
               ambiente interno: a trajetória é estimada pela integração das velocidades (ver EstimadorEstado). */
        port sdkVoo : SdkControladorVoo;
        port sdkBateria : SdkBateria;
        port sdkEnlace : SdkEnlace;
        port sdkPercepcao : SdkPercepcao;
        port sdkCamera : SdkCamera;
        attribute precisaoPairadoHorizontal : LengthValue = 0.3 [m];   // especificação DJI com posicionamento visual — verificar
        attribute precisaoPairadoVertical : LengthValue = 0.1 [m];     // idem — verificar
        attribute taxaControleVirtualMin : Real = 5.0;                   // Hz — verificar
        attribute taxaControleVirtualMax : Real = 25.0;                  // Hz — verificar
        attribute comprimentoComHelices : LengthValue = 0.298 [m];      // verificar no manual
        attribute larguraComHelices : LengthValue = 0.373 [m];          // verificar no manual
        attribute alturaTotal : LengthValue = 0.101 [m];                // verificar no manual
        attribute exigePisoTexturizado : Boolean = true;
    }

    part def RadioDjiN :> Nivel0::RadioDJI {
        doc /* Rádio-enlace obrigatório para o Mobile SDK (RC-N2 ou RC-N3). Fica ligado e conectado ao notebook por USB, repassado ao
               celular por cabo USB; os sticks não são usados. */
    }

    // =========================================================================================== contratos de interface
    interface def ContratoSdkControladorVoo {
        doc /* App ponte <-> controlador de voo, pelo caminho USB -> rádio -> enlace O4.
               Pré: aeronave conectada; controle virtual habilitado antes de enviar velocidades.
               Comandos de velocidade no referencial do solo (norte, leste, baixo), m/s.
               Latência não especificada pela DJI: medir em ensaio e registrar. Perda de enlace: a própria aeronave
               executa acaoPerdaSinal = pousar. */
        end appPonte : ~SdkControladorVoo;
        end aeronave : SdkControladorVoo;
    }

    interface def ContratoSocketPonte {
        doc /* Nó ponte (notebook) <-> app ponte (celular), TCP pelo Wi-Fi (nos testes sem drone: adb forward para o
               Android emulado). Mensagens JSON delimitadas por
               linha, com campo "tipo" (telemetria, cmd_vel, acao, heartbeat, erro). Telemetria a 10 Hz; cmd_vel a
               20 Hz; heartbeat a 1 Hz nos dois sentidos. Pós: sem mensagem do nó ponte por prazoWatchdog o app envia
               velocidade zero; sem heartbeat por prazoPerdaPonte o app comanda pouso automático (perdaPonte). */
        end ros : PortaSocket;
        end celular : PortaSocket;
        attribute porta : Integer = 5760;
        attribute prazoWatchdog : DurationValue = 0.2 [s];
        attribute prazoPerdaPonte : DurationValue = 2 [s];
    }

    interface def ContratoTopicoCmdVel {
        doc /* /dji/cmd_vel: velocidades no ReferencialLocal (m/s), saturadas pelo controle; QoS best effort,
               profundidade 1 (só o comando mais recente importa). */
        end publicador : TopicoCmdVel;
        end assinante : ~TopicoCmdVel;
        attribute vMaxHorizontal : SpeedValue = 0.3 [m/s];
        attribute vMaxVertical : SpeedValue = 0.3 [m/s];
        attribute taxa : Real = 10.0;   // Hz
    }

    interface def ContratoTopicoTelemetria {
        doc /* /dji/telemetria: unidades SI, referencial do solo, instante do relógio do Linux na recepção e instante
               do Android na leitura (permite medir latência). QoS best effort, profundidade 1. */
        end publicador : TopicoTelemetria;
        end assinante : ~TopicoTelemetria;
        attribute taxa : Real = 10.0;   // Hz
        attribute idadeMaxima : DurationValue = 0.3 [s];
    }

    // =========================================================================================== módulos de software
    part def ModuloSoftware {
        attribute arquivoCodigo : String;
    }

    // ---------------------------------------------------------------- app ponte (Kotlin, celular)
    part def GerenciadorConexaoSdk :> ModuloSoftware {
        doc /* Registra o app no SDK (chave de app, ativação online na primeira vez) e detecta a aeronave conectada. */
        attribute :>> arquivoCodigo = "android_ponte/app/src/celular/java/br/usp/psi3442/ponte/ConexaoSdk.kt";
    }
    part def LeitorTelemetria :> ModuloSoftware {
        doc /* Assina as chaves do SDK e monta amostras Telemetria a 10 Hz. */
        attribute :>> arquivoCodigo = "android_ponte/app/src/main/java/br/usp/psi3442/ponte/LeitorTelemetria.kt";
    }
    part def EmissorComandos :> ModuloSoftware {
        doc /* Converte cmd_vel do ReferencialLocal para norte/leste/baixo com psi0 e envia ao controle virtual a 20 Hz;
               executa decolagem e pouso; watchdog de 0,2 s envia velocidade zero; perda da ponte dispara pouso. */
        attribute :>> arquivoCodigo = "android_ponte/app/src/main/java/br/usp/psi3442/ponte/EmissorComandos.kt";
    }
    part def ConfiguradorSeguranca :> ModuloSoftware {
        doc /* Antes da decolagem: ação em perda de sinal = pousar; desabilita retorno por GNSS; limite de altura.
               Confirma por leitura das chaves. */
        attribute :>> arquivoCodigo = "android_ponte/app/src/main/java/br/usp/psi3442/ponte/ConfiguradorSeguranca.kt";
        attribute acaoPerdaSinal : AcaoPerdaSinal = AcaoPerdaSinal::pousar;
    }
    part def ServidorSocket :> ModuloSoftware {
        doc /* Servidor TCP do ContratoSocketPonte (JSON por linha, heartbeat). */
        attribute :>> arquivoCodigo = "android_ponte/app/src/main/java/br/usp/psi3442/ponte/ServidorSocket.kt";
    }

    part def LeitorCameraObstaculos :> ModuloSoftware {
        doc /* Tarefa 2. Quadros: MediaDataCenter.cameraStreamManager.addFrameListener(LEFT_OR_MAIN, NV21), 1 a cada
               0,2 s, reduzidos por amostragem (Nv21.kt) a <= 640 px de largura e codificados em JPEG (YuvImage).
               Distâncias: PerceptionManager.addObstacleDataListener -> ObstacleData.horizontalObstacleDistance (mm,
               a partir do nariz, sentido horário, passo horizontalAngleInterval — verificar). Gimbal em pitch 0°
               (GimbalKey.KeyRotateByAngle, ABSOLUTE_ANGLE) ao habilitar o controle virtual. APIs conferidas no jar do
               MSDK 5.20.1. Variante falsa: CenaFalsa.kt (traçado de raios) para testes sem aeronave. */
        attribute :>> arquivoCodigo = "android_ponte/app/src/celular/java/br/usp/psi3442/ponte/DroneDji.kt";
        attribute taxaQuadros : Real = 5.0;    // Hz
    }
    part def ServidorVideo :> ModuloSoftware {
        doc /* Canal de vídeo: TCP na porta do socket + 1; linha JSON de cabeçalho ("quadro", instante, largura, altura,
               bytes, pitch do gimbal) seguida do JPEG. Só o quadro mais recente é enviado (descarta os atrasados). */
        attribute :>> arquivoCodigo = "android_ponte/app/src/main/java/br/usp/psi3442/ponte/ServidorVideo.kt";
    }

    part def AppPonteDJIN :> Nivel1::AppPonteDJI {
        port sdkVoo : ~SdkControladorVoo;
        port sdkBateria : ~SdkBateria;
        port sdkEnlace : ~SdkEnlace;
        port sdkPercepcao : ~SdkPercepcao;
        port sdkCamera : ~SdkCamera;
        part gerenciadorConexao : GerenciadorConexaoSdk;
        part leitorTelemetria : LeitorTelemetria;
        part emissorComandos : EmissorComandos;
        part configuradorSeguranca : ConfiguradorSeguranca;
        part servidorSocket : ServidorSocket;
        part leitorCameraObstaculos : LeitorCameraObstaculos;
        part servidorVideo : ServidorVideo;
    }

    // ---------------------------------------------------------------- nós ROS 2 (Python)
    part def ClienteSocketPonte :> ModuloSoftware {
        doc /* Cliente TCP do ContratoSocketPonte; reconecta automaticamente. A perda da ponte aparece como
               ausência de /dji/telemetria e é tratada pela supervisão (telemetriaAtrasada). */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/cliente_socket_ponte.py";
    }
    part def ClienteVideo :> ModuloSoftware {
        doc /* Tarefa 2. Cliente do canal de vídeo (LeitorQuadros remonta cabeçalho + JPEG); o nó publica /dji/camera
               (sensor_msgs/Image) e converte "obstaculos" em /dji/obstaculos (LaserScan, anti-horário). */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/cliente_socket_ponte.py";
    }
    part def ConversorMensagens :> ModuloSoftware {
        doc /* JSON <-> mensagens psi3442_interfaces; publica /dji/telemetria; assina /dji/cmd_vel e /dji/acao. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_ponte_dji.py";
    }
    part def ParserComandos :> ModuloSoftware {
        doc /* Aceita só "executar tarefa 1", "executar tarefa 2" e "interromper"; publica /operador/comando. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_interface_operador.py";
    }
    part def PainelTerminal :> ModuloSoftware {
        doc /* Mostra tarefa, estado, vértice, cronômetro, x/y/z, velocidades, bateria e falhas (assina /tarefa/status, /falhas). */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/painel.py";
    }
    part def CarregadorConfig :> ModuloSoftware {
        doc /* Lê e valida o YAML (unidades SI, tolerâncias presentes, vértices coerentes com aresta e altura). */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/carregador_config.py";
    }
    part def SeletorTarefa :> ModuloSoftware {
        doc /* Executa ModosOperacao: ativa a tarefa pedida, recusa a Tarefa 2 antes da Tarefa 1 concluída em voo
               real, envia decolar/pousar por /dji/acao, repassa interrupções. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_gerenciador_tarefas.py";
    }
    part def PlanejadorTrajetoria :> ModuloSoftware {
        doc /* Setpoints [A, B, C, D, A] (abcd) ou [A, D, C, B, A] (adcb); fornece o setpoint do índice atual. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/planejador_trajetoria.py";
    }
    part def VerificadorTolerancia :> ModuloSoftware {
        doc /* dentro = |erro horizontal| <= tolHorizontal e |erro vertical| <= tolVertical e |v| <= vPairadoMax. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/verificador_tolerancia.py";
    }
    part def CronometroPermanencia :> ModuloSoftware {
        doc /* Relógio monotônico (tempo real). Conta enquanto o veredito é "dentro"; zera quando sai; emite
               PermanenciaConcluida aos 60 s contínuos; registra início, interrupções e duração de cada tentativa. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/cronometro_permanencia.py";
        attribute duracaoAlvo : DurationValue = 60 [s];
    }
    part def SupervisorTarefa1 :> ModuloSoftware {
        doc /* Executa a máquina de estados da Tarefa 1 e publica /setpoint e /tarefa/evento. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_tarefa1.py";
        exhibit state maquina : MaquinaEstadosTarefa1;
    }
    part def EstimadorEstado :> ModuloSoftware {
        doc /* Algoritmo: x, y por integração trapezoidal das velocidades norte/leste (posicionamento visual da DJI),
               a partir de A, convertidas ao ReferencialLocal com psi0; z pela altura ToF (reserva: altitude relativa).
               Origem e psi0 registrados na borda de subida de motoresLigados; no solo, com motores desligados, não há
               integração.
               Estado inválido se a amostra estiver velha ou o posicionamento visual inativo. A deriva da integração
               é o principal risco: validar com medição externa. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_estimacao_estado.py";
        attribute idadeMaxAmostra : DurationValue = 0.3 [s];
    }
    part def ControladorPosicao :> ModuloSoftware {
        doc /* Algoritmo: por eixo, v = saturacao(kp * erro, vMax). Pouso: descida em rampa até alturaInicioPouso,
               depois pouso automático da DJI; velocidade de toque lida da telemetria e registrada. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_controle_voo.py";
        attribute kp : Real = 0.8;                                  // 1/s — ajustar em ensaio
        attribute vMaxHorizontal : SpeedValue = 0.3 [m/s];
        attribute vMaxVertical : SpeedValue = 0.3 [m/s];
        attribute alturaInicioPouso : LengthValue = 0.3 [m];
    }
    part def MonitorFalhas :> ModuloSoftware {
        doc /* Tratamento de erros (tipo -> detecção -> reação):
               perdaEnlace                 -> conectado = false             -> aeronave pousa sozinha (failsafe); registra
               perdaPonte                  -> sem heartbeat > 2 s           -> app ponte comanda pouso; registra
               telemetriaAtrasada          -> amostra > prazoTelemetria      -> velocidade zero; persistindo, término seguro
               bateriaBaixa                -> em voo, carga < bateriaCritica -> término seguro (bateriaMinima só para iniciar)
               estimativaInvalida          -> estimador marca inválido       -> velocidade zero; persistindo, término seguro
               posicionamentoVisualInativo -> chave do SDK = false           -> término seguro
               desvioExcessivo             -> distância horizontal ao contorno do quadrado (ou altura acima de 1,80 m)
                                              > desvioMaximo                -> término seguro
               tempoTarefaExcedido         -> tempo > tempoMaxTarefa         -> término seguro
               comandoRejeitado            -> erro devolvido pelo SDK        -> antes do voo: volta a ocioso; em voo: término seguro
               Término seguro = pouso no local. Todos os eventos vão para /falhas e para o registro. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_supervisao.py";
        attribute prazoTelemetria : DurationValue = 0.5 [s];
        attribute desvioMaximo : LengthValue = 0.6 [m];
    }
    part def GravadorRosbag :> ModuloSoftware {
        doc /* ros2 bag record de todos os tópicos, um bag por execução do launch. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/launch/registro.launch.py";
    }
    part def ExportadorCsv :> ModuloSoftware {
        doc /* Converte o bag em CSV com colunas instante_s, tarefa, estado, vertice, x_m, y_m, z_m, vx_mps, vy_mps,
               vz_mps, dentro, permanencia_s, cmd_vx_mps, cmd_vy_mps, cmd_vz_mps, bateria_pct, evento, tipo_falha. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/ferramentas/exportar_csv.py";
    }

    part def InterfaceOperadorN :> Nivel1::InterfaceOperador {
        part parserComandos : ParserComandos;
        part painelTerminal : PainelTerminal;
    }
    part def GerenciadorTarefasN :> Nivel1::GerenciadorTarefas {
        part carregadorConfig : CarregadorConfig;
        part seletorTarefa : SeletorTarefa;
    }
    part def Tarefa1N :> Nivel1::Tarefa1VooFamiliarizacao {
        part planejador : PlanejadorTrajetoria;
        part verificador : VerificadorTolerancia;
        part cronometro : CronometroPermanencia;
        part supervisorTarefa1 : SupervisorTarefa1;
    }
    part def EstimacaoEstadoN :> Nivel1::EstimacaoEstado {
        part estimador : EstimadorEstado;
    }
    part def ControleVooN :> Nivel1::ControleVoo {
        part controlador : ControladorPosicao;
    }
    part def SupervisaoSegurancaN :> Nivel1::SupervisaoSeguranca {
        part monitorFalhas : MonitorFalhas;
    }
    part def RegistroN :> Nivel1::Registro {
        part gravadorBag : GravadorRosbag;
        part exportadorCsv : ExportadorCsv;
    }
    part def NoPonteDJIN :> Nivel1::NoPonteDJI {
        part clienteSocket : ClienteSocketPonte;
        part conversorMensagens : ConversorMensagens;
        part clienteVideo : ClienteVideo;
    }

    part def AplicacaoROS2N :> Nivel1::AplicacaoROS2N1 {
        part :>> interfaceOperador : InterfaceOperadorN;
        part :>> gerenciador : GerenciadorTarefasN;
        part :>> tarefa1 : Tarefa1N;
        part :>> estimacao : EstimacaoEstadoN;
        part :>> controle : ControleVooN;
        part :>> supervisao : SupervisaoSegurancaN;
        part :>> registro : RegistroN;
        part :>> noPonte : NoPonteDJIN;
        part :>> tarefa2 : Tarefa2N;
        part :>> visao : VisaoComputacionalN;
        part :>> mapeamento : MapeamentoLocalN;
        interface contratoCmdVel : ContratoTopicoCmdVel connect controle.pubCmdVel to noPonte.subCmdVel;
        interface contratoTelemetria : ContratoTopicoTelemetria connect noPonte.pubTelemetria to estimacao.subTelemetria;
    }

    part def DispositivoMovelN :> Nivel1::DispositivoMovelN1 {
        part :>> appPonte : AppPonteDJIN;
    }

    part def NotebookLinuxN :> Nivel1::NotebookLinuxN1 {
        part :>> ros2 : AplicacaoROS2N;
    }

    part def SistemaMissoesN :> Nivel1::SistemaMissoesAutonomasN1 {
        doc /* As conexões abaixo são lógicas (SDK); fisicamente passam por USB, rádio e enlace O4. */
        part :>> notebook : NotebookLinuxN;
        part :>> celular : DispositivoMovelN;
        interface contratoSocket : ContratoSocketPonte connect notebook.ros2.noPonte.socket to celular.appPonte.socket;
        part :>> radio : RadioDjiN;
        part :>> drone : DroneN;
        interface contratoSdk : ContratoSdkControladorVoo connect celular.appPonte.sdkVoo to drone.sdkVoo;
        connect celular.appPonte.sdkBateria to drone.sdkBateria;
        connect celular.appPonte.sdkEnlace to drone.sdkEnlace;
        connect celular.appPonte.sdkPercepcao to drone.sdkPercepcao;
        connect celular.appPonte.sdkCamera to drone.sdkCamera;
    }

    // =========================================================================================== configuração proposta (Tarefa 1)
    item configTarefa1 : ConfiguracaoTarefa1 {
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
        :>> vToqueMax = 0.50 [m/s];
        :>> vDeslocamentoMax = 0.30 [m/s];
        :>> bateriaMinimaPercentual = 30.0;
        :>> bateriaCriticaPercentual = 15.0;
        :>> alturaMinDecolagem = 0.50 [m];
        :>> tempoMaxPreparacao = 10 [s];
        :>> tempoMaxDecolagem = 20 [s];
        :>> persistenciaFalha = 1 [s];
        :>> tempoMaxTarefa = 600 [s];
        :>> tempoEstabilizacao = 2 [s];
    }

    // =========================================================================================== ações folha e ciclo
    action def LerAmostra { out tel : Telemetria; }
    action def AtualizarEstimativa { in tel : Telemetria; out estado : EstadoEstimado; }
    action def ObterSetpoint { out setpoint : Setpoint; }
    action def AvaliarTolerancia { in estado : EstadoEstimado; in setpoint : Setpoint; out veredito : VereditoTolerancia; }
    action def AtualizarCronometro { in veredito : VereditoTolerancia; out concluido : Boolean; }
    action def DetectarFalhas { in tel : Telemetria; in estado : EstadoEstimado; out falha : Boolean; }
    action def AvancarMaquinaEstados {
        in veredito : VereditoTolerancia;
        in concluido : Boolean;
        in falha : Boolean;
        out discreto : ComandoDiscreto;
    }
    action def CalcularVelocidade { in estado : EstadoEstimado; in setpoint : Setpoint; out comando : ComandoVelocidade; }
    action def EnviarComandos { in comando : ComandoVelocidade; in discreto : ComandoDiscreto; }
    action def GravarRegistro { in tel : Telemetria; in estado : EstadoEstimado; in veredito : VereditoTolerancia; }

    action def CicloControle {
        doc /* Cadeia executada a cada amostra de telemetria (10 Hz), em tempo real, distribuída entre nós ROS 2:
               telemetria -> estado -> veredito/cronômetro/falhas -> máquina de estados -> cmd_vel -> app ponte.
               A latência total da cadeia é medida pelos instantes registrados em cada mensagem. */
        action ler : LerAmostra;
        action estimar : AtualizarEstimativa;
        action setpoint : ObterSetpoint;
        action avaliar : AvaliarTolerancia;
        action cronometrar : AtualizarCronometro;
        action detectar : DetectarFalhas;
        action avancar : AvancarMaquinaEstados;
        action calcular : CalcularVelocidade;
        action enviar : EnviarComandos;
        action gravar : GravarRegistro;

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

    // =========================================================================================== máquina de estados da Tarefa 1 (P06)
    state def MaquinaEstadosTarefa1 {
        doc /* Refina o modo Nivel1::ModosOperacao::tarefa1.
               Estados exigidos por P06: decolagem, deslocamento, permanência, retorno, pouso e falha.
               As condições de disparo de cada evento estão nas definições dos sinais (Comum). */
        attribute indiceVertice : Integer;     // 0=A, 1=B, 2=C, 3=D
        attribute ultimoIndice : Integer = 3;

        entry; then aguardando;

        state aguardando;
        transition ativada first aguardando accept ExecutarTarefa1 then preparando;

        state preparando { entry action verificarPonteConexaoBateriaESeguranca; }
        transition preparado first preparando accept PreparacaoConcluida then emVoo;
        transition desistir first preparando accept FalhaDetectada then aguardando;

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
        transition interrompida first emVoo accept InterromperTarefa then pousoSeguro;

        state pousando {
            entry action descerEmRampa;
            do action monitorarToque;
        }
        transition pousou first pousando accept PousoConfirmado then concluida;
        transition interrompidaNoPouso first pousando accept InterromperTarefa then pousoSeguro;

        state pousoSeguro {
            doc /* Falha ou interrupção: pouso no local (nunca retorno por GNSS). */
            entry action pousarNoLocal;
        }
        transition pousouEmFalha first pousoSeguro accept PousoConfirmado then abortada;

        state concluida { entry action publicarTarefaConcluidaEFecharRegistro; }
        state abortada { entry action publicarAbortoEFecharRegistro; }
    }


    // =========================================================================================== Tarefa 2 (Questão 2)
    part def DetectorYolo :> ModuloSoftware {
        doc /* R02. YOLOv8 nano (5 classes = cores conhecidas), treinado com imagens sintéticas por randomização de
               domínio (ferramentas/gerar_dataset_baloes.py, treinar_yolo.py) e exportado em ONNX (opset 12); executado
               pelo módulo dnn do OpenCV, sem PyTorch em voo. Entrada 416x416 com letterbox; NMS 0,45. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_visao_computacional.py";
        attribute limiarConfianca : Real = 0.5;
    }
    part def GeometriaCamera :> ModuloSoftware {
        doc /* Pinhole com campo de visão horizontal da config (resolução lida do quadro). Direção = centro da caixa
               (azimute no ReferencialLocal, elevação do raio); distância câmera->centro = r / sen(atan(r_px / f)),
               não confiável com a caixa cortada na borda (descartada no mapa). */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_visao_computacional.py";
    }
    part def MedidorProximidade :> ModuloSoftware {
        doc /* R04/R05. De perto o balão não cabe numa caixa: na linha central da imagem, o trecho contínuo da cor
               central dá as bordas esquerda/direita; meia-largura angular a -> D = r / sen(a), azimute = média das
               bordas. Precisão ~0,4 mm/px a 0,2 m. Trecho cortado pela borda -> só limite superior (-D). Também
               fornece a cor dominante no centro (HSV), usada na confirmação do alvo. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_visao_computacional.py";
    }
    part def FusaoBaloes :> ModuloSoftware {
        doc /* Cada detecção vira um ponto (pose estimada + deslocamento da câmera + D na direção medida); associação
               por cor e janela max(0,45 m; 3σ; 0,15 D); média ponderada por 1/D²; CANDIDATO -> CONFIRMADO com
               observacoesMin; DESTRUIDO por evento. Balões com > 20 observações viram marcos: o resíduo de uma
               detecção de perto realinha o mapa inteiro (ganho 0,05), compensando a deriva da posição integrada. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_mapeamento_local.py";
    }
    part def GradeOcupacao :> ModuloSoftware {
        doc /* Grade 2D de 0,20 m a partir de /dji/obstaculos (acertos e células livres por raio); células de balões
               mapeados não contam como obstáculo fixo. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_mapeamento_local.py";
        attribute resolucao : LengthValue = 0.2 [m];
    }
    part def PlanejadorVarredura :> ModuloSoftware {
        doc /* Grade de pontos de busca em serpentina dentro do volume (passoBusca), começando na decolagem; em cada
               ponto, giro de 360° em passos de 45° com pausa para a visão. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_tarefa2.py";
    }
    part def PlanejadorRotas :> ModuloSoftware {
        doc /* R06. Menor rota num grafo de visibilidade (Dijkstra): nós em 8 direções em volta de cada balão do mapa,
               arestas onde nenhum balão bloqueia o segmento (folga = r + meia-diagonal do envelope 0,239 m + margem:
               0,50 m cor não alvo, 0,30 m outra cor-alvo, 0,15 m candidato ainda não confirmado); replanejada a cada passo
               se um balão recém-mapeado bloqueia o trecho restante. Ponto de aproximação: 8 direções em volta do alvo,
               livres de obstáculos e de outros balões. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_tarefa2.py";
    }
    part def EstimadorDistanciaAlvo :> ModuloSoftware {
        doc /* R04/R05. d = |c - p_frente| - r, p_frente = pose estimada + rEnvelope na direção do nariz. O centro c do
               alvo é (1) refinado no ponto de espera pela média das detecções de perto e (2) reancorado a cada quadro
               pela medida de proximidade (filtro 0,5; salto máx. 0,40 m), junto com os pontos de espera e final.
               Assim a permanência segue o balão (inclusive em movimento) e não a posição integrada, que deriva.
               A contagem só corre com medida direta recente QUE CONCORDA com o alvo (a até 0,10 m do centro; perto
               de um fantasma do mapa a câmera pode estar vendo outro balão da mesma cor); um limite superior só vale
               se garantir d <= 5 cm. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_tarefa2.py";
    }
    part def SupervisorTarefa2 :> ModuloSoftware {
        doc /* Executa a máquina de estados da Tarefa 2 a 10 Hz; publica /setpoint (com guinada) e /tarefa/evento
               (BALAO_DESTRUIDO com o centro medido, que realinha o mapa). Impede contagem duplicada: destruídos,
               descartados e inalcançáveis são ignorados na seleção. */
        attribute :>> arquivoCodigo = "ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_tarefa2.py";
        exhibit state maquina : MaquinaEstadosTarefa2;
    }

    part def VisaoComputacionalN :> Nivel1::VisaoComputacional {
        part detector : DetectorYolo;
        part geometria : GeometriaCamera;
        part proximidade : MedidorProximidade;
    }
    part def MapeamentoLocalN :> Nivel1::MapeamentoLocal {
        part fusao : FusaoBaloes;
        part grade : GradeOcupacao;
    }
    part def Tarefa2N :> Nivel1::Tarefa2Baloes {
        part varredura : PlanejadorVarredura;
        part rotas : PlanejadorRotas;
        part estimadorDistancia : EstimadorDistanciaAlvo;
        part cronometro : CronometroPermanencia;     // reuso da Tarefa 1 (mesma classe, tempo real)
        part supervisorTarefa2 : SupervisorTarefa2;
    }

    // ---------------------------------------------------------------- ambiente de teste (fora do sistema de voo)
    part def SimuladorGazebo {
        doc /* Gazebo Harmonic 8 + ros_gz: sala gerada com semente (gerar_sala_t2.py), drone caixa-preta com
               VelocityControl, câmera 640x480 e sensor de distâncias 360° (no lugar da percepção DJI); app ponte
               simulado com o mesmo protocolo. O AvaliadorT2 usa a verdade do simulador só para validar (R05) e grava
               avaliacao.csv/resumo.yaml. Ambiente sem sudo: conda RoboStack (ambiente/instalar_gazebo.sh). */
        attribute geradorSala : String = "ros2_ws/src/psi3442_gazebo/psi3442_gazebo/gerar_sala_t2.py";
        attribute avaliador : String = "ros2_ws/src/psi3442_gazebo/psi3442_gazebo/avaliador_t2.py";
        attribute appPonteSimulado : String = "ros2_ws/src/psi3442_gazebo/psi3442_gazebo/app_ponte_gazebo.py";
    }
    part simulador : SimuladorGazebo;

    item configTarefa2 : ConfiguracaoTarefa2 {
        doc /* Valores de config/tarefas.yaml (seções tarefa2 e visao). Margens (R06) definidas antes dos testes. */
        :>> coresAlvo = ("vermelho", "azul");
        :>> coresConhecidas = ("vermelho", "azul", "verde", "amarelo", "roxo");
        :>> alturaBusca = 1.4 [m];
        :>> passoBusca = 2.2 [m];
        :>> raioBalao = 0.13 [m];
        :>> raioEnvelopeFrontal = 0.149 [m];
        :>> distanciaAlvo = 0.025 [m];
        :>> distanciaMaxima = 0.05 [m];
        :>> tempoPermanencia = 60 [s];
        :>> distanciaAproximacao = 0.60 [m];
        :>> vAproximacaoFinal = 0.08 [m/s];
        :>> margemObstaculos = 0.40 [m];
        :>> margemNaoAlvo = 0.50 [m];
        :>> margemOutrosAlvos = 0.30 [m];
        :>> observacoesMin = 3;
        :>> tempoConfirmacao = 4 [s];
        :>> tempoSemConfirmacao = 1 [s];
        :>> tentativasPorBalao = 3;
        :>> tempoMaxTarefa = 1500 [s];
        :>> campoVisaoHorizontal = 82.1;
        :>> limiarConfianca = 0.5;
    }

    state def MaquinaEstadosTarefa2 {
        doc /* Refina o modo Nivel1::ModosOperacao::tarefa2 (R03, R04, R07). Falha ou interrupção em qualquer estado
               de voo -> pousoSeguro (pouso no local, nunca retorno por GNSS). */
        entry; then aguardando;

        state aguardando;
        transition ativada first aguardando accept ExecutarTarefa2 then preparando;
        state preparando { entry action verificarPonteConexaoBateriaESeguranca; }
        transition preparado first preparando accept PreparacaoConcluida then emVoo;
        transition desistir first preparando accept FalhaDetectada then aguardando;

        state emVoo {
            entry; then decolando;
            state decolando { entry action enviarDecolagem; }
            transition decolou first decolando accept DecolagemConcluida then subindo;
            state subindo { do action subirAteAlturaBusca; }
            transition naAltura first subindo accept AlturaAtingida then girando;

            state girando { do action girar360ComPausas; }
            transition alvoNoGiro first girando accept AlvoConfirmadoNoMapa then aproximando;
            transition giroFeito first girando accept GiroCompleto then deslocando;
            transition semMaisPontos first girando accept VarreduraCompleta then retornando;

            state deslocando { do action seguirRotaAteProximoPonto; }
            transition alvoNoCaminho first deslocando accept AlvoConfirmadoNoMapa then aproximando;
            transition chegouPonto first deslocando accept PontoBuscaAtingido then girando;

            state aproximando { do action seguirRotaAteEspera; }
            transition naEspera first aproximando accept PontoEsperaAtingido then confirmando;
            transition bloqueado first aproximando accept AlvoInalcancavel then girando;

            state confirmando { do action refinarCentroComDeteccoesDePerto; }
            transition confirmado first confirmando accept ConfirmacaoVisual then aproximacaoFinal;
            transition descartado first confirmando accept SemConfirmacao then girando;

            state aproximacaoFinal { do action rampaAteDistanciaAlvoReancorando; }
            transition naFaixa first aproximacaoFinal accept FaixaAtingida then permanecendo;

            state permanecendo {
                entry action zerarCronometro;
                do action manterDistanciaReancorando;
            }
            transition reiniciar first permanecendo accept SaiuDaFaixa then permanecendo;
            transition destruido first permanecendo accept BalaoDestruido then afastando;
            transition contato first permanecendo accept ContatoEstimado then afastando;

            state afastando { do action voltarAoPontoDeEspera; }
            transition novaTentativa first afastando accept AfastamentoConcluido then confirmando;
            transition proximoAlvo first afastando accept AlvoConfirmadoNoMapa then aproximando;
            transition retomarBusca first afastando accept GiroCompleto then girando;

            state retornando { do action seguirRotaAteDecolagem; }
        }
        transition iniciarPouso first emVoo accept Estabilizado then pousando;
        transition falhaEmVoo first emVoo accept FalhaDetectada then pousoSeguro;
        transition interrompida first emVoo accept InterromperTarefa then pousoSeguro;

        state pousando { entry action descerEmRampa; do action monitorarToque; }
        transition pousou first pousando accept PousoConfirmado then concluida;
        transition interrompidaNoPouso first pousando accept InterromperTarefa then pousoSeguro;
        state pousoSeguro { entry action pousarNoLocal; }
        transition pousouEmFalha first pousoSeguro accept PousoConfirmado then abortada;
        state concluida { entry action publicarResumoDosBaloes; }
        state abortada { entry action publicarAbortoEFecharRegistro; }
    }

    action def AdquirirQuadro { out quadro : QuadroCamera; }
    action def DetectarBaloes { in quadro : QuadroCamera; in estado : EstadoEstimado; out alvos : Alvos; }
    action def AtualizarMapa { in alvos : Alvos; in obstaculos : Obstaculos; in estado : EstadoEstimado; out mapa : MapaLocal; }
    action def EstimarDistanciaAlvo { in alvos : Alvos; in estado : EstadoEstimado; out distancia : LengthValue; }
    action def DecidirTarefa2 { in mapa : MapaLocal; in distancia : LengthValue; in estado : EstadoEstimado; out setpoint : Setpoint; }

    action def CicloPercepcaoDecisao {
        doc /* Malha fechada exigida na seção 5: imagem -> percepção -> decisão -> comando -> movimento -> nova imagem.
               Quadros a 5 Hz; decisão e controle a 10 Hz; cmd_vel a 20 Hz no app ponte. */
        action adquirir : AdquirirQuadro;
        action detectar : DetectarBaloes;
        action estimar : AtualizarEstimativa;
        action mapear : AtualizarMapa;
        action medir : EstimarDistanciaAlvo;
        action decidir : DecidirTarefa2;
        action calcular : CalcularVelocidade;
        action enviar : EnviarComandos;

        first start then adquirir;
        first adquirir then estimar;
        first estimar then detectar;
        first detectar then mapear;
        first mapear then medir;
        first medir then decidir;
        first decidir then calcular;
        first calcular then enviar;
        first enviar then done;

        flow from adquirir.quadro to detectar.quadro;
        flow from estimar.estado to detectar.estado;
        flow from detectar.alvos to mapear.alvos;
        flow from detectar.alvos to medir.alvos;
        flow from estimar.estado to medir.estado;
        flow from mapear.mapa to decidir.mapa;
        flow from medir.distancia to decidir.distancia;
        flow from decidir.setpoint to calcular.setpoint;
        flow from calcular.comando to enviar.comando;
    }

    // =========================================================================================== instâncias e rastreabilidade
    part sistemaN : SistemaMissoesN;
    action ciclo : CicloControle;

    allocate ciclo.ler to sistemaN.notebook.ros2.noPonte.conversorMensagens;
    allocate ciclo.estimar to sistemaN.notebook.ros2.estimacao.estimador;
    allocate ciclo.setpoint to sistemaN.notebook.ros2.tarefa1.planejador;
    allocate ciclo.avaliar to sistemaN.notebook.ros2.tarefa1.verificador;
    allocate ciclo.cronometrar to sistemaN.notebook.ros2.tarefa1.cronometro;
    allocate ciclo.detectar to sistemaN.notebook.ros2.supervisao.monitorFalhas;
    allocate ciclo.avancar to sistemaN.notebook.ros2.tarefa1.supervisorTarefa1;
    allocate ciclo.calcular to sistemaN.notebook.ros2.controle.controlador;
    allocate ciclo.enviar to sistemaN.notebook.ros2.noPonte.clienteSocket;
    allocate ciclo.enviar to sistemaN.celular.appPonte.emissorComandos;
    allocate ciclo.gravar to sistemaN.notebook.ros2.registro.gravadorBag;

    // refinamento nível 1 -> nível n
    allocate Nivel1::funcaoGlobal.interpretarComando to sistemaN.notebook.ros2.interfaceOperador.parserComandos;
    allocate Nivel1::funcaoGlobal.interpretarComando to sistemaN.notebook.ros2.interfaceOperador.painelTerminal;
    allocate Nivel1::funcaoGlobal.gerenciarTarefas to sistemaN.notebook.ros2.gerenciador.carregadorConfig;
    allocate Nivel1::funcaoGlobal.gerenciarTarefas to sistemaN.notebook.ros2.gerenciador.seletorTarefa;
    allocate Nivel1::funcaoGlobal.executarTarefa1 to sistemaN.notebook.ros2.tarefa1.planejador;
    allocate Nivel1::funcaoGlobal.executarTarefa1 to sistemaN.notebook.ros2.tarefa1.verificador;
    allocate Nivel1::funcaoGlobal.executarTarefa1 to sistemaN.notebook.ros2.tarefa1.cronometro;
    allocate Nivel1::funcaoGlobal.executarTarefa1 to sistemaN.notebook.ros2.tarefa1.supervisorTarefa1;
    allocate Nivel1::funcaoGlobal.estimarEstado to sistemaN.notebook.ros2.estimacao.estimador;
    allocate Nivel1::funcaoGlobal.controlarVoo to sistemaN.notebook.ros2.controle.controlador;
    allocate Nivel1::funcaoGlobal.supervisionar to sistemaN.notebook.ros2.supervisao.monitorFalhas;
    allocate Nivel1::funcaoGlobal.registrar to sistemaN.notebook.ros2.registro.gravadorBag;
    allocate Nivel1::funcaoGlobal.registrar to sistemaN.notebook.ros2.registro.exportadorCsv;
    allocate Nivel1::funcaoGlobal.traduzirParaDji to sistemaN.notebook.ros2.noPonte.clienteSocket;
    allocate Nivel1::funcaoGlobal.traduzirParaDji to sistemaN.notebook.ros2.noPonte.conversorMensagens;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.gerenciadorConexao;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.leitorTelemetria;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.emissorComandos;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.configuradorSeguranca;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.servidorSocket;

    // requisito -> módulo (Questão 1)
    satisfy Nivel0::p01 by sistemaN.notebook.ros2.estimacao.estimador;
    satisfy Nivel0::p01 by sistemaN.notebook.ros2.controle.controlador;
    satisfy Nivel0::p01 by sistemaN.celular.appPonte.emissorComandos;
    satisfy Nivel0::p02 by sistemaN.notebook.ros2.tarefa1.planejador;
    satisfy Nivel0::p02 by sistemaN.notebook.ros2.estimacao.estimador;
    satisfy Nivel0::p02 by sistemaN.notebook.ros2.controle.controlador;
    satisfy Nivel0::p03 by sistemaN.notebook.ros2.tarefa1.verificador;
    satisfy Nivel0::p03 by sistemaN.notebook.ros2.tarefa1.cronometro;
    satisfy Nivel0::p03 by sistemaN.notebook.ros2.tarefa1.supervisorTarefa1;
    satisfy Nivel0::p04 by sistemaN.notebook.ros2.controle.controlador;
    satisfy Nivel0::p04 by sistemaN.notebook.ros2.tarefa1.supervisorTarefa1;
    satisfy Nivel0::p04 by sistemaN.celular.appPonte.emissorComandos;
    satisfy Nivel0::p05 by sistemaN.notebook.ros2.gerenciador.carregadorConfig;
    satisfy Nivel0::p05 by sistemaN.notebook.ros2.tarefa1.verificador;
    satisfy Nivel0::p05 by sistemaN.notebook.ros2.tarefa1.cronometro;
    satisfy Nivel0::p06 by sistemaN.notebook.ros2.registro.gravadorBag;
    satisfy Nivel0::p06 by sistemaN.notebook.ros2.registro.exportadorCsv;
    satisfy Nivel0::p06 by sistemaN.notebook.ros2.tarefa1.supervisorTarefa1;
    satisfy Nivel0::r07 by sistemaN.notebook.ros2.supervisao.monitorFalhas;
    satisfy Nivel0::r07 by sistemaN.celular.appPonte.configuradorSeguranca;
    satisfy Nivel0::r07 by sistemaN.celular.appPonte.emissorComandos;

    // --------------------------------------------------------------------------------------- Tarefa 2
    action cicloT2 : CicloPercepcaoDecisao;
    allocate cicloT2.adquirir to sistemaN.celular.appPonte.leitorCameraObstaculos;
    allocate cicloT2.adquirir to sistemaN.notebook.ros2.noPonte.clienteVideo;
    allocate cicloT2.detectar to sistemaN.notebook.ros2.visao.detector;
    allocate cicloT2.detectar to sistemaN.notebook.ros2.visao.geometria;
    allocate cicloT2.estimar to sistemaN.notebook.ros2.estimacao.estimador;
    allocate cicloT2.mapear to sistemaN.notebook.ros2.mapeamento.fusao;
    allocate cicloT2.mapear to sistemaN.notebook.ros2.mapeamento.grade;
    allocate cicloT2.medir to sistemaN.notebook.ros2.visao.proximidade;
    allocate cicloT2.medir to sistemaN.notebook.ros2.tarefa2.estimadorDistancia;
    allocate cicloT2.decidir to sistemaN.notebook.ros2.tarefa2.supervisorTarefa2;
    allocate cicloT2.calcular to sistemaN.notebook.ros2.controle.controlador;
    allocate cicloT2.enviar to sistemaN.celular.appPonte.emissorComandos;

    allocate Nivel1::funcaoGlobal.executarTarefa2 to sistemaN.notebook.ros2.tarefa2.varredura;
    allocate Nivel1::funcaoGlobal.executarTarefa2 to sistemaN.notebook.ros2.tarefa2.rotas;
    allocate Nivel1::funcaoGlobal.executarTarefa2 to sistemaN.notebook.ros2.tarefa2.estimadorDistancia;
    allocate Nivel1::funcaoGlobal.executarTarefa2 to sistemaN.notebook.ros2.tarefa2.cronometro;
    allocate Nivel1::funcaoGlobal.executarTarefa2 to sistemaN.notebook.ros2.tarefa2.supervisorTarefa2;
    allocate Nivel1::funcaoGlobal.perceberAlvos to sistemaN.notebook.ros2.visao.detector;
    allocate Nivel1::funcaoGlobal.perceberAlvos to sistemaN.notebook.ros2.visao.geometria;
    allocate Nivel1::funcaoGlobal.perceberAlvos to sistemaN.notebook.ros2.visao.proximidade;
    allocate Nivel1::funcaoGlobal.mapear to sistemaN.notebook.ros2.mapeamento.fusao;
    allocate Nivel1::funcaoGlobal.mapear to sistemaN.notebook.ros2.mapeamento.grade;
    allocate Nivel1::funcaoGlobal.traduzirParaDji to sistemaN.notebook.ros2.noPonte.clienteVideo;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.leitorCameraObstaculos;
    allocate Nivel1::funcaoGlobal.acionarSdk to sistemaN.celular.appPonte.servidorVideo;

    // requisito -> módulo (Questão 2)
    satisfy Nivel0::r01 by sistemaN.notebook.ros2.gerenciador.carregadorConfig;
    satisfy Nivel0::r02 by sistemaN.notebook.ros2.visao.detector;
    satisfy Nivel0::r02 by sistemaN.notebook.ros2.visao.geometria;
    satisfy Nivel0::r03 by sistemaN.notebook.ros2.tarefa2.supervisorTarefa2;
    satisfy Nivel0::r03 by sistemaN.notebook.ros2.tarefa2.varredura;
    satisfy Nivel0::r04 by sistemaN.notebook.ros2.tarefa2.estimadorDistancia;
    satisfy Nivel0::r04 by sistemaN.notebook.ros2.tarefa2.cronometro;
    satisfy Nivel0::r04 by sistemaN.notebook.ros2.visao.proximidade;
    satisfy Nivel0::r05 by sistemaN.notebook.ros2.visao.proximidade;
    satisfy Nivel0::r05 by sistemaN.notebook.ros2.estimacao.estimador;
    satisfy Nivel0::r06 by sistemaN.notebook.ros2.tarefa2.rotas;
    satisfy Nivel0::r06 by sistemaN.notebook.ros2.mapeamento.grade;
    satisfy Nivel0::r06 by sistemaN.notebook.ros2.supervisao.monitorFalhas;
    satisfy Nivel0::r08 by sistemaN.notebook.ros2.interfaceOperador.painelTerminal;
    satisfy Nivel0::r08 by sistemaN.notebook.ros2.registro.exportadorCsv;
    satisfy Nivel0::r09 by sistemaN.notebook.ros2.gerenciador.carregadorConfig;
    satisfy Nivel0::r09 by sistemaN.notebook.ros2.registro.gravadorBag;
}
