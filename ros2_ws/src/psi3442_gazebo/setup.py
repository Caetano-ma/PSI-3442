from glob import glob

from setuptools import setup

PACOTE = 'psi3442_gazebo'

setup(
    name=PACOTE,
    version='0.1.0',
    packages=[PACOTE],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + PACOTE]),
        ('share/' + PACOTE, ['package.xml']),
        ('share/' + PACOTE + '/worlds', glob('worlds/*.sdf')),
        ('share/' + PACOTE + '/launch', glob('launch/*.launch.py')),
        ('share/' + PACOTE + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Caetano-ma',
    maintainer_email='281951699+Caetano-ma@users.noreply.github.com',
    description='Simulação das Tarefas 1 e 2 no Gazebo Harmonic (PSI3442 P2 2026).',
    license='MIT',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'app_ponte_gazebo = psi3442_gazebo.app_ponte_gazebo:main',
        'gerar_sala_t2 = psi3442_gazebo.gerar_sala_t2:main',
        'avaliador_t2 = psi3442_gazebo.avaliador_t2:main',
    ]},
)
