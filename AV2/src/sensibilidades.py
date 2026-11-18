"""Análises complementares, separadas do teste climático já registrado."""

from __future__ import annotations

import argparse
import json
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .auditar_base import RAIZ_PROJETO, carregar_dados
from .baselines import previsoes_baselines
from .experimentos import CLIMA, CONTROLE, TERRITORIO, ajustar_candidato, candidatos
from .preparar_alvos import ALVO_QUATRO_SEMANAS, ALVO_SEMANAL, preparar_painel

SAIDA = RAIZ_PROJETO / "AV2" / "artefatos"
HORIZONTES = ((1, ALVO_SEMANAL, "DATA_ALVO"), (4, ALVO_QUATRO_SEMANAS, "DATA_FIM_ALVO_4S"))
POPULACAO = ["POPULACAO_BAIRRO_ANO", "DENSIDADE_HAB_KM2_ANO"]
MODELO = "Gradient Boosting"


def prever(treino, avaliacao, alvo, numericas):
    ajuste = ajustar_candidato(MODELO, candidatos()[MODELO], numericas, treino, alvo)
    with threadpool_limits(limits=2):
        return ajuste.predict(avaliacao[numericas + TERRITORIO])


def medicao(observado, previsto):
    erro = observado - previsto
    if erro.empty or not np.isfinite(erro).all():
        raise ValueError("Amostra vazia ou com erro indefinido.")
    return {"linhas": len(erro), "MAE": erro.abs().mean(), "RMSE": np.sqrt(erro.pow(2).mean())}


def ablaçoes(painel):
    variantes = {"sem clima": CONTROLE, "com clima": CONTROLE + CLIMA}
    ablaçao = {
        "sem chuva": [c for c in CLIMA if c.startswith(("PRECIPITACAO_", "CHUVA_"))],
        "sem temperatura": [c for c in CLIMA if c.startswith("TEMPERATURA_")],
        "sem umidade": [c for c in CLIMA if c.startswith("UMIDADE_")],
    }
    for janela in (2, 4, 8):
        ablaçao[f"sem janela {janela} semanas"] = [c for c in CLIMA if f"_{janela}S_" in c]
    for nome, removidas in ablaçao.items():
        variantes[nome] = CONTROLE + [c for c in CLIMA if c not in removidas]
    variantes["sem clima + população retrospectiva"] = CONTROLE + POPULACAO
    variantes["com clima + população retrospectiva"] = CONTROLE + CLIMA + POPULACAO

    resultados = []
    for semanas, alvo, _ in HORIZONTES:
        particao = painel[f"CONJUNTO_{semanas}S"]
        treino = painel.loc[particao.eq("treino")]
        validacao = painel.loc[particao.eq("validacao")]
        for nome, numericas in variantes.items():
            previsto = prever(treino, validacao, alvo, numericas)
            resultados.append({
                "semanas": semanas, "variante": nome, **medicao(validacao[alvo], previsto)
            })
    return pd.DataFrame(resultados)


def serie_sem_clima(painel, corte_validacao, corte_teste):
    resultados = []
    for semanas, alvo, fim in HORIZONTES:
        elegivel = "ELEGIVEL_SEM_CLIMA" if semanas == 1 else "ELEGIVEL_SEM_CLIMA_4S"
        base = painel.loc[painel[elegivel]]
        treino = base.loc[base[fim].lt(corte_validacao)]
        validacao = base.loc[base["DATA_ALVO"].ge(corte_validacao) & base[fim].lt(corte_teste)]
        teste = base.loc[base["DATA_ALVO"].ge(corte_teste)]
        for particao, ajuste, quadro in (
            ("validação", treino, validacao),
            ("teste", pd.concat([treino, validacao]), teste),
        ):
            if ajuste[fim].max() > quadro["DATA_SEMANA"].min():
                raise ValueError("Um alvo de ajuste ultrapassa a origem da previsão.")
            referencias = previsoes_baselines(quadro, semanas)
            referencias[MODELO] = prever(ajuste, quadro, alvo, CONTROLE)
            for nome, valores in referencias.items():
                resultados.append({
                    "semanas": semanas, "conjunto": particao, "modelo": nome,
                    "inicio": quadro["DATA_ALVO"].min().date().isoformat(),
                    "fim": quadro[fim].max().date().isoformat(),
                    **medicao(quadro[alvo], valores)
                })
    return pd.DataFrame(resultados)


def avaliar_priorizacao():
    """Mede a coincidência entre os 10 bairros previstos e observados por mês."""
    with ZipFile(SAIDA / "mes_calendario.zip") as arquivo:
        previsoes = pd.read_csv(arquivo.open("previsoes.csv"))
    recorte = previsoes.loc[previsoes["conjunto"].eq("teste")]
    resultados = []
    for (mes, cenario), grupo in recorte.groupby(["MES_ALVO", "cenario"]):
        # Nome do bairro resolve empates de forma determinística.
        melhores = grupo.sort_values(["previsto", "BAIRRO"], ascending=[False, True]).head(10)
        observados = grupo.sort_values(["observado", "BAIRRO"], ascending=[False, True]).head(10)
        resultados.append({
            "mes": mes, "cenario": cenario,
            "bairros_em_comum_top10": int(melhores["BAIRRO"].isin(observados["BAIRRO"]).sum()),
            "fracao_notificacoes_nos_10_previstos": melhores["observado"].sum() / grupo["observado"].sum(),
        })
    return pd.DataFrame(resultados)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corte-validacao", type=pd.Timestamp)
    parser.add_argument("--corte-teste", type=pd.Timestamp)
    opcoes = parser.parse_args()
    if bool(opcoes.corte_validacao) != bool(opcoes.corte_teste):
        parser.error("Informe os dois cortes da série complementar.")
    painel = preparar_painel(*carregar_dados())
    if opcoes.corte_teste:
        if not opcoes.corte_validacao < opcoes.corte_teste:
            parser.error("O início da validação deve anteceder o do teste.")
        serie = serie_sem_clima(painel, opcoes.corte_validacao, opcoes.corte_teste)
        destino = SAIDA / "serie_sem_clima.zip"
        with ZipFile(destino, "w", compression=ZIP_DEFLATED) as arquivo:
            arquivo.writestr("metricas.csv", serie.to_csv(index=False))
            arquivo.writestr("manifesto.json", json.dumps({
                "corte_validacao": opcoes.corte_validacao.date().isoformat(),
                "corte_teste": opcoes.corte_teste.date().isoformat(),
            }, indent=2))
        print(serie.round(3).to_string(index=False))
        return
    dados = ablaçoes(painel)
    prioridade = avaliar_priorizacao()
    with ZipFile(SAIDA / "sensibilidades.zip", "w", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("ablacoes_validacao.csv", dados.to_csv(index=False))
        arquivo.writestr("priorizacao_mensal.csv", prioridade.to_csv(index=False))
    print(dados.round(3).to_string(index=False))
    print(prioridade.groupby("cenario").mean(numeric_only=True).round(3).to_string())


if __name__ == "__main__":
    main()
