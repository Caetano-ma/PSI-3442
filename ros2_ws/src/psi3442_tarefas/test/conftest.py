import os
import sys

# permite rodar `pytest` direto na árvore de fontes, sem colcon nem ROS 2
PACOTE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for caminho in (PACOTE, os.path.dirname(os.path.abspath(__file__)), os.path.join(PACOTE, 'ferramentas')):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
