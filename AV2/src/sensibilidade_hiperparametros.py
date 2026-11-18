"""Verifica, só na validação, se a conclusão depende da configuração fixa do Gradient Boosting.

Varia learning_rate, número de árvores (max_iter) e tamanho das árvores (max_leaf_nodes) nas
versões com e sem clima, no horizonte de quatro semanas. Não altera o modelo levado ao teste nem
usa o teste reservado. Uso: python -B -m AV2.src.sensibilidade_hiperparametros
"""

from __future__ import annotations

import json
from itertools import product
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from .auditar_base import RAIZ_PROJETO, carregar_dados
from .experimentos import CLIMA, CONTROLE, SEMENTE, TERRITORIO, ajustar_candidato
from .preparar_alvos import ALVO_QUATRO_SEMANAS, preparar_painel

SAIDA = RAIZ_PROJETO / "AV2" / "artefatos" / "hiperparametros.zip"
GRADE = {"learning_rate": (0.05, 0.1, 0.2), "max_iter": (100, 300), "max_leaf_nodes": (15, 31)}
CONGELADA = {"learning_rate": 0.1, "max_iter": 100, "max_leaf_nodes": 15}


def medir(painel: pd.DataFrame) -> pd.DataFrame:
    conjunto = painel["CONJUNTO_4S"]
    treino = painel.loc[conjunto.eq("treino")]
    validacao = painel.loc[conjunto.eq("validacao")]
    linhas = []
    for valores in product(*GRADE.values()):
        parametros = dict(zip(GRADE, valores))
        for cenario, numericas in (("sem clima", CONTROLE), ("com clima", CONTROLE + CLIMA)):
            estimador = HistGradientBoostingRegressor(
                loss="poisson", early_stopping=False, random_state=SEMENTE, **parametros
            )
            inicio = perf_counter()
            modelo = ajustar_candidato("Gradient Boosting", estimador, numericas, treino, ALVO_QUATRO_SEMANAS)
            with threadpool_limits(limits=2):
                previsto = modelo.predict(validacao[numericas + TERRITORIO])
            linhas.append({**parametros, "cenario": cenario,
                           "MAE": (validacao[ALVO_QUATRO_SEMANAS] - previsto).abs().mean(),
                           "segundos": perf_counter() - inicio,
                           "configuracao_congelada": parametros == CONGELADA})
    return pd.DataFrame(linhas)


def main() -> None:
    tabela = medir(preparar_painel(*carregar_dados()))
    manifesto = {"modelo": "HistGradientBoostingRegressor (perda Poisson)", "horizonte_semanas": 4,
                 "conjunto": "validação", "grade": GRADE, "configuracao_congelada": CONGELADA,
                 "observacao": "Verificação de robustez; o teste reservado não foi usado nem refeito."}
    with ZipFile(SAIDA, "w", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
        arquivo.writestr("grade.csv", tabela.to_csv(index=False))
    print(tabela.round(3).to_string(index=False))
    print(f"Registrado em {SAIDA}")


if __name__ == "__main__":
    main()
