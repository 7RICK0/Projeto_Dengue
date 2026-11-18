"""Primeira comparação dos candidatos nos cortes de treino e validação."""

from __future__ import annotations

from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from .baselines import previsoes_baselines
from .preparar_alvos import ALVO_QUATRO_SEMANAS, ALVO_SEMANAL


SEMENTE = 42
TERRITORIO = ["BAIRRO", "RPA"]
CONTROLE = [
    "NOTIFICACOES_SEMANAIS",
    *(f"NOTIFICACOES_LAG_{i}" for i in range(1, 5)),
    "MEDIA_NOTIFICACOES_4S",
    "SEMANA_SIN",
    "SEMANA_COS",
]
CLIMA = [
    "PRECIPITACAO_SEMANAL_MM",
    "TEMPERATURA_MEDIA_C",
    "UMIDADE_MEDIA_PCT",
    *(f"{nome}_LAG_{i}_{unidade}" for nome, unidade in (
        ("PRECIPITACAO", "MM"), ("TEMPERATURA", "C"), ("UMIDADE", "PCT")
    ) for i in range(1, 9)),
    *(coluna for i in (2, 4, 8) for coluna in (
        f"CHUVA_{i}S_MM", f"TEMPERATURA_MEDIA_{i}S_C", f"UMIDADE_MEDIA_{i}S_PCT"
    )),
]


def candidatos() -> dict:
    """Configurações iniciais fixadas para a rodada sem busca de parâmetros."""
    return {
        "Poisson": PoissonRegressor(alpha=0.1, max_iter=1_000),
        "Random Forest": RandomForestRegressor(
            n_estimators=100, max_depth=12, min_samples_leaf=5, n_jobs=2, random_state=SEMENTE
        ),
        "Gradient Boosting": HistGradientBoostingRegressor(
            loss="poisson", max_iter=100, max_leaf_nodes=15, early_stopping=False,
            random_state=SEMENTE,
        ),
    }


def ajustar_candidato(nome, estimador, numericas, treino, alvo):
    """Ajusta codificação, escala quando aplicável e modelo na mesma amostra."""
    # One-hot de bairro/RPA e escala (só Poisson) ajustados apenas no treino, dentro do pipeline.
    preparo = ColumnTransformer([
        ("numericas", StandardScaler() if nome == "Poisson" else "passthrough", numericas),
        ("territorio", OneHotEncoder(handle_unknown="ignore", sparse_output=False), TERRITORIO),
    ])
    modelo = make_pipeline(preparo, estimador)
    with threadpool_limits(limits=2):
        modelo.fit(treino[numericas + TERRITORIO], treino[alvo])
    return modelo


def medir_previsoes(previsoes: pd.DataFrame, limite_pico: float) -> dict:
    erro = previsoes["previsto"] - previsoes["observado"]
    # Pico = percentil 90 dos alvos positivos do treino.
    pico = previsoes["observado"].ge(limite_pico)
    return {
        "linhas": len(erro),
        "MAE": erro.abs().mean(),
        "RMSE": np.sqrt(erro.pow(2).mean()),
        "MAE_positivos": erro[previsoes["observado"].gt(0)].abs().mean(),
        "MAE_picos": erro[pico].abs().mean(),
        "n_picos": int(pico.sum()),
        "MAE_municipal": erro.groupby(previsoes["DATA_ALVO"]).sum().abs().mean(),
    }


def comparar_validacao(painel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve métricas e previsões por bairro apenas para a validação."""
    metricas = []
    previsoes = []
    for semanas, alvo in ((1, ALVO_SEMANAL), (4, ALVO_QUATRO_SEMANAS)):
        conjunto = painel[f"CONJUNTO_{semanas}S"]
        treino = painel.loc[conjunto.eq("treino")]
        validacao = painel.loc[conjunto.eq("validacao")]
        campos = TERRITORIO + CONTROLE + CLIMA + [alvo]
        for amostra in (treino, validacao):
            if amostra.empty or amostra[campos].isna().any().any():
                raise ValueError(f"Treino ou validação de {semanas} semana(s) incompletos.")
        limite_pico = treino.loc[treino[alvo].gt(0), alvo].quantile(0.90)

        def registrar(nome, cenario, previsto, segundos=0.0):
            observado = validacao[["BAIRRO", "DATA_SEMANA", "DATA_ALVO", alvo]].rename(
                columns={alvo: "observado"}
            )
            observado = observado.assign(
                horizonte_semanas=semanas, modelo=nome, cenario=cenario, previsto=previsto
            )
            if not np.isfinite(observado["previsto"]).all() or observado["previsto"].lt(0).any():
                raise ValueError(f"Previsões inválidas para {nome}/{cenario}/{semanas} semana(s).")
            previsoes.append(observado)
            metricas.append({
                "horizonte_semanas": semanas, "modelo": nome, "cenario": cenario,
                "segundos_ajuste": segundos, **medir_previsoes(observado, limite_pico)
            })

        for nome, previsto in previsoes_baselines(validacao, semanas).items():
            registrar(nome, "baseline", previsto)

        # Mesmo modelo e mesmas linhas; a única diferença entre cenários é o bloco climático.
        for cenario, numericas in (("sem clima", CONTROLE), ("com clima", CONTROLE + CLIMA)):
            entradas = numericas + TERRITORIO
            for nome, estimador in candidatos().items():
                inicio = perf_counter()
                modelo = ajustar_candidato(nome, estimador, numericas, treino, alvo)
                segundos = perf_counter() - inicio
                with threadpool_limits(limits=2):
                    previsto = modelo.predict(validacao[entradas])
                registrar(nome, cenario, previsto, segundos)

    resultado = pd.DataFrame(metricas).sort_values(["horizonte_semanas", "MAE", "modelo"])
    return resultado.reset_index(drop=True), pd.concat(previsoes, ignore_index=True)
