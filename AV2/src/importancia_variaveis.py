"""Importância por permutação do Gradient Boosting com clima, medida só na validação.

O HistGradientBoostingRegressor não expõe `feature_importances_`. Por isso medimos quanto o MAE
da validação piora quando cada atributo é embaralhado, mantendo os demais. O teste reservado não
é usado. Uso: python -B -m AV2.src.importancia_variaveis
"""

from __future__ import annotations

import json
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from threadpoolctl import threadpool_limits

from .auditar_base import RAIZ_PROJETO, carregar_dados
from .experimentos import CLIMA, CONTROLE, SEMENTE, TERRITORIO, ajustar_candidato, candidatos
from .preparar_alvos import ALVO_QUATRO_SEMANAS, ALVO_SEMANAL, preparar_painel

SAIDA = RAIZ_PROJETO / "AV2" / "artefatos" / "importancia_variaveis.zip"
MODELO = "Gradient Boosting"
REPETICOES = 10


def grupo(coluna: str) -> str:
    if coluna in TERRITORIO:
        return "Território"
    if coluna.startswith(("PRECIPITACAO", "CHUVA")):
        return "Chuva"
    if coluna.startswith("TEMPERATURA"):
        return "Temperatura"
    if coluna.startswith("UMIDADE"):
        return "Umidade"
    if coluna.startswith("SEMANA_"):
        return "Calendário"
    return "Histórico de notificações"


def medir(painel: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    numericas = CONTROLE + CLIMA
    colunas = numericas + TERRITORIO
    for semanas, alvo in ((1, ALVO_SEMANAL), (4, ALVO_QUATRO_SEMANAS)):
        conjunto = painel[f"CONJUNTO_{semanas}S"]
        treino = painel.loc[conjunto.eq("treino")]
        validacao = painel.loc[conjunto.eq("validacao")]
        modelo = ajustar_candidato(MODELO, candidatos()[MODELO], numericas, treino, alvo)
        with threadpool_limits(limits=2):
            # Embaralha cada atributo na validação e mede o aumento do MAE.
            resultado = permutation_importance(
                modelo, validacao[colunas], validacao[alvo], scoring="neg_mean_absolute_error",
                n_repeats=REPETICOES, random_state=SEMENTE, n_jobs=1,
            )
        for coluna, media, desvio in zip(colunas, resultado.importances_mean, resultado.importances_std):
            linhas.append({"horizonte_semanas": semanas, "atributo": coluna, "grupo": grupo(coluna),
                           "aumento_MAE": media, "desvio": desvio})
    tabela = pd.DataFrame(linhas)
    if not np.isfinite(tabela[["aumento_MAE", "desvio"]]).all().all():
        raise ValueError("Importância indefinida.")
    return tabela.sort_values(["horizonte_semanas", "aumento_MAE"], ascending=[True, False])


def main() -> None:
    tabela = medir(preparar_painel(*carregar_dados()))
    manifesto = {"modelo": MODELO, "cenario": "com clima", "conjunto": "validação",
                 "metrica": "aumento do MAE ao embaralhar o atributo", "repeticoes": REPETICOES,
                 "semente": SEMENTE}
    with ZipFile(SAIDA, "w", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
        arquivo.writestr("importancia.csv", tabela.to_csv(index=False))
    print(tabela.groupby(["horizonte_semanas", "grupo"])["aumento_MAE"].sum().round(4).to_string())
    print(tabela.groupby("horizonte_semanas").head(8).round(4).to_string(index=False))
    print(f"Registrado em {SAIDA}")


if __name__ == "__main__":
    main()
