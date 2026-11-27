"""Gera relatorio.pdf (de relatorio.md) e o ZIP da entrega final do Moodle (ambiente conda 'sysml': markdown +
weasyprint). Rodar antes: python3 gerar_graficos.py (Python do sistema, com matplotlib).

    ~/miniforge3/envs/sysml/bin/python gerar_entrega.py

O ZIP leva: relatório e apresentação (apresentacao.pdf, exportada do artefato de slides, se presente), README,
código-fonte da aplicação ROS 2 e do adaptador DJI (sem builds), modelo SysML editável e vistas, matrizes de
rastreabilidade, configurações, testes, ferramentas, roteiro de ensaios e resultados/logs de simulação
(identificados em ensaios/simulacao/). Sem a App Key, sem bags completos e sem o enunciado.
"""
import re
import zipfile
from pathlib import Path

import markdown
from weasyprint import HTML

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parent.parent

CSS = """
@page { size: A4; margin: 17mm 15mm 17mm 15mm;
        @bottom-right { content: counter(page) " / " counter(pages); font-size: 8pt; color: #666; } }
body { font-family: 'Liberation Sans', 'DejaVu Sans', sans-serif; font-size: 9.3pt; line-height: 1.36; color: #222; }
h1 { font-size: 16pt; margin: 0 0 4pt 0; color: #14213D; }
h2 { font-size: 12.5pt; margin: 13pt 0 5pt 0; padding-bottom: 2pt; border-bottom: 1px solid #2F6FBF; color: #14213D;
     break-after: avoid; }
h3 { font-size: 10.5pt; margin: 9pt 0 3pt 0; break-after: avoid; color: #14213D; }
p, li { margin: 3pt 0; }
ul { padding-left: 14pt; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 8pt 0; font-size: 8.2pt; break-inside: auto; }
tr { break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 2.5pt 4.5pt; vertical-align: top; text-align: left; }
th { background: #E6EEF8; }
img { max-width: 100%; max-height: 105mm; display: block; margin: 5pt auto; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.8pt; background: #f4f4f4; padding: 0 2pt; }
hr { border: 0; border-top: 1px solid #ccc; margin: 7pt 0; }
a { color: #1C4587; text-decoration: none; }
"""

CONTEUDO = [
    "README.md", "CLAUDE.md", ".gitignore",
    "modelo_sysml/*.sysml", "modelo_sysml/Modelo.ipynb", "modelo_sysml/*.py", "modelo_sysml/*.sh",
    "modelo_sysml/vistas/*", "modelo_sysml/rastreabilidade/*",
    "diagramas/*",
    "ambiente/*",
    "ensaios/*.md", "ensaios/*.py", "ensaios/simulacao/**/*",
    "ros2_ws/README.md", "ros2_ws/docker/*",
    "ros2_ws/src/**/*",
    "android_ponte/*.kts", "android_ponte/*.sh", "android_ponte/*.md", "android_ponte/gradle.properties",
    "android_ponte/gradlew", "android_ponte/gradle/**/*", "android_ponte/app/*.kts", "android_ponte/app/*.pro",
    "android_ponte/app/src/**/*",
    "entregas/2026-12-04_final/*.md", "entregas/2026-12-04_final/*.py", "entregas/2026-12-04_final/figuras/*",
]
EXCLUIR = ("__pycache__", ".pytest_cache", "/build/", "/.gradle/", ".DS_Store", "local.properties")


def gerar_pdf():
    md = (PASTA / "relatorio.md").read_text(encoding="utf-8")
    # o Markdown exige linha em branco antes de uma lista que segue um parágrafo
    md = re.sub(r"(?m)^(?![ \t]*(?:[-*] |\d+\. |\|))(.+)\n(?=[ \t]*(?:[-*] |\d+\. ))", r"\1\n\n", md)
    corpo = markdown.markdown(md, extensions=["tables", "sane_lists"])
    html = (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><style>{CSS}</style></head>"
            f"<body>{corpo}</body></html>")
    HTML(string=html, base_url=str(PASTA)).write_pdf(PASTA / "relatorio.pdf")
    print(f"Gerado: {PASTA / 'relatorio.pdf'}")


def montar_zip():
    destino = PASTA / "PSI3442_P2_entrega_final_13681130.zip"
    vistos = set()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(PASTA / "relatorio.pdf", "relatorio.pdf")
        if (PASTA / "apresentacao.pdf").exists():
            z.write(PASTA / "apresentacao.pdf", "apresentacao.pdf")
        else:
            print("aviso: apresentacao.pdf ausente (exporte o artefato de slides para esta pasta)")
        for padrao in CONTEUDO:
            for arq in sorted(RAIZ.glob(padrao)):
                rel = arq.relative_to(RAIZ).as_posix()
                if arq.is_file() and rel not in vistos and not any(e in "/" + rel for e in EXCLUIR):
                    vistos.add(rel)
                    z.write(arq, "repositorio/" + rel)
    print(f"Gerado: {destino} ({len(vistos)} arquivos do repositório, {destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    gerar_pdf()
    montar_zip()
