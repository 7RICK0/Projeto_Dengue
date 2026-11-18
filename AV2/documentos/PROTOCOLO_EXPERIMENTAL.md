# Protocolo usado na AV2

As regras foram definidas antes da modelagem e a configuração final foi escolhida na validação, antes de consultar o teste reservado.

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

## Desenho da avaliação

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

| Modelo ou referência | Por que entrou na comparação |
|---|---|
| **Persistência** | Repetir a contagem recente dá uma referência simples para a próxima semana. |
| **Média móvel** | Usar a média das quatro semanas anteriores reduz a influência de uma semana atípica e dá uma referência de curto prazo. |
| **Regressão de Poisson** | É um modelo simples e interpretável para contagens. Serve para comparar com modelos que aprendem relações mais complexas. |
| **Random Forest** | Combina várias árvores de decisão. Permite investigar relações não lineares e interações entre variáveis, como chuva e temperatura. |
| **Gradient Boosting** | Ajusta árvores em sequência para reduzir os erros anteriores. Foi testado com perda de Poisson, adequada a uma contagem não negativa. |

As referências simples ajudam a medir se o aprendizado de máquina acrescenta valor. Os três candidatos representam formas diferentes de aprender com a mesma base.

Para a janela de quatro semanas, os dois baselines repetem por quatro semanas o nível semanal de sua respectiva regra.

A primeira rodada usa Poisson regularizada, Random Forest com profundidade e tamanho de folha limitados, e Gradient Boosting de histogramas com perda Poisson. O código registra a semente das árvores. Categorias são codificadas no treino e as entradas numéricas são padronizadas apenas para Poisson.

### 5. Métricas e regra de seleção

- **MAE (erro absoluto médio).** Foi a métrica principal porque mostra a distância média entre a previsão e o valor observado na unidade do projeto: notificações por bairro. A seleção usou o MAE de validação de cada horizonte.
- **RMSE (raiz do erro quadrático médio).** Dá mais peso a erros grandes e ajuda a identificar modelos que erram muito em algumas previsões.
- **Erro absoluto no total municipal.** Compara a soma prevista para o Recife com a soma observada. Ajuda a avaliar o planejamento para a cidade inteira, enquanto o MAE por bairro mede a precisão territorial.
- **Erros em períodos com notificações e nos picos.** Mostram como o modelo se sai quando há registros e quando a demanda pode ser maior. A análise por bairro e por período verifica se o desempenho varia no território e ao longo do tempo.

O teste final foi realizado após fixar a configuração escolhida na validação.

### 6. Experimentos de sensibilidade

- com e sem clima, na coorte comum;
- com e sem população/densidade, pois parte da série é estimada ou projetada;
- todas as notificações A90 versus classificação encerrada, apenas como sensibilidade agregada se a base disponível permitir sem vazamento;
- os dois horizontes estudados têm alvo e validação próprios. Horizontes adicionais exigem nova avaliação.

## Seleção feita na validação

| Horizonte | Referência escolhida por MAE na validação | Candidato para comparação climática |
|---|---|---|
| Próxima semana | Persistência | Gradient Boosting com e sem clima |
| Próximas quatro semanas | Média das quatro semanas anteriores | Gradient Boosting com e sem clima |

O Gradient Boosting tem os mesmos parâmetros, atributos e semente da validação. O ajuste final usa a união de treino e validação de cada horizonte. A primeira emissão no teste só usa alvos de desenvolvimento fechados até a semana de referência. Nas emissões seguintes, os históricos se atualizam conforme os dados observados até cada origem e o estimador permanece fixo. O limiar diagnóstico de pico continua sendo o percentil 90 dos alvos positivos do treino original.

A avaliação final usa o MAE como métrica principal. O efeito do clima será medido entre as duas versões do Gradient Boosting no mesmo conjunto, e a utilidade prática será comparada à referência simples já escolhida. O teste fornece evidência de generalização para as configurações avaliadas.

### Resultado da escolha

O **Gradient Boosting** teve o menor MAE entre os candidatos de aprendizado de máquina na validação, com e sem clima, nos dois horizontes. As referências simples também foram levadas ao teste, porque eram competitivas na validação.

No teste de **quatro semanas**, horizonte principal, o **Gradient Boosting com clima** obteve o menor MAE entre as opções avaliadas: **2,882 notificações por bairro**, contra **2,978** do mesmo modelo sem clima e **3,835** da média móvel. Na **próxima semana**, o Gradient Boosting com clima também teve o menor MAE por bairro (**1,016**), com uma diferença pequena em relação à versão sem clima.
