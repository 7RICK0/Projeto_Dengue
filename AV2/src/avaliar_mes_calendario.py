"""Avaliação separada do total de notificações no mês civil inteiro."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .auditar_base import RAIZ_PROJETO, carregar_dados
from .experimentos import CLIMA, CONTROLE, TERRITORIO, ajustar_candidato, candidatos
from .observar_meses import observar_meses
from .preparar_alvos import FIM_TESTE_CLIMATICO, preparar_painel


SAIDA = RAIZ_PROJETO / "AV2" / "artefatos" / "mes_calendario.zip"
MODELO = "Gradient Boosting"
ENTRADAS_MENSAIS = CONTROLE + ["DIAS_MES", "DIAS_ENTRE_REFERENCIA_E_MES"]


def montar_amostra(painel, observados, config):
    amostra = observados.copy()
    inicio = amostra["MES_ALVO"]
    amostra["FIM_MES"] = inicio + pd.offsets.MonthEnd()
    amostra["DATA_SEMANA"] = inicio - pd.to_timedelta(inicio.dt.dayofweek + 7, unit="D")
    amostra["DATA_EMISSAO"] = amostra["DATA_SEMANA"] + pd.Timedelta(days=6)
    amostra["DIAS_MES"] = inicio.dt.days_in_month
    amostra["DIAS_ENTRE_REFERENCIA_E_MES"] = (inicio - amostra["DATA_EMISSAO"]).dt.days
    if not amostra["DATA_EMISSAO"].lt(inicio).all():
        raise ValueError("Data de emissão não antecede o mês.")
    amostra = amostra.merge(painel, on=["DATA_SEMANA", "BAIRRO"], how="left", validate="one_to_one")
    amostra["CONJUNTO_MES"] = "fora"
    inicio = amostra["MES_ALVO"]
    fim = amostra["FIM_MES"]
    corte_validacao = pd.Timestamp(config["corte_validacao"])
    corte_teste = pd.Timestamp(config["corte_teste"])
    amostra.loc[fim.lt(corte_validacao), "CONJUNTO_MES"] = "treino"
    amostra.loc[inicio.ge(corte_validacao) & fim.lt(corte_teste), "CONJUNTO_MES"] = "validacao"
    amostra.loc[inicio.ge(corte_teste) & fim.le(FIM_TESTE_CLIMATICO + pd.Timedelta(days=6)),
                "CONJUNTO_MES"] = "teste"
    amostra["HISTORICO_COMPLETO"] = amostra[CONTROLE + TERRITORIO].notna().all(axis=1)
    amostra["CLIMA_COMPLETO"] = amostra["HISTORICO_COMPLETO"] & amostra[CLIMA].notna().all(axis=1)
    return amostra


def comparar(ajuste, avaliacao):
    if ajuste.empty or avaliacao.empty:
        raise ValueError("O experimento precisa de meses de ajuste e avaliação.")
    if ajuste["FIM_MES"].max() > avaliacao["DATA_EMISSAO"].min():
        raise ValueError("Alvo mensal ainda aberto na primeira emissão de avaliação.")
    base = avaliacao[["BAIRRO", "MES_ALVO", "FIM_MES", "DATA_EMISSAO", "observado"]]
    casos = [("média móvel", avaliacao["MEDIA_NOTIFICACOES_4S"] * avaliacao["DIAS_MES"] / 7)]
    for nome, colunas in (("sem clima", ENTRADAS_MENSAIS), ("com clima", ENTRADAS_MENSAIS + CLIMA)):
        modelo = ajustar_candidato(MODELO, candidatos()[MODELO], colunas, ajuste, "observado")
        with threadpool_limits(limits=2):
            casos.append((nome, modelo.predict(avaliacao[colunas + TERRITORIO])))
    previsoes = pd.concat([base.assign(cenario=nome, previsto=valores) for nome, valores in casos])
    previsoes = previsoes.assign(erro=previsoes["previsto"] - previsoes["observado"])
    metricas = []
    for nome, grupo in previsoes.groupby("cenario", sort=False):
        erro = grupo["erro"]
        metricas.append({
            "cenario": nome, "meses": grupo["MES_ALVO"].nunique(), "linhas": len(grupo),
            "MAE": erro.abs().mean(), "RMSE": np.sqrt(erro.pow(2).mean()),
            "MAE_municipal": grupo.groupby("MES_ALVO")["erro"].sum().abs().mean(),
        })
    return pd.DataFrame(metricas), previsoes


def main():
    if SAIDA.exists():
        raise SystemExit(f"Os resultados mensais já estão gravados em {SAIDA}.")
    dados, config = carregar_dados()
    painel = preparar_painel(dados, config)
    observados = observar_meses(painel, config["intervalos_cobertura"])
    amostra = montar_amostra(painel, observados, config)
    cobertura = amostra.groupby(["CONJUNTO_MES", "MES_ALVO", "DATA_EMISSAO"], as_index=False).agg(
        bairros=("BAIRRO", "nunique"), historico_completo=("HISTORICO_COMPLETO", "sum"),
        clima_completo=("CLIMA_COMPLETO", "sum"),
    )
    quantidade_bairros = painel["BAIRRO"].nunique()
    cobertura["MES_COMPARAVEL"] = cobertura["clima_completo"].eq(quantidade_bairros)
    meses_comuns = cobertura.loc[cobertura["MES_COMPARAVEL"], "MES_ALVO"]
    comum = amostra.loc[amostra["MES_ALVO"].isin(meses_comuns)]
    treino = comum.loc[comum["CONJUNTO_MES"].eq("treino")]
    validacao = comum.loc[comum["CONJUNTO_MES"].eq("validacao")]
    teste = comum.loc[comum["CONJUNTO_MES"].eq("teste")]
    metricas_val, pv_val = comparar(treino, validacao)
    metricas_teste, pv_teste = comparar(pd.concat([treino, validacao]), teste)
    manifesto = {
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "alvo": "Notificações A90 pela data civil, do primeiro ao último dia do mês",
        "emissao": "Fechamento da última semana de segunda a domingo anterior ao dia 1",
        "natureza": "Análise retrospectiva complementar em período relacionado ao teste semanal já avaliado",
        "modelo": MODELO, "parametros": candidatos()[MODELO].get_params(),
        "entradas_sem_clima": ENTRADAS_MENSAIS + TERRITORIO, "entradas_climaticas": CLIMA,
        "fontes": "Mesmos CSVs anuais e GeoJSON da AV1, verificados por hash e reconciliados por bairro-semana",
        "meses": {
            nome: sorted(am["MES_ALVO"].dt.strftime("%Y-%m").unique())
            for nome, am in (("treino", treino), ("validacao", validacao), ("teste", teste))
        },
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SAIDA, "x", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("manifesto.json", json.dumps(manifesto, indent=2, ensure_ascii=False))
        arquivo.writestr("observados_mes.csv", observados.to_csv(index=False))
        arquivo.writestr("cobertura_mes.csv", cobertura.to_csv(index=False))
        arquivo.writestr("metricas.csv", pd.concat([
            metricas_val.assign(conjunto="validacao"), metricas_teste.assign(conjunto="teste")
        ]).to_csv(index=False))
        arquivo.writestr("previsoes.csv", pd.concat([
            pv_val.assign(conjunto="validacao"), pv_teste.assign(conjunto="teste")
        ]).to_csv(index=False))
    print(json.dumps(manifesto["meses"], ensure_ascii=False))
    print(metricas_teste.round(3).to_string(index=False))
    print(f"Resultados em {SAIDA}")


if __name__ == "__main__":
    main()
