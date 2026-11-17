# Entrega 1 - AV1: entendimento e preparação dos dados

- **Projeto:** AnteceDengue
- **Disciplina:** Aprendizado de Máquina (SI031) - CESAR School
- **Professora:** Chaina Oliveira
- **Aluno:** Erick Acioli Belo
- **Nota da entrega original:** 8,0/10

## 1. Visão geral

O AnteceDengue nasceu do desafio público [“Limitações na Antecipação de Surtos de Dengue na Cidade do Recife”](https://bancodeoportunidades.recife.pe.gov.br/), apresentado também em https://shiny-raindrop-cee689.netlify.app. O projeto investiga se chuva, temperatura e umidade, combinadas com informações epidemiológicas e territoriais, podem antecipar aumentos de casos notificados nos bairros e apoiar visitas, inspeções e ações preventivas antes do crescimento dos registros.

A AV1 cobre o ciclo inicial do projeto: entendimento do problema, aquisição e descrição dos dados, análise exploratória, tratamento, pré-processamento e engenharia de atributos. O treinamento e a seleção do modelo pertencem à AV2.

O primeiro experimento preditivo da AV2 estimará a quantidade de notificações do mesmo bairro na semana seguinte. Horizontes de semanas, meses ou ano permanecem como objetivo de produto, mas cada horizonte precisará de alvo, dados e validação próprios.

## 2. Materiais da Entrega 1

### Entrega original avaliada

- [`notebooks/Projeto_AV1_Dengue_Recife_original.ipynb`](notebooks/Projeto_AV1_Dengue_Recife_original.ipynb): notebook que integrou as fontes e gerou a primeira base.
- [`docs/Documentacao_AV1_Dengue.pdf`](docs/Documentacao_AV1_Dengue.pdf): documentação entregue na primeira etapa.
- [`slides/Apresentacao_AV1.pdf`](slides/Apresentacao_AV1.pdf): apresentação da AV1.

### Revisão preparada para a AV2

- [`notebooks/AnteceDengue_AV1_revisada.ipynb`](notebooks/AnteceDengue_AV1_revisada.ipynb): notebook reorganizado, corrigido e reexecutado com fontes oficiais em 17/11/2026.
- [`artefatos/execucao_2026-11-17/`](artefatos/execucao_2026-11-17): dataset, manifesto, configuração, preprocessadores e relatórios produzidos pela mesma execução.
- [Notebook revisado no Colab](https://colab.research.google.com/drive/1MpXxyiLApFqNRDW0AjeOK8G3z2Y053i6).
- [Pasta oficial do projeto no Google Drive](https://drive.google.com/drive/folders/1oQXWFYeC_-33eYTr_Q75-bXMiFFtg3yE?usp=sharing).

Os arquivos originais foram preservados. A revisão não apaga nem substitui a entrega que recebeu 8/10; ela registra as correções necessárias para que a modelagem da AV2 parta de uma base mais confiável.

## 3. Problema, tese e alvo

**Tese:** chuva, temperatura e umidade possuem efeitos contemporâneos, acumulados e defasados que podem acrescentar capacidade de antecipar o aumento de casos notificados nos bairros do Recife, apoiando a identificação de áreas prioritárias e o planejamento preventivo.

**Unidade de análise:** bairro x semana.

**Alvo principal:** `NOTIFICACOES_PROXIMA_SEMANA`, que representa a quantidade de casos notificados de dengue A90 publicados para o mesmo bairro em `t+1`. “Casos notificados” é a expressão de comunicação; `NOTIFICACOES` permanece no código por precisão técnica.

O alvo não representa automaticamente casos confirmados, pessoas únicas ou episódios clínicos únicos. A classificação final pode ser encerrada ou revisada depois da semana da notificação; por isso, códigos 10, 11 e 12 são analisados como sensibilidade separada e nunca como entrada do modelo principal. A decisão preserva a tese operacional de antecipar demanda de vigilância sem usar informação futura.

## 4. Fontes de dados

| Fonte | Informação utilizada | Papel no projeto |
|---|---|---|
| [Banco de Oportunidades do Recife](https://bancodeoportunidades.recife.pe.gov.br/) | Desafio de antecipação territorializada e preventiva | Origem do problema e resultados esperados |
| [Prefeitura do Recife - notificações](https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya) | Data, semana, bairro, identificação e classificação dos registros | Construir a contagem semanal e o alvo futuro |
| [Prefeitura do Recife - área urbana](https://dados.recife.pe.gov.br/dataset/area-urbana) | Malha oficial, nomes de bairros e RPAs | Padronizar territórios e apoiar o mapa |
| [CIEVS/Sesau Recife - população 2010–2017](https://cievsrecife.files.wordpress.com/2017/11/populac3a7c3a3o-2010-a-2017-uvepi1.pdf) | Censo 2010 e estimativas institucionais por bairro | Usar população de 2016–2017 no intervalo correspondente |
| [IBGE - Censo 2022](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_xlsx/) | População observada e área dos 94 bairros | Servir de checkpoint censitário e calcular densidade e incidência |
| [IBGE/SIDRA - tabela 6579](https://sidra.ibge.gov.br/tabela/6579) | Totais municipais anuais | Reconciliar estimativas intercensitárias e projeções pós-Censo |
| [INMET - estação A301](https://portal.inmet.gov.br/dadoshistoricos) | Chuva, temperatura e umidade horárias | Criar atributos climáticos semanais |

Uma única estação climática é compartilhada por todos os bairros e não representa os microclimas do Recife. A população agora acompanha o ano da observação: 2016–2017 usa a estimativa institucional publicada pelo CIEVS; 2018–2021 é reconstrução intercensitária entre 2017 e 2022 reconciliada ao total municipal; 2022 é Censo observado; 2023–2025 são projeções pós-Censo. Cada linha identifica tipo, fonte e método, sem apresentar estimativas como medições censitárias.

Os códigos de classificação foram interpretados com apoio do [dicionário oficial de dengue do Ministério da Saúde](https://opendatasus.saude.gov.br/dataset/4d5e5d44-58a8-4d67-b8aa-4ef1e4b00a1c/resource/ccc60f03-2834-49a3-98f7-7ee76f50a316/download/dic_dados_dengue.pdf) e do [dicionário do Sinan Online](https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf).

## 5. Atendimento aos requisitos da professora

| Requisito da AV1 | Entrega original | Revisão atual | Situação e pendências |
|---|---|---|---|
| **1. Entendimento do problema** | Contexto, objetivo, uso esperado e primeiro alvo foram apresentados | Problema, tese, unidade de análise e momento da previsão foram explicitados | **Atendido.** Manter a distinção entre notificações, casos confirmados e alertas |
| **2. Detalhamento do dataset** | Fontes e variáveis principais foram descritas | Esquemas anuais, agravo A90, tipos, unidades, origem, papel, classificações e ausências foram auditados | **Atendido.** Relatórios da execução acompanham o dataset |
| **3. Análise exploratória** | Incluiu distribuições, rankings, sazonalidade e correlações | EDA usa apenas treino, inclui Pearson e Spearman, atrasos de 0–8 semanas, janelas acumuladas, controle mensal, estabilidade anual, análise municipal e por bairro | **Atendido na revisão.** Associação não é tratada como causalidade ou previsão |
| **4. Tratamento e pré-processamento** | Tratou ausências, duplicatas e integrações, mas perdeu registros antigos e misturou calendários | Harmonizou esquemas, removeu duplicatas globais, auditou ano real, IDs, zeros e clima, alinhou calendários e demonstrou encoding e escalas | **Atendido com limitações documentadas.** Sensibilidades acompanham a AV2 |
| **5. Feature engineering** | Criou lags, média móvel, chuva acumulada, sazonalidade, incidência e densidade, mas com explicação insuficiente | Foram criados atrasos de chuva, temperatura e umidade de 1–8 semanas e janelas de 2/4/8 semanas, com regra, unidade, justificativa e disponibilidade temporal | **Atendido na revisão.** A utilidade será testada dentro da validação temporal da AV2 |
| **6. Documentação** | Documento, notebook e interpretações foram entregues | Notebook, README, dicionário, manifesto, configuração, ambiente e validador foram atualizados | **Atendido na revisão.** PDF e slides originais permanecem como histórico da entrega avaliada |
| **7. Apresentação da primeira etapa** | Problema, dados, EDA, tratamento, features e descobertas foram apresentados | Os materiais originais foram preservados | **Entregue na AV1.** Uma síntese corrigida deve alimentar a apresentação final da AV2 |

### Síntese do atendimento

A entrega original cumpriu a estrutura geral da AV1 e recebeu 8/10. A revisão fortaleceu principalmente organização, recuperação dos registros anuais, engenharia de atributos, EDA das novas variáveis, demonstração de normalização/padronização e prevenção de vazamento temporal.

A AV1 revisada está técnica e metodologicamente preparada para servir de base à AV2. Alvo, agravo, IDs, cobertura, clima, coorte e portabilidade foram tratados com decisões explícitas e análises de sensibilidade. As limitações não desapareceram, mas agora estão quantificadas e devem acompanhar o protocolo e a análise crítica da AV2.

## 6. O que mudou na revisão

| Área | Melhoria implementada |
|---|---|
| Organização | Seções com objetivo, código, saída e interpretação; tabelas de qualidade e dicionário completo |
| Aquisição | Aliases controlados, validação do agravo A90 e bloqueio de esquema ou doença inesperada |
| Limpeza | Duplicatas exatas removidas globalmente; ano real auditado; IDs divergentes preservados e comparados com cenário conservador |
| Calendário | Notificações e clima alinhados à mesma semana civil local, de segunda a domingo |
| Cobertura | Zero auditado por ano; ausência climática não vira chuva zero; limiares de 80%, 90% e 95% comparados |
| Feature engineering | Histórico auxiliar de 1–4 semanas; clima defasado de 1–8; chuva acumulada e médias de temperatura/umidade em 2/4/8 semanas; sazonalidade, território e população alinhada ao ano |
| População e incidência | Substituição do Censo 2022 fixo por série bairro-ano, com Censo, estimativas e projeções explicitamente diferenciados |
| Pré-processamento | One-hot encoding e alternativas Min-Max, StandardScaler e sem escala, ajustados apenas no treino |
| Validação temporal | Coortes com e sem clima explicitadas, perdas por etapa, divisão por semana-alvo e teste reservado |
| Rastreabilidade | Relatórios, dataset, configuração e manifesto UTF-8, versões fixadas e validador automático |

## 7. Estado auditado do notebook revisado

O arquivo local foi inspecionado e reexecutado de ponta a ponta em 17/11/2026 com as fontes oficiais:

- 56 células totais;
- 27 células de código;
- 27 células de código com contagem de execução salva;
- nenhuma saída de erro registrada;
- saídas e conclusão de execução preservadas no notebook.

### Resultados registrados nessa execução

| Indicador | Resultado |
|---|---:|
| Linhas adquiridas das fontes anuais | 71.663 |
| Registros após a limpeza | 71.175 |
| Duplicatas exatas globais removidas | 4 |
| IDs-ano com registros analiticamente divergentes preservados | 787 |
| Diferença no cenário conservador de um registro por ID-ano | 791 (aprox. 1,1%) |
| Registros publicados fora do ano nominal auditados pela data real | 219 |
| Bairros | 94 |
| Linhas no painel bairro-semana | 49.162 |
| Colunas exportadas | 72 |
| Linhas com alvo e histórico completos, sem exigir clima | 48.504 |
| Linhas da coorte comum com histórico e clima completos | 20.304 |
| Retenção da coorte comum | 41,30% |
| Período da semana-alvo na coorte comum | 25/04/2016 a 08/11/2021 |
| Período da EDA anterior à validação | 04/01/2016 a 09/03/2020 |
| Corte inicial de validação por semana-alvo | 23/03/2020 |
| Corte inicial de teste por semana-alvo | 02/11/2020 |

A análise semanal simples preservou o resultado anterior: o maior Pearson entre clima da semana e casos notificados futuros foi chuva com duas semanas de antecedência (`0,155`). Spearman revelou relação monotônica mais clara, chegando a `0,416` para chuva quatro semanas antes.

A chuva acumulada em oito semanas apresentou Pearson `0,618` e Spearman `0,631` com o total municipal da semana seguinte. O valor não é apresentado isoladamente como prova: depois de retirar a média de cada mês, a associação da chuva de oito semanas caiu para Pearson `0,218`, e o padrão anual foi instável — forte em 2016, 2018 e 2019, mas ausente em 2017 e pouco informativo no trecho de 2020. A janela é candidata promissora para validação, não resultado preditivo.

No treino da coorte comum, 60,74% dos alvos são zero, a mediana é 0, a média é 1,05 e o máximo é 71 casos notificados. Essa distribuição justifica baselines fortes, modelos de contagem e análise específica de picos.

**Importante:** a reexecução de 17/11/2026 terminou com as 27 células de código executadas e nenhuma saída de erro. O validador confirmou 49.162 linhas, 72 colunas, 20.304 observações elegíveis, população anual completa nas semanas cobertas, JSONs UTF-8, relatórios climáticos e carregamento dos três preprocessadores.

## 8. Decisões fixadas e limitações levadas à AV2

1. O alvo principal usa todas as notificações A90; classificação final é sensibilidade separada.
2. IDs divergentes são preservados no cenário principal e comparados com um cenário conservador agregado.
3. Zero significa ausência de registro sob a hipótese de cobertura, nunca ausência comprovada de infecção.
4. O cenário principal usa 90% de cobertura climática; 80% e 95% foram auditados e não alteram a limitação temporal da estação.
5. A estação A301 não representa microclimas e sua série útil limita a coorte comum a 2016–2021. Os arquivos de 2022 e 2023 possuem linhas horárias, mas as três medidas usadas estão vazias.
6. A coorte sem clima alcança 2025; a comparação justa entre modelos com e sem clima usa somente as mesmas 20.304 linhas da coorte comum.
7. Atrasos de 1–8 semanas e janelas de 2/4/8 foram fixados antes da nova execução; todos os resultados foram exportados para evitar escolha seletiva.
8. Correlação bruta, anomalia mensal e estabilidade anual são relatadas juntas; nenhuma substitui a validação temporal da AV2.
9. Limiares históricos de prioridade foram preparados por bairro apenas no treino e não constituem alertas oficiais.
10. O protótipo de 2025 permanece ilustrativo até receber previsões validadas da AV2.
11. População e densidade usam o ano da observação. Somente 2022 é Censo observado dentro da série analítica; estimativas e projeções permanecem identificadas e devem entrar na análise de sensibilidade da AV2.

## 9. Passagem preparada para a AV2

Ao fim da semana `t`, o primeiro experimento usará apenas informações disponíveis até esse momento para estimar `NOTIFICACOES_PROXIMA_SEMANA` no mesmo bairro.

### Conjuntos de atributos

1. **Controle sem clima:** histórico auxiliar + calendário + território.
2. **Hipótese principal com clima:** o mesmo conjunto acrescido de chuva, temperatura e umidade atuais, defasadas e acumuladas.

As duas versões devem usar as mesmas observações e os mesmos períodos para que a comparação seja justa.

### Modelos candidatos

- baseline de persistência;
- regressão de Poisson;
- árvore de decisão;
- Random Forest.

Nenhum modelo vencedor foi escolhido. A seleção será feita com validação temporal, usando **MAE** como métrica principal e **RMSE** como complemento. O teste final permanecerá reservado até a configuração estar fixada. Também serão examinados picos, semanas com notificações, erros por bairro, agregado municipal, estabilidade temporal e custo.

## 10. Reprodução

1. Abra o notebook revisado localmente ou pelo Colab.
2. Execute as células em ordem com acesso às fontes oficiais.
3. Confira os relatórios de aquisição, perdas, integração territorial, cobertura climática e divisão temporal.
4. Preserve juntos o dataset, o manifesto, a configuração e os relatórios da mesma execução.
5. Refaça os preprocessadores dentro de cada divisão temporal da AV2; não reutilize um ajuste que tenha visto períodos futuros.
6. Instale as versões registradas em [`requirements.txt`](requirements.txt) quando precisar reproduzir o ambiente local.
7. Valide a saída com `python scripts/validar_artefatos.py <diretorio-da-execucao>`.

### Artefatos preservados da execução de 17/11/2026

- [`dataset_av1_revisado.csv`](artefatos/execucao_2026-11-17/dataset_av1_revisado.csv);
- [`manifesto_execucao.json`](artefatos/execucao_2026-11-17/manifesto_execucao.json);
- [`config_av2.json`](artefatos/execucao_2026-11-17/config_av2.json);
- [`relatorios/`](artefatos/execucao_2026-11-17/relatorios): aquisição, qualidade, cobertura, integração, população bairro-ano, reconciliação populacional, atrasos climáticos, janelas acumuladas, controle de sazonalidade, estabilidade anual, limiares de atenção, escalas e coorte;
- preprocessadores normalizado, padronizado e sem escala, mantidos como evidência da AV1.

Os grandes caches de download não foram copiados para esta pasta. O manifesto conserva URLs, hashes e tamanhos das fontes usadas na execução.
