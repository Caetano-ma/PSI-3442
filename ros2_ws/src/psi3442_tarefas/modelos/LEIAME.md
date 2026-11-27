# Modelo de detecção de balões

`baloes_yolov8n.onnx` — YOLOv8 nano (ultralytics 8.4.220), 5 classes na ordem de `config/tarefas.yaml`
(`visao.classes`: vermelho, azul, verde, amarelo, roxo), entrada 416×416, exportado em ONNX opset 12.

- Pesos iniciais: `yolov8n.pt` (COCO). Treino: **1 época** em CPU (~20 min), 2 500 imagens sintéticas de
  `ferramentas/gerar_dataset_baloes.py --semente 1` (validação: 400 imagens, semente 1001). Hiperparâmetros em
  `ferramentas/treinar_yolo.py` (aumento de matiz pequeno: a classe é a cor).
- Validação sintética com o mesmo código do voo (`treinar_yolo.py avaliar`, ONNX Runtime): `metricas_detector.json`
  (precisão 0,918, revocação 0,869; revocação ≥ 0,91 para diâmetro aparente ≥ 60 px; 27 trocas de cor em 936 balões).
- Execução em voo: ONNX Runtime (CPU). O `cv2.dnn` do OpenCV 4.6 não carrega a cabeça do YOLOv8.
- Limitação: nunca visto em imagens reais. Antes da demonstração, ajustar com quadros reais da sala (mesmo script).
