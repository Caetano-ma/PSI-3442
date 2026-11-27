"""GravadorRosbag (nível n): ros2 bag record de todos os tópicos do sistema, um bag por execução.

    ros2 launch psi3442_tarefas registro.launch.py [pasta_bags:=~/psi3442_bags]
Depois: python3 ferramentas/exportar_csv.py <pasta do bag>  (gera o CSV de evidência)
"""
import datetime
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration

TOPICOS = [
    '/operador/comando', '/tarefa/ativa', '/tarefa/status', '/tarefa/evento', '/dji/acao', '/setpoint',
    '/estado', '/dji/telemetria', '/dji/cmd_vel', '/falhas',
    '/alvos', '/mapa', '/dji/obstaculos',          # Tarefa 2 (os quadros /dji/camera ficam de fora: volume)
    '/gazebo/mini4pro/odometria', '/avaliador/distancia_m',   # só na simulação: verdade para validação (R05)
]


def _gravador(context):
    pasta = os.path.expanduser(LaunchConfiguration('pasta_bags').perform(context))
    os.makedirs(pasta, exist_ok=True)
    nome = 'execucao_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return [ExecuteProcess(cmd=['ros2', 'bag', 'record', '-o', os.path.join(pasta, nome)] + TOPICOS,
                           output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('pasta_bags', default_value=os.path.expanduser('~/psi3442_bags')),
        OpaqueFunction(function=_gravador),
    ])
