# Workspace ROS 2 — Sistema de Missões Autônomas (ciclo C2)

Implementação, em ROS 2 Jazzy, da Tarefa 1 e dos serviços comuns às duas tarefas, conforme o nível n
(`modelo_sysml/03_NivelN.sysml`). Cada arquivo corresponde a uma folha do modelo. A lógica de cada módulo é uma
classe sem dependência de ROS 2, testável com `pytest` em qualquer máquina. O nó rclpy fica na função `main()`
do mesmo arquivo.

| Pacote | Conteúdo |
|---|---|
| `psi3442_interfaces` | 10 mensagens (`msg/`), unidades SI |
| `psi3442_tarefas` | nós, simulador, configuração (`config/`), launch, exportador de CSV e testes |
| `psi3442_gazebo` | simulação da Tarefa 1 no Gazebo Harmonic: mundo, app ponte simulado e launch |

## Nós e módulos

| Executável (`ros2 run psi3442_tarefas …`) | Arquivo | Módulo do nível n |
|---|---|---|
| `interface_operador` | `no_interface_operador.py` | ParserComandos |
| `painel` | `painel.py` | PainelTerminal |
| `gerenciador_tarefas` | `no_gerenciador_tarefas.py` (+ `carregador_config.py`) | SeletorTarefa, CarregadorConfig |
| `tarefa1` | `no_tarefa1.py` (+ `planejador_trajetoria.py`, `verificador_tolerancia.py`, `cronometro_permanencia.py`) | SupervisorTarefa1, PlanejadorTrajetoria, VerificadorTolerancia, CronometroPermanencia |
| `estimacao_estado` | `no_estimacao_estado.py` | EstimadorEstado |
| `controle_voo` | `no_controle_voo.py` | ControladorPosicao |
| `supervisao` | `no_supervisao.py` | MonitorFalhas |
| `ponte_dji` | `no_ponte_dji.py` (+ `cliente_socket_ponte.py`) | ConversorMensagens, ClienteSocketPonte |
| `simulador_ponte` | `simulador_cinematico.py` | substitui o app ponte + drone nos ensaios sem voo |
| — | `launch/registro.launch.py`, `ferramentas/exportar_csv.py` | GravadorRosbag, ExportadorCsv |

## Compilar e executar (Linux com ROS 2 Jazzy)

```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build && source install/setup.bash

# terminal 1: sistema completo (com o app ponte: adb forward tcp:5760 tcp:5760)
ros2 launch psi3442_tarefas sistema.launch.py
#   ou com o simulador cinemático no lugar do app ponte e do drone:
ros2 launch psi3442_tarefas sistema.launch.py simulador:=true
#   ensaio rápido (5 s por vértice; só no simulador):
ros2 launch psi3442_tarefas sistema.launch.py simulador:=true \
    config:=$(ros2 pkg prefix psi3442_tarefas)/share/psi3442_tarefas/config/tarefas_teste_rapido.yaml

# terminal 2: painel        terminal 3: comandos do operador
ros2 run psi3442_tarefas painel
ros2 run psi3442_tarefas interface_operador        # digite: executar tarefa 1 | interromper

# depois (Ctrl+C no terminal 1 fecha o bag): CSV de evidência
python3 install/psi3442_tarefas/share/psi3442_tarefas/ferramentas/exportar_csv.py ~/psi3442_bags/execucao_<data>
```

Falhas podem ser injetadas no simulador, por exemplo
`simulador_args:="--rejeitar decolar"`, `"--vies-norte 0.01"` (deriva), `"--silencio 30 5"` (ponte calada por 5 s),
`"--sem-posicionamento-visual-em 20"` e `"--bateria-inicial 31"`.

A conclusão da Tarefa 1 com `simulador:=false` fica registrada em `~/.psi3442/progresso.json`. Só esse registro
libera `executar tarefa 2`; conclusões no simulador não contam.

## Testes

```bash
cd ros2_ws/src/psi3442_tarefas && python3 -m pytest -q test     # sem ROS 2 (precisa de pytest e pyyaml)
cd ros2_ws && colcon test && colcon test-result --verbose         # com ROS 2
```

| Teste do modelo | Arquivo | O que verifica |
|---|---|---|
| T05 (P05) | `test/test_cronometro_permanencia.py` | 40 s dentro, uma amostra fora, 60 s dentro: só conclui 60 s depois do reinício |
| T07 (R07) | `test/test_monitor_falhas.py` | reação de cada TipoFalha; em malha fechada: perda da ponte, comando rejeitado, bateria crítica e posicionamento visual inativo terminam em pouso no local |
| T08 (P02) | `test/test_estimacao_estado.py` | conversão de referencial e integração: erro < 1 mm em 10 s para vários psi0 |
| T10 (R03) | `test/test_gerenciador_tarefas.py` | só `executar tarefa 1` leva a `concluida` (60 s por vértice, ordem A-B-C-D e A-D-C-B, pouso suave em A); Tarefa 2 recusada antes da Tarefa 1 em voo real |
| — | `test/test_modulos.py` | configuração, planejador, verificador, controle, protocolo/socket, parser, CSV |

Os testes de malha fechada (`test/sistema_simulado.py`) ligam as mesmas classes dos nós ao simulador com relógio
injetado, passando pela codificação JSON real da ponte. A missão completa simulada leva menos de 1 s.

Sem Linux (por exemplo, no Windows), o workspace compila e é testado na imagem oficial `ros:jazzy-ros-base`.
O script abaixo também faz o ensaio integrado T10 com o simulador e exporta bag e CSV:

```bash
docker run --rm -v "$(pwd):/repo:ro" ros:jazzy-ros-base bash /repo/ros2_ws/docker/ensaio_t10.sh
```

## Simulação no Gazebo (Tarefa 1)

O pacote `psi3442_gazebo` simula a Tarefa 1 no Gazebo Harmonic, a versão que acompanha o Jazzy.
A aplicação ROS 2 roda inteira e sem mudança; só o lado do drone é substituído:

- **Mundo** (`worlds/sala_tarefa1.sdf`):
  - sala com piso, fitas sob o quadrado e as marcas A (vermelho), B (verde), C (azul) e D (amarelo);
  - régua vertical em A, com 1,70 m, 1,80 m e 1,90 m;
  - um cilindro translúcido em cada vértice com a tolerância de P05 (raio de 0,30 m, ±0,10 m em torno de 1,80 m).
- **Aeronave**: o modelo `mini4pro` tem as dimensões aproximadas do Mini 4 Pro e é tratado como **caixa-preta**,
  como no resto da arquitetura. Não há hélices nem firmware simulados. O sistema `VelocityControl` do Gazebo
  executa a velocidade pedida, e a gravidade do corpo fica desligada, como se o firmware sustentasse a aeronave.
- **App ponte simulado** (`app_ponte_gazebo`):
  - usa o mesmo protocolo TCP do app Kotlin, com os mesmos watchdogs, decolagem e pouso automáticos e resposta
    de 1ª ordem do simulador cinemático;
  - executa o movimento no Gazebo e mede a telemetria na odometria do Gazebo (tempo de simulação);
  - o nariz aponta para o leste (guinada 90°), o que exercita a conversão com ψ₀.

No Windows, com o Docker Desktop, a janela aparece pelo WSLg:

```powershell
.\ros2_ws\docker\simular_gazebo.ps1 rapido                      # constrói a imagem na 1ª vez (~4 min)
docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh          # digite: executar tarefa 1
docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh painel   # painel (opcional)
```

Opções: `rapido` (5 s por vértice), `comando_automatico:=true` (envia "executar tarefa 1" após 15 s),
`gui:=false` (sem janela), `app_args:="--vies-norte 0.01"` (deriva, para estudar H5).
Ctrl+C encerra e exporta o CSV para `simulacoes\`. No Linux com Jazzy e `ros-jazzy-ros-gz`, basta
`ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py`.

Resultado verificado em 24/11, com 5 s por vértice:

- a missão foi do comando ao pouso, com toque a 0,39 m/s;
- o modelo terminou no Gazebo a 1 cm de A;
- o fator de tempo real foi 0,999.

A renderização é por software (`LIBGL_ALWAYS_SOFTWARE=1`), suficiente para esta sala.

## Protocolo da ponte (ContratoSocketPonte)

TCP na porta 5760, JSON UTF-8, uma mensagem por linha, com o campo `tipo`. A especificação completa dos campos
está no cabeçalho de `no_ponte_dji.py`, que o app ponte em Kotlin (ciclo C3) deve seguir.
O simulador (`simulador_cinematico.py`) é a implementação de referência do lado do app:

- conversão do `cmd_vel` local para norte/leste com `psi0_graus`;
- watchdog de 0,2 s: sem `cmd_vel`, velocidade zero;
- 2 s sem heartbeat em voo: pouso automático;
- a resposta `erro` quando o SDK rejeita um comando.

## Ajustes de implementação em relação ao modelo SysML

Refletidos no modelo em 27/11/2026 (`00_Comum`, `02_Nivel1`, `03_NivelN`), validado com `executar_modelo.py` e
`gerar_matriz.py`.

1. **Assinaturas a mais.** A Tarefa 1 também assina `/dji/telemetria`, para as checagens da preparação e para
   `emVoo`/`motoresLigados` em `DecolagemConcluida` e `PousoConfirmado`. O gerenciador assina `/dji/telemetria` e
   `/estado`, para aceitar comandos, montar o painel e encerrar o término seguro.
2. **Comandos discretos.** A tarefa não publica em `/dji/acao`: pede a ação ao gerenciador por `/tarefa/evento`
   (tipo `SOLICITA_ACAO`), e só ele envia ao SDK. As falhas chegam à tarefa pelo gerenciador, que publica
   `/tarefa/ativa = 0` e comanda o pouso.
3. **Campos novos nas mensagens.**
   - `Telemetria`: `controle_virtual_ativo` e `acao_perda_sinal`, que confirmam a preparação por leitura.
   - `EstadoEstimado`: `psi0_graus` e `motivo_invalido`.
   - `ComandoVelocidade`: `psi0_graus`, para que o app converta ao referencial do solo.
   - `Setpoint`: `ativo` (falso durante a decolagem e o pouso automáticos).
   - `StatusTarefa` e `EventoTarefa`: campos detalhados para o painel e o CSV.
4. **Origem e psi0.** São registrados na borda de subida de `motoresLigados`; no solo, com os motores
   desligados, não há integração.
5. **Parâmetros novos no YAML.**
   - `bateria_critica_pct` = 15 %: limite para o término seguro em voo. `bateria_minima_pct` = 30 % passa a
     ser só a condição para iniciar; com um limite único de 30 %, a tarefa abortaria logo após decolar com 30 %.
   - `altura_min_decolagem_m`, `tempo_max_preparacao_s`, `tempo_max_decolagem_s` e `persistencia_falha_s`.
6. **Desvio excessivo.** É a distância horizontal ao contorno do quadrado ou o excesso de altura acima de 1,80 m.
   Assim, a descida vertical de um pouso no local fora de A não dispara a falha de novo.
7. **Interrupção durante o pouso final.** A tarefa vai para `pousoSeguro` e termina `abortada`, não
   `concluida`.
8. **Registro.** Um bag por execução do launch (o modelo dizia um bag por tarefa).
