# AnteceDengue — Entrega 2 (AV2)

A AV2 avalia se chuva, temperatura e umidade ajudam a antecipar a quantidade de notificações de dengue A90 por bairro do Recife. A [AV1 revisada](../AV1/README.md) preparou 49.162 observações semanais de 94 bairros. A comparação com e sem clima usa as 20.304 observações com cobertura climática completa entre 2016 e 2021.

## Materiais

- [Notebook executado](notebooks/AnteceDengue_AV2_modelagem.ipynb) · [Abrir no Colab](https://colab.research.google.com/github/7RICK0/Projeto_Dengue/blob/main/AV2/notebooks/AnteceDengue_AV2_modelagem.ipynb)
- [Relatório técnico (PDF)](documentos/Relatorio_AnteceDengue_AV2.pdf) · [Documentação completa da AV1 e AV2 (PDF)](documentos/Documentacao_AnteceDengue_AV1_AV2.pdf)
- [Protocolo experimental](documentos/PROTOCOLO_EXPERIMENTAL.md) · [Planejamento e perguntas do projeto](documentos/PLANEJAMENTO_E_PERGUNTAS_AV2.md)
- [Painel web](painel/abrir_painel.html) · [Inventário dos resultados](artefatos/README.md)

## Método

Comparamos regressão de Poisson, Random Forest e Gradient Boosting com duas referências simples, persistência e média móvel. Nas versões com e sem clima, conservamos as mesmas observações, datas e configurações. Ambas usam histórico de notificações, calendário e bairro. A versão com clima acrescenta chuva, temperatura e umidade com defasagens e janelas acumuladas.

Separamos treino, validação e teste em ordem cronológica. Usamos a validação para escolher o modelo pelo MAE e reservamos o período de 02/11/2020 a 08/11/2021 para a avaliação final. A análise por mês de calendário tem avaliação própria, separada do horizonte móvel de quatro semanas; a série anual usa apenas o histórico de notificações.

## Resultados

| Horizonte | Régua simples | GB sem clima | GB com clima | Ganho do clima |
|---|---:|---:|---:|---:|
| Próxima semana | 1,132 (persistência) | 1,024 | 1,016 | 0,8% |
| **Próximas 4 semanas** | 3,835 (média móvel) | 2,978 | **2,882** | **3,2%** |

Os valores são MAE, em notificações por bairro. Em 4 semanas, o R² foi 0,698 com clima, 0,681 sem clima e 0,360 na média móvel.

Para quatro semanas, o modelo com clima reduziu o MAE em **24,9%** frente à média móvel. O ganho isolado de **3,2%** ficou inconclusivo: o intervalo de 95% do bootstrap vai de −3,0% a +7,6%. O modelo tende a subestimar picos. No Ibura, em um dos exemplos, previu cerca de 49 notificações e foram registradas 141. A cobertura de uma única estação e de um único período de teste reduz o alcance das conclusões. O painel serve como apoio à priorização de ações preventivas. [Gráfico do ganho com clima](artefatos/figuras/bootstrap_ganho_clima.png)

### Mês e ano de calendário

- **Mês civil** (7 meses × 94 bairros): MAE por bairro de 5,47 na média móvel, 3,93 sem clima e 4,00 com clima. Com clima, o erro do total da cidade caiu de 220,16 para 207,19. Em abril de 2021, o Recife subiu de 258 para 496 notificações, e o modelo previu 332. [Gráfico](artefatos/figuras/notificacoes_por_mes.png)
- **Ano** (regra sem clima: mediana dos 3 anos anteriores): previu 3.683 notificações para 2024 (foram 10.548) e 3.701 para 2025 (foram 9.150). A estimativa para 2026 é de 8.228. Serve só como ordem de grandeza. [Gráfico](artefatos/figuras/notificacoes_por_ano.png)

## Requisitos e execução

O notebook organiza a entrega em **Modelagem → Experimentos → Avaliação → Modelo final → Conclusões**. Ele mostra a comparação entre candidatos, a justificativa da escolha, a importância das variáveis e exemplos de erro. O relatório discute qualidade dos dados, pontos fortes, limitações e próximos passos.

- **Painel no PC.** Abra [`painel/abrir_painel.html`](painel/abrir_painel.html) no navegador. O painel funciona offline.
- **Painel no Colab.** Use **Ambiente de execução → Executar tudo**. O painel aparece na saída da primeira célula de código.
- **Verificações locais registradas.** Os 11 testes de integridade passaram e o notebook reproduziu as saídas em execução local do zero. O teste do Colab após o envio ao GitHub continua pendente.

Para reproduzir no PC, execute na raiz do repositório com Python 3.11 ou superior.

```powershell
python -m pip install -r AV1/requirements.txt
python -B -m unittest discover -s AV2/tests -t .
python -B AV2/tests/rodar_notebook_do_zero.py
```

Os resultados reservados estão em `artefatos/teste_final.zip` e `artefatos/mes_calendario.zip`. A reprodução do notebook lê esses arquivos e preserva a avaliação congelada.
