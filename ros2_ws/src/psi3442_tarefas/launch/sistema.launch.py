"""Sobe a aplicação ROS 2 completa (nível 1): gerenciador, Tarefa 1, estimação, controle, supervisão, ponte DJI e
registro. A interface do operador e o painel rodam em terminais próprios (precisam do teclado/tela):

    ros2 launch psi3442_tarefas sistema.launch.py                      # com o app ponte (adb forward tcp:5760)
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
    parametros = [{'config': config}]

    def no(executavel, extras=()):
        return Node(package='psi3442_tarefas', executable=executavel, name=executavel, output='screen',
                    parameters=parametros + list(extras), emulate_tty=True)

    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=os.path.join(share, 'config', 'tarefas.yaml'),
                              description='arquivo YAML das tarefas'),
        DeclareLaunchArgument('simulador', default_value='false',
                              description='true: sobe o simulador cinemático no lugar do app ponte'),
        DeclareLaunchArgument('registro', default_value='true', description='grava rosbag2 de todos os tópicos'),
        DeclareLaunchArgument('pasta_bags', default_value=os.path.expanduser('~/psi3442_bags')),
        DeclareLaunchArgument('simulador_args', default_value='',
                              description='argumentos extras do simulador (ex.: "--vies-norte 0.01")'),

        Node(package='psi3442_tarefas', executable='simulador_ponte', name='simulador_ponte', output='screen',
             arguments=[LaunchConfiguration('simulador_args')], condition=IfCondition(simulador)),
        no('gerenciador_tarefas', [{'simulacao': ParameterValue(simulador, value_type=bool)}]),
        no('tarefa1'),
        no('estimacao_estado'),
        no('controle_voo'),
        no('supervisao'),
        no('ponte_dji'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'registro.launch.py')),
            launch_arguments={'pasta_bags': LaunchConfiguration('pasta_bags')}.items(),
            condition=IfCondition(LaunchConfiguration('registro'))),
    ])
