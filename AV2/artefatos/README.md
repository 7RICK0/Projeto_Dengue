# Artefatos da AV2: resultados que o notebook e o painel usam para rodar

Esta pasta guarda os resultados registrados dos experimentos. O notebook lê as tabelas para reproduzir a avaliação e os gráficos. O exportador lê os resultados usados na interface e grava `AV2/painel/dados.js`. O painel aberto no navegador lê apenas esse arquivo de dados. Os arquivos `teste_final.zip` e `mes_calendario.zip` guardam as avaliações congeladas.

Cada `.zip` tem tabelas em CSV e um `manifesto.json`, que registra data, versões e parâmetros da execução.

| Arquivo | O que guarda | Quem usa |
|---|---|---|
| `teste_final.zip` | Métricas e previsões do **teste final** (nov/2020 a nov/2021), executado uma única vez | Notebook, painel, testes |
| `mes_calendario.zip` | Previsão do **mês civil completo** por bairro, com observados e cobertura climática | Notebook, painel, testes |
| `previsao_anual.zip` | Regra anual sem clima: 2024, 2025 e estimativa de 2026 | Notebook, painel |
| `importancia_variaveis.zip` | Importância de cada variável, medida na validação | Notebook |
| `sensibilidades.zip` | Efeito de retirar grupos de variáveis e acerto dos bairros prioritários | Notebook, painel |
| `hiperparametros.zip` | Grade de 12 configurações do Gradient Boosting, na validação | Notebook |
| `clima_sem_temperatura.zip` | Análise complementar: modelo sem a temperatura | Notebook |
| `serie_sem_clima.zip` | Série complementar sem clima até 2025 | Notebook |
| `figuras/` | Cópias de 8 gráficos do notebook, usadas no relatório PDF e no README | Relatório, README |

Para atualizar os dados do painel a partir dos resultados salvos, execute `python -B -m AV2.src.exportar_painel` na raiz do projeto.
