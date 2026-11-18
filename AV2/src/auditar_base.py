"""Auditoria inicial da base preparada para a AV2 do AnteceDengue.

Este módulo não treina modelos. Ele apenas verifica se o dataset e a configuração
herdados da AV1 têm a estrutura necessária para congelar o protocolo experimental.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
ARTEFATOS_AV1 = RAIZ_PROJETO / "AV1" / "artefatos"
CAMINHO_DATASET = ARTEFATOS_AV1 / "dataset_av1_revisado.csv"
CAMINHO_CONFIG = ARTEFATOS_AV1 / "config_av2.json"

COLUNAS_OBRIGATORIAS = {
    "BAIRRO",
    "DATA_SEMANA",
    "DATA_ALVO",
    "NOTIFICACOES_PROXIMA_SEMANA",
    "ELEGIVEL_AV2",
    "CONJUNTO",
}


def carregar_dados() -> tuple[pd.DataFrame, dict]:
    """Carrega dataset e configuração, falhando cedo em caso de ausência."""
    if not CAMINHO_DATASET.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {CAMINHO_DATASET}")
    if not CAMINHO_CONFIG.exists():
        raise FileNotFoundError(f"Configuração não encontrada: {CAMINHO_CONFIG}")

    dados = pd.read_csv(CAMINHO_DATASET, low_memory=False)
    with CAMINHO_CONFIG.open(encoding="utf-8") as arquivo:
        config = json.load(arquivo)
    return dados, config


def auditar(dados: pd.DataFrame, config: dict) -> dict:
    """Retorna um resumo verificável sem alterar o dataset original."""
    ausentes = sorted(COLUNAS_OBRIGATORIAS.difference(dados.columns))
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {ausentes}")

    dados = dados.copy()
    dados["DATA_ALVO"] = pd.to_datetime(dados["DATA_ALVO"], errors="raise")
    elegivel = dados[dados["ELEGIVEL_AV2"].astype(str).str.lower().isin({"true", "1"})]

    alvo_config = config.get("alvo")
    if alvo_config != "NOTIFICACOES_PROXIMA_SEMANA":
        raise ValueError(f"Alvo inesperado na configuração: {alvo_config!r}")

    por_conjunto = {}
    for nome, grupo in elegivel.groupby("CONJUNTO", sort=True):
        por_conjunto[str(nome)] = {
            "linhas": int(len(grupo)),
            "semanas": int(grupo["DATA_ALVO"].nunique()),
            "bairros": int(grupo["BAIRRO"].nunique()),
            "inicio": grupo["DATA_ALVO"].min().date().isoformat(),
            "fim": grupo["DATA_ALVO"].max().date().isoformat(),
        }

    fora = elegivel[elegivel["CONJUNTO"] == "fora"]
    semanas_fora = sorted(data.date().isoformat() for data in fora["DATA_ALVO"].unique())

    return {
        "linhas_dataset": int(len(dados)),
        "colunas_dataset": int(dados.shape[1]),
        "linhas_elegiveis_av2": int(len(elegivel)),
        "bairros_elegiveis": int(elegivel["BAIRRO"].nunique()),
        "alvo": alvo_config,
        "corte_validacao_config": config.get("corte_validacao"),
        "corte_teste_config": config.get("corte_teste"),
        "por_conjunto": por_conjunto,
        "linhas_elegiveis_marcadas_fora": int(len(fora)),
        "semanas_elegiveis_marcadas_fora": semanas_fora,
        "alertas": [
            "Há observações elegíveis marcadas como 'fora' nas datas exatas dos cortes; "
            "as fronteiras devem ser decididas antes do treinamento."
        ]
        if len(fora)
        else [],
    }


def main() -> None:
    dados, config = carregar_dados()
    resultado = auditar(dados, config)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

