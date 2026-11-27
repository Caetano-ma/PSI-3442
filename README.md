# PSI3442 — P2 2026 — Missões autônomas com o DJI Mini 4 Pro

Equipe: **Caetano Maciel Anibali (nº USP 13681130)**.
Enunciado: *Segunda Prova — PSI3442*, v2.5 de 15/11/2026 (documento dos docentes, não incluído no repositório).

- **Tarefa 1 (Questão 1, P01–P06):** decolar a 1,80 m, percorrer o quadrado A-B-C-D de 1,50 m, pairar 60 s contínuos
  em cada vértice, voltar a A e pousar suavemente.
- **Tarefa 2 (Questão 2, R01–R09):** varrer a sala, mapear os balões, aproximar de cada balão de cor-alvo até
  0 < d ≤ 5 cm e pairar ali 60 s contínuos. O balão passa a "destruído", fica no mapa e é ignorado no resto da missão.

O operador só envia `executar tarefa 1`, `executar tarefa 2` ou `interromper`. Ninguém pilota.

## Arquitetura

```
notebook Linux (ROS 2 Jazzy)  ──Wi-Fi/TCP 5760 (JSON) + 5761 (vídeo)──  celular Android (app ponte, DJI MSDK 5.20.1)
  interface do operador, gerenciador,                                      │ USB (modo acessório)
  Tarefa 1, Tarefa 2, estimação, controle,                                 controle remoto RC-N2/RC-N3 ── enlace O4 ── Mini 4 Pro
  supervisão, visão computacional (YOLOv8n/ONNX),
  mapeamento local, registro (rosbag2 + CSV), nó ponte DJI
```

- O drone e o rádio são **caixas-pretas**. São explorados só pelo que o SDK expõe: velocidades, altura, guinada,
  estados, decolagem e pouso automáticos, controle virtual em velocidade, câmera e distâncias de obstáculos.
- Toda a lógica roda em nós ROS 2 (Python). Ela fica em classes sem ROS, testáveis com pytest; o nó rclpy fica no
  `main()` de cada arquivo.
- O app ponte (Kotlin) esconde o SDK atrás da interface `Drone`. Há duas implementações:
  - `DroneDji`: aeronave real;
  - `DroneFalso`: cinemático, com câmera sintética, para o emulador e o modo "falso" do celular.
- Sem GNSS em ambiente interno:
  - posição: integração das velocidades do posicionamento visual da DJI (a deriva é um risco);
  - altura: sensor ToF.
- Na Tarefa 2, a distância ao balão é **medida pela câmera** (largura do balão na imagem). Ela é usada para
  reancorar o alvo a cada quadro, de modo que a permanência siga o balão e não a posição integrada.

Modelo SysML 2.0 (níveis 0, 1 e n das duas tarefas) em [`modelo_sysml/`](modelo_sysml). Matrizes de rastreabilidade
em [`modelo_sysml/rastreabilidade/`](modelo_sysml/rastreabilidade). Relatório e apresentação em
[`entregas/2026-12-04_final/`](entregas/2026-12-04_final).

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `modelo_sysml/` | `00_Comum` … `04_Verificacao.sysml`, `executar_modelo.py` (valida e exporta as vistas), `gerar_matriz.py` (matrizes Q1/Q2 e consistência entre níveis) |
| `diagramas/` | Diagramas funcionais de nível 0 e 1 |
| `ros2_ws/src/psi3442_interfaces` | 14 mensagens ROS 2 (telemetria, estado, setpoint, eventos, alvos, mapa…) |
| `ros2_ws/src/psi3442_tarefas` | Nós, `config/tarefas.yaml` (R01), launch, ferramentas (CSV, métricas, dados sintéticos, treino YOLO), testes |
| `ros2_ws/src/psi3442_gazebo` | Mundos/gerador de sala, app ponte simulado, avaliador da Tarefa 2 (verdade do simulador), launch das duas tarefas |
| `android_ponte/` | App ponte Kotlin (variantes `emulador` e `celular`), testes JVM, `ensaio_emulador.sh` |
| `ensaios/` | Roteiro de voo (T00–T04 e Tarefa 2), `teste_eixos.py`, resultados de simulação |
| `ambiente/` | Scripts de instalação (conda `sysml`, Gazebo sem sudo, venv do YOLO) |

## Instalação (Ubuntu 24.04 / Linux Mint 22)

```bash
# ROS 2 Jazzy do sistema (voo real e testes): https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
sudo apt install ros-jazzy-ros-base python3-colcon-common-extensions python3-pytest python3-opencv
cd ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build && source install/setup.bash

# Gazebo Harmonic + ros_gz SEM sudo (conda RoboStack; compila em ros2_ws/install_gz)
bash ambiente/instalar_gazebo.sh          # ou, com sudo: sudo apt install ros-jazzy-ros-gz

bash ambiente/instalar_ambiente.sh        # modelo SysML (kernel SysML v2 0.63.1 + JupyterLab + weasyprint)
bash ambiente/instalar_yolo.sh            # só para retreinar o detector

# App ponte: JDK 21 + Android SDK (plataforma 35). App Key da DJI em ~/.gradle/gradle.properties: DJI_API_KEY=...
cd android_ponte && ./gradlew assembleCelularDebug     # app/build/outputs/apk/celular/debug/app-celular-debug.apk
```

Versões usadas:

| Componente | Versão |
|---|---|
| ROS 2 | Jazzy (sistema e RoboStack) |
| Gazebo | Harmonic, gz-sim 8.10.0 |
| DJI Mobile SDK | 5.20.1 |
| Kotlin / AGP | conforme `android_ponte/build.gradle.kts` |
| Python | 3.12 (sistema) e 3.14 (RoboStack) |
| OpenCV (inferência) | 4.6 (sistema) |
| Treino do detector | ultralytics 8.4.220, torch 2.15.0 (CPU) |
| Kernel SysML v2 | 0.63.1 |

## Executar na simulação (Gazebo)

Os resultados de simulação usam o **relógio do simulador** e estão separados dos de voo real (`ensaios/simulacao/`).

**Terminal 1**: sobe o Gazebo e o mesmo sistema ROS 2 do voo; o app ponte simulado substitui app, SDK, controle e drone.
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate ros_gz && source ros2_ws/install_gz/setup.bash
ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py                       # Tarefa 1
ros2 launch psi3442_gazebo tarefa2_gazebo.launch.py semente:=1 baloes:=6  # Tarefa 2: sala aleatória (semente registrada)
```
- `gui:=false` roda sem janela.
- `config:=…/tarefas_teste_rapido.yaml` encurta as permanências para 5 s.
- `comando_automatico:=true` envia o comando sozinho.
- Na Tarefa 2, o avaliador grava `~/.ros/psi3442_sala_t2/avaliacao.csv` e `resumo.yaml`, com a distância **verdadeira**
  (só para validar; ela nunca chega ao algoritmo, conforme o R05).

**Terminal 2**: o operador, igual ao voo real. Digite `executar tarefa 1`, `executar tarefa 2` ou `interromper`.
```bash
ros2 run psi3442_tarefas interface_operador
```

**Terminal 3** (opcional): o painel do R08. Ele **só mostra** estado, alvo, distância, cronômetro, eventos e falhas;
não aceita digitação.
```bash
ros2 run psi3442_tarefas painel
```

A simulação fica parada até receber o comando, a não ser com `comando_automatico:=true`.

Depois de cada ensaio, gere o CSV de evidência e as métricas da seção 7:
```bash
python3 ros2_ws/src/psi3442_tarefas/ferramentas/exportar_csv.py ~/psi3442_bags/<execucao> -o ensaio.csv
python3 ros2_ws/src/psi3442_tarefas/ferramentas/analisar_ensaio.py ensaio.csv [--avaliacao avaliacao.csv]
```

## Executar no drone real

Pré-requisitos (dependem da equipe e dos docentes):
- controle **RC-N2 ou RC-N3**: o Mini 4 Pro não é suportado pelo MSDK com o DJI RC 2;
- celular Android ARM64;
- App Key da DJI para o pacote `br.usp.psi3442.ponte`;
- notebook e celular na mesma rede Wi-Fi.

1. Instale `app-celular-debug.apk` no celular e ligue-o ao controle por USB. Abra o app e toque em **Iniciar (dji)**.
2. **Terminal 1** (notebook):
   ```bash
   ros2 launch psi3442_tarefas sistema.launch.py host_ponte:=<IP do celular>
   ```
3. **Terminal 2**: `ros2 run psi3442_tarefas interface_operador`, depois `executar tarefa 1`.
   A Tarefa 2 só é aceita depois da Tarefa 1 concluída em voo real.
4. Antes do primeiro voo, faça os testes em solo e o **T00** (`ensaios/teste_eixos.py`), que confere o eixo
   norte/leste do controle virtual. Depois, siga `ensaios/roteiro_voo_tarefa1.md` (T01–T04 e os ensaios da Tarefa 2).

Para testar o celular sem a aeronave, use **Iniciar (falso)**: o drone é cinemático e a câmera mostra uma sala
sintética com balões. Para testar tudo no notebook, use o emulador Android: `bash android_ponte/ensaio_emulador.sh rapido`.

## Testes

```bash
cd ros2_ws/src/psi3442_tarefas && python3 -m pytest -q test   # lógica das duas tarefas (malha fechada sintética)
cd ros2_ws/src/psi3442_gazebo && python3 -m pytest -q test    # gerador de sala, avaliador, app ponte simulado
cd android_ponte && ./gradlew testEmuladorDebugUnitTest       # app ponte (protocolo, watchdog, vídeo, obstáculos)
cd modelo_sysml && ~/miniforge3/envs/sysml/bin/python executar_modelo.py && python3 gerar_matriz.py
```

## Situação (o que está validado e o que não está)

| Item | Teste sem voo | Simulação (Gazebo) | Voo real |
|---|---|---|---|
| Tarefa 1 | ✔ pytest | ✔ concluída com 4 × 60 s | pendente (depende do controle RC-N2/N3 e da App Key) |
| Tarefa 2 | ✔ pytest (deriva, balão em movimento, falhas) | ver `ensaios/simulacao/` | pendente |
| App ponte com o SDK real | ✔ compila contra o MSDK 5.20.1; testes JVM | — | pendente: APIs de câmera, obstáculos e gimbal ainda não exercitadas com a aeronave |

Valores marcados "verificar" no código e no modelo ainda não foram confirmados com a aeronave. Entre eles:
- o campo de visão do fluxo ao vivo;
- a unidade e o sentido do `ObstacleData`;
- o eixo roll/pitch do controle virtual;
- o envelope frontal com hélices.

## Uso de inteligência artificial

O projeto foi desenvolvido com o **Claude Code** (Anthropic; modelos Claude Opus). Os prompts relevantes, os
artefatos gerados e as correções feitas estão no relatório final (seção "Uso de IA"), e as decisões de projeto
registradas em `CLAUDE.md`. A equipe responde pela consistência e pela validação.
