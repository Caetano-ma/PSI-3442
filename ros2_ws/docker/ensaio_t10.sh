#!/bin/bash
# Ensaio T10 integrado: launch completo + simulador, comando do operador, bag e CSV.
# Uso: docker run --rm -v "$(pwd):/repo:ro" [-v "<pasta>:/saida"] ros:jazzy-ros-base bash /repo/ros2_ws/docker/ensaio_t10.sh
set -m   # controle de jobs: o launch em segundo plano recebe SIGINT normalmente
source /opt/ros/jazzy/setup.bash
mkdir -p /ws/src && cp -r /repo/ros2_ws/src/. /ws/src/ && cd /ws
colcon build >/dev/null 2>&1 || { echo "falha na compilação"; exit 1; }
source install/setup.bash
CFG=/ws/install/psi3442_tarefas/share/psi3442_tarefas/config/tarefas_teste_rapido.yaml
ros2 launch psi3442_tarefas sistema.launch.py simulador:=true config:=$CFG pasta_bags:=/tmp/bags > /tmp/launch.log 2>&1 &
LAUNCH=$!
sleep 8
status() { timeout 5 ros2 topic echo --once /tarefa/status psi3442_interfaces/msg/StatusTarefa 2>/dev/null | grep -E "^(modo|estado|nome_vertice|mensagem):" | tr '\n' ' '; echo; }
echo "--- executar tarefa 2 (deve recusar):"
ros2 run psi3442_tarefas interface_operador --comando "executar tarefa 2" 2>&1 | tail -3; echo "código de saída: ${PIPESTATUS[0]}"
echo "--- executar tarefa 1:"
ros2 run psi3442_tarefas interface_operador --comando "executar tarefa 1" 2>&1 | tail -3; echo "código de saída: ${PIPESTATUS[0]}"
for i in $(seq 1 20); do
  sleep 5; linha=$(status); echo "t+$((i*5))s: $linha"
  if echo "$linha" | grep -q "conclu\|abortada"; then break; fi
done
sleep 2
kill -INT -- -$LAUNCH
timeout 30 tail --pid=$LAUNCH -f /dev/null; echo "launch encerrado: $?"
BAG=$(ls -d /tmp/bags/*/ | head -1); BAG=${BAG%/}
ls "$BAG"
echo "--- exportar CSV"
python3 /ws/install/psi3442_tarefas/share/psi3442_tarefas/ferramentas/exportar_csv.py "$BAG"
echo "--- CSV (cabeçalho + linhas com eventos):"
head -1 "$BAG.csv"
awk -F, 'NR>1 && $17!=""' "$BAG.csv" | head -40
echo "--- eventos:"; cut -d, -f1-6 "${BAG}_eventos.csv" | head -60
mkdir -p /saida 2>/dev/null && cp "$BAG.csv" "${BAG}_eventos.csv" /tmp/launch.log /saida/ 2>/dev/null || true
