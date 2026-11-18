# Artefatos da AV1: a base de dados que a AV2 usa

Saídas do notebook revisado da AV1 (`AV1/notebooks/AnteceDengue_AV1_revisada.ipynb`), executado com as fontes oficiais em 17/11/2026.

## Usados pela AV2 (não apagar)

| Arquivo | O que é |
|---|---|
| `dataset_av1_revisado.csv` | **A base do projeto:** 49.162 linhas (94 bairros × 523 semanas), com notificações, clima, território e atributos |
| `config_av2.json` | Alvo, cortes de treino, validação e teste e listas de atributos herdados pela AV2 |
| `manifesto_execucao.json` | Endereços, tamanhos e hashes das fontes oficiais usadas |
| `relatorios/aquisicao_por_ano.csv` | Arquivos anuais de notificações, usados pela AV2 para reconstruir os totais por mês |

## Evidências da AV1

| Arquivo | O que é |
|---|---|
| `relatorios/` (demais CSVs) | Tabelas da análise exploratória, da qualidade dos dados, da cobertura, das correlações e das sensibilidades, as mesmas mostradas no notebook |
| `preprocessador_*.joblib` | Demonstração de codificação e escala (normalizado, padronizado e sem escala), ajustados só no treino |

Para conferir que a base está íntegra: `python -B AV1/scripts/validar_artefatos.py AV1/artefatos` (resultado esperado: `VALIDACAO_OK`).
