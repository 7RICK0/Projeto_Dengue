"""Executa o notebook da AV2 do zero, em memória, e confere o resultado.

Rodar da raiz do repositório (leva cerca de 2 minutos):

    python -B AV2/tests/rodar_notebook_do_zero.py

O arquivo do notebook não é alterado. O script verifica:
1. nenhuma célula com erro;
2. 28 células de código e 20 figuras;
3. tabelas e textos gerados agora iguais aos salvos no notebook (resultados reproduzidos),
   ignorando só a coluna que mede o tempo de treino em segundos.
4. a primeira célula de código gera o botão que abre o painel (o endereço muda a cada execução e não é comparado).
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parents[2]
NOTEBOOK = RAIZ / "AV2" / "notebooks" / "AnteceDengue_AV2_modelagem.ipynb"
CELULAS_DE_CODIGO = 28
FIGURAS = 20
CELULA_DO_PAINEL = "painel-link"  # mostra o botão do painel; o endereço muda a cada execução


COLUNAS_DE_TEMPO = ("segundos_ajuste",)  # duração do treino: muda a cada execução, não é resultado


def sem_colunas_de_tempo(tabela: str) -> str:
    """Apaga, numa tabela do pandas em texto, as colunas que medem tempo de execução."""
    linhas = tabela.splitlines()
    if not linhas:
        return tabela
    for coluna in COLUNAS_DE_TEMPO:
        inicio = linhas[0].find(coluna)
        if inicio >= 0:
            fim = inicio + len(coluna)
            linhas = [linha[:inicio] + " " * max(0, min(len(linha), fim) - inicio) + linha[fim:] for linha in linhas]
    return "\n".join(linhas)


def textos(celula) -> str:
    """Saídas em texto da célula, sem endereços de memória nem tempos, que mudam a cada execução."""
    partes = []
    for saida in celula.get("outputs", []):
        if saida.get("output_type") == "stream":
            partes.append(saida.get("text", ""))
        dados = saida.get("data", {})
        partes.append(sem_colunas_de_tempo(dados.get("text/plain", "")))
    texto = "".join(partes)
    return re.sub(r"0x[0-9a-fA-F]+", "0x", texto)


def main() -> int:
    salvo = nbformat.read(NOTEBOOK, as_version=4)
    novo = nbformat.read(NOTEBOOK, as_version=4)
    inicio = time.time()
    NotebookClient(novo, timeout=1200, kernel_name="python3",
                   resources={"metadata": {"path": str(NOTEBOOK.parent)}}).execute()
    duracao = time.time() - inicio

    codigo_novo = [c for c in novo.cells if c.cell_type == "code"]
    codigo_salvo = [c for c in salvo.cells if c.cell_type == "code"]
    erros = [i for i, c in enumerate(codigo_novo) for s in c.outputs if s.output_type == "error"]
    figuras = sum(1 for c in codigo_novo for s in c.outputs if "image/png" in s.get("data", {}))
    diferentes = [c.get("id") for c, s in zip(codigo_novo, codigo_salvo)
                  if c.get("id") != CELULA_DO_PAINEL and textos(c) != textos(s)]
    painel = next(c for c in codigo_novo if c.get("id") == CELULA_DO_PAINEL)
    botao_do_painel = any("abrir_painel.html" in str(s.get("data", {}).get("text/html", "")) for s in painel.outputs)

    print(f"Tempo de execução: {duracao:.0f} s")
    print(f"Células de código: {len(codigo_novo)} (esperado {CELULAS_DE_CODIGO})")
    print(f"Células com erro: {len(erros)}")
    print(f"Figuras: {figuras} (esperado {FIGURAS})")
    print(f"Células com texto diferente do salvo: {len(diferentes)} {diferentes or ''}")
    print(f"Botão do painel gerado na primeira célula: {'sim' if botao_do_painel else 'NÃO'}")

    ok = not erros and len(codigo_novo) == CELULAS_DE_CODIGO and figuras == FIGURAS and not diferentes and botao_do_painel
    print("NOTEBOOK_OK" if ok else "NOTEBOOK_FALHOU")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
