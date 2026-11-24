"""Tarefa 1 no Gazebo: mundo da sala + ponte ros_gz + app ponte simulado + aplicação ROS 2 completa.

    ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py                     # com a janela do Gazebo
    ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py gui:=false          # só o servidor (sem janela)
    ros2 launch psi3442_gazebo tarefa1_gazebo.launch.py comando_automatico:=true   # envia "executar tarefa 1"
Em outro terminal: ros2 run psi3442_tarefas painel  /  ros2 run psi3442_tarefas interface_operador
As conclusões no Gazebo não contam como voo real (simulacao:=true no gerenciador).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction,
                            TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _gazebo(context):
    share = get_package_share_directory('psi3442_gazebo')
    mundo = os.path.join(share, 'worlds', 'sala_tarefa1.sdf')
    gui = LaunchConfiguration('gui').perform(context).lower() in ('true', '1')
    gz_args = f'-r {mundo}' if gui else f'-r -s {mundo}'
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('ros_gz_sim'), 'launch',
                                                   'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items())]


def generate_launch_description():
    share = get_package_share_directory('psi3442_gazebo')
    share_tarefas = get_package_share_directory('psi3442_tarefas')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='abre a janela do Gazebo'),
        DeclareLaunchArgument('config', default_value=os.path.join(share_tarefas, 'config', 'tarefas.yaml')),
        DeclareLaunchArgument('registro', default_value='true'),
        DeclareLaunchArgument('pasta_bags', default_value=os.path.expanduser('~/psi3442_bags')),
        DeclareLaunchArgument('comando_automatico', default_value='false',
                              description='envia "executar tarefa 1" pela interface do operador após o atraso'),
        DeclareLaunchArgument('atraso_comando', default_value='15.0'),
        DeclareLaunchArgument('app_args', default_value='', description='ex.: "--vies-norte 0.01"'),

        OpaqueFunction(function=_gazebo),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='ponte_ros_gz', output='screen',
             parameters=[{'config_file': os.path.join(share, 'config', 'ponte_ros_gz.yaml')}]),
        Node(package='psi3442_gazebo', executable='app_ponte_gazebo', name='app_ponte_gazebo', output='screen',
             arguments=[LaunchConfiguration('app_args')]),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share_tarefas, 'launch', 'sistema.launch.py')),
            launch_arguments={'simulador': 'false', 'simulacao': 'true', 'config': LaunchConfiguration('config'),
                              'registro': LaunchConfiguration('registro'),
                              'pasta_bags': LaunchConfiguration('pasta_bags')}.items()),
        TimerAction(period=LaunchConfiguration('atraso_comando'), condition=IfCondition(
            LaunchConfiguration('comando_automatico')), actions=[
            ExecuteProcess(cmd=['ros2', 'run', 'psi3442_tarefas', 'interface_operador', '--comando',
                                'executar tarefa 1'], output='screen')]),
    ])
