"""Testes de integridade da AV2: alvos, cortes, métricas registradas e dados do painel.

Rodar a partir da raiz do repositório:
    python -B -m unittest discover -s AV2/tests -t .
Nenhum teste treina modelos nem altera artefatos.
"""

from __future__ import annotations

import io
import json
import unittest
import zipfile

import numpy as np
import pandas as pd

from AV2.src.auditar_base import RAIZ_PROJETO, carregar_dados
from AV2.src.experimentos import medir_previsoes
from AV2.src.exportar_painel import ALIASES_MALHA, chave
from AV2.src.preparar_alvos import ALVO_QUATRO_SEMANAS, ALVO_SEMANAL, preparar_painel

ARTEFATOS = RAIZ_PROJETO / "AV2" / "artefatos"


def ler_zip(nome: str, arquivo: str) -> bytes:
    with zipfile.ZipFile(ARTEFATOS / nome) as z:
        return z.read(arquivo)


def ler_dados_painel() -> dict:
    texto = (RAIZ_PROJETO / "AV2" / "painel" / "dados.js").read_text(encoding="utf-8")
    return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])


class TestPreparacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dados, config = carregar_dados()
        cls.dados = dados
        cls.config = config
        cls.painel = preparar_painel(dados, config)

    def test_uma_linha_por_bairro_e_semana(self):
        self.assertFalse(self.painel.duplicated(["BAIRRO", "DATA_SEMANA"]).any())
        self.assertEqual(self.painel["BAIRRO"].nunique(), 94)

    def test_zero_e_ausente_sao_diferentes(self):
        # Semana sem cobertura fica ausente; não vira zero.
        sem_cobertura = ~self.painel["COBERTURA_DENGUE"]
        self.assertTrue(self.painel.loc[sem_cobertura, "NOTIFICACOES_SEMANAIS"].isna().all())

    def test_defasagens_usam_somente_o_passado(self):
        p = self.painel
        serie = p.set_index(["BAIRRO", "DATA_SEMANA"])["NOTIFICACOES_SEMANAIS"]
        anteriores = [
            serie.reindex(pd.MultiIndex.from_arrays(
                [p["BAIRRO"], p["DATA_SEMANA"] - pd.Timedelta(weeks=k)])).to_numpy()
            for k in range(1, 5)
        ]
        lag1 = p["NOTIFICACOES_LAG_1"].to_numpy()
        ok = ~np.isnan(lag1) & ~np.isnan(anteriores[0])
        np.testing.assert_allclose(lag1[ok], anteriores[0][ok])
        media = p["MEDIA_NOTIFICACOES_4S"].to_numpy()
        esperada = np.mean(np.vstack(anteriores), axis=0)
        ok = ~np.isnan(media) & ~np.isnan(esperada)
        np.testing.assert_allclose(media[ok], esperada[ok])

    def test_janelas_nao_atravessam_cortes(self):
        p = self.painel
        corte_val = pd.Timestamp(self.config["corte_validacao"])
        corte_teste = pd.Timestamp(self.config["corte_teste"])
        for nome, ini, fim in (("treino", None, corte_val), ("validacao", corte_val, corte_teste)):
            grupo = p.loc[p["CONJUNTO_4S"].eq(nome)]
            self.assertTrue(grupo["DATA_FIM_ALVO_4S"].lt(fim).all(), nome)
            if ini is not None:
                self.assertTrue(grupo["DATA_ALVO"].ge(ini).all(), nome)
        teste = p.loc[p["CONJUNTO_4S"].eq("teste")]
        self.assertTrue(teste["DATA_ALVO"].ge(corte_teste).all())

    def test_alvo_quatro_semanas_e_soma_das_quatro(self):
        p = self.painel
        serie = p.set_index(["BAIRRO", "DATA_SEMANA"])["NOTIFICACOES_SEMANAIS"]
        futuras = sum(
            serie.reindex(pd.MultiIndex.from_arrays(
                [p["BAIRRO"], p["DATA_SEMANA"] + pd.Timedelta(weeks=k)])).to_numpy()
            for k in range(1, 5)
        )
        alvo = p[ALVO_QUATRO_SEMANAS].to_numpy()
        ok = ~np.isnan(alvo)
        np.testing.assert_allclose(alvo[ok], futuras[ok])
        np.testing.assert_allclose(
            p[ALVO_SEMANAL].dropna().to_numpy(),
            serie.reindex(pd.MultiIndex.from_arrays(
                [p["BAIRRO"], p["DATA_SEMANA"] + pd.Timedelta(weeks=1)])).dropna().to_numpy(),
        )


class TestTesteFinal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metricas = pd.read_csv(io.BytesIO(ler_zip("teste_final.zip", "metricas.csv")))
        cls.previsoes = pd.read_csv(io.BytesIO(ler_zip("teste_final.zip", "previsoes.csv")))
        cls.manifesto = json.loads(ler_zip("teste_final.zip", "manifesto.json"))

    def test_metricas_recalculadas_batem(self):
        limites = {h["semanas"]: h["limite_pico_treino"] for h in self.manifesto["horizontes"]}
        for (semanas, modelo, cenario), grupo in self.previsoes.groupby(
            ["horizonte_semanas", "modelo", "cenario"]
        ):
            calculado = medir_previsoes(grupo, limites[semanas])
            registrado = self.metricas.query(
                "horizonte_semanas == @semanas and modelo == @modelo and cenario == @cenario"
            ).iloc[0]
            for nome in ("MAE", "RMSE", "MAE_picos", "MAE_municipal"):
                self.assertAlmostEqual(calculado[nome], registrado[nome], places=6, msg=nome)

    def test_cenarios_usam_as_mesmas_linhas(self):
        for _, grupo in self.previsoes.groupby("horizonte_semanas"):
            chaves = {
                cenario: frozenset(zip(g["BAIRRO"], g["DATA_SEMANA"]))
                for cenario, g in grupo.groupby("cenario")
            }
            self.assertEqual(len(set(chaves.values())), 1)

    def test_numeros_citados_nos_materiais(self):
        def mae(semanas, cenario):
            return self.metricas.query(
                "horizonte_semanas == @semanas and cenario == @cenario")["MAE"].iloc[0]
        self.assertAlmostEqual(mae(4, "baseline"), 3.835, places=3)
        self.assertAlmostEqual(mae(4, "sem clima"), 2.978, places=3)
        self.assertAlmostEqual(mae(4, "com clima"), 2.882, places=3)
        self.assertAlmostEqual(100 * (1 - mae(4, "com clima") / mae(4, "baseline")), 24.9, places=1)
        self.assertAlmostEqual(100 * (1 - mae(4, "com clima") / mae(4, "sem clima")), 3.2, places=1)

    def test_dados_do_manifesto_conferem(self):
        import hashlib
        # O manifesto foi gravado quando a pasta se chamava execucao_2026-11-17; o conteúdo é o que importa.
        # Ele registrou os arquivos com quebra de linha do Windows (CRLF), e o Git os guarda com LF.
        # Por isso a quebra de linha é padronizada para CRLF antes do hash, em qualquer sistema.
        for nome in ("dataset_av1_revisado.csv", "config_av2.json"):
            conteudo = (RAIZ_PROJETO / "AV1" / "artefatos" / nome).read_bytes()
            conteudo = conteudo.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            atual = hashlib.sha256(conteudo).hexdigest()
            self.assertEqual(atual, self.manifesto["sha256"][f"AV1/artefatos/execucao_2026-11-17/{nome}"], nome)


class TestPainel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dados = ler_dados_painel()
        cls.previsoes = pd.read_csv(io.BytesIO(ler_zip("mes_calendario.zip", "previsoes.csv")))

    def test_meses_do_painel_batem_com_o_artefato(self):
        bairros = [ALIASES_MALHA.get(chave(m["name"]), chave(m["name"])) for m in self.dados["mapa"]]
        self.assertEqual(len(set(bairros)), 94)
        comparados = 0
        for mes in self.dados["meses"]:
            for cenario, campo in (("com clima", "com"), ("sem clima", "sem")):
                grupo = self.previsoes[
                    self.previsoes["MES_ALVO"].str[:7].eq(mes["inicio"][:7])
                    & self.previsoes["cenario"].eq(cenario)
                    & self.previsoes["conjunto"].eq("teste")
                ]
                if campo not in mes:
                    self.assertTrue(grupo.empty, mes["inicio"])
                    continue
                por_bairro = grupo.set_index("BAIRRO").reindex(bairros)
                np.testing.assert_allclose(por_bairro["previsto"], mes[campo], atol=0.06)
                np.testing.assert_array_equal(por_bairro["observado"], mes["observado"])
                comparados += 1
        self.assertEqual(comparados, 14)

    def test_emissao_antes_do_mes(self):
        for mes in self.dados["meses"]:
            self.assertLess(mes["emissao"], mes["inicio"])

    def test_servidor_entrega_a_pagina_do_painel(self):
        from urllib.request import ProxyHandler, build_opener

        from AV2.src.servir_painel import encerrar_servidores, iniciar_servidor

        self.addCleanup(encerrar_servidores)
        servidor = iniciar_servidor(RAIZ_PROJETO / "AV2" / "painel")
        navegador = build_opener(ProxyHandler({}))  # sem proxy: o endereço é só desta máquina
        for arquivo in ("abrir_painel.html", "dados.js"):
            with navegador.open(f"http://127.0.0.1:{servidor.server_port}/{arquivo}", timeout=10) as resposta:
                self.assertEqual(resposta.status, 200, arquivo)
                self.assertGreater(len(resposta.read()), 1000, arquivo)

    def test_botao_do_painel_tem_link_e_textos(self):
        from AV2.src.servir_painel import TEXTO_DO_BOTAO, montar_caixa

        for no_colab in (False, True):
            caixa = montar_caixa("http://127.0.0.1:5000/abrir_painel.html?a=1&b=2", no_colab)
            self.assertIn('href="http://127.0.0.1:5000/abrir_painel.html?a=1&amp;b=2"', caixa)  # endereço escapado
            self.assertIn('target="_blank"', caixa)  # abre em uma página própria
            self.assertIn(TEXTO_DO_BOTAO, caixa)
            self.assertIn("Explore a previsão bairro por bairro", caixa)
        self.assertIn("só funciona nesta sessão do Colab", montar_caixa("https://x/", True))
        self.assertIn("só neste computador", montar_caixa("http://127.0.0.1:1/", False))


if __name__ == "__main__":
    unittest.main()
