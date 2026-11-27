"""Monta o notebook do modelo SysML 2.0, executa no kernel 'sysml', reporta erros e exporta as vistas.

Uso (com o ambiente conda 'sysml'):
    python executar_modelo.py            # gera, executa e exporta vistas/
    python executar_modelo.py --so-gerar # apenas gera Modelo.ipynb (para abrir no JupyterLab)
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PASTA = Path(__file__).resolve().parent
NOTEBOOK = PASTA / "Modelo.ipynb"
VISTAS = PASTA / "vistas"

VISOES = [
    ("01_nivel0_contexto", "Nível 0 — contexto operacional e fronteira do sistema",
     "%viz --view=interconnection Nivel0::ContextoOperacional"),
    ("02_nivel0_sistema", "Nível 0 — componentes do sistema de missões",
     "%viz --view=interconnection Nivel0::SistemaMissoesAutonomas"),
    ("03_nivel0_cenario", "Nível 0 — cenário de operação",
     "%viz --view=action Nivel0::CenarioOperacao"),
    ("04_requisitos", "Requisitos das Questões 1 e 2",
     "%viz --view=tree --style=LR Comum::RequisitosQ1 Comum::RequisitosQ2"),
    ("05_nivel1_nos_ros2", "Nível 1 — nós ROS 2 e suas portas de tópico (pub = porta, sub = porta conjugada ~)",
     "%viz --view=tree --style=LR Nivel1::InterfaceOperador Nivel1::GerenciadorTarefas Nivel1::Tarefa1VooFamiliarizacao "
     "Nivel1::Tarefa2Baloes Nivel1::Registro Nivel1::EstimacaoEstado Nivel1::ControleVoo Nivel1::VisaoComputacional "
     "Nivel1::MapeamentoLocal "
     "Nivel1::SupervisaoSeguranca Nivel1::NoPonteDJI"),
    ("06_nivel1_funcional", "Nível 1 — decomposição funcional da função global",
     "%viz --view=action Nivel1::ExecutarTarefaAutonoma"),
    ("07_nivel1_modos", "Nível 1 — modos de operação (executar tarefa 1 / 2)",
     "%viz --view=state Nivel1::ModosOperacao"),
    ("08_niveln_drone_sdk", "Nível n — drone caixa-preta explorado pelo SDK",
     "%viz --view=tree --style=LR NivelN::DroneN NivelN::SdkControladorVoo NivelN::SdkBateria "
     "NivelN::SdkEnlace NivelN::SdkPercepcao"),
    ("09_niveln_modulos_ros2", "Nível n — módulos dos nós ROS 2",
     "%viz --view=tree --style=LR NivelN::InterfaceOperadorN NivelN::GerenciadorTarefasN NivelN::Tarefa1N "
     "NivelN::EstimacaoEstadoN NivelN::ControleVooN NivelN::SupervisaoSegurancaN NivelN::RegistroN NivelN::NoPonteDJIN"),
    ("09b_niveln_modulos_tarefa2", "Nível n — módulos da Tarefa 2, visão computacional e mapeamento local",
     "%viz --view=tree --style=LR NivelN::Tarefa2N NivelN::VisaoComputacionalN NivelN::MapeamentoLocalN"),
    ("10_niveln_app_ponte", "Nível n — módulos do app ponte (celular ligado ao controle)",
     "%viz --view=tree --style=LR NivelN::AppPonteDJIN"),
    ("11_niveln_contratos", "Nível n — contratos de interface",
     "%viz --view=tree --style=LR NivelN::ContratoSdkControladorVoo NivelN::ContratoSocketPonte "
     "NivelN::ContratoTopicoCmdVel NivelN::ContratoTopicoTelemetria"),
    ("12_niveln_estados_tarefa1", "Nível n — máquina de estados da Tarefa 1 (P06)",
     "%viz --view=state NivelN::MaquinaEstadosTarefa1"),
    ("13_niveln_ciclo", "Nível n — ciclo de controle a 10 Hz",
     "%viz --view=action NivelN::CicloControle"),
    ("12b_niveln_estados_tarefa2", "Nível n — máquina de estados da Tarefa 2 (R03, R04, R07)",
     "%viz --view=state NivelN::MaquinaEstadosTarefa2"),
    ("13b_niveln_ciclo_tarefa2", "Nível n — malha fechada imagem -> percepção -> decisão -> comando (Tarefa 2)",
     "%viz --view=action NivelN::CicloPercepcaoDecisao"),
    ("14_verificacao", "Casos de verificação da Questão 1",
     "%viz --view=tree --style=LR VerificacaoQ1"),
    ("15_verificacao_q2", "Casos de verificação da Questão 2",
     "%viz --view=tree --style=LR VerificacaoQ2"),
]


def montar_notebook():
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "sysml", "display_name": "SysML", "language": "sysml"}
    nb.cells.append(nbformat.v4.new_markdown_cell(
        "# PSI3442 — P2 — Sistema de Missões Autônomas: modelo SysML 2.0 (níveis 0, 1 e n)\n\n"
        "As células de código abaixo são cópias dos arquivos `*.sysml` desta pasta. Edite os arquivos e rode "
        "`python executar_modelo.py --so-gerar` para atualizar o notebook. Execute tudo com *Run → Run All Cells*."))
    for arq in sorted(PASTA.glob("*.sysml")):
        nb.cells.append(nbformat.v4.new_markdown_cell(f"## `{arq.name}`"))
        nb.cells.append(nbformat.v4.new_code_cell(arq.read_text(encoding="utf-8")))
    nb.cells.append(nbformat.v4.new_markdown_cell("# Vistas"))
    for _, titulo, comando in VISOES:
        nb.cells.append(nbformat.v4.new_markdown_cell(f"### {titulo}"))
        nb.cells.append(nbformat.v4.new_code_cell(comando))
    return nb


def exportar_vistas(nb):
    VISTAS.mkdir(exist_ok=True)
    rsvg = shutil.which("rsvg-convert") or str(Path(sys.executable).parent / "rsvg-convert")
    celulas_viz = [c for c in nb.cells if c.cell_type == "code" and c.source.startswith("%viz")]
    for (nome, _, _), celula in zip(VISOES, celulas_viz):
        svg = next((o.data["image/svg+xml"] for o in celula.get("outputs", [])
                    if o.output_type in ("display_data", "execute_result") and "image/svg+xml" in o.data), None)
        if svg is None:
            print(f"  [sem imagem] {nome}")
            continue
        destino = VISTAS / f"{nome}.svg"
        destino.write_text(svg if isinstance(svg, str) else "".join(svg), encoding="utf-8")
        subprocess.run([rsvg, "-z", "1.5", "-b", "white", "-o", str(destino.with_suffix(".png")), str(destino)],
                       check=False)
        print(f"  {destino.relative_to(PASTA)} (+ .png)")


def coletar_erros(nb):
    erros = []
    for celula in nb.cells:
        for o in celula.get("outputs", []):
            texto = o.get("text", "") if o.output_type == "stream" else ""
            if o.output_type == "error":
                texto = f"ERROR: {o.ename} {o.evalue}"
            erros += [linha for linha in texto.splitlines() if re.match(r"\s*ERROR", linha)]
    return erros


def main():
    nb = montar_notebook()
    if "--so-gerar" in sys.argv:
        nbformat.write(nb, NOTEBOOK)
        print(f"Notebook gerado: {NOTEBOOK}")
        return 0
    print("Executando o modelo no kernel SysML (leva ~1 min na primeira vez)...")
    NotebookClient(nb, timeout=900, kernel_name="sysml", allow_errors=True).execute(
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    nbformat.write(nb, NOTEBOOK)
    erros = coletar_erros(nb)
    if erros:
        print(f"{len(erros)} erro(s) no modelo:")
        print("\n".join(erros))
    else:
        print("Modelo válido: nenhum erro de sintaxe ou de resolução de nomes.")
    print("Vistas exportadas:")
    exportar_vistas(nb)
    print(f"Notebook com resultados: {NOTEBOOK}")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
