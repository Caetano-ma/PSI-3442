"""Gera a sala da Tarefa 2 para o Gazebo Harmonic: balões de várias cores em posições aleatórias (semente).

- Mundo = ReferencialLocal (origem no ponto de decolagem, x à frente do nariz, y à esquerda, z para cima).
- Paredes fecham a sala com folga em volta do volume permitido da Tarefa 2 (config tarefa2.volume_*); móveis
  opcionais encostados nas paredes, vistos pelo sensor de distâncias (R06).
- Balões: elipsoides levemente alongados (raio nominal tarefa2.raio_balao_m), estáticos, com nó e cordão; centros
  dentro do volume, separados entre si e longe da decolagem. Pelo menos um de cada cor-alvo.
- Aeronave: o mesmo modelo caixa-preta da Tarefa 1 (copiado de sala_tarefa1.sdf), com a câmera frontal (640x480,
  campo de visão de tarefa visao.hfov_graus) e um sensor de distâncias 360° no plano da aeronave, no lugar da
  percepção de obstáculos da DJI (/dji/obstaculos).
- Grava também `verdade.yaml` (posições reais), usado só pelo avaliador (R05) e pela geração de imagens.

    ros2 run psi3442_gazebo gerar_sala_t2 --semente 3 --baloes 7 --saida ~/.ros/psi3442_sala_t2
"""
import argparse
import math
import os
import random

import yaml

CORES_RGB = {                       # matizes dentro das faixas HSV da visão (no_visao_computacional.FAIXAS_HSV)
    'vermelho': (0.85, 0.08, 0.08), 'azul': (0.10, 0.25, 0.85), 'verde': (0.10, 0.70, 0.20),
    'amarelo': (0.95, 0.80, 0.10), 'roxo': (0.55, 0.15, 0.75),
}
FOLGA_PAREDE_M = 0.6                # parede a esta distância além do volume permitido
ALTURA_SALA_M = 3.0
SEPARACAO_MIN_M = 1.1               # entre centros de balões (deixa espaço para a aproximação)
DISTANCIA_DECOLAGEM_MIN_M = 1.2


def sortear_baloes(rng, n, cores_alvo, cores, volume, raio, z_min=0.9, z_max=2.0, margem=0.45):
    (x0, x1), (y0, y1) = volume
    cores_sorteio = list(cores_alvo) + [rng.choice(cores) for _ in range(max(0, n - len(cores_alvo)))]
    rng.shuffle(cores_sorteio)
    baloes = []
    for cor in cores_sorteio:
        for _ in range(2000):
            x, y = rng.uniform(x0 + margem, x1 - margem), rng.uniform(y0 + margem, y1 - margem)
            z = rng.uniform(z_min, z_max)
            if math.hypot(x, y) < DISTANCIA_DECOLAGEM_MIN_M:
                continue
            if all(math.dist((x, y, z), (b['x'], b['y'], b['z'])) >= SEPARACAO_MIN_M for b in baloes):
                baloes.append({'cor': cor, 'x': round(x, 3), 'y': round(y, 3), 'z': round(z, 3), 'raio': raio,
                               'alvo': cor in cores_alvo})
                break
        else:
            raise RuntimeError('não coube mais um balão na sala: reduza --baloes')
    return baloes


def _material(rgb, brilho=0.4):
    r, g, b = rgb
    return (f'<material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse>'
            f'<specular>{brilho} {brilho} {brilho} 1</specular></material>')


def sdf_balao(i, b):
    r = b['raio']
    rz = r * 1.12
    return f'''
    <model name="balao_{i}_{b['cor']}">
      <static>true</static>
      <pose>{b['x']} {b['y']} {b['z']} 0 0 0</pose>
      <link name="link">
        <collision name="colisao"><geometry><sphere><radius>{r}</radius></sphere></geometry></collision>
        <visual name="balao"><geometry><ellipsoid><radii>{r} {r} {rz:.3f}</radii></ellipsoid></geometry>{_material(CORES_RGB[b['cor']], 0.6)}</visual>
        <visual name="no"><pose>0 0 {-rz - 0.01:.3f} 0 0 0</pose><geometry><sphere><radius>0.012</radius></sphere></geometry>{_material(CORES_RGB[b['cor']], 0.1)}</visual>
        <visual name="cordao"><pose>0 0 {-rz - 0.21:.3f} 0 0 0</pose><geometry><cylinder><radius>0.0015</radius><length>0.4</length></cylinder></geometry>{_material((0.95, 0.95, 0.95), 0.0)}</visual>
      </link>
    </model>'''


def sdf_sala(volume):
    (x0, x1), (y0, y1) = volume
    xa, xb, ya, yb = x0 - FOLGA_PAREDE_M, x1 + FOLGA_PAREDE_M, y0 - FOLGA_PAREDE_M, y1 + FOLGA_PAREDE_M
    cx, cy, lx, ly, h = (xa + xb) / 2, (ya + yb) / 2, xb - xa, yb - ya, ALTURA_SALA_M
    cores = [(0.92, 0.92, 0.88), (0.88, 0.90, 0.92), (0.90, 0.88, 0.86), (0.86, 0.90, 0.88)]
    paredes = [(f'{xb + 0.05:.2f} {cy:.2f}', f'0.1 {ly + 0.2:.2f}'), (f'{xa - 0.05:.2f} {cy:.2f}', f'0.1 {ly + 0.2:.2f}'),
               (f'{cx:.2f} {yb + 0.05:.2f}', f'{lx + 0.2:.2f} 0.1'), (f'{cx:.2f} {ya - 0.05:.2f}', f'{lx + 0.2:.2f} 0.1')]
    partes = []
    for k, ((pos, tam), cor) in enumerate(zip(paredes, cores)):
        geo = f'<geometry><box><size>{tam} {h}</size></box></geometry>'
        partes.append(f'<collision name="parede_{k}"><pose>{pos} {h / 2} 0 0 0</pose>{geo}</collision>'
                      f'<visual name="parede_{k}"><pose>{pos} {h / 2} 0 0 0</pose>{geo}{_material(cor, 0.05)}</visual>')
    # móveis encostados nas paredes (fora do volume): armário e mesa
    moveis = [((xb - 0.25, cy + 0.8, 0.9), (0.5, 1.2, 1.8), (0.45, 0.32, 0.20)),
              ((cx - 0.6, ya + 0.35, 0.375), (1.4, 0.7, 0.75), (0.30, 0.30, 0.32))]
    for k, ((px, py, pz), (sx, sy, sz), cor) in enumerate(moveis):
        geo = f'<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>'
        partes.append(f'<collision name="movel_{k}"><pose>{px:.2f} {py:.2f} {pz:.2f} 0 0 0</pose>{geo}</collision>'
                      f'<visual name="movel_{k}"><pose>{px:.2f} {py:.2f} {pz:.2f} 0 0 0</pose>{geo}{_material(cor, 0.1)}</visual>')
    piso = (f'<collision name="piso"><geometry><plane><normal>0 0 1</normal><size>{lx + 2} {ly + 2}</size></plane>'
            f'</geometry></collision><visual name="piso"><pose>{cx:.2f} {cy:.2f} 0 0 0 0</pose><geometry><plane>'
            f'<normal>0 0 1</normal><size>{lx:.2f} {ly:.2f}</size></plane></geometry>{_material((0.55, 0.50, 0.42), 0.0)}'
            f'</visual><visual name="marca_decolagem"><pose>0 0 0.002 0 0 0</pose><geometry><box><size>0.4 0.4 0.002'
            f'</size></box></geometry>{_material((0.2, 0.2, 0.2), 0.0)}</visual>')
    return (f'\n    <model name="sala">\n      <static>true</static>\n      <link name="link">\n        {piso}\n        '
            + '\n        '.join(partes) + '\n      </link>\n    </model>')


def sensores(hfov_graus, largura, altura):
    return f'''
        <sensor name="camera" type="camera">
          <pose>0.10 0 0.03 0 0 0</pose>
          <always_on>true</always_on>
          <update_rate>10</update_rate>
          <visualize>false</visualize>
          <topic>/mini4pro/camera</topic>
          <camera>
            <horizontal_fov>{math.radians(hfov_graus):.4f}</horizontal_fov>
            <image><width>{largura}</width><height>{altura}</height><format>R8G8B8</format></image>
            <clip><near>0.02</near><far>25</far></clip>
            <noise><type>gaussian</type><mean>0</mean><stddev>0.004</stddev></noise>
          </camera>
        </sensor>
        <sensor name="obstaculos" type="gpu_lidar">
          <pose>0 0 0.05 0 0 0</pose>
          <always_on>true</always_on>
          <update_rate>5</update_rate>
          <topic>/mini4pro/obstaculos</topic>
          <lidar>
            <scan><horizontal><samples>120</samples><resolution>1</resolution><min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal></scan>
            <range><min>0.25</min><max>8.0</max><resolution>0.01</resolution></range>
            <noise><type>gaussian</type><mean>0</mean><stddev>0.02</stddev></noise>
          </lidar>
        </sensor>'''


def gerar(mundo_t1, baloes, volume, hfov_graus=82.1, largura=640, altura=480):
    with open(mundo_t1) as f:
        t1 = f.read()
    gui = t1[t1.index('<gui'):t1.index('</gui>') + len('</gui>')]
    gui = gui.replace('<camera_pose>-1.3 -1.5 2.9 0 0.52 0.83</camera_pose>',
                      '<camera_pose>-0.8 -0.9 4.6 0 0.75 0.75</camera_pose>')
    drone = t1[t1.index('<model name="mini4pro">'):t1.index('</model>', t1.index('<model name="mini4pro">')) + 8]
    # lente atrás do centro óptico, para a câmera não ver o próprio visual por dentro
    lente = '<pose>0.10 0 0.03 0 0 0</pose>\n          <geometry><sphere><radius>0.022</radius>'
    assert lente in drone, 'modelo da aeronave em sala_tarefa1.sdf mudou: atualizar gerar_sala_t2.py'
    drone = drone.replace(lente, '<pose>0.085 0 0.03 0 0 0</pose>\n          <geometry><sphere><radius>0.014</radius>')
    fim_link = drone.index('</link>')
    drone = drone[:fim_link] + sensores(hfov_graus, largura, altura).lstrip('\n') + '\n      ' + drone[fim_link:]
    return f'''<?xml version="1.0"?>
<!-- Sala da Tarefa 2, gerada por psi3442_gazebo/gerar_sala_t2.py (não editar à mão). Ver o cabeçalho do script. -->
<sdf version="1.9">
  <world name="sala_tarefa2">
    <physics name="passo_4ms" type="ignored">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>

    {gui}

    <scene>
      <ambient>0.55 0.55 0.55 1</ambient>
      <background>0.80 0.85 0.90 1</background>
      <grid>false</grid>
      <shadows>true</shadows>
    </scene>
    <light type="directional" name="luz_teto">
      <cast_shadows>true</cast_shadows>
      <pose>2 2 6 0 0 0</pose>
      <diffuse>0.85 0.85 0.85 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.2 0.3 -0.93</direction>
    </light>
    <light type="point" name="luz_ambiente">
      <pose>2 1.5 2.8 0 0 0</pose>
      <diffuse>0.35 0.35 0.35 1</diffuse>
      <attenuation><range>12</range><constant>0.6</constant><linear>0.05</linear><quadratic>0.0</quadratic></attenuation>
      <cast_shadows>false</cast_shadows>
    </light>
{sdf_sala(volume)}
{''.join(sdf_balao(i, b) for i, b in enumerate(baloes, start=1))}

    {drone}
  </world>
</sdf>
'''


def main():
    from ament_index_python.packages import get_package_share_directory

    from psi3442_tarefas import carregador_config

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    share_t = get_package_share_directory('psi3442_tarefas')
    ap.add_argument('--config', default=os.path.join(share_t, 'config', 'tarefas.yaml'))
    ap.add_argument('--semente', type=int, default=1)
    ap.add_argument('--baloes', type=int, default=7)
    ap.add_argument('--saida', default=os.path.expanduser('~/.ros/psi3442_sala_t2'))
    a, _ = ap.parse_known_args()
    cfg = carregador_config.carregar(a.config)
    t2, v = cfg.tarefa2, cfg.visao
    volume = ((t2.volume_x_min_m, t2.volume_x_max_m), (t2.volume_y_min_m, t2.volume_y_max_m))
    rng = random.Random(a.semente)
    baloes = sortear_baloes(rng, a.baloes, t2.cores_alvo, list(t2.cores_conhecidas), volume, t2.raio_balao_m,
                            z_min=max(0.9, t2.volume_z_min_m + 0.3), z_max=min(2.0, t2.volume_z_max_m - 0.3))
    os.makedirs(os.path.expanduser(a.saida), exist_ok=True)
    saida = os.path.expanduser(a.saida)
    mundo_t1 = os.path.join(get_package_share_directory('psi3442_gazebo'), 'worlds', 'sala_tarefa1.sdf')
    with open(os.path.join(saida, 'sala_tarefa2.sdf'), 'w') as f:
        f.write(gerar(mundo_t1, baloes, volume, v.hfov_graus, v.largura_px, v.altura_px))
    with open(os.path.join(saida, 'verdade.yaml'), 'w') as f:
        yaml.safe_dump({'semente': a.semente, 'cores_alvo': list(t2.cores_alvo), 'baloes': baloes}, f,
                       allow_unicode=True, sort_keys=False)
    for b in baloes:
        print(f"{b['cor']:>9} {'ALVO' if b['alvo'] else '    '} ({b['x']:.2f}, {b['y']:.2f}, {b['z']:.2f}) m")
    print(f'mundo em {saida}/sala_tarefa2.sdf')


if __name__ == '__main__':
    main()
