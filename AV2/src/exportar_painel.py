"""Exporta os resultados agregados para o painel web."""

import json
import unicodedata
from zipfile import ZipFile

import pandas as pd

from .analises_clima import sinal_climatico
from .auditar_base import RAIZ_PROJETO, carregar_dados
from .preparar_alvos import preparar_painel

ARTEFATOS = RAIZ_PROJETO / "AV2" / "artefatos"
DESTINO = RAIZ_PROJETO / "AV2" / "painel" / "dados.js"
ALIASES_MALHA = {
    "COHAB - IBURA DE CIMA": "COHAB",
    "SITIO DOS PINTOS - SAO BRAS": "SITIO DOS PINTOS",
}


def chave(nome: str) -> str:
    return " ".join("".join(
        c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c)
    ).upper().split())


def prever_por_bairro(quadro, bairros):
    valores = {}
    for rotulo, cod in (("sem clima", "sem"), ("com clima", "com")):
        bloco = quadro.loc[quadro["cenario"].eq(rotulo)].set_index("BAIRRO")
        if not bloco.empty:
            if set(bloco.index) != set(bairros) or bloco.index.has_duplicates:
                raise ValueError("A previsão deve cobrir os 94 bairros exatamente uma vez.")
            valores[cod] = bloco.loc[bairros, "previsto"].round(4).tolist()
    return valores


def arred(valores, casas=3):
    return [None if pd.isna(v) else round(float(v), casas) for v in valores]


def resultados_gerais(painel, bairros):
    """Reúne as métricas, séries e indicadores exibidos pelo painel."""
    with ZipFile(ARTEFATOS / "teste_final.zip") as arquivo:
        metricas = pd.read_csv(arquivo.open("metricas.csv"))
        previsoes = pd.read_csv(arquivo.open("previsoes.csv"))
    teste = [{"semanas": int(m.horizonte_semanas), "cenario": m.cenario, "MAE": round(m.MAE, 3)}
             for m in metricas.itertuples(index=False)]

    # Janelas de quatro semanas do teste: total da cidade e série de cada bairro
    quatro = previsoes.loc[previsoes["horizonte_semanas"].eq(4)]
    datas = sorted(quatro["DATA_ALVO"].unique())
    largo = quatro.pivot_table(index=["BAIRRO", "DATA_ALVO"], columns="cenario", values="previsto")
    obs = quatro.loc[quatro["cenario"].eq("com clima")].set_index(["BAIRRO", "DATA_ALVO"])["observado"]
    indice = pd.MultiIndex.from_product([bairros, datas])
    largo, obs = largo.reindex(indice), obs.reindex(indice)
    serie_bairros = {"observado": [arred(obs.loc[b], 0) for b in bairros]}
    for rotulo, cod in (("com clima", "com"), ("sem clima", "sem"), ("baseline", "media")):
        serie_bairros[cod] = [arred(largo.loc[b, rotulo], 1) for b in bairros]
    cidade = {"observado": arred(obs.groupby(level=1).sum(), 0)}
    for rotulo, cod in (("com clima", "com"), ("sem clima", "sem"), ("baseline", "media")):
        cidade[cod] = arred(largo[rotulo].groupby(level=1).sum(), 0)

    # Ganho do clima por bairro no teste de quatro semanas (MAE sem clima - MAE com clima)
    erro = quatro.assign(erro=(quatro["previsto"] - quatro["observado"]).abs())
    mae = erro.pivot_table(index="BAIRRO", columns="cenario", values="erro", aggfunc="mean")
    ganho_bairro = arred((mae["sem clima"] - mae["com clima"]).loc[bairros], 2)
    total_bairro = obs.groupby(level=0).sum().loc[bairros]

    _, calendario = sinal_climatico(painel)

    with ZipFile(ARTEFATOS / "sensibilidades.zip") as arquivo:
        prior = pd.read_csv(arquivo.open("priorizacao_mensal.csv"))
    prior = prior.pivot_table(index="mes", columns="cenario", values="bairros_em_comum_top10")

    return {
        "teste": teste,
        "datas_teste": datas,
        "cidade_teste": cidade,
        "serie_bairros": serie_bairros,
        "ganho_bairro": ganho_bairro,
        "total_bairro_teste": arred(total_bairro, 0),
        "calendario": {"chuva": arred(calendario["chuva"], 1), "notificacoes": arred(calendario["notificacoes"], 0)},
        "priorizacao": [{"mes": m, "com": round(r["com clima"], 0), "sem": round(r["sem clima"], 0),
                         "media": round(r["média móvel"], 0)} for m, r in prior.iterrows()],
    }


def main():
    painel = preparar_painel(*carregar_dados())
    mapa = json.loads((RAIZ_PROJETO / "prototype" / "map-paths.json").read_text(encoding="utf-8-sig"))
    nomes_malha = [chave(item["name"]) for item in mapa]
    bairros = [ALIASES_MALHA.get(nome, nome) for nome in nomes_malha]
    if len(bairros) != 94 or set(bairros) != set(painel["BAIRRO"]):
        raise ValueError("Os bairros da malha divergem do painel.")

    with ZipFile(ARTEFATOS / "mes_calendario.zip") as arquivo:
        cobertura = pd.read_csv(arquivo.open("cobertura_mes.csv"))
        observados = pd.read_csv(arquivo.open("observados_mes.csv"))
        previstos = pd.read_csv(arquivo.open("previsoes.csv"))
    meses = []
    for item in cobertura.loc[cobertura["CONJUNTO_MES"].eq("teste")].itertuples(index=False):
        totais = observados.loc[observados["MES_ALVO"].eq(item.MES_ALVO)].set_index("BAIRRO")
        meses.append({
            "inicio": item.MES_ALVO, "emissao": item.DATA_EMISSAO,
            "observado": totais.loc[bairros, "observado"].tolist(),
            **prever_por_bairro(previstos.loc[previstos["MES_ALVO"].eq(item.MES_ALVO)], bairros),
        })

    with ZipFile(ARTEFATOS / "teste_final.zip") as arquivo:
        semanais = pd.read_csv(arquivo.open("previsoes.csv"))
    semanais = semanais.loc[semanais["horizonte_semanas"].eq(1)]
    semanas = []
    inicio = pd.Timestamp(meses[0]["inicio"])
    fim = pd.Timestamp(meses[-1]["inicio"]) + pd.offsets.MonthEnd()
    periodo = painel.loc[painel["COBERTURA_DENGUE"] &
                        (painel["DATA_SEMANA"] + pd.Timedelta(days=6)).ge(inicio) &
                        painel["DATA_SEMANA"].le(fim)]
    for data, grupo in periodo.groupby("DATA_SEMANA"):
        rotulo = data.date().isoformat()
        semanas.append({
            "inicio": rotulo,
            "fim": (data + pd.Timedelta(days=6)).date().isoformat(),
            "emissao": (data - pd.Timedelta(days=1)).date().isoformat(),
            "observado": grupo.set_index("BAIRRO").loc[bairros, "NOTIFICACOES_SEMANAIS"].astype(int).tolist(),
            **prever_por_bairro(semanais.loc[semanais["DATA_ALVO"].eq(rotulo)], bairros),
        })
    with ZipFile(ARTEFATOS / "previsao_anual.zip") as arquivo:
        anuais = pd.read_csv(arquivo.open("previsoes.csv"))
        metodo_anual = json.loads(arquivo.read("manifesto.json"))["regra"]
    anos = []
    for ano, grupo in anuais.groupby("ano"):
        por_bairro = grupo.set_index("BAIRRO").loc[bairros]
        item = {"inicio": f"{ano}-01-01", "tipo": por_bairro["tipo"].iloc[0]}
        if por_bairro["observado"].notna().all():
            item["observado"] = por_bairro["observado"].astype(int).tolist()
        if por_bairro["previsto"].notna().all():
            item["sem"] = por_bairro["previsto"].round(4).tolist()
            item["data_corte"] = f"{ano - 1}-12-31"
        anos.append(item)
    pacote = {"mapa": mapa, "meses": meses, "semanas": semanas, "anos": anos, "metodo_anual": metodo_anual,
              "resultados": resultados_gerais(painel, bairros)}
    texto = json.dumps(pacote, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    DESTINO.write_text(f"globalThis.AnteceDengue = {texto};\n", encoding="utf-8")
    print(f"{len(bairros)} bairros, {len(anos)} anos, {len(meses)} meses e {len(semanas)} semanas em {DESTINO}")


if __name__ == "__main__":
    main()
