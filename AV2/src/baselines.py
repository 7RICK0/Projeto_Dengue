"""Referências simples na validação, nos dois horizontes da AV2."""

import numpy as np
import pandas as pd

from .preparar_alvos import ALVO_QUATRO_SEMANAS, ALVO_SEMANAL


def previsoes_baselines(dados: pd.DataFrame, semanas: int) -> dict[str, pd.Series]:
    # Réguas sem ML; para 4 semanas, repete o nível semanal quatro vezes.
    return {
        "Persistência": semanas * dados["NOTIFICACOES_SEMANAIS"],
        "Média das quatro semanas anteriores": semanas * dados["MEDIA_NOTIFICACOES_4S"],
    }


def avaliar_baselines_validacao(painel: pd.DataFrame) -> pd.DataFrame:
    """Compara as referências usando apenas os alvos da validação climática."""
    resultados = []
    for semanas, alvo in ((1, ALVO_SEMANAL), (4, ALVO_QUATRO_SEMANAS)):
        validacao = painel.loc[painel[f"CONJUNTO_{semanas}S"].eq("validacao")]
        for nome, previsao in previsoes_baselines(validacao, semanas).items():
            erro = previsao - validacao[alvo]
            if erro.empty or not np.isfinite(erro).all():
                raise ValueError(f"Alvo ou referência incompleta na validação de {semanas} semana(s).")
            resultados.append(
                {
                    "horizonte_semanas": semanas,
                    "referencia": nome,
                    "linhas": len(erro),
                    "MAE": erro.abs().mean(),
                    "RMSE": np.sqrt(erro.pow(2).mean()),
                }
            )
    return pd.DataFrame(resultados)
