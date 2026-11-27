# App ponte DJI (ciclo C3)

App Android (Kotlin) que liga o nó `ponte_dji` do ROS 2 à aeronave, pelo ContratoSocketPonte: TCP na porta 5760,
JSON por linha. A especificação está no cabeçalho de `ros2_ws/src/psi3442_tarefas/psi3442_tarefas/no_ponte_dji.py`.

| Arquivo | Módulo do nível n |
|---|---|
| `Ponte.kt` | orquestração: um executor para mensagens, emissor (20 Hz), telemetria (10 Hz), heartbeat (1 Hz) |
| `ServidorSocket.kt` | ServidorSocket |
| `LeitorTelemetria.kt` | LeitorTelemetria |
| `EmissorComandos.kt` | EmissorComandos: conversão local → norte/leste com ψ₀, watchdog 0,2 s, pouso após 2 s sem heartbeat |
| `ConfiguradorSeguranca.kt` | ConfiguradorSeguranca: ação em perda de sinal = pousar |
| `Drone.kt` | interface que isola o SDK da DJI |
| `DroneFalso.kt` | drone cinemático (mesma dinâmica de `simulador_cinematico.py`) |
| `celular/…/DroneDji.kt`, `ConexaoSdk.kt` | DJI Mobile SDK v5.20.1 (só na variante `celular`) |

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

```bash
# terminal 1: emulador e app
emulator -avd psi3442 &                       # AVD x86_64, Android 14
adb install -r app/build/outputs/apk/emulador/debug/app-emulador-debug.apk
adb forward tcp:5760 tcp:5760                  # no app: "Iniciar (falso)"
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

O que ainda precisa ser confirmado com a aeronave (marcado em `DroneDji.kt`): o eixo norte/leste do controle virtual
(`ROLL_E_NORTE`, verificado pelo T00), o referencial de `KeyAircraftVelocity` e a unidade de `KeyUltrasonicHeight`
(até lá a altura vem de `KeyAltitude`).
