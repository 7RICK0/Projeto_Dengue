"""Reconstitui os totais por bairro e mês a partir das fontes fixadas na AV1."""

from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io
import json
import re
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

from .auditar_base import ARTEFATOS_AV1, RAIZ_PROJETO


def _funcoes_av1() -> dict:
    """Reutiliza somente as funções puras de leitura e normalização da AV1."""
    caminho = RAIZ_PROJETO / "AV1" / "notebooks" / "AnteceDengue_AV1_revisada.ipynb"
    notebook = json.loads(caminho.read_text(encoding="utf-8"))
    fonte, = (
        "".join(celula["source"]) for celula in notebook["cells"]
        if celula["cell_type"] == "code" and "".join(celula["source"]).startswith("def sem_acentos(")
    )
    nomes = {
        "sem_acentos", "nome_padrao", "coluna_padrao", "ler_csv_bytes",
        "selecionar_notificacoes", "inicio_semana", "datas_notificacao", "codigo_inteiro",
    }
    arvore = ast.parse(fonte)
    arvore.body = [
        item for item in arvore.body if (
            isinstance(item, ast.FunctionDef) and item.name in nomes
        ) or (
            isinstance(item, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "ALIASES" for t in item.targets)
        )
    ]
    contexto = {"pd": pd, "io": io, "re": re, "unicodedata": unicodedata}
    exec(compile(arvore, str(caminho), "exec"), contexto)
    return contexto


def _baixar(url: str, hash_esperado: str) -> bytes:
    endereco = urlparse(url)
    if endereco.scheme != "https" or endereco.hostname != "dados.recife.pe.gov.br":
        raise ValueError(f"Origem municipal inesperada: {url}")
    with urlopen(Request(url, headers={"User-Agent": "AnteceDengue-academico/3"}), timeout=45) as resposta:
        payload = resposta.read()
    if sha256(payload).hexdigest() != hash_esperado:
        raise ValueError(f"A fonte municipal diverge da versão da AV1: {endereco.path.rsplit('/', 1)[-1]}.")
    return payload


def observar_meses(painel: pd.DataFrame, intervalos: list) -> pd.DataFrame:
    """Retorna contagens mensais verificadas, sem gravar registros individuais."""
    funcoes = _funcoes_av1()
    fontes = pd.read_csv(ARTEFATOS_AV1 / "relatorios" / "aquisicao_por_ano.csv")
    manifesto = json.loads((ARTEFATOS_AV1 / "manifesto_execucao.json").read_text(encoding="utf-8-sig"))
    mapa, = (item for item in manifesto["fontes"] if item["origem"].endswith("/bairros-do-recife.geojson"))

    def carregar_ano(linha):
        conteudo = _baixar(linha.url, linha.sha256)
        selecionado = funcoes["selecionar_notificacoes"](funcoes["ler_csv_bytes"](conteudo), linha.ano)
        if len(selecionado) != linha.registros:
            raise ValueError(f"Número de registros divergente no arquivo de {linha.ano}.")
        return selecionado

    with ThreadPoolExecutor(max_workers=4) as executor:
        partes = list(executor.map(carregar_ano, fontes.itertuples(index=False)))
    dados = pd.concat(partes, ignore_index=True)
    geo = json.loads(_baixar(mapa["origem"], mapa["sha256"]))
    nome_padrao = funcoes["nome_padrao"]
    nomes = {
        int(item["properties"]["CBAIRRCODI"]) // 10: nome_padrao(item["properties"]["EBAIRRNOME"])
        for item in geo["features"]
    }

    dados["DT_NOTIFIC"] = funcoes["datas_notificacao"](dados["DT_NOTIFIC"])
    for coluna in ("ID_BAIRRO", "CLASSI_FIN"):
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")
    dados["ID_AGRAVO"] = dados["ID_AGRAVO"].astype("string").str.strip().str.upper()
    if dados["ID_AGRAVO"].dropna().ne("A90").any():
        raise ValueError("A fonte nominal de dengue contém códigos diferentes de A90.")
    dados["NU_NOTIFIC"] = funcoes["codigo_inteiro"](dados["NU_NOTIFIC"])
    campos = [
        "NU_NOTIFIC", "DT_NOTIFIC", "ID_BAIRRO", "NM_BAIRRO", "CLASSI_FIN",
        "ID_MUNICIPIO_RESIDENCIA", "ID_AGRAVO",
    ]
    duplicadas = dados["NU_NOTIFIC"].notna() & dados.duplicated(campos)
    dados = dados.loc[~duplicadas].copy()
    municipio = funcoes["codigo_inteiro"](dados["ID_MUNICIPIO_RESIDENCIA"])
    dados["BAIRRO"] = dados["ID_BAIRRO"].map(nomes).fillna(dados["NM_BAIRRO"].map(nome_padrao))
    bairros = sorted(painel["BAIRRO"].unique())
    registros = dados.loc[
        (municipio.isna() | municipio.isin(("261160", "2611606")))
        & dados["DT_NOTIFIC"].notna() & dados["BAIRRO"].isin(bairros),
        ["BAIRRO", "DT_NOTIFIC"],
    ].copy()

    # Cada bairro-semana coberto precisa reproduzir exatamente o painel já auditado.
    semanais = registros.groupby([funcoes["inicio_semana"](registros["DT_NOTIFIC"]), "BAIRRO"]).size()
    previamente = painel.loc[painel["COBERTURA_DENGUE"]].set_index(["DATA_SEMANA", "BAIRRO"])
    comparaveis = semanais.reindex(previamente.index, fill_value=0)
    if not comparaveis.eq(previamente["NOTIFICACOES_SEMANAIS"]).all():
        raise ValueError("A reconstituição diária não reproduz o painel semanal da AV1.")

    dias_cobertos = set()
    for inicio, fim in intervalos:
        dias_cobertos.update(pd.date_range(inicio, fim))
    meses = [
        mes for mes in pd.date_range(min(dias_cobertos), max(dias_cobertos), freq="MS")
        if all(d in dias_cobertos for d in pd.date_range(mes, mes + pd.offsets.MonthEnd()))
    ]
    por_mes = registros.groupby([registros["DT_NOTIFIC"].dt.to_period("M").dt.to_timestamp(), "BAIRRO"]).size()
    grade = pd.MultiIndex.from_product([meses, bairros], names=["MES_ALVO", "BAIRRO"])
    return por_mes.reindex(grade, fill_value=0).rename("observado").reset_index()
