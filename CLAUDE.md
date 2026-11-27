# PSI3442 — P2 2026 — Sistema de Missões Autônomas com DJI Mini 4 Pro

Contexto para continuar o trabalho em outra máquina. Responder sempre em **português**.

## O projeto

Segunda prova de PSI3442 (Projeto de Sistemas Embarcados, Poli-USP), enunciado v2.5 de 15/11/2026
(`P2_PSI3442_2026_v2_5.docx`, **fora do repositório** por ser documento do professor — pedir ao usuário se precisar).
Duas questões, chamadas aqui de tarefas:

- **Tarefa 1** (Questão 1, P01–P06): decolar a 1,80 m, quadrado A-B-C-D de 1,50 m, pairar 60 s contínuos em cada
  vértice, voltar a A e pousar suavemente. Precisa ser demonstrada em voo real antes da Tarefa 2.
- **Tarefa 2** (Questão 2, R01–R09): identificar balões de cores-alvo e permanecer a 0 < d ≤ 5 cm por 60 s.

Prazos: entrega intermediária **27/11/2026** (pronta em `entregas/2026-11-27_intermediaria/`); entrega final e
demonstração em voo real **04/12/2026**. Equipe: Caetano Maciel Anibali (13681130); outros integrantes talvez depois.

## Arquitetura decidida (não mudar sem o usuário pedir)

- O drone é dado; o problema é de **software**. O alvo da decomposição são as **tarefas**; drone e rádio são caixas-pretas.
- **Notebook Linux com ROS 2 Jazzy** (Mint 22 / Ubuntu 24.04) roda toda a lógica em nós ROS 2 (Python/rclpy):
  interface do operador, gerenciador de tarefas, Tarefa 1, Tarefa 2, estimação de estado, controle de voo, supervisão
  e segurança, registro (rosbag2 + CSV), percepção visual (T2), mapeamento local grosseiro (T2), nó ponte ROS 2 ↔ DJI.
- **App ponte** em Kotlin (`android_ponte/`) com o **DJI Mobile SDK v5.20.1** atrás da interface `Drone`; fala com o
  ROS 2 por TCP (porta 5760, JSON por linha, heartbeat). Duas variantes: `emulador` (drone falso, sem SDK, roda no
  Android emulado do notebook com `adb forward`) e `celular` (SDK real, ARM64).
- **Verificado em 27/11** no manifesto do app de exemplo da DJI: o SDK fala com o controle pelo **modo acessório USB**
  (o controle é o hospedeiro USB). Um emulador num notebook não consegue isso, então **o voo real usa o app no celular
  ligado ao controle**, e o notebook se conecta a ele pelo Wi-Fi (`host_ponte:=<IP>` no launch). O emulador serve para
  testar o app inteiro contra o ROS 2 sem drone. Modelo SysML e diagramas atualizados em 27/11 (pedido do usuário):
  celular/tablet Android fora do notebook, Wi-Fi até o ROS 2, USB até o rádio; tablet Android também serve (iPad não).
- **Visão computacional** (Tarefa 2): nó `VisaoComputacional` (antes "Percepção Visual") sobre os quadros da câmera
  repassados pelo celular; publica `/alvos` para a Tarefa 2 e o mapeamento local.
- O operador só envia `executar tarefa 1`, `executar tarefa 2` ou `interromper`; ninguém pilota.
- **Controle remoto:** verificado nas notas do MSDK v5 que o Mini 4 Pro só funciona com **DJI RC N2 ou RC N3**
  (SDK ≥ 5.13.0; atual 5.20.1); DJI RC 2 não é suportado e não há conexão direta celular ↔ drone. O usuário diz não ter
  controle → hipótese H7: o kit do laboratório tem um (confirmar com os docentes). É o maior bloqueio do projeto.
- Sem GNSS em ambiente interno: posição = integração das velocidades do posicionamento visual da DJI (deriva é risco);
  altura = sensor ToF. Referencial local: origem em A no piso, x para B, y para D, z para cima.
- P05 aprovado pelo usuário: ±0,10 m vertical, ±0,30 m horizontal, 0,15 m/s para "pairado", 0,50 m/s no toque.
- Balões da Tarefa 2: estáticos (forma de fixação irrelevante).

## Estrutura e comandos

| Caminho | Conteúdo |
|---|---|
| `diagramas/gerar_diagramas.py` | Diagramas funcionais de nível 0 e 1 (estilo dos diagramas do usuário) → `nivel_0.png`, `nivel_1.png` |
| `modelo_sysml/00_Comum.sysml` … `04_Verificacao.sysml` | Modelo SysML 2.0: tipos/tópicos/requisitos, nível 0, nível 1, nível n, casos de verificação |
| `modelo_sysml/executar_modelo.py` | Valida o modelo no kernel SysML e exporta 14 vistas para `vistas/`; gera `Modelo.ipynb` |
| `modelo_sysml/gerar_matriz.py` | Matriz de rastreabilidade da Tarefa 1 + checagem de consistência entre níveis (sai com erro se houver furo) |
| `modelo_sysml/abrir_jupyter.sh` | Abre o modelo no JupyterLab |
| `ensaios/roteiro_voo_tarefa1.md` | Procedimentos dos ensaios em voo T01–T04 |
| `entregas/2026-11-27_intermediaria/` | `relatorio.md` → `gerar_pdf.py` → `relatorio.pdf` + ZIP do Moodle |
| `ambiente/instalar_ambiente.sh` | Recria o ambiente conda `sysml` (kernel SysML v2 0.63.1, JupyterLab, weasyprint) |
| `ros2_ws/` | Workspace ROS 2 (ciclo C2): `psi3442_interfaces` (10 mensagens) e `psi3442_tarefas` (nós, simulador, launch, CSV, testes). Ver `ros2_ws/README.md`; os 8 ajustes em relação ao modelo foram refletidos no SysML em 27/11 |
| `ros2_ws/src/psi3442_gazebo/` + `ros2_ws/docker/simular_gazebo.ps1` | Tarefa 1 no Gazebo Harmonic (imagem `psi3442-gazebo`, `Dockerfile.gazebo`), janela via WSLg; drone caixa-preta com VelocityControl; app ponte simulado com o mesmo protocolo TCP |
| `ros2_ws/docker/ensaio_t10.sh` | Compila e faz o ensaio T10 integrado (launch + simulador + bag + CSV) na imagem `ros:jazzy-ros-base` |
| `android_ponte/` | App ponte (C3): variantes `emulador` e `celular`, testes JVM (protocolo, T09, integração), `ensaio_emulador.sh` (Tarefa 1 de ponta a ponta com o app no emulador e o ROS 2 real). Ver `android_ponte/README.md` |
| `ensaios/teste_eixos.py` | T00: confere o eixo norte/leste do controle virtual com a aeronave real, antes do T01 |
| `contexto_claude/memoria/` | Memórias do Claude da máquina anterior (ver `contexto_claude/LEIA-ME.md`) |

```bash
bash ambiente/instalar_ambiente.sh                                   # uma vez por máquina
PY=~/miniforge3/envs/sysml/bin/python
cd modelo_sysml && $PY executar_modelo.py && python3 gerar_matriz.py  # depois de editar o modelo
$PY diagramas/gerar_diagramas.py                                      # depois de editar os diagramas
$PY entregas/2026-11-27_intermediaria/gerar_pdf.py                    # regenera PDF e ZIP
cd ros2_ws/src/psi3442_tarefas && python3 -m pytest -q test           # 76 testes da lógica, sem ROS 2
docker run --rm -v "$(pwd):/repo:ro" ros:jazzy-ros-base bash /repo/ros2_ws/docker/ensaio_t10.sh   # da raiz
cd android_ponte && ./gradlew testEmuladorDebugUnitTest assembleEmuladorDebug assembleCelularDebug
bash android_ponte/ensaio_emulador.sh rapido                          # da raiz: emulador + ROS 2 + tarefa 1
```

Máquinas: **atual (27/11): notebook Linux Mint 22** com ROS 2 Jazzy nativo (`/opt/ros/jazzy`, sem `ros-jazzy-ros-gz`),
conda `sysml` em `~/miniforge3`, JDK 21, Android SDK em `~/Android/Sdk` (plataformas 34/35, emulador, AVD `psi3442`
x86_64 com KVM) e `gh` autenticado. O Windows 11 usado em 24/11 tinha:
Nela, a lógica é testada com Python 3.12 + pytest, e a compilação e os nós rodam no Docker Desktop (imagem
`ros:jazzy-ros-base`). O WSL tem Ubuntu 26.04, onde não há pacotes do Jazzy. Não há `gh`: o push usa o
gerenciador de credenciais do Git para Windows.
A lógica fica em classes sem ROS (testáveis em qualquer lugar); o nó rclpy fica no `main()` do mesmo arquivo.

Pegadinhas do SysML v2 Pilot já encontradas: `interface` é palavra reservada; `flow` não liga o parâmetro da própria
ação (usar `bind`); item dentro de item é `item`, não `attribute`; não nomear partes como o `subject` dos requisitos
(o subject se chama `sujeito`). Visões de interconexão grandes ficam ilegíveis — usar `--view=tree --style=LR`.

## Convenções de trabalho

- **Publicar no GitHub após cada mudança** (https://github.com/Caetano-ma/PSI-3442, branch `main`, público).
  Não alterar o git config. Commit com
  `git -c user.name=Caetano-ma -c user.email=281951699+Caetano-ma@users.noreply.github.com commit ...`
  e push com `git -c credential.helper= -c credential.helper='!gh auth git-credential' push` (requer `gh auth login`).
  Na máquina Windows (sem `gh`), `git push origin main` pela ferramenta Bash funciona via Git Credential Manager;
  pela ferramenta PowerShell falha com "terminal prompts disabled".
- Quando o usuário fornecer diagramas/modelos próprios, **adaptar minimamente** (manter blocos, layout e cores);
  ele rejeitou redesenhos do zero.
- Instruções condicionais ("se X estiver errado, aponte e pare") devem ser seguidas literalmente.
- Valores e nomes de API marcados "verificar" no modelo ainda não foram confirmados — não apresentá-los como fatos.

## Como o usuário roda a simulação (e o que confundiu em 24/11)

São dois terminais, e a correspondência com o voo real é esta:
- **Terminal 1:** `.\ros2_ws\docker\simular_gazebo.ps1 rapido` no Windows, ou
  `ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py` no Linux. Ele sobe o sistema ROS 2 de verdade, que é o mesmo
  do voo, e também o Gazebo com o `app_ponte_gazebo`, que substitui o app Kotlin, o SDK, o controle e o drone.
  No voo real, o terminal 1 vira `adb forward tcp:5760 tcp:5760` seguido de `ros2 launch psi3442_tarefas sistema.launch.py`.
- **Terminal 2:** o operador, igual no voo real. No Windows é `docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh`;
  no Linux, `ros2 run psi3442_tarefas interface_operador`. Nele se digita `executar tarefa 1`.
- O **painel** (`operador.sh painel` / `ros2 run psi3442_tarefas painel`) **só mostra o estado e não aceita digitação**.
  O usuário o confundiu com o operador e achou que o terminal tinha travado.
- **A simulação não faz nada até receber o comando**, a menos que se passe `comando_automatico:=true`.
  O usuário esperou 2 min com o drone parado em A por isso.
- **Defeito corrigido** (commit `dfada22`): o `interface_operador --comando` publicava assim que encontrava *qualquer*
  assinante. O rosbag é descoberto antes do gerenciador, e o comando se perdia, o que afetava o `comando_automatico` e
  o `ensaio_t10.sh`. Agora o envio espera o `gerenciador_tarefas` estar descoberto e casado com o publicador.
- Ao ouvir "o drone está parado", inspecionar o contêiner antes de responder: `/tarefa/status`, `ps`, `~/.ros/log/latest/`.

## Plano para a máquina Linux Mint (pedido do usuário em 24/11)

O usuário vai mudar o Claude para um notebook **Linux Mint** e quer que ele faça **todo o restante** lá. Ordem sugerida:

1. **Ambiente.** Mint 22 tem base Ubuntu 24.04 (noble); no repositório apt do ROS, usar `UBUNTU_CODENAME`, não o
   codinome do Mint.
   - Instalar `ros-jazzy-desktop` (ou `ros-base`), `ros-jazzy-ros-gz`, `python3-colcon-common-extensions` e `python3-pytest`.
   - Rodar `bash ambiente/instalar_ambiente.sh` para o conda `sysml`.
   - Restaurar as memórias de `contexto_claude/` (ver o LEIA-ME).
2. **Revalidar** com `colcon build && colcon test`, que deu 79 testes nos 3 pacotes em 24/11. Depois, rodar o Gazebo
   nativo com `ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py config:=…/tarefas_teste_rapido.yaml`.
3. **Modelo SysML.** Refletir no modelo os 8 ajustes da seção "Ajustes de implementação" de `ros2_ws/README.md`.
   Em seguida, rodar `executar_modelo.py` e `gerar_matriz.py`.
4. **C1, viabilidade da ponte.** Instalar o Android Studio, o SDK e o emulador e testar o MSDK v5 no emulador.
   - As bibliotecas nativas do SDK são ARM: verificar se a imagem do emulador traduz ARM.
   - Testar o controle por USB passthrough e a ativação da App Key.
   - Se falhar, usar o celular Android físico.
5. **C3, app ponte Kotlin.**
   - Módulos: ConexaoSdk, LeitorTelemetria, EmissorComandos, ConfiguradorSeguranca, ServidorSocket.
   - Seguir o protocolo do cabeçalho de `no_ponte_dji.py`.
   - Isolar o SDK da DJI atrás de uma interface, com uma implementação falsa no lugar. Assim o app pode ser testado
     contra o ROS 2 sem drone; a referência de comportamento é `simulador_cinematico.py`.
   - Depois, testes em solo, T09 e latência.
6. **C4 e C5:** voos T01–T04 com o usuário e a Tarefa 2, conforme as pendências abaixo.

Dependem do usuário:
- o controle RC-N2/RC-N3 do kit (H7);
- o cadastro de desenvolvedor DJI e a App Key, que fica ligada ao nome do pacote do app;
- a confirmação de `bateria_critica_pct` = 15 %.

## Pendências (em 27/11/2026)

Feito em 27/11 (Linux Mint): workspace ROS 2 revalidado nativo (76 testes); 8 ajustes refletidos no SysML; app ponte
(C3) com 16 testes JVM; variante `celular` compila e empacota com o SDK 5.20.1; Tarefa 1 completa de ponta a ponta
com o app no emulador (AOSP, drone falso) e o ROS 2 real: concluída, telemetria a 10 Hz, erro vertical máx. 0,069 m.

Para voar a Tarefa 1 no drone físico, depende do usuário:
1. Controle RC-N2 ou RC-N3 do kit (H7) — sem ele o SDK não alcança o Mini 4 Pro.
2. Celular Android ARM64 (Android 7+) e cabo para o controle.
3. Conta de desenvolvedor DJI e App Key do tipo Mobile SDK com o pacote `br.usp.psi3442.ponte`, em
   `~/.gradle/gradle.properties` como `DJI_API_KEY=…`; internet no celular na 1ª execução (registro).
4. Confirmar `bateria_critica_pct` = 15 %.

Depois, em ordem: instalar `app-celular-debug.apk` (adb por USB), modo "falso" no celular com o ROS 2 pelo Wi-Fi
(`host_ponte:=<IP>`), testes em solo (registro do SDK, telemetria, ação em perda de sinal = pousar, comando rejeitado,
perda da ponte), **T00** (`ensaios/teste_eixos.py`), T01–T04 (`ensaios/roteiro_voo_tarefa1.md`), ajuste de kp e
latência, demonstração. Ciclo C5 (Tarefa 2), vídeo, README final e relatório continuam pendentes.
