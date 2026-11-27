"""Tarefa 2 no Gazebo: sala com balões aleatórios (semente) + câmera e distâncias + aplicação ROS 2 completa.

    ros2 launch psi3442_gazebo tarefa2_gazebo.launch.py semente:=3 baloes:=7          # com a janela do Gazebo
    ros2 launch psi3442_gazebo tarefa2_gazebo.launch.py gui:=false comando_automatico:=true
Em outro terminal: ros2 run psi3442_tarefas interface_operador  ->  executar tarefa 2   (ou o painel)
A sala é gerada a cada execução em <pasta_sala> (sala_tarefa2.sdf + verdade.yaml). O avaliador usa a verdade só para
validar (R05) e grava avaliacao.csv e resumo.yaml na mesma pasta. A Tarefa 2 é liberada sem a Tarefa 1 em voo real
porque é simulação (liberar_tarefa2:=true); as conclusões não contam como voo real.
"""
import os
import subprocess
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, OpaqueFunction,
                            TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _gazebo(context):
    pasta = os.path.expanduser(LaunchConfiguration('pasta_sala').perform(context))
    config = LaunchConfiguration('config').perform(context)
    subprocess.run([sys.executable, '-m', 'psi3442_gazebo.gerar_sala_t2', '--config', config,
                    '--semente', LaunchConfiguration('semente').perform(context),
                    '--baloes', LaunchConfiguration('baloes').perform(context), '--saida', pasta], check=True)
    mundo = os.path.join(pasta, 'sala_tarefa2.sdf')
    gui = LaunchConfiguration('gui').perform(context).lower() in ('true', '1')
    gz_args = f'-r {mundo}' if gui else f'-r -s --headless-rendering {mundo}'
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('ros_gz_sim'), 'launch',
                                                       'gz_sim.launch.py')),
            launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items()),
        Node(package='psi3442_gazebo', executable='avaliador_t2', name='avaliador_t2', output='screen',
             arguments=['--verdade', os.path.join(pasta, 'verdade.yaml'), '--saida', pasta]),
    ]


def generate_launch_description():
    share = get_package_share_directory('psi3442_gazebo')
    share_tarefas = get_package_share_directory('psi3442_tarefas')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='abre a janela do Gazebo'),
        DeclareLaunchArgument('config', default_value=os.path.join(share_tarefas, 'config', 'tarefas.yaml')),
        DeclareLaunchArgument('semente', default_value='1', description='semente da posição e das cores dos balões'),
        DeclareLaunchArgument('baloes', default_value='6', description='quantidade de balões'),
        DeclareLaunchArgument('pasta_sala', default_value='~/.ros/psi3442_sala_t2'),
        DeclareLaunchArgument('registro', default_value='true'),
        DeclareLaunchArgument('pasta_bags', default_value=os.path.expanduser('~/psi3442_bags')),
        DeclareLaunchArgument('comando_automatico', default_value='false',
                              description='envia "executar tarefa 2" pela interface do operador após o atraso'),
        DeclareLaunchArgument('atraso_comando', default_value='20.0'),
        DeclareLaunchArgument('app_args', default_value='', description='ex.: "--vies-norte 0.004"'),

        OpaqueFunction(function=_gazebo),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='ponte_ros_gz', output='screen',
             parameters=[{'config_file': os.path.join(share, 'config', 'ponte_ros_gz_t2.yaml')}]),
        Node(package='psi3442_gazebo', executable='app_ponte_gazebo', name='app_ponte_gazebo', output='screen',
             arguments=[LaunchConfiguration('app_args')]),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share_tarefas, 'launch', 'sistema.launch.py')),
            launch_arguments={'simulador': 'false', 'simulacao': 'true', 'liberar_tarefa2': 'true',
                              'video_ponte': 'false', 'use_sim_time': 'true', 'config': LaunchConfiguration('config'),
                              'registro': LaunchConfiguration('registro'),
                              'pasta_bags': LaunchConfiguration('pasta_bags')}.items()),
        TimerAction(period=LaunchConfiguration('atraso_comando'), condition=IfCondition(
            LaunchConfiguration('comando_automatico')), actions=[
            ExecuteProcess(cmd=['ros2', 'run', 'psi3442_tarefas', 'interface_operador', '--comando',
                                'executar tarefa 2'], output='screen')]),
    ])
