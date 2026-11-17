# AnteceDengue — Aplicação web de apoio à antecipação territorial da dengue

Projeto de Machine Learning que integra histórico epidemiológico, clima e território para estimar **onde**, **quando** e **quanto** os casos notificados de dengue podem aumentar nos bairros do Recife. O objetivo é apoiar ações preventivas antes do crescimento observado dos registros.

> **Pergunta central:** é possível antecipar a quantidade de casos notificados de dengue por bairro usando somente informações disponíveis até o momento da previsão?

## Acessos rápidos

| Origem do projeto | Arquivos | Notebooks | Entregas |
|---|---|---|---|
| [Desafio no Banco de Oportunidades](https://shiny-raindrop-cee689.netlify.app/) | [Google Drive](https://drive.google.com/drive/folders/1oQXWFYeC_-33eYTr_Q75-bXMiFFtg3yE?usp=sharing) | [AV1 no Colab](https://colab.research.google.com/drive/1MpXxyiLApFqNRDW0AjeOK8G3z2Y053i6) | [Relatório técnico da AV1](AV1/README.md) |
|  |  | [AV1 revisada](AV1/notebooks/AnteceDengue_AV1_revisada.ipynb) · [AV1 original](AV1/notebooks/Projeto_AV1_Dengue_Recife_original.ipynb) | [Planejamento da AV2](AV2/docs/PLANEJAMENTO_E_PERGUNTAS_AV2.md) |

> A AV1 revisada deste repositório é a referência técnica atual. A cópia do Colab precisa ser sincronizada separadamente após alterações autorizadas.

## Origem do problema

O AnteceDengue nasceu do desafio público **“Limitações na Antecipação de Surtos de Dengue na Cidade do Recife”**, publicado em 23/01/2026. O problema é a dificuldade de integrar dados epidemiológicos, ambientais e territoriais para antecipar áreas e períodos de maior risco, fazendo com que ações de controle possam começar somente quando os registros já estão crescendo.

## Evolução das entregas

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>✅ Entrega 1 — concluída</h3>
      <p><strong>Fundamentos, dados, análise exploratória e preparação.</strong></p>
      <ul>
        <li>Coleta e auditoria dos registros oficiais de dengue.</li>
        <li>Limpeza de datas, bairros, IDs, classificações e duplicidades.</li>
        <li>Integração com bairros, população, área e clima do INMET.</li>
        <li>Agregação na unidade <strong>bairro-semana</strong>.</li>
        <li>Criação de histórico de casos, sazonalidade e atributos climáticos.</li>
        <li>Chuva, temperatura e umidade com atrasos de 1 a 8 semanas.</li>
        <li>Janelas climáticas acumuladas de 2, 4 e 8 semanas.</li>
        <li>Separação temporal entre treino, validação e teste.</li>
        <li>Notebook executado, artefatos gerados e validação reproduzível.</li>
      </ul>
      <p><a href="AV1/README.md"><strong>Ver documentação completa da Entrega 1 →</strong></a></p>
    </td>
    <td width="50%" valign="top">
      <h3>🚧 Pós-AV1 e início da Entrega 2</h3>
      <p><strong>Revisão metodológica, modelagem e avaliação.</strong></p>
      <ul>
        <li>Base revisada e alinhada ao desafio público.</li>
        <li>Foco confirmado em clima, casos notificados e território.</li>
        <li>Sinais exploratórios de chuva acumulada identificados.</li>
        <li>Alvo inicial: casos notificados por bairro na semana seguinte.</li>
        <li>Random Forest Regressor como principal candidato.</li>
        <li>Comparação planejada com referência simples e outros modelos.</li>
        <li>Experimento central definido: modelos com e sem clima.</li>
        <li>Seleção por validação temporal; teste final permanece reservado.</li>
        <li>Protótipo permanece ilustrativo até receber previsões validadas.</li>
      </ul>
      <p><a href="AV2/docs/PLANEJAMENTO_E_PERGUNTAS_AV2.md"><strong>Ver planejamento completo da Entrega 2 →</strong></a></p>
    </td>
  </tr>
</table>

## Entrega 1 em números

| Registros brutos | Registros válidos | Painel bairro-semana | Bairros | Atributos | Coorte com clima completo |
|---:|---:|---:|---:|---:|---:|
| 71.663 | 71.175 | 49.162 linhas | 94 | 69 colunas | 20.304 linhas |

### Resultado essencial da análise exploratória

A chuva acumulada em oito semanas apresentou Pearson `0,618` e Spearman `0,631` com o total municipal da semana seguinte. Depois da retirada das médias mensais, o Pearson caiu para `0,218`, e a associação variou entre os anos. Portanto, o resultado da AV1 é **promissor, mas exploratório**: justifica testar o clima na AV2, sem provar causalidade ou ganho preditivo.

O notebook revisado possui 56 células, com 27 células de código executadas sem erro. A validação dos artefatos retornou:

```text
VALIDACAO_OK linhas=49162 colunas=69 coorte=20304
```

## Protótipo e acompanhamento

Clique nas imagens para abrir os ambientes do projeto.

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <a href="https://check-detach-31150593.figma.site">
        <img src="prototype/gestao-preview.png" alt="Prévia do protótipo AnteceDengue" width="100%">
      </a>
      <br>
      <strong>Aplicação web — protótipo publicado</strong><br>
      <small>Mapa e consulta territorial com dados ilustrativos.</small>
    </td>
    <td width="50%" align="center" valign="top">
      <a href="https://trello.com/b/SBeFEpG9/antecedengue-av1-e-av2">
        <img src="prototype/trello-preview.png" alt="Prévia do quadro AnteceDengue no Trello" width="100%">
      </a>
      <br>
      <strong>Planejamento no Trello</strong><br>
      <small>Backlog, andamento e validação das entregas.</small>
    </td>
  </tr>
</table>

## Próxima etapa

A AV2 começará com uma referência simples e múltiplos modelos de regressão, mantendo os períodos em ordem temporal. O objetivo científico será verificar se chuva, temperatura e umidade melhoram de forma consistente a previsão futura quando comparadas ao histórico epidemiológico. Perguntas, protocolo e entregáveis estão concentrados no [documento de planejamento da AV2](AV2/docs/PLANEJAMENTO_E_PERGUNTAS_AV2.md).

## Limites de interpretação

- Casos notificados não equivalem necessariamente a casos confirmados ou pessoas únicas.
- Correlações exploratórias não comprovam causalidade nem capacidade preditiva.
- O protótipo ainda não está integrado a um modelo treinado.
- A ferramenta será apoio à decisão e não alerta epidemiológico oficial.
- Horizontes maiores que uma semana exigem avaliações próprias.
