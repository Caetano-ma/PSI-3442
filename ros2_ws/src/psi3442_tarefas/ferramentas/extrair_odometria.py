#!/usr/bin/env python3
"""Extrai de um bag de simulação a pose VERDADEIRA (/gazebo/mini4pro/odometria) e a estimada (/estado), alinhadas
pelo instante de gravação, para validar a estimação (R05) e as métricas da Tarefa 1 contra a verdade.

Saída CSV: t_s, x_real_m, y_real_m, z_real_m, guinada_real_graus, x_est_m, y_est_m, z_est_m, erro_h_m, erro_v_m
Uso (com o ROS 2 do ambiente da simulação):  python3 extrair_odometria.py <pasta_do_bag> -o verdade.csv
"""
import argparse
import bisect
import csv
import math


def ler(pasta):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    leitor = rosbag2_py.SequentialReader()
    leitor.open(rosbag2_py.StorageOptions(uri=pasta), rosbag2_py.ConverterOptions('', ''))
    tipos = {t.name: t.type for t in leitor.get_all_topics_and_types()}
    odom, est = [], []
    while leitor.has_next():
        topico, dados, t_ns = leitor.read_next()
        if topico not in ('/gazebo/mini4pro/odometria', '/estado'):
            continue
        msg = deserialize_message(dados, get_message(tipos[topico]))
        t = t_ns * 1e-9
        if topico == '/estado':
            est.append((t, msg.x_m, msg.y_m, msg.z_m, msg.valido))
        else:
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            yaw = math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))
            odom.append((t, p.x, p.y, p.z, yaw))
    return odom, est


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bag')
    ap.add_argument('-o', '--saida', default='verdade.csv')
    a = ap.parse_args()
    odom, est = ler(a.bag)
    if not odom:
        raise SystemExit('bag sem /gazebo/mini4pro/odometria')
    tempos = [o[0] for o in odom]
    t0 = est[0][0] if est else odom[0][0]
    erros_h = []
    with open(a.saida, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['t_s', 'x_real_m', 'y_real_m', 'z_real_m', 'guinada_real_graus', 'x_est_m', 'y_est_m', 'z_est_m',
                    'erro_h_m', 'erro_v_m'])
        for t, x, y, z, valido in est:
            k = min(bisect.bisect_left(tempos, t), len(odom) - 1)
            _, xr, yr, zr, g = odom[k]
            eh, ev = math.hypot(x - xr, y - yr), z - zr
            if valido and zr > 0.3:
                erros_h.append(eh)
            w.writerow([f'{t - t0:.3f}', f'{xr:.4f}', f'{yr:.4f}', f'{zr:.4f}', f'{g:.2f}', f'{x:.4f}', f'{y:.4f}',
                        f'{z:.4f}', f'{eh:.4f}', f'{ev:.4f}'])
    if erros_h:
        print(f'{len(est)} amostras; erro horizontal da estimativa em voo: máx. {max(erros_h):.3f} m, '
              f'final {erros_h[-1]:.3f} m')


if __name__ == '__main__':
    main()
