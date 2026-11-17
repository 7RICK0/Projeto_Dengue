"""Validação local dos artefatos gerados pela AV1 revisada."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd


ARQUIVOS_OBRIGATORIOS = [
    "dataset_av1_revisado.csv",
    "manifesto_execucao.json",
    "config_av2.json",
    "preprocessador_normalizado.joblib",
    "preprocessador_padronizado.joblib",
    "preprocessador_sem_escala.joblib",
]

RELATORIOS_OBRIGATORIOS = [
    "aquisicao_por_ano.csv",
    "qualidade_por_ano.csv",
    "classificacao_final_por_ano.csv",
    "sensibilidade_classificacao_por_ano.csv",
    "sensibilidade_ids_por_ano.csv",
    "registros_fora_ano_arquivo.csv",
    "auditoria_zeros_por_ano.csv",
    "sensibilidade_limiar_clima.csv",
    "correlacoes_clima_defasagens_treino.csv",
    "correlacoes_features_climaticas_treino.csv",
    "correlacoes_features_climaticas_anomalias_treino.csv",
    "correlacao_chuva8_por_ano_treino.csv",
    "coorte_comparacao_av2.csv",
    "periodos_coortes_av2.csv",
    "distribuicao_alvo_treino.csv",
    "limiares_atencao_treino.csv",
    "populacao_bairro_ano.csv",
    "reconciliacao_populacao_por_ano.csv",
    "dicionario_completo.csv",
    "resumo_execucao_real.json",
]


def validar_utf8(path: Path) -> None:
    path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("diretorio", type=Path)
    args = parser.parse_args()
    raiz = args.diretorio.resolve()
    relatorios = raiz / "relatorios"

    ausentes = [nome for nome in ARQUIVOS_OBRIGATORIOS if not (raiz / nome).is_file()]
    ausentes += [f"relatorios/{nome}" for nome in RELATORIOS_OBRIGATORIOS if not (relatorios / nome).is_file()]
    assert not ausentes, f"Artefatos ausentes: {ausentes}"

    for path in [raiz / "manifesto_execucao.json", raiz / "config_av2.json", relatorios / "resumo_execucao_real.json"]:
        validar_utf8(path)
        json.loads(path.read_text(encoding="utf-8"))

    dataset = pd.read_csv(raiz / "dataset_av1_revisado.csv", low_memory=False)
    manifesto = json.loads((raiz / "manifesto_execucao.json").read_text(encoding="utf-8"))
    config = json.loads((raiz / "config_av2.json").read_text(encoding="utf-8"))

    assert len(dataset) == manifesto["linhas_painel"]
    assert len(dataset.columns) == manifesto["colunas"]
    assert config["alvo"] == "NOTIFICACOES_PROXIMA_SEMANA"
    assert manifesto["definicao_alvo"].startswith("notificações A90")
    assert not dataset.duplicated(["BAIRRO", "DATA_SEMANA"]).any()
    assert dataset.loc[~dataset["COBERTURA_DENGUE"], "NOTIFICACOES_SEMANAIS"].isna().all()
    assert dataset.loc[dataset["CONJUNTO"].isin(["treino", "validacao", "teste"]), config["alvo"]].notna().all()
    assert dataset["ELEGIVEL_AV2"].sum() == manifesto["coorte_elegivel"]
    for coluna in [
        "POPULACAO_BAIRRO_ANO",
        "POPULACAO_MUNICIPAL_ANO",
        "TIPO_POPULACAO",
        "FONTE_POPULACAO",
        "DENSIDADE_HAB_KM2_ANO",
    ]:
        assert coluna in dataset, f"Variável populacional ausente: {coluna}"
    cobertas = dataset["COBERTURA_DENGUE"]
    assert dataset.loc[cobertas, "POPULACAO_BAIRRO_ANO"].notna().all()
    assert dataset.loc[cobertas, "POPULACAO_BAIRRO_ANO"].gt(0).all()
    assert "POPULACAO_2022" not in config["entradas_numericas"]
    assert "POPULACAO_BAIRRO_ANO" in config["entradas_numericas"]
    assert "DENSIDADE_HAB_KM2_ANO" in config["entradas_numericas"]
    for atraso in range(1, 9):
        for coluna in [
            f"PRECIPITACAO_LAG_{atraso}_MM",
            f"TEMPERATURA_LAG_{atraso}_C",
            f"UMIDADE_LAG_{atraso}_PCT",
        ]:
            assert coluna in dataset, f"Feature climática ausente: {coluna}"
            assert coluna in config["entradas_numericas"], f"Feature fora da configuração: {coluna}"
    for janela in [2, 4, 8]:
        for coluna in [
            f"CHUVA_{janela}S_MM",
            f"TEMPERATURA_MEDIA_{janela}S_C",
            f"UMIDADE_MEDIA_{janela}S_PCT",
        ]:
            assert coluna in dataset, f"Janela climática ausente: {coluna}"
            assert coluna in config["entradas_numericas"], f"Janela fora da configuração: {coluna}"

    for nome in ["normalizado", "padronizado", "sem_escala"]:
        joblib.load(raiz / f"preprocessador_{nome}.joblib")

    print(
        "VALIDACAO_OK",
        f"linhas={len(dataset)}",
        f"colunas={len(dataset.columns)}",
        f"coorte={int(dataset['ELEGIVEL_AV2'].sum())}",
    )


if __name__ == "__main__":
    main()
