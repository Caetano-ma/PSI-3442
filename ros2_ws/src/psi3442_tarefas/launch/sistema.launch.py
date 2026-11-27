"""Sobe a aplicação ROS 2 completa (nível 1): gerenciador, Tarefas 1 e 2, estimação, controle, supervisão, visão
computacional, mapeamento local, ponte DJI e registro. A interface do operador e o painel rodam em terminais próprios (precisam do teclado/tela):

    ros2 launch psi3442_tarefas sistema.launch.py                      # com o app ponte (adb forward tcp:5760)
    ros2 launch psi3442_tarefas sistema.launch.py host_ponte:=<IP>     # app ponte no celular, pelo Wi-Fi
    ros2 launch psi3442_tarefas sistema.launch.py simulador:=true      # com o simulador cinemático
    ros2 run psi3442_tarefas painel
    ros2 run psi3442_tarefas interface_operador
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('psi3442_tarefas')
    config = LaunchConfiguration('config')
    simulador = LaunchConfiguration('simulador')
    tempo_sim = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    parametros = [{'config': config, 'use_sim_time': tempo_sim}]

    def no(executavel, extras=(), relogio_sim=True):
        return Node(package='psi3442_tarefas', executable=executavel, name=executavel, output='screen',
                    parameters=(parametros if relogio_sim else [{'config': config}]) + list(extras), emulate_tty=True)

    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=os.path.join(share, 'config', 'tarefas.yaml'),
                              description='arquivo YAML das tarefas'),
        DeclareLaunchArgument('simulador', default_value='false',
                              description='true: sobe o simulador cinemático no lugar do app ponte'),
        DeclareLaunchArgument('simulacao', default_value=simulador,
                              description='true: conclusões não contam como voo real (padrão: igual a simulador; '
                                          'o launch do Gazebo passa true)'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='true no Gazebo: cronômetro e prazos no relógio do simulador (R04)'),
        DeclareLaunchArgument('video_ponte', default_value='true',
                              description='false: câmera e distâncias vêm de outra fonte (Gazebo), não do app ponte'),
        DeclareLaunchArgument('liberar_tarefa2', default_value='false',
                              description='true: aceita a Tarefa 2 sem a Tarefa 1 em voo real (só em simulação)'),
        DeclareLaunchArgument('registro', default_value='true', description='grava rosbag2 de todos os tópicos'),
        DeclareLaunchArgument('pasta_bags', default_value=os.path.expanduser('~/psi3442_bags')),
        DeclareLaunchArgument('simulador_args', default_value='',
                              description='argumentos extras do simulador (ex.: "--vies-norte 0.01")'),
        DeclareLaunchArgument('host_ponte', default_value='127.0.0.1',
                              description='endereço do app ponte: 127.0.0.1 com adb forward (emulador) ou o IP do '
                                          'celular ligado ao controle (Wi-Fi)'),

        Node(package='psi3442_tarefas', executable='simulador_ponte', name='simulador_ponte', output='screen',
             arguments=[LaunchConfiguration('simulador_args')], condition=IfCondition(simulador)),
        no('gerenciador_tarefas', [{
            'simulacao': ParameterValue(LaunchConfiguration('simulacao'), value_type=bool),
            'liberar_tarefa2': ParameterValue(LaunchConfiguration('liberar_tarefa2'), value_type=bool)}]),
        no('tarefa1'),
        no('tarefa2'),
        no('visao_computacional'),
        no('mapeamento_local'),
        no('estimacao_estado'),
        no('controle_voo'),
        no('supervisao'),
        no('ponte_dji', [{'host': LaunchConfiguration('host_ponte'),
                          'video': ParameterValue(LaunchConfiguration('video_ponte'), value_type=bool)}],
           relogio_sim=False),     # watchdogs do app ponte são em tempo real

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'registro.launch.py')),
            launch_arguments={'pasta_bags': LaunchConfiguration('pasta_bags')}.items(),
            condition=IfCondition(LaunchConfiguration('registro'))),
    ])
