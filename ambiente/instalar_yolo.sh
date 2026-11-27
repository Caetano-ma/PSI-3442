#!/bin/bash
# venv para gerar o conjunto sintético e treinar o detector (PyTorch CPU + ultralytics). Só é necessário para
# retreinar: o modelo exportado (ros2_ws/src/psi3442_tarefas/modelos/baloes_yolov8n.onnx) roda só com o OpenCV.
set -e
python3 -m venv ~/venvs/yolo
~/venvs/yolo/bin/pip install --upgrade pip
~/venvs/yolo/bin/pip install torch==2.15.0 torchvision --index-url https://download.pytorch.org/whl/cpu
~/venvs/yolo/bin/pip install ultralytics==8.4.220 onnx onnxslim
FERR="$(cd "$(dirname "$0")/../ros2_ws/src/psi3442_tarefas/ferramentas" && pwd)"
echo "Gerar dados:  python3 $FERR/gerar_dataset_baloes.py --saida ~/psi3442_dados/baloes --semente 1"
echo "Treinar:      ~/venvs/yolo/bin/python $FERR/treinar_yolo.py treinar --epocas 8"
echo "Avaliar:      python3 $FERR/treinar_yolo.py avaliar"
