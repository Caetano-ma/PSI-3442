"""Gera relatorio.pdf a partir de relatorio.md (ambiente conda 'sysml': markdown + weasyprint)."""
from pathlib import Path

import markdown
from weasyprint import HTML

PASTA = Path(__file__).resolve().parent

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm;
        @bottom-right { content: counter(page) " / " counter(pages); font-size: 8pt; color: #666; } }
body { font-family: 'Liberation Sans', 'DejaVu Sans', sans-serif; font-size: 9.5pt; line-height: 1.38; color: #222; }
h1 { font-size: 17pt; margin: 0 0 4pt 0; color: #1E3D14; }
h2 { font-size: 13pt; margin: 14pt 0 5pt 0; padding-bottom: 2pt; border-bottom: 1px solid #93C47D; color: #1E3D14;
     break-after: avoid; }
h3 { font-size: 11pt; margin: 10pt 0 4pt 0; break-after: avoid; }
p, li { margin: 3pt 0; }
ul { padding-left: 14pt; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 8pt 0; font-size: 8.5pt; break-inside: auto; }
tr { break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #E8F5E9; }
img { max-width: 100%; display: block; margin: 6pt auto; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8pt; background: #f4f4f4; padding: 0 2pt; }
hr { border: 0; border-top: 1px solid #ccc; margin: 8pt 0; }
a { color: #1C4587; text-decoration: none; }
"""


def main():
    md = (PASTA / "relatorio.md").read_text(encoding="utf-8")
    corpo = markdown.markdown(md, extensions=["tables", "sane_lists"])
    html = f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{corpo}</body></html>"
    HTML(string=html, base_url=str(PASTA)).write_pdf(PASTA / "relatorio.pdf")
    print(f"Gerado: {PASTA / 'relatorio.pdf'}")


if __name__ == "__main__":
    main()
