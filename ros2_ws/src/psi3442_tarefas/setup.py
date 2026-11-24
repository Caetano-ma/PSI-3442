from glob import glob

from setuptools import setup

PACOTE = 'psi3442_tarefas'

setup(
    name=PACOTE,
    version='0.1.0',
    packages=[PACOTE],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + PACOTE]),
        ('share/' + PACOTE, ['package.xml']),
        ('share/' + PACOTE + '/config', glob('config/*.yaml')),
        ('share/' + PACOTE + '/launch', glob('launch/*.launch.py')),
        ('share/' + PACOTE + '/ferramentas', glob('ferramentas/*.py')),
    ],
    install_requires=['setuptools', 'pyyaml'],
    zip_safe=True,
    maintainer='Caetano-ma',
    maintainer_email='281951699+Caetano-ma@users.noreply.github.com',
    description='Nós ROS 2 da Tarefa 1 e serviços comuns (PSI3442 P2 2026).',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'interface_operador = psi3442_tarefas.no_interface_operador:main',
            'painel = psi3442_tarefas.painel:main',
            'gerenciador_tarefas = psi3442_tarefas.no_gerenciador_tarefas:main',
            'tarefa1 = psi3442_tarefas.no_tarefa1:main',
            'estimacao_estado = psi3442_tarefas.no_estimacao_estado:main',
            'controle_voo = psi3442_tarefas.no_controle_voo:main',
            'supervisao = psi3442_tarefas.no_supervisao:main',
            'ponte_dji = psi3442_tarefas.no_ponte_dji:main',
            'simulador_ponte = psi3442_tarefas.simulador_cinematico:main',
        ],
    },
)
