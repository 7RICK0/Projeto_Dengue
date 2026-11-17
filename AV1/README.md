# AnteceDengue — AV1: entendimento e preparação dos dados

**Disciplina:** Aprendizado de Máquina (SI031), CESAR School · **Professora:** Chaina Oliveira · **Aluno:** Erick Acioli Belo

O AnteceDengue investiga se o histórico de notificações e as condições climáticas ajudam a antecipar aumentos de dengue nos bairros do Recife. O objetivo é apoiar a prevenção e o planejamento de ações. A AV1 reuniu, analisou e preparou os dados. A primeira previsão a ser avaliada na AV2 estima a quantidade de notificações por bairro na semana seguinte.

- [Notebook revisado da AV1 no Colab](https://colab.research.google.com/drive/1MpXxyiLApFqNRDW0AjeOK8G3z2Y053i6)
- [Notebook da entrega original](https://drive.google.com/file/d/1l5gE4bAepVZOID-jIpaI7bWHt0M86iMw/view)
- [Slides da primeira entrega](https://drive.google.com/file/d/1LAcEYa9UGkUpkPDHoMJzGeT0Lr12jSN5/view)

## Materiais preservados localmente

- `notebooks/Projeto_AV1_Dengue_Recife_original.ipynb`: entrega original que recebeu 8/10.
- `notebooks/AnteceDengue_AV1_revisada.ipynb`: revisão executada, com as saídas salvas.
- `docs/Documentacao_AV1_Dengue.pdf`: documentação da primeira entrega.
- `slides/Apresentacao_AV1.pdf`: apresentação da primeira entrega.

Esses arquivos permitem revisar a AV1 sem depender apenas dos links externos. O CSV, o manifesto e os relatórios gerados pela execução revisada ainda precisam ser reproduzidos ou recuperados antes da modelagem da AV2.

## O que foi entregue na AV1

A primeira versão definiu o problema, descreveu as fontes e fez a análise exploratória das notificações. O notebook integrou dados de território e clima, agregou os registros por bairro e semana, criou variáveis de histórico e exportou a primeira base para modelagem. A entrega recebeu **8/10**. Os pontos de melhoria relatados foram a organização do notebook e o aprofundamento da construção e da análise das novas variáveis.

## O que mudou após a entrega

| Área | Melhoria na versão revisada |
|---|---|
| Organização | Seções com objetivos, tabelas de qualidade, dicionário das variáveis e resumo da execução. |
| Leitura e limpeza | Esquemas anuais harmonizados, perdas contabilizadas e regra explícita para registros com identificadores repetidos. Removemos cópias idênticas com ID presente e preservamos registros divergentes para análise de sensibilidade. |
| Calendário e cobertura | Notificações e clima usam a mesma semana civil, de segunda a domingo. Semanas de fronteira incompletas ficam sem contagem válida. Dentro da cobertura assumida, zero indica ausência de registro na fonte. |
| Engenharia de atributos | Defasagens de 1 a 4 semanas, média móvel, chuva acumulada, sazonalidade e medidas territoriais com fórmulas, justificativas e análise exploratória. Janelas incompletas ficam ausentes. |
| Pré-processamento | Normalização Min-Max e padronização demonstradas em alternativas separadas, ajustadas somente no treino. O CSV preserva as escalas originais e o alvo permanece como contagem. |
| Continuidade | Alvo da próxima semana por bairro, coorte comum para comparar modelos com e sem clima, cortes temporais iniciais e exportação com relatórios e manifesto de execução. |

## Dados e resultados da revisão

| Fonte | Uso |
|---|---|
| [Prefeitura do Recife — notificações](https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya) | Registros anuais publicados, com agregação por bairro e semana. |
| [Prefeitura do Recife — área urbana](https://dados.recife.pe.gov.br/dataset/area-urbana) | Referências de bairros e regiões político-administrativas. |
| [IBGE — Censo 2022](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_xlsx/) | População e área dos bairros para calcular densidade e taxas. |
| [INMET — estação A301](https://portal.inmet.gov.br/dadoshistoricos) | Chuva, temperatura e umidade, agregadas por semana conforme a cobertura horária. |

Na execução de referência, em **04/11/2026**, foram lidas **71.663 linhas** de arquivos de 2016 a 2025. Após a limpeza, restaram **71.176 registros**. O painel exportado contém **49.162 linhas por bairro e semana, 36 colunas e 94 bairros**. O número de linhas do painel mede combinações de território e tempo. A contagem analisada representa registros publicados de notificação.

A análise exploratória usou o período anterior à validação. A maior correlação linear municipal em valor absoluto entre as combinações avaliadas foi entre chuva e notificações duas semanas depois, de aproximadamente **0,15**. A associação foi fraca e variou entre anos. O ganho preditivo do clima será medido na AV2.

## Como reproduzir

1. Abra o notebook revisado no Colab e execute as células em ordem. A aquisição depende da disponibilidade das fontes oficiais. Os arquivos anuais do INMET podem levar alguns minutos para baixar.
2. Confira os relatórios de perdas, junções, cobertura climática e partições temporais. Eles documentam o recorte válido de cada análise.
3. No painel de arquivos do Colab, baixe `dados_av1_revisada/dataset_av1_revisado.csv` e preserve o manifesto e os relatórios da mesma execução. Use o CSV agregado na AV2.

## Passagem para a AV2

A unidade de modelagem é **bairro × semana**. Ao fim da semana atual, as entradas disponíveis até essa data servem para estimar `CASOS_PROXIMA_SEMANA` no mesmo bairro. A comparação inicial usa persistência, regressão de Poisson, árvore de decisão e Random Forest. Cada modelo candidato será avaliado com e sem clima nas mesmas observações, usando **MAE** como métrica principal e **RMSE** como complemento.

O recorte climático inicial cobre **2016–2021** e usa uma única estação para todo o Recife. A discussão dos resultados deve considerar atrasos e revisões nas notificações, identificadores ambíguos, classificação dos registros, cobertura e população de referência do Censo 2022. A antecedência mensal segue como meta do projeto e exige avaliação própria.
