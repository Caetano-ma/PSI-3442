#!/usr/bin/env bash
# Recria o ambiente do projeto em outra máquina Linux x86_64 (sem sudo):
# Miniforge em ~/miniforge3 + ambiente conda "sysml" com o kernel SysML v2 (Pilot 0.63.1), JupyterLab,
# Graphviz, gerador de PDF (weasyprint) e matplotlib. Requer Java 21+ instalado no sistema.
set -euo pipefail

CONDA_DIR="$HOME/miniforge3"
ENV=sysml

command -v java >/dev/null || { echo "Instale o Java 21+ (ex.: sudo apt install openjdk-21-jre) e rode de novo."; exit 1; }

if [ ! -x "$CONDA_DIR/bin/conda" ]; then
    instalador="$(mktemp -d)/Miniforge3.sh"
    curl -fsSL -o "$instalador" https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
    bash "$instalador" -b -p "$CONDA_DIR"
fi

if [ ! -d "$CONDA_DIR/envs/$ENV" ]; then
    "$CONDA_DIR/bin/conda" create -n "$ENV" -y -c conda-forge \
        "jupyter-sysml-kernel=0.63.1" "python=3.12" "jupyterlab=4.*" "graphviz=2.*" nodejs \
        weasyprint markdown matplotlib nbclient
fi

export PATH="$CONDA_DIR/envs/$ENV/bin:$PATH"
jupyter labextension install "@systems-modeling/jupyterlab-sysml@0.63.1" >/dev/null 2>&1 || \
    echo "Aviso: extensão de sintaxe do JupyterLab não instalada (opcional)."
jupyter kernelspec list | grep -q sysml && echo "Ambiente pronto. Teste: cd modelo_sysml && $CONDA_DIR/envs/$ENV/bin/python executar_modelo.py"
