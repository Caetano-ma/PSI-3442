#!/bin/bash
# Terminal do operador dentro do contêiner da simulação:  docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh
#   painel  -> bash /repo/ros2_ws/docker/operador.sh painel
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
if [ "$1" = "painel" ]; then
  exec ros2 run psi3442_tarefas painel
fi
exec ros2 run psi3442_tarefas interface_operador
