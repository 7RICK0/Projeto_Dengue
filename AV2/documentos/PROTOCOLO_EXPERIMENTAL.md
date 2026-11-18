# Protocolo experimental da AV2 — versão aprovada

> Estado: **aprovado e congelado antes da modelagem**. Alterações metodológicas relevantes deverão ser justificadas e confirmadas antes de consultar o teste final.

## Decisões já sustentadas pelo problema e pelos requisitos

- unidade de análise: bairro por semana;
- saída principal: **previsão mensal — próximas 4 semanas**, somando `t+1` a `t+4`;
- saída complementar: previsão da próxima semana (`t+1`);
- visão principal na aplicação e na apresentação: mês de calendário, com detalhamento semanal. A convenção para semanas que atravessam meses e o momento de emissão da projeção mensal serão definidos antes dessa consolidação;
- tarefa principal: regressão de contagem;
- comparação científica central: mesmas linhas e mesmo protocolo, com e sem clima;
- ordem temporal preservada, sem embaralhamento aleatório;
- pré-processamento ajustado somente no treino de cada experimento;
- teste final reservado até a seleção pela validação;
- resultados analisados no geral, por bairro, por período, em semanas positivas, em picos e no agregado municipal.

## Protocolo aprovado

### 1. Coortes de análise

- **Comparação climática principal:** 20.304 linhas de 94 bairros com histórico e clima completos entre 2016 e 2021. É a comparação direta e justa entre versões com e sem clima.
- **Análise epidemiológica complementar:** até 48.504 linhas com alvo e histórico completos entre 2016 e 2025, sem exigir clima. Ela preserva os anos recentes, mas não será usada para atribuir ganho às variáveis climáticas.

### 2. Fronteiras temporais

A configuração herdada informa validação em `2020-03-23` e teste em `2020-11-02`, mas o dataset marca exatamente essas duas semanas como `fora`. São 188 linhas elegíveis, 94 por semana.

Decisão: não descartar essas semanas. Usar no horizonte semanal:

- treino: semana-alvo até 16/03/2020;
- validação: semana-alvo de 23/03/2020 até 26/10/2020;
- teste: semana-alvo de 02/11/2020 até 08/11/2021.

No horizonte de quatro semanas, a soma usa as datas exatas de `t+1` a `t+4`. Só são elegíveis as janelas com quatro contagens observadas e inteiramente contidas no mesmo conjunto. Os atributos climáticos são exigidos na semana de referência e em suas defasagens, já que são entradas disponíveis no momento da previsão. A última semana-alvo disponível na janela de quatro semanas da coorte comum é 16/08/2021. As três últimas semanas de início elegíveis para o horizonte semanal cruzam o fim do período reservado quando avaliadas no horizonte de quatro semanas.

Incluir as datas de corte pressupõe emissão após o fechamento da semana de referência e disponibilidade das contagens correspondentes nesse momento. A base histórica foi consolidada. Atrasos de publicação ou revisão devem ser tratados como limitação da simulação retrospectiva e avaliados antes do uso operacional.

### 3. Cenários de atributos

1. **Controle epidemiológico:** histórico de notificações, calendário e território, sem clima.
2. **Modelo integrado:** as mesmas entradas acrescidas de chuva, temperatura e umidade.

Os dois cenários usarão as mesmas linhas na comparação climática. O cenário aplicado no produto será escolhido pelos resultados, e não pela expectativa inicial de que o clima necessariamente melhore a previsão.

População e densidade ficam fora da comparação principal por cobertura histórica insuficiente. A regra é usar estimativas do ano da previsão somente quando a edição correspondente já estava disponível. Entre as edições localizadas, a [edição até 2017](https://cievsrecife.files.wordpress.com/2017/11/populac3a7c3a3o-2010-a-2017-uvepi1.pdf) traz data editorial de dezembro de 2017, a [edição até 2020](https://cievsrecife.wordpress.com/wp-content/uploads/2020/11/populacao-2010-a-2020.pdf) de novembro de 2020 e a [edição até 2021](https://cievsrecife.wordpress.com/wp-content/uploads/2021/10/populacao-2010-a-2021.pdf) de setembro de 2021. Mesmo usando o primeiro dia do mês editorial como limite otimista, as edições identificadas cobrem no máximo 1.504 de 20.304 linhas da coorte semanal (7,4%), com zero das 3.008 linhas de validação. O [IBGE](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao) oferece totais anuais por município.

A população reconstruída na AV1 para 2018–2021 usa o Censo de 2022 e continua disponível para sensibilidade retrospectiva. Os dois cenários principais mantêm bairro e RPA como atributos territoriais e excluem também incidência, que depende da população.

### 4. Referências e modelos candidatos

- baseline de persistência: repetir a contagem atual;
- baseline de média móvel: média das quatro semanas anteriores;
- regressão de Poisson;
- Random Forest;
- Gradient Boosting Regressor.

São três modelos de aprendizado de máquina e duas referências simples. A professora exige múltiplos modelos candidatos, mas não determina quantidade mínima. Três candidatos oferecem diversidade suficiente sem aumentar experimentos sem justificativa. Nenhum algoritmo será tratado previamente como vencedor.

Para a janela de quatro semanas, os dois baselines repetem por quatro semanas o nível semanal de sua respectiva regra.

A primeira rodada usa Poisson regularizada, Random Forest com profundidade e tamanho de folha limitados, e Gradient Boosting de histogramas com perda Poisson. O código registra a semente das árvores. Categorias são codificadas no treino e as entradas numéricas são padronizadas apenas para Poisson.

### 5. Métricas e regra de seleção

- métrica principal: MAE, na unidade de notificações por bairro no horizonte avaliado;
- métricas complementares: RMSE e erro absoluto agregado municipal;
- diagnósticos: MAE em semanas positivas, erro nos maiores picos, distribuição por bairro e estabilidade por período;
- seleção: desempenho na validação, estabilidade, capacidade de lidar com picos, simplicidade e custo;
- teste: uma avaliação final após congelar a configuração.

### 6. Experimentos de sensibilidade

- com e sem clima, na coorte comum;
- com e sem população/densidade, pois parte da série é estimada ou projetada;
- todas as notificações A90 versus classificação encerrada, apenas como sensibilidade agregada se a base disponível permitir sem vazamento;
- os dois horizontes aprovados têm alvo e validação próprios. Horizontes adicionais exigem nova avaliação.

## Seleção aprovada antes do teste

| Horizonte | Referência escolhida por MAE na validação | Candidato para comparação climática |
|---|---|---|
| Próxima semana | Persistência | Gradient Boosting com e sem clima |
| Próximas quatro semanas | Média das quatro semanas anteriores | Gradient Boosting com e sem clima |

O Gradient Boosting tem os mesmos parâmetros, atributos e semente da validação. O ajuste final usa a união de treino e validação de cada horizonte. A primeira emissão no teste só usa alvos de desenvolvimento fechados até a semana de referência. Nas emissões seguintes, os históricos se atualizam conforme os dados observados até cada origem e o estimador permanece fixo. O limiar diagnóstico de pico continua sendo o percentil 90 dos alvos positivos do treino original.

A avaliação final usa o MAE como métrica principal. O efeito do clima será medido entre as duas versões do Gradient Boosting no mesmo conjunto, e a utilidade prática será comparada à referência simples já escolhida. O teste fornece evidência de generalização para as configurações aprovadas.

