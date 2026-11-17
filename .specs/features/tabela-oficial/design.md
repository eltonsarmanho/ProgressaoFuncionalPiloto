# Tabela Oficial Design

**Spec**: `.specs/features/tabela-oficial/spec.md`
**Status**: Approved (mudança de dados e de regras sobre componentes já existentes; sem arquitetura nova)

---

## Architecture Overview

Nada de arquitetura nova. A tabela passa a ser dado semeado a partir de um JSON gerado uma vez da planilha oficial. Três regras do motor mudam: o Grupo I vira horas de PIT fora do total, o critério ganha carga horária mínima e a quantidade por horas some dos Grupos IV. As regras de sugestão da leitura de documentos são renumeradas pela descrição do item. As camadas seguem a AD-001.

## Code Reuse Analysis

| Component | Location | How to Use |
| --- | --- | --- |
| `seed_scoring_tables`, `seed_data/*.json`, repositórios de tabela | `backend/app/infrastructure/database/{seed.py,seed_data/,repositories.py}` | Troca os JSON de IFCH e FASI por `ufpa.json`; arquivamento das tabelas antigas pelo mesmo repositório |
| `ScoringCriterion`, `calculate`, `criterion_points` | `backend/app/domain/{entities/scoring.py,rules/scoring_engine.py,rules/scoring_points.py}` | `CARGA_SEMANAL` já calcula as horas; ganha `min_hours` e o resumo de horas por período |
| `ScoringAlertCode`, `NotScoredReason` | `backend/app/domain/rules/scoring_alerts.py` | Novos códigos `CARGA_HORARIA_NAO_INFORMADA` e `CARGA_HORARIA_INSUFICIENTE` |
| Regras de sugestão e de quantidade | `backend/app/domain/rules/{suggestion_rules.py,quantity_rules.py}` | Renumeração e quantidades por unidade |
| `CreateActivity` e `UpdateActivity` | `backend/app/application/use_cases/scoring.py` | Recusam `points_override` no Grupo I |
| Tela da Etapa 4 | `frontend/src/{components/ScoringTable.tsx,components/ScoringSummary.tsx,pages/ProcessScoring.tsx,api/types.ts}` | Grupo I em horas |
| Gerador a partir da planilha | `openpyxl` do ambiente de apoio fora do projeto | Gera `ufpa.json`; não vira dependência do backend |

## Components

### Dados: `ufpa.json`

- **Location**: `backend/app/infrastructure/database/seed_data/ufpa.json`
- Estrutura igual à dos JSON atuais (tabela, versão, grupos, critérios, `minimums`), com `min_hours` nos critérios IV.3, IV.4 e IV.5 (20) e `block 30 h` no VII.11. Grupo I: dois critérios `CARGA_SEMANAL` (17 semanas; preparação 1 e 2), `counts_in_total` falso, unidade "horas (PIT)". Grupos II a VIII em `POR_UNIDADE`, exceto VII.11 em `POR_BLOCO_DE_HORAS`. VIII.37 com 0 pontos.
- Os cinco valores decididos pelo usuário levam um `review_note` com a divergência da planilha e a decisão.

### Domínio

- `ScoringCriterion.min_hours: Decimal | None` (entidade, modelo, migração `0004_min_hours.py`, repositório).
- `scoring_alerts.py`: `NotScoredReason.CARGA_HORARIA_INSUFICIENTE`, `ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA`.
- `scoring_engine.calculate`: com `min_hours`, horas `< min_hours` → não pontuada; sem horas → pontua e alerta; resultado ganha `group1_hours_by_period` (soma de horas de PIT por `academic_period`) e `group1_total_hours`; as linhas do Grupo I ficam com `points = 0` e `pit_hours = horas`.
- `CreateActivity` e `UpdateActivity`: `points_override` em atividade do Grupo I → `ValidationFailed("points_override")`.

### Regras de sugestão e quantidade

Mudanças de número em relação à numeração do Anexo I (o resto das regras não muda):

| Tipo | Antes | Agora | Observação |
| --- | --- | --- | --- |
| `ARTIGO_INTERNACIONAL_INDEXADO` | VIII.11 (alt. VIII.13) | VIII.9 (alt. VIII.11) | |
| `ARTIGO_NACIONAL_INDEXADO` | VIII.12 (alt. VIII.13) | VIII.10 (alt. VIII.11) | |
| `ARTIGO_NAO_INDEXADO` | VIII.13 | VIII.11 | |
| `TRABALHO_COMPLETO_CONGRESSO` | VIII.23 (alt. VIII.12) | VIII.19 (alt. VIII.10) | |
| `COMUNICACAO_COM_RESUMO` / `SEM_RESUMO` | VIII.24 / VIII.25 | VIII.20 / VIII.21 | |
| `APRESENTACAO_TRABALHO_INTERNACIONAL` / `NACIONAL` | VIII.26 / VIII.27 | VIII.22 / VIII.23 | |
| `PALESTRA` | VIII.28 | VIII.24 | mesma descrição |
| `PATENTE_DEPOSITADA` / `CONCEDIDA` | VIII.35 / VIII.36 | VIII.29 / VIII.30 | |
| `REGISTRO_SOFTWARE` | VIII.63 | VIII.33 | |
| `CONSULTORIA_AD_HOC` | VIII.66 | VIII.36 | |
| `BANCA_SELECAO_POS` / `BANCA_SELECAO_BOLSAS` | III.8 / III.9 (alt. III.12) | III.8 / III.9 (sem alternativas) | III.12 não existe |
| `BANCA_PROCESSO_SELETIVO` | III.11 (alt. III.12) | sem item | |
| `EXTENSAO_EVENTO_MINISTRANTE` | IV.7 | sem item | IV.7 não existe |

Quantidade: `EXTENSAO_CURSO_COORDENACAO`, `EXTENSAO_CURSO_MINISTRANTE` e `EXTENSAO_EVENTO_COORDENACAO` passam a quantidade 1 por documento, com as horas guardadas; `ESTAGIO_CAPACITACAO` continua por horas.

### Dados em produção

`seed_scoring_tables` cria a tabela oficial e, para as tabelas "IFCH" e "FASI" antigas: se nenhuma versão está escolhida por processo, `archived = true` e remove as associações de unidade; se alguma está, não altera.

### Frontend

`ScoringTable` mostra o Grupo I com a coluna "horas (PIT)" e sem pontos; `ScoringSummary` rotula "Total geral (Grupos II a VIII)", mostra as horas de PIT por período e o total de horas; `api/types.ts` ganha `pit_hours`, `group1_hours_by_period` e `group1_total_hours`; o esquema da API de pontuação expõe os mesmos campos.

## Data Models

`scoring_criteria.min_hours numeric(9,2) null` (migração 0004). Nenhuma outra mudança de esquema.

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| --- | --- | --- |
| Atividade de curso abaixo de 20 h | Não pontua, razão `CARGA_HORARIA_INSUFICIENTE` | Linha explica por que não conta |
| Curso sem horas informadas | Pontua e alerta `CARGA_HORARIA_NAO_INFORMADA` | Pede para informar as horas |
| `points_override` no Grupo I | 422 no campo | Campo destacado |
| Versão antiga escolhida por processo | Mantida sem alteração | Processo continua calculando |

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| --- | --- | --- | --- |
| Transcrição de 97 itens da planilha | `seed_data/ufpa.json` (novo) | Pontuação errada em todos os processos | Gerado por script da planilha; testes de contagem e de soma por grupo (158, 44, 40, 75, 332, 258, 407); itens de referência conferidos um a um |
| Muitos testes apontam para a tabela da FASI e do IFCH | `backend/tests/integration/**` | Churn alto e risco de enfraquecer teste | Tarefas por arquivo; todo valor que mudar é registrado no commit; o Verificador confere asserções removidas |
| Regras de sugestão apontando para item inexistente | `suggestion_rules.py` | Atividade sugerida sem enquadramento | Teste que confere todos os itens contra a tabela semeada |
| Produção já tem as tabelas antigas | banco `progressao` na VM | Duas tabelas sugeridas para a unidade | Arquivamento na semeadura; conferência pela API após o deploy |
| Planilha tem texto e fórmula diferentes em 5 itens | `ufpa.json` | Valor errado | Decisões do usuário gravadas no `review_note` e na spec |

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Gerar o JSON por script fora do projeto | `openpyxl` só no ambiente de apoio | Não acrescenta dependência ao backend; a fonte fica registrada em `FONTES.md` |
| Grupo I | `points = 0` e `pit_hours` na linha | Evita ler horas como pontos e mantém a coluna de pontos coerente com o total |
| Tabelas antigas | Arquivar, não apagar | Rastreabilidade e retorno |
