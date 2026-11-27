#!/usr/bin/env bash
# Ensaio integrado no emulador: app ponte (variante emulador, drone falso) + sistema ROS 2 real + operador.
# Envia "executar tarefa 1", acompanha /tarefa/status até concluir e exporta o CSV.
# A conclusão é marcada como simulação (simulacao:=true): não conta como voo real.
#
# Uso: bash android_ponte/ensaio_emulador.sh [rapido|completo]     (rapido = 5 s por vértice; padrão)
#      JANELA=1 mostra a janela do emulador.
set -m
set -e
PASTA="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(dirname "$PASTA")"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
ADB="$SDK/platform-tools/adb"
AVD=psi3442
PACOTE=br.usp.psi3442.ponte.emulador
SAIDA="$RAIZ/simulacoes/emulador_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SAIDA"

if ! "$ADB" get-state >/dev/null 2>&1; then
    echo "--- iniciando o emulador ($AVD)"
    JANELA_ARG=$([ "${JANELA:-0}" = 1 ] || echo "-no-window")
    "$SDK/emulator/emulator" -avd "$AVD" -no-snapshot -no-audio -no-boot-anim $JANELA_ARG > "$SAIDA/emulador.log" 2>&1 &
    "$ADB" wait-for-device
    until [ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do sleep 2; done
fi

echo "--- compilando e instalando o app (variante emulador)"
(cd "$PASTA" && ./gradlew -q assembleEmuladorDebug)
"$ADB" install -r "$PASTA/app/build/outputs/apk/emulador/debug/app-emulador-debug.apk" >/dev/null
"$ADB" forward tcp:5760 tcp:5760 >/dev/null
"$ADB" shell am force-stop "$PACOTE"
"$ADB" logcat -c
"$ADB" shell am start -n "$PACOTE/br.usp.psi3442.ponte.MainActivity" --es modo falso >/dev/null
sleep 3

echo "--- sistema ROS 2"
source /opt/ros/jazzy/setup.bash
(cd "$RAIZ/ros2_ws" && colcon build --packages-select psi3442_interfaces psi3442_tarefas >/dev/null)
source "$RAIZ/ros2_ws/install/setup.bash"
CFG_DIR="$(ros2 pkg prefix psi3442_tarefas)/share/psi3442_tarefas/config"
CFG="$CFG_DIR/tarefas_teste_rapido.yaml"
[ "${1:-rapido}" = completo ] && CFG="$CFG_DIR/tarefas.yaml"
ros2 launch psi3442_tarefas sistema.launch.py simulacao:=true config:="$CFG" pasta_bags:="$SAIDA/bags" \
    > "$SAIDA/launch.log" 2>&1 &
LAUNCH=$!
sleep 8

status() { timeout 5 ros2 topic echo --once /tarefa/status psi3442_interfaces/msg/StatusTarefa 2>/dev/null \
    | grep -E "^(modo|estado|nome_vertice|mensagem):" | tr '\n' ' '; echo; }
echo "--- executar tarefa 1"
ros2 run psi3442_tarefas interface_operador --comando "executar tarefa 1" 2>&1 | tail -2
FIM=$([ "${1:-rapido}" = completo ] && echo 120 || echo 30)
for i in $(seq 1 "$FIM"); do
    sleep 5
    linha=$(status)
    echo "t+$((i * 5))s: $linha"
    if echo "$linha" | grep -q "conclu\|abortada"; then break; fi
done
sleep 2
kill -INT -- -$LAUNCH 2>/dev/null || true
timeout 30 tail --pid=$LAUNCH -f /dev/null || true
"$ADB" logcat -d -s System.out:I AndroidRuntime:E > "$SAIDA/app.log" 2>&1 || true

BAG=$(ls -d "$SAIDA"/bags/*/ 2>/dev/null | head -1); BAG=${BAG%/}
if [ -n "$BAG" ]; then
    python3 "$(ros2 pkg prefix psi3442_tarefas)/share/psi3442_tarefas/ferramentas/exportar_csv.py" "$BAG" >/dev/null
    echo "--- eventos:"; cut -d, -f1-6 "${BAG}_eventos.csv" | head -40
fi
echo "--- resultados em $SAIDA"
