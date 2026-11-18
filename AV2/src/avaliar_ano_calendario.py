"""Prevê notificações por bairro e ano usando somente totais dos anos anteriores."""

from __future__ import annotations

import hashlib
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from .auditar_base import RAIZ_PROJETO


ARTEFATOS = RAIZ_PROJETO / "AV2" / "artefatos"
FONTE = ARTEFATOS / "mes_calendario.zip"
SAIDA = ARTEFATOS / "previsao_anual.zip"
VALIDACAO = (2020, 2021, 2022, 2023)
TESTE = (2024, 2025)
ESTIMATIVA = 2026


def avaliar_anos(meses: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    meses = meses.copy()
    meses["MES_ALVO"] = pd.to_datetime(meses["MES_ALVO"], format="%Y-%m-%d", errors="raise")
    if (meses["MES_ALVO"].isna().any() or meses["BAIRRO"].isna().any()
            or not meses["MES_ALVO"].dt.is_month_start.all()
            or meses.duplicated(["MES_ALVO", "BAIRRO"]).any()):
        raise ValueError("Cada linha deve representar um bairro e um mês civil distinto.")
    if meses["observado"].isna().any() or not meses["observado"].ge(0).all():
        raise ValueError("As contagens mensais observadas precisam ser válidas.")

    meses["ano"] = meses["MES_ALVO"].dt.year
    meses = meses.loc[meses["ano"].lt(ESTIMATIVA)]
    grupos = meses.groupby(["ano", "BAIRRO"])["observado"]
    totais = grupos.sum().unstack()
    anos_esperados = list(range(2016, ESTIMATIVA))
    if (totais.index.tolist() != anos_esperados or totais.shape[1] != 94
            or totais.isna().any().any() or not grupos.size().eq(12).all()):
        raise ValueError("A série anual exige doze meses em cada um dos 94 bairros de 2016 a 2025.")

    # Acrescenta um ano vazio para estimar 2026 a partir dos anos já observados.
    com_estimativa = totais.reindex(anos_esperados + [ESTIMATIVA])
    passado = com_estimativa.shift(1)
    candidatos = {
        "Último ano": passado,
        "Média dos três anos anteriores": passado.rolling(3, min_periods=3).mean(),
        "Mediana dos três anos anteriores": passado.rolling(3, min_periods=3).median(),
    }
    # Escolhe a regra anual pelo menor MAE na validação 2020-2023.
    erros_validacao = {
        nome: (tabela.loc[list(VALIDACAO)] - totais.loc[list(VALIDACAO)]).abs().to_numpy().mean()
        for nome, tabela in candidatos.items()
    }
    # A ordem do dicionário resolve empates a favor da regra mais simples.
    vencedor = min(erros_validacao, key=erros_validacao.get)
    previsoes = candidatos[vencedor]
    metricas = []
    for nome, mae in erros_validacao.items():
        metricas.append({"conjunto": "validação", "ano": "2020–2023", "regra": nome,
                         "MAE_bairro": mae, "erro_recife": None})
    for ano in TESTE:
        residuos = previsoes.loc[ano] - totais.loc[ano]
        metricas.append({"conjunto": "teste", "ano": str(ano), "regra": vencedor,
                         "MAE_bairro": residuos.abs().mean(), "erro_recife": residuos.sum()})

    rotulos = {ano: "teste" if ano in TESTE else "histórico" for ano in anos_esperados}
    rotulos[ESTIMATIVA] = "estimativa"
    observado_long = com_estimativa.stack(future_stack=True).rename("observado")
    previsao_long = previsoes.loc[list(TESTE) + [ESTIMATIVA]].stack().rename("previsto")
    resultados = pd.concat([observado_long, previsao_long], axis=1).reset_index()
    resultados["tipo"] = resultados["ano"].map(rotulos)
    manifesto = {
        "regra": vencedor,
        "metrica_selecao": "MAE por bairro e ano na validação",
        "validacao": list(VALIDACAO),
        "teste": list(TESTE),
        "estimativa": ESTIMATIVA,
        "unidade": "contagem de notificações de dengue A90 por bairro e ano civil",
        "entradas": "totais de anos anteriores, sem clima",
        "nota": "Base consolidada até dezembro de 2025. Disponibilidade operacional na data de corte não verificada.",
    }
    return resultados, pd.DataFrame(metricas), manifesto


def main() -> None:
    with ZipFile(FONTE) as fonte, fonte.open("observados_mes.csv") as arquivo:
        meses = pd.read_csv(arquivo)
    resultados, metricas, manifesto = avaliar_anos(meses)
    manifesto["sha256_fonte"] = hashlib.sha256(FONTE.read_bytes()).hexdigest()
    with ZipFile(SAIDA, "w", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("previsoes.csv", resultados.to_csv(index=False))
        arquivo.writestr("metricas.csv", metricas.to_csv(index=False))
        arquivo.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
    print(metricas.round(2).to_string(index=False))
    print(resultados.groupby("ano")[["observado", "previsto"]].sum(min_count=1).round(1).to_string())


if __name__ == "__main__":
    main()
