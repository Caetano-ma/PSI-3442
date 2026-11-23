"""Gera a matriz requisito -> função -> elemento -> módulo/arquivo -> teste/evidência a partir dos arquivos .sysml
e confere a consistência entre os níveis. Sai com código 1 se houver pendências.

Uso: python3 gerar_matriz.py   (gera rastreabilidade/matriz_q1.csv e rastreabilidade/matriz_q1.md)
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

PASTA = Path(__file__).resolve().parent
SAIDA = PASTA / "rastreabilidade"


def ler(nome):
    return (PASTA / nome).read_text(encoding="utf-8")


def ultimo(caminho):
    return caminho.split(".")[-1]


def main():
    comum, n0, n1, nn, ver = (ler(f) for f in
                              ("00_Comum.sysml", "01_Nivel0.sysml", "02_Nivel1.sysml", "03_NivelN.sysml", "04_Verificacao.sysml"))

    # requisito: uso -> (id, definição)
    ids = dict(re.findall(r"requirement def <(\w+)> (\w+)", comum))
    id_por_def = {d: i for i, d in ids.items()}
    requisitos = {uso: (id_por_def[d], d) for uso, d in re.findall(r"requirement (\w+) : (\w+);", n0)}

    # requisito -> função (nível 1)
    funcoes_do_req = defaultdict(list)
    for req, func in re.findall(r"satisfy Nivel0::(\w+) by funcaoGlobal\.(\w+);", n1):
        funcoes_do_req[req].append(func)

    # função -> elemento do nível 1
    elementos_da_func = defaultdict(list)
    for func, alvo in re.findall(r"allocate funcaoGlobal\.(\w+) to ([\w.]+);", n1):
        elementos_da_func[func].append(alvo.replace("sistema.", ""))

    # função -> módulo do nível n
    modulos_da_func = defaultdict(list)
    for func, alvo in re.findall(r"allocate Nivel1::funcaoGlobal\.(\w+) to ([\w.]+);", nn):
        modulos_da_func[func].append(ultimo(alvo))

    # módulo (uso) -> definição -> arquivo
    def_do_modulo = dict(re.findall(r"^\s+part (\w+) : (\w+);", nn, re.M))
    arquivo_da_def = dict(re.findall(
        r"part def (\w+) :> ModuloSoftware \{.*?arquivoCodigo = \"([^\"]+)\"", nn, re.S))

    # requisito satisfeito diretamente por módulo no nível n
    modulos_do_req = defaultdict(set)
    for req, alvo in re.findall(r"satisfy Nivel0::(\w+) by sistemaN\.([\w.]+);", nn):
        modulos_do_req[req].add(ultimo(alvo))

    # testes
    testes_do_req = defaultdict(list)
    for tid, corpo in re.findall(r"verification def <(\w+)> \w+ \{(.*?)\n    \}", ver, re.S):
        req = re.search(r"verify Nivel0::(\w+);", corpo).group(1)
        amb = re.search(r'ambiente : String = "([^"]+)"', corpo).group(1)
        evid = re.search(r'evidencia : String = "([^"]+)"', corpo).group(1)
        arq = re.search(r'arquivoTeste : String = "([^"]+)"', corpo).group(1)
        testes_do_req[req].append((tid, amb, evid, arq))

    linhas, pendencias = [], []
    for req, (rid, rdef) in requisitos.items():
        funcs = funcoes_do_req.get(req, [])
        testes = testes_do_req.get(req, [])
        if not funcs:
            pendencias.append(f"{rid}: nenhuma função satisfaz o requisito")
        if not testes:
            pendencias.append(f"{rid}: nenhum caso de verificação")
        alcancados = set()
        txt_testes = "; ".join(f"{t[0]} ({t[1]}) — {t[3]}" for t in testes)
        txt_evid = "; ".join(f"{t[0]}: {t[2]}" for t in testes)
        for func in funcs:
            elems = elementos_da_func.get(func, [])
            mods = modulos_da_func.get(func, [])
            if not elems:
                pendencias.append(f"{rid}/{func}: função sem alocação no nível 1")
            if not mods:
                pendencias.append(f"{rid}/{func}: função sem módulo no nível n")
            for mod in mods or ["—"]:
                alcancados.add(mod)
                d = def_do_modulo.get(mod)
                arq = arquivo_da_def.get(d, "—")
                if mod != "—" and arq == "—":
                    pendencias.append(f"{rid}/{func}/{mod}: módulo sem arquivo de código")
                linhas.append([rid, rdef, func, ", ".join(elems) or "—", mod, arq, txt_testes, txt_evid])
        for mod in sorted(modulos_do_req.get(req, set()) - alcancados):
            pendencias.append(f"{rid}: módulo {mod} satisfaz o requisito no nível n mas não vem de nenhuma função ligada a ele")

    SAIDA.mkdir(exist_ok=True)
    cab = ["Requisito", "Definição", "Função (nível 1)", "Elemento (nível 1)", "Módulo (nível n)",
           "Arquivo de código", "Teste", "Evidência"]
    with open(SAIDA / "matriz_q1.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([cab] + linhas)
    with open(SAIDA / "matriz_q1.md", "w", encoding="utf-8") as f:
        f.write("# Matriz de rastreabilidade — Questão 1\n\n_Gerada por `gerar_matriz.py` a partir do modelo SysML._\n\n")
        f.write("| " + " | ".join(cab) + " |\n|" + "---|" * len(cab) + "\n")
        for lin in linhas:
            f.write("| " + " | ".join(c.replace("|", "/") for c in lin) + " |\n")

    print(f"{len(linhas)} linhas -> {SAIDA / 'matriz_q1.csv'} e matriz_q1.md")
    if pendencias:
        print(f"{len(pendencias)} pendência(s) de consistência:")
        print("\n".join("  - " + p for p in pendencias))
        return 1
    print("Consistência entre níveis: OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
