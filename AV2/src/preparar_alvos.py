"""Prepara os horizontes de previsão a partir do painel bairro-semana da AV1."""

from __future__ import annotations

import json

import pandas as pd

from .auditar_base import carregar_dados


ALVO_SEMANAL = "NOTIFICACOES_PROXIMA_SEMANA"
ALVO_QUATRO_SEMANAS = "NOTIFICACOES_PROXIMAS_4_SEMANAS"
FIM_TESTE_CLIMATICO = pd.Timestamp("2021-11-08")
CONJUNTOS = ("treino", "validacao", "teste")


def preparar_painel(dados: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Calcula alvos e cortes da coorte comum sem modificar o painel da AV1."""
    painel = dados.rename(columns={"CONJUNTO": "CONJUNTO_AV1"}).copy()
    for coluna in ("DATA_SEMANA", "DATA_ALVO"):
        painel[coluna] = pd.to_datetime(painel[coluna], format="%Y-%m-%d")
        if painel[coluna].isna().any() or painel[coluna].dt.dayofweek.ne(0).any():
            raise ValueError(f"{coluna} deve conter segundas-feiras válidas.")
    if painel["BAIRRO"].isna().any() or painel.duplicated(["BAIRRO", "DATA_SEMANA"]).any():
        raise ValueError("O painel precisa ter uma linha por bairro e semana.")
    if not painel["DATA_ALVO"].eq(painel["DATA_SEMANA"] + pd.Timedelta(weeks=1)).all():
        raise ValueError("DATA_ALVO precisa apontar para a semana seguinte.")

    for coluna in ("COBERTURA_DENGUE", "ELEGIVEL_SEM_CLIMA", "ELEGIVEL_AV2"):
        valores = painel[coluna].astype(str).str.lower().map(
            {"true": True, "false": False, "1": True, "0": False}
        )
        if valores.isna().any():
            raise ValueError(f"{coluna} contém valores que não são booleanos.")
        painel[coluna] = valores.astype(bool)

    corte_validacao = pd.Timestamp(config["corte_validacao"])
    corte_teste = pd.Timestamp(config["corte_teste"])
    if not corte_validacao < corte_teste <= FIM_TESTE_CLIMATICO:
        raise ValueError("Cortes temporais fora de ordem.")
    if config["alvo"] != ALVO_SEMANAL:
        raise ValueError("Alvo semanal divergente na configuração da AV1.")

    # A busca por data preserva lacunas. Um deslocamento por linha poderia pulá-las.
    observado = painel.set_index(["BAIRRO", "DATA_SEMANA"])
    contagens = observado["NOTIFICACOES_SEMANAIS"].where(observado["COBERTURA_DENGUE"])
    futuras = pd.DataFrame(index=painel.index)
    for horizonte in range(1, 5):
        chaves = pd.MultiIndex.from_arrays(
            [painel["BAIRRO"], painel["DATA_SEMANA"] + pd.Timedelta(weeks=horizonte)]
        )
        futuras[horizonte] = contagens.reindex(chaves).to_numpy()

    semanal = futuras[1]
    original = painel[ALVO_SEMANAL]
    igual = semanal.eq(original) | (semanal.isna() & original.isna())
    if not igual.all():
        raise ValueError("O alvo t+1 reconstruído não bate com a AV1. Consulte a cobertura.")
    painel[ALVO_SEMANAL] = semanal
    # Alvo de 4 semanas só existe com as quatro contagens observadas.
    painel[ALVO_QUATRO_SEMANAS] = futuras.sum(axis=1, min_count=4)
    painel["DATA_FIM_ALVO_4S"] = painel["DATA_ALVO"] + pd.Timedelta(weeks=3)
    painel["ELEGIVEL_SEM_CLIMA_4S"] = (
        painel["ELEGIVEL_SEM_CLIMA"] & painel[ALVO_QUATRO_SEMANAS].notna()
    )
    comum = painel["ELEGIVEL_AV2"]
    sem_clima = painel["ELEGIVEL_SEM_CLIMA"]
    if (comum & ~sem_clima).any() or (sem_clima & semanal.isna()).any():
        raise ValueError("As condições de elegibilidade da AV1 estão inconsistentes.")

    def conjunto_por_data(datas: pd.Series) -> pd.Series:
        conjunto = pd.Series("fora", index=datas.index)
        conjunto.loc[datas.lt(corte_validacao)] = "treino"
        conjunto.loc[datas.ge(corte_validacao) & datas.lt(corte_teste)] = "validacao"
        conjunto.loc[datas.ge(corte_teste) & datas.le(FIM_TESTE_CLIMATICO)] = "teste"
        return conjunto

    # Divisão temporal pela data do alvo: treino < validação < teste, nunca embaralhado.
    primeiro_conjunto = conjunto_por_data(painel["DATA_ALVO"])
    ultimo_conjunto = conjunto_por_data(painel["DATA_FIM_ALVO_4S"])
    painel["CONJUNTO_1S"] = primeiro_conjunto.where(comum, "fora")
    # Janela que cruza um corte é descartada para não vazar o futuro.
    janela_contida = primeiro_conjunto.eq(ultimo_conjunto)
    janela_completa = painel[ALVO_QUATRO_SEMANAS].notna()
    painel["CONJUNTO_4S"] = painel["CONJUNTO_1S"].where(
        janela_contida & janela_completa, "fora"
    )
    return painel


def resumir_preparacao(painel: pd.DataFrame) -> dict:
    """Conta linhas e semanas por conjunto, sem exibir desfechos."""
    bairros = set(painel["BAIRRO"])
    resumo = {"bairros_no_painel": len(bairros)}
    for horizonte, fim in (("1S", "DATA_ALVO"), ("4S", "DATA_FIM_ALVO_4S")):
        coluna = f"CONJUNTO_{horizonte}"
        conjuntos = {}
        ultimo_alvo_anterior = None
        for nome in CONJUNTOS:
            grupo = painel.loc[painel[coluna].eq(nome)]
            tamanhos = grupo.groupby("DATA_ALVO")["BAIRRO"].nunique()
            if grupo.empty or not tamanhos.eq(len(bairros)).all():
                raise ValueError(f"{nome}/{horizonte} vazio ou com semanas incompletas por bairro.")
            if ultimo_alvo_anterior is not None and ultimo_alvo_anterior > grupo["DATA_SEMANA"].min():
                raise ValueError(f"Alvos anteriores ainda em aberto no começo de {nome}/{horizonte}.")
            ultimo_alvo_anterior = grupo[fim].max()
            conjuntos[nome] = {
                "linhas": len(grupo),
                "semanas_de_inicio": len(tamanhos),
                "primeira_semana_alvo": grupo["DATA_ALVO"].min().date().isoformat(),
                "ultima_semana_alvo": ultimo_alvo_anterior.date().isoformat(),
            }
        resumo[horizonte] = conjuntos

    semanal = painel["CONJUNTO_1S"].ne("fora")
    quatro_semanas = painel["CONJUNTO_4S"].ne("fora")
    excluidas = painel.loc[semanal & ~quatro_semanas]
    resumo["exclusoes_4S"] = {
        "linhas": len(excluidas),
        "semanas_de_inicio": sorted(excluidas["DATA_ALVO"].dt.strftime("%Y-%m-%d").unique()),
    }
    recuperadas = painel.loc[semanal & painel["CONJUNTO_AV1"].eq("fora"), "DATA_ALVO"]
    resumo["semanas_recuperadas_1S"] = sorted(recuperadas.dt.strftime("%Y-%m-%d").unique())
    for coluna, fim in (
        ("ELEGIVEL_SEM_CLIMA", "DATA_ALVO"),
        ("ELEGIVEL_SEM_CLIMA_4S", "DATA_FIM_ALVO_4S"),
    ):
        grupo = painel.loc[painel[coluna]]
        resumo[coluna] = {
            "linhas": len(grupo),
            "semanas_de_inicio": grupo["DATA_ALVO"].nunique(),
            "primeira_semana_alvo": grupo["DATA_ALVO"].min().date().isoformat(),
            "ultima_semana_alvo": grupo[fim].max().date().isoformat(),
        }
    return resumo


def main() -> None:
    dados, config = carregar_dados()
    painel = preparar_painel(dados, config)
    print(json.dumps(resumir_preparacao(painel), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
