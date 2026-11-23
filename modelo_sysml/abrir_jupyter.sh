#!/usr/bin/env bash
# Abre o modelo SysML 2.0 no JupyterLab (kernel SysML v2 Pilot 0.63.1, ambiente conda "sysml" em ~/miniforge3).
set -e
cd "$(dirname "$0")"
export PATH="$HOME/miniforge3/envs/sysml/bin:$PATH"
if [ ! -f Modelo.ipynb ] || [ -n "$(find . -maxdepth 1 -name '*.sysml' -newer Modelo.ipynb)" ]; then
    python executar_modelo.py --so-gerar
fi
exec jupyter lab Modelo.ipynb
