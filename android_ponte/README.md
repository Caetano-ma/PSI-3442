# App ponte DJI (ciclos C3 e C5)

App Android (Kotlin) que liga o nó `ponte_dji` do ROS 2 à aeronave pelo ContratoSocketPonte. Usa dois canais:
- **TCP 5760**: JSON por linha (telemetria, comandos, heartbeat, erros, obstáculos);
- **TCP 5761**: canal de vídeo, uma linha JSON de cabeçalho seguida do JPEG, só o quadro mais recente.

A especificação está no cabeçalho de `ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_ponte_dji.py`.

| Arquivo | Módulo do nível n |
|---|---|
| `Ponte.kt` | orquestração: um executor para mensagens, emissor (20 Hz), telemetria (10 Hz), heartbeat (1 Hz) |
| `ServidorSocket.kt` | ServidorSocket |
| `LeitorTelemetria.kt` | LeitorTelemetria |
| `EmissorComandos.kt` | EmissorComandos: conversão local → norte/leste com ψ₀, watchdog 0,2 s, pouso após 2 s sem heartbeat |
| `ConfiguradorSeguranca.kt` | ConfiguradorSeguranca: ação em perda de sinal = pousar |
| `Drone.kt` | interface que isola o SDK da DJI |
| `DroneFalso.kt` | drone cinemático (mesma dinâmica de `simulador_cinematico.py`), com guinada; com `CenaFalsa` gera quadros e distâncias |
| `CenaFalsa.kt` | sala sintética com balões, renderizada por traçado de raios (testes da Tarefa 2 sem aeronave) |
| `ServidorVideo.kt` | canal de vídeo (porta 5761): cabeçalho JSON + JPEG, descarta quadros atrasados |
| `Nv21.kt`, `JpegAndroid.kt` | redução de quadros NV21 a ~640 px e codificação JPEG |
| `celular/…/DroneDji.kt`, `ConexaoSdk.kt` | DJI Mobile SDK v5.20.1 (só na variante `celular`): telemetria, comandos, câmera, obstáculos, gimbal |

### APIs do MSDK 5.20.1 usadas (nomes conferidos no jar `dji-sdk-v5-aircraft-provided-5.20.1`)

| Interface `Drone` | API |
|---|---|
| telemetria | `KeyManager.listen`: `FlightControllerKey.KeyAircraftVelocity`, `KeyAltitude`, `KeyUltrasonicHeight`, `KeyAircraftAttitude`, `KeyIsFlying`, `KeyAreMotorsOn`, `KeyFlightMode`, `KeyConnection`, `KeyFailsafeAction`; `BatteryKey.KeyChargeRemainingInPercent`; `FlightAssistantKey.KeyVisionPositioningEnabled`; `GimbalKey.KeyGimbalAttitude` |
| decolar / pousar | `KeyManager.performAction(FlightControllerKey.KeyStartTakeoff / KeyStartAutoLanding)` |
| controle virtual | `VirtualStickManager`: `enableVirtualStick`, `setVirtualStickAdvancedModeEnabled`, `sendVirtualStickAdvancedParam` |
| perda de sinal | `KeyManager.setValue(FlightControllerKey.KeyFailsafeAction, FailsafeAction.LANDING)` |
| câmera (Tarefa 2) | `MediaDataCenter.getInstance().cameraStreamManager.addFrameListener(ComponentIndexType.LEFT_OR_MAIN, FrameFormat.NV21, …)` |
| obstáculos (Tarefa 2) | `PerceptionManager.getInstance().addObstacleDataListener` → `ObstacleData.horizontalObstacleDistance`, `horizontalAngleInterval` |
| câmera nivelada | `KeyManager.performAction(GimbalKey.KeyRotateByAngle, GimbalAngleRotation(ABSOLUTE_ANGLE, pitch 0°))` |

Testes JVM (22): protocolo, watchdog e perda da ponte (T09), integração com socket, redução NV21, canal de vídeo,
obstáculos, cena falsa e guinada do drone falso.

## Por que duas variantes

O SDK da DJI fala com o controle RC-N2/RC-N3 pelo **modo acessório USB** do Android: o controle é o hospedeiro USB e o
Android é o dispositivo. A porta USB de um notebook não faz esse papel, então um Android **emulado** não consegue
conversar com o controle. Por isso:

- **`emulador`** — drone falso, sem SDK, roda no emulador x86_64. Serve para testar o app inteiro contra o sistema
  ROS 2 real, sem drone e sem App Key.
- **`celular`** — SDK da DJI, só ARM64. É o que vai no **celular ligado ao controle** no voo real. Também oferece o
  modo "falso", para testar o celular antes de ter o controle.

## Compilar e testar

Pré-requisitos: JDK 17+ e o Android SDK (`local.properties` com `sdk.dir=…`; não vai para o repositório).

```bash
cd android_ponte
./gradlew testEmuladorDebugUnitTest     # testes na JVM: protocolo, T09 (watchdog/perda da ponte), integração
./gradlew assembleEmuladorDebug         # app-emulador-debug.apk
./gradlew assembleCelularDebug          # app-celular-debug.apk (precisa da App Key para registrar o SDK)
```

A App Key fica fora do repositório. Crie-a em <https://developer.dji.com> (conta de desenvolvedor, tipo Mobile SDK)
com o nome de pacote **`br.usp.psi3442.ponte`** e coloque em `~/.gradle/gradle.properties`:

```properties
DJI_API_KEY=sua-chave
```

## Emulador (sem drone)

Use uma imagem **AOSP sem os apps do Google** (`default`): com a imagem `google_apis` e 2 GB, os apps do Google
disputam CPU e memória e o agendamento do app ponte atrasa centenas de milissegundos.

```bash
sdkmanager "platform-tools" "emulator" "system-images;android-34;default;x86_64"
avdmanager create avd -n psi3442 -k "system-images;android-34;default;x86_64" -d pixel_6
sed -i 's/^hw.ramSize=.*/hw.ramSize=3072/' ~/.android/avd/psi3442.avd/config.ini
```

Ensaio automático (da raiz do repositório): `bash android_ponte/ensaio_emulador.sh rapido` — sobe o emulador, instala
o app, inicia o drone falso, sobe o sistema ROS 2 com `simulacao:=true`, envia `executar tarefa 1` e exporta o CSV
para `simulacoes/`. Passo a passo manual:

```bash
# terminal 1: emulador e app
emulator -avd psi3442 &                       # AVD x86_64, Android 14
adb install -r app/build/outputs/apk/emulador/debug/app-emulador-debug.apk
adb forward tcp:5760 tcp:5760; adb forward tcp:5761 tcp:5761   # no app: "Iniciar (falso)"
# terminal 2: sistema ROS 2 (o mesmo do voo)
ros2 launch psi3442_tarefas sistema.launch.py
# terminal 3: operador (aceita digitação)      terminal 4 (opcional): painel (só mostra)
ros2 run psi3442_tarefas interface_operador     # digite: executar tarefa 1
```

## Voo real

1. Celular Android (ARM64, Android 7+) ligado ao controle pelo cabo; app `celular`, botão "Iniciar (dji)".
   Na primeira vez, o celular precisa de internet para registrar a App Key.
2. Notebook e celular na mesma rede Wi-Fi (ou o notebook no ponto de acesso do celular). O app mostra o IP.
3. `python3 ensaios/teste_eixos.py --host <IP>` (T00) antes do primeiro voo da Tarefa 1.
4. `ros2 launch psi3442_tarefas sistema.launch.py host_ponte:=<IP>` e o operador como acima.

O que ainda precisa ser confirmado com a aeronave (marcado em `DroneDji.kt`):
- o eixo norte/leste do controle virtual (`ROLL_E_NORTE`, verificado pelo T00);
- o referencial de `KeyAircraftVelocity`;
- a unidade de `KeyUltrasonicHeight` (até lá, a altura vem de `KeyAltitude`);
- para a Tarefa 2:
  - a resolução e o campo de visão do fluxo ao vivo (`visao.hfov_graus` na config);
  - a unidade (mm), a origem e o sentido de `ObstacleData` (anteparo a distância conhecida, em solo);
  - o gimbal efetivamente em 0° (o nó ponte avisa no log se o pitch passar de 3°).
