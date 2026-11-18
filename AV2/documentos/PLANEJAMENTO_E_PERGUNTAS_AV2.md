# AV2 - Planejamento e perguntas que o AnteceDengue precisa responder

## 1. Origem e compromisso do projeto

O AnteceDengue nasceu do desafio público **"Limitações na Antecipação de Surtos de Dengue na Cidade do Recife"**, divulgado no [Banco de Oportunidades do Recife](https://bancodeoportunidades.recife.pe.gov.br/) e apresentado na [página original do desafio](https://shiny-raindrop-cee689.netlify.app/).

O Banco de Oportunidades não apresentou um questionário formal nem, na página consultada, disponibilizou diretamente um conjunto de dados. Ele descreveu um problema público: dados epidemiológicos, ambientais e operacionais não são suficientemente integrados para antecipar a disseminação das arboviroses, fazendo com que muitas ações ocorram quando os casos já estão crescendo.

Por isso, a AV2 precisa transformar o desafio público em perguntas verificáveis, experimentos reproduzíveis e uma saída útil para prevenção.

## 2. Pergunta central

> É possível antecipar onde e quando os casos notificados de dengue aumentarão em Recife, integrando dados epidemiológicos, climáticos e territoriais?

Neste projeto, "casos notificados" corresponde aos registros de vigilância disponíveis na base. O termo não deve ser confundido com notificações de aplicativo, casos necessariamente confirmados ou número garantido de pessoas únicas.

## 3. Perguntas que a AV2 precisa responder

1. **Quando?** Com quantas semanas de antecedência é possível estimar o aumento dos casos notificados?
2. **Onde?** Quais bairros apresentam maior quantidade prevista ou maior risco de aumento?
3. **Quanto?** Quantos casos notificados são esperados por bairro no horizonte avaliado?
4. **O clima ajuda?** Chuva, temperatura e umidade melhoram o desempenho em comparação com modelos que usam apenas o histórico epidemiológico e as demais informações disponíveis?
5. **Quais atrasos climáticos importam?** Quais defasagens e janelas acumuladas - por exemplo, duas, quatro ou oito semanas - acrescentam informação útil?
6. **O resultado se sustenta no futuro?** O desempenho permanece aceitável em períodos posteriores que não participaram do treinamento nem da escolha do modelo?
7. **A saída é territorialmente útil?** O resultado permite priorizar bairros, períodos e ações preventivas antes do crescimento observado dos registros?
8. **Quais são as limitações?** Como subnotificação, atraso de registro, cobertura climática incompleta, mudanças no padrão temporal, desigualdades territoriais e capacidade operacional afetam o uso do resultado?

## 4. Como cada pergunta será respondida

| Pergunta | Evidência mínima esperada na AV2 |
|---|---|
| Quando? | Definir e avaliar separadamente cada horizonte de previsão; começar por uma semana à frente e não generalizar esse resultado para meses ou anos. |
| Onde? | Produzir resultados por bairro e examinar erros e cobertura territorial, além do agregado municipal. |
| Quanto? | Tratar a contagem futura de casos notificados como alvo e apresentar previsões com unidade e período explícitos. |
| O clima ajuda? | Comparar os mesmos algoritmos, linhas, cortes temporais e métricas em versões com e sem variáveis climáticas. |
| Quais atrasos importam? | Avaliar defasagens e janelas definidas antes do teste final, justificadas pela literatura e pela disponibilidade temporal. |
| Funciona no futuro? | Separar treino, validação e teste em ordem temporal; manter o teste final reservado até a escolha da configuração. |
| É útil para prevenção? | Traduzir o resultado validado em mapa e consulta por bairro, sem apresentar classificação exploratória como alerta epidemiológico oficial. |
| Quais limitações? | Relatar qualidade e cobertura dos dados, erros por período e bairro, falhas nos picos, incertezas e riscos de uso. |

### Controle populacional

População, densidade e incidência devem usar o valor correspondente ao bairro e ao ano da observação. O dataset identifica separadamente Censo observado, estimativa institucional, estimativa intercensitária e projeção pós-Censo. A AV2 deve registrar essa incerteza e comparar o desempenho com e sem os atributos populacionais, sem tratar valores estimados como medições exatas.

## 5. Critério científico central

A hipótese principal é que chuva, temperatura e umidade, consideradas com atrasos e acumulações biologicamente plausíveis, possam acrescentar capacidade preditiva. A AV1 encontrou sinais exploratórios, especialmente para chuva acumulada, mas associação não comprova causalidade nem ganho de previsão.

A conclusão sobre a utilidade do clima será dada somente pela comparação temporal da AV2:

- referência ingênua e modelos sem clima;
- os mesmos modelos com clima;
- seleção pela validação;
- avaliação única e final no teste reservado;
- análise de desempenho geral, picos, bairros, semanas com casos e estabilidade temporal.

Se o clima não melhorar o desempenho fora da amostra, essa ausência de ganho deverá ser relatada como resultado científico, e não escondida.

## 6. Termos estatísticos que devem permanecer com o nome padrão

- **Correlação de Pearson:** mede principalmente a intensidade e a direção de uma relação linear entre os valores originais. É mais sensível a valores extremos.
- **Correlação de Spearman:** mede a intensidade e a direção de uma relação monotônica a partir da ordem ou posição dos valores. Pode captar relações que aumentam ou diminuem de forma consistente mesmo sem formar uma linha reta e tende a ser menos sensível a valores extremos.

Os sobrenomes **Pearson** e **Spearman** são os nomes científicos padronizados dos coeficientes, usados em livros, artigos e programas estatísticos. Na apresentação, podem aparecer acompanhados de linguagem simples - por exemplo, "relação linear (Pearson)" e "relação por ordenação (Spearman)" -, mas não devem ser substituídos por nomes inventados.

Nenhum dos dois coeficientes, isoladamente, demonstra causalidade ou garante que uma variável melhorará as previsões.

## 7. Entregáveis que devem materializar as respostas

- notebook ou código reproduzível de modelagem e avaliação;
- experimentos comparativos com múltiplos modelos e uma referência simples;
- tabela com versões com e sem clima nas mesmas condições;
- justificativa do modelo selecionado e análise dos erros;
- relatório final com respostas explícitas às oito perguntas;
- apresentação final coerente com os resultados reproduzíveis;
- mapa e consulta por bairro alimentados somente por previsões validadas, mantendo como ilustrativo tudo o que ainda não vier do modelo.

**Importante — última ação da AV2: pedir o check final da professora.** Fazer o pedido com os materiais já prontos, depois da conferência interna da entrega.
