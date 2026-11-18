"""Análises sobre previsões e dados já registrados: confiabilidade do ganho e sinal climático.

Nada aqui treina modelos nem reutiliza o teste para escolhas. As funções são usadas pelo
notebook e pela exportação do painel, para que os dois mostrem exatamente os mesmos números.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COMPARACOES = {
    "Clima × sem clima (bairro)": ("bairro", "com clima", "sem clima"),
    "Clima × sem clima (cidade)": ("cidade", "com clima", "sem clima"),
    "ML com clima × média móvel": ("bairro", "com clima", "baseline"),
}


def bootstrap_ganhos(previsoes: pd.DataFrame, semanas: int, sorteios: int = 5000, bloco: int = 4,
                     semente: int = 42) -> tuple[pd.DataFrame, dict]:
    """Bootstrap em blocos circulares de semanas sobre previsões já registradas.

    Retorna o resumo (mediana, intervalo de 95% e % de sorteios com ganho) e os ganhos sorteados.
    """
    rng = np.random.default_rng(semente)
    parte = previsoes.loc[previsoes["horizonte_semanas"].eq(semanas)]
    largo = parte.pivot_table(index=["DATA_SEMANA", "BAIRRO"], columns="cenario", values=["observado", "previsto"])
    observado = largo["observado"]["com clima"]

    # Erro somado por semana: por bairro (soma dos erros) e da cidade (erro do total)
    erro = {"bairro": largo["previsto"].sub(observado, axis=0).abs().groupby(level=0).sum(),
            "cidade": largo["previsto"].groupby(level=0).sum().sub(observado.groupby(level=0).sum(), axis=0).abs()}
    linhas = largo.groupby(level=0).size()
    total = len(linhas)

    ganhos = {nome: [] for nome in COMPARACOES}
    for _ in range(sorteios):
        # Junta blocos de semanas seguidas (circular), preservando a dependência entre semanas vizinhas
        inicios = rng.integers(0, total, size=int(np.ceil(total / bloco)))
        idx = np.concatenate([np.arange(s, s + bloco) % total for s in inicios])[:total]
        mae = {"bairro": erro["bairro"].iloc[idx].sum() / linhas.iloc[idx].sum(),
               "cidade": erro["cidade"].iloc[idx].mean()}
        for nome, (nivel, modelo, referencia) in COMPARACOES.items():
            ganhos[nome].append(1 - mae[nivel][modelo] / mae[nivel][referencia])

    resumo = []
    for nome, valores in ganhos.items():
        valores = np.array(valores) * 100
        ganhos[nome] = valores
        resumo.append({"horizonte_semanas": semanas, "comparação": nome,
                       "ganho_mediano_%": np.median(valores),
                       "IC95_inferior_%": np.percentile(valores, 2.5),
                       "IC95_superior_%": np.percentile(valores, 97.5),
                       "sorteios_com_ganho_%": (valores > 0).mean() * 100})
    return pd.DataFrame(resumo), ganhos


def serie_cidade(painel: pd.DataFrame) -> pd.DataFrame:
    """Notificações e clima da cidade por semana (o clima é o mesmo para todos os bairros)."""
    cidade = (painel.groupby("DATA_SEMANA")
              .agg(notificacoes=("NOTIFICACOES_SEMANAIS", "sum"), umidade=("UMIDADE_MEDIA_PCT", "first"),
                   chuva=("PRECIPITACAO_SEMANAL_MM", "first"), temperatura=("TEMPERATURA_MEDIA_C", "first")))
    cidade.index = pd.to_datetime(cidade.index)
    return cidade.asfreq("7D")


def sinal_climatico(painel: pd.DataFrame, defasagem_max: int = 16) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Correlação de Spearman entre o clima de L semanas antes e as notificações, e calendário típico.

    As notificações entram como desvio da média do próprio ano (escala log), para que anos
    epidêmicos muito grandes, como 2016, não dominem a correlação.
    """
    cidade = serie_cidade(painel)
    log_n = np.log1p(cidade["notificacoes"])
    desvio_ano = log_n - log_n.groupby(cidade.index.year).transform("mean")
    nomes = {"chuva": "Chuva", "umidade": "Umidade", "temperatura": "Temperatura"}
    correlacoes = pd.DataFrame(
        {nome: [cidade[col].shift(L).corr(desvio_ano, method="spearman") for L in range(defasagem_max + 1)]
         for col, nome in nomes.items()},
        index=pd.RangeIndex(defasagem_max + 1, name="semanas antes"))

    # Calendário típico no período com clima: chuva média e mediana semanal de notificações por mês
    com_clima = cidade.dropna(subset=["chuva", "umidade"])
    calendario = com_clima.groupby(com_clima.index.month).agg(chuva=("chuva", "mean"),
                                                             notificacoes=("notificacoes", "median"))
    calendario.index.name = "mes"
    return correlacoes, calendario
