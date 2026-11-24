#!/bin/bash
# Tarefa 1 no Gazebo, dentro da imagem psi3442-gazebo (Dockerfile.gazebo). Compila o workspace e sobe tudo.
# Argumentos extras vão para o launch, ex.:  gui:=false  comando_automatico:=true  config:=.../tarefas_teste_rapido.yaml
# No Windows, use ros2_ws/docker/simular_gazebo.ps1 (monta o display do WSLg).
# Bags e CSV ficam em /saida quando essa pasta for montada (senão, em /tmp/bags).
set -m
source /opt/ros/jazzy/setup.bash
mkdir -p /ws/src && cp -r /repo/ros2_ws/src/. /ws/src/ && cd /ws
colcon build --event-handlers console_direct- > /tmp/build.log 2>&1 || { tail -30 /tmp/build.log; exit 1; }
source install/setup.bash
PASTA=/tmp/bags; [ -d /saida ] && PASTA=/saida
RAPIDO=/ws/install/psi3442_tarefas/share/psi3442_tarefas/config/tarefas_teste_rapido.yaml
args=()
for a in "$@"; do [ "$a" = "rapido" ] && args+=("config:=$RAPIDO") || args+=("$a"); done
echo "Gazebo + ROS 2 prontos. Em outro terminal:  docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh"
ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py pasta_bags:=$PASTA "${args[@]}" &
LAUNCH=$!
trap 'kill -INT -- -$LAUNCH 2>/dev/null' INT TERM
wait $LAUNCH
# exporta o CSV da execução mais recente
BAG=$(ls -dt $PASTA/execucao_*/ 2>/dev/null | head -1)
if [ -n "$BAG" ]; then
  python3 /ws/install/psi3442_tarefas/share/psi3442_tarefas/ferramentas/exportar_csv.py "${BAG%/}" || true
fi
