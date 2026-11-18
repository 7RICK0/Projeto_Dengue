"""Análise complementar posterior: Gradient Boosting com clima, mas sem temperatura.

A retirada da temperatura foi decidida pela validação (ablação), depois do teste oficial já
registrado em `teste_final.zip`. Este resultado NÃO substitui o oficial: é rotulado como análise
posterior, porque o teste reservado já tinha sido examinado. Mesmos cortes, parâmetros e
ajuste em treino + validação do teste oficial.
Uso: python -B -m AV2.src.avaliar_sem_temperatura
"""

from __future__ import annotations

import json
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .auditar_base import RAIZ_PROJETO, carregar_dados
from .experimentos import CLIMA, CONTROLE, TERRITORIO, ajustar_candidato, candidatos, medir_previsoes
from .preparar_alvos import ALVO_QUATRO_SEMANAS, ALVO_SEMANAL, preparar_painel

SAIDA = RAIZ_PROJETO / "AV2" / "artefatos" / "clima_sem_temperatura.zip"
MODELO = "Gradient Boosting"
CLIMA_SEM_TEMPERATURA = [c for c in CLIMA if not c.startswith("TEMPERATURA")]


def main() -> None:
    painel = preparar_painel(*carregar_dados())
    numericas = CONTROLE + CLIMA_SEM_TEMPERATURA
    resumo, previsoes = [], []
    for semanas, alvo in ((1, ALVO_SEMANAL), (4, ALVO_QUATRO_SEMANAS)):
        conjunto = painel[f"CONJUNTO_{semanas}S"]
        treino = painel.loc[conjunto.eq("treino")]
        desenvolvimento = painel.loc[conjunto.isin(("treino", "validacao"))]
        teste = painel.loc[conjunto.eq("teste")]
        limite_pico = float(treino.loc[treino[alvo].gt(0), alvo].quantile(0.9))
        ajuste = ajustar_candidato(MODELO, candidatos()[MODELO], numericas, desenvolvimento, alvo)
        with threadpool_limits(limits=2):
            previsto = ajuste.predict(teste[numericas + TERRITORIO])
        if not np.isfinite(previsto).all() or (previsto < 0).any():
            raise ValueError("Previsão inválida.")
        valores = teste[["BAIRRO", "DATA_SEMANA", "DATA_ALVO"]].assign(
            horizonte_semanas=semanas, modelo=MODELO, cenario="clima sem temperatura",
            observado=teste[alvo], previsto=previsto)
        previsoes.append(valores)
        resumo.append({"horizonte_semanas": semanas, "modelo": MODELO, "cenario": "clima sem temperatura",
                       **medir_previsoes(valores, limite_pico)})
    metricas = pd.DataFrame(resumo)
    manifesto = {
        "natureza": "análise complementar posterior; não substitui teste_final.zip",
        "motivo": "na validação de quatro semanas, retirar a temperatura reduziu o MAE de 3,081 para 3,014",
        "atributos_climaticos": CLIMA_SEM_TEMPERATURA,
        "parametros": candidatos()[MODELO].get_params(),
    }
    with ZipFile(SAIDA, "w", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2, default=str))
        arquivo.writestr("metricas.csv", metricas.to_csv(index=False))
        arquivo.writestr("previsoes.csv", pd.concat(previsoes, ignore_index=True).to_csv(index=False))
    print(metricas.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
