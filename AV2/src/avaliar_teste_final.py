"""Executa e registra a avaliação das configurações aprovadas para o teste."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from .auditar_base import CAMINHO_CONFIG, CAMINHO_DATASET, RAIZ_PROJETO, carregar_dados
from .baselines import previsoes_baselines
from .experimentos import CLIMA, CONTROLE, TERRITORIO, ajustar_candidato, candidatos, medir_previsoes
from .preparar_alvos import (
    ALVO_QUATRO_SEMANAS, ALVO_SEMANAL, preparar_painel, resumir_preparacao,
)

SAIDA = RAIZ_PROJETO / "AV2" / "artefatos" / "teste_final.zip"
MODELO = "Gradient Boosting"
RODADAS = (
    (1, ALVO_SEMANAL, "DATA_ALVO", "Persistência"),
    (4, ALVO_QUATRO_SEMANAS, "DATA_FIM_ALVO_4S", "Média das quatro semanas anteriores"),
)


def sha256(arquivo: Path) -> str:
    with arquivo.open("rb") as origem:
        return hashlib.file_digest(origem, "sha256").hexdigest()


def main() -> None:
    # O teste reservado só pode ser executado uma vez.
    if SAIDA.exists():
        raise SystemExit(f"O teste já foi registrado em {SAIDA}. Consulte os resultados salvos.")
    painel = preparar_painel(*carregar_dados())
    resumir_preparacao(painel)
    resumo, previsoes, selecao = [], [], []
    for semanas, alvo, fim, referencia in RODADAS:
        conjunto = painel[f"CONJUNTO_{semanas}S"]
        treino = painel.loc[conjunto.eq("treino")]
        # Modelo final reajustado em treino + validação, com parâmetros congelados.
        desenvolvimento = painel.loc[conjunto.isin(("treino", "validacao"))]
        teste = painel.loc[conjunto.eq("teste")]
        ultimo_alvo_ajuste = desenvolvimento[fim].max()
        # Garante que nenhum alvo do ajuste termine depois do início do teste.
        if ultimo_alvo_ajuste > teste["DATA_SEMANA"].min():
            raise ValueError("Dados de ajuste ainda em aberto na primeira previsão de teste.")
        limite_pico = float(treino.loc[treino[alvo].gt(0), alvo].quantile(0.9))
        base = teste[["BAIRRO", "DATA_SEMANA", "DATA_ALVO"]].assign(DATA_FIM_ALVO=teste[fim])
        saidas = [(referencia, "baseline", previsoes_baselines(teste, semanas)[referencia])]
        for cenario, numericas in (("sem clima", CONTROLE), ("com clima", CONTROLE + CLIMA)):
            colunas = numericas + TERRITORIO
            estimador = candidatos()[MODELO]
            ajuste = ajustar_candidato(MODELO, estimador, numericas, desenvolvimento, alvo)
            with threadpool_limits(limits=2):
                previsto = ajuste.predict(teste[colunas])
            saidas.append((MODELO, cenario, previsto))

        for nome, cenario, previsto in saidas:
            valores = base.assign(horizonte_semanas=semanas, modelo=nome, cenario=cenario,
                                  observado=teste[alvo], previsto=previsto)
            contagens = valores[["observado", "previsto"]].to_numpy()
            if not np.isfinite(contagens).all() or (contagens < 0).any():
                raise ValueError(f"Contagem inválida para {nome}/{cenario}/{semanas}.")
            previsoes.append(valores)
            resumo.append({"horizonte_semanas": semanas, "modelo": nome, "cenario": cenario,
                           **medir_previsoes(valores, limite_pico)})
        selecao.append({
            "semanas": semanas, "referencia": referencia, "alvo": alvo,
            "limite_pico_treino": limite_pico, "linhas_ajuste": len(desenvolvimento),
            "ultimo_alvo_ajuste": ultimo_alvo_ajuste.date().isoformat(),
            "primeira_semana_teste": teste["DATA_ALVO"].min().date().isoformat(),
            "ultima_semana_teste": teste[fim].max().date().isoformat(),
        })

    metricas = pd.DataFrame(resumo)
    valores = pd.concat(previsoes, ignore_index=True)
    fontes = [CAMINHO_DATASET, CAMINHO_CONFIG, Path(__file__)]
    fontes += [Path(__file__).with_name(nome) for nome in (
        "experimentos.py", "baselines.py", "preparar_alvos.py"
    )]
    manifesto = {
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "versoes": {"numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__},
        "criterio_principal": "MAE",
        "modelo": MODELO, "parametros": candidatos()[MODELO].get_params(),
        "atributos_sem_clima": CONTROLE + TERRITORIO, "atributos_climaticos": CLIMA,
        "horizontes": selecao,
        "sha256": {p.relative_to(RAIZ_PROJETO).as_posix(): sha256(p) for p in fontes},
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SAIDA, "x", compression=ZIP_DEFLATED) as arquivo:
        arquivo.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
        arquivo.writestr("metricas.csv", metricas.to_csv(index=False))
        arquivo.writestr("previsoes.csv", valores.to_csv(index=False))
    print(metricas.round(3).to_string(index=False))
    print(f"Resultados registrados em {SAIDA}")


if __name__ == "__main__":
    main()
