# Tabela Oficial Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tabela-oficial/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from project guidelines, spec and the existing suites. Guidelines found: requisitos do usuário, seção 19; AD-001; AD-004; suites e comandos de `pontuacao` e `inteligencia-documental`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (entities, rules, engine) | unit | All branches; 1:1 to spec ACs; every boundary (19,99 h e 20 h) | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` |
| Seed data and repositories | unit / integration | Contagem, somas por grupo, itens de referência, idempotência, ida e volta no banco | `backend/tests/{unit,integration}/test_*.py` | `cd backend && .venv/bin/pytest -q` |
| Use cases + API | integration | Cada AC; erros 422 com o campo | `backend/tests/integration/**` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend | unit | Cada TELA AC | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Docs | none | build gate only | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | After tasks with integration tests | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Build | After phase completion or docs-only tasks | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm test -- --run && npm run build` |

---

## Execution Plan

### Phase 1: Critério, motor e esquema

```
T1 → T2 → T3 → T4 → T5 → T6 → T7
```

### Phase 2: Dados da tabela oficial e semeadura

```
T8 → T9 → T10 → T11
```

### Phase 3: Regras de sugestão e testes dependentes

```
T12 → T13 → T14 → T15 → T16 → T17 → T18
```

### Phase 4: Interface e documentação

```
T19 → T20 → T21 → T22 → T23
```

---

## Task Breakdown

### T1: Carga horária mínima no critério

**What**: `ScoringCriterion.min_hours: Decimal | None` (padrão `None`).
**Where**: `backend/app/domain/entities/scoring.py`
**Depends on**: None
**Reuses**: `ScoringCriterion` existente
**Requirement**: OFI-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O campo existe, é opcional e não muda a igualdade nem a construção dos testes existentes
- [x] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add minimum hours to scoring criteria`

---

### T2: Códigos de carga mínima

**What**: `NotScoredReason.CARGA_HORARIA_INSUFICIENTE` e `ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA`.
**Where**: `backend/app/domain/rules/scoring_alerts.py`
**Depends on**: T1
**Reuses**: enums do arquivo
**Requirement**: OFI-06, OFI-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os dois códigos existem com o nome exato
- [x] Os testes de alertas existentes continuam passando; Gate quick passa; 2+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add minimum hours reason and alert codes`

---

### T3: Motor: regra da carga mínima

**What**: Com `min_hours`: horas menores que o mínimo não pontuam; sem horas pontuam com alerta.
**Where**: `backend/app/domain/rules/scoring_engine.py`
**Depends on**: T2
**Reuses**: `calculate`
**Requirement**: OFI-06, OFI-07, edge case das 20 horas

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 19,99 h: `NAO_PONTUADA` com `CARGA_HORARIA_INSUFICIENTE`; 20 h exatas: pontua
- [x] Sem horas: pontua e emite `CARGA_HORARIA_NAO_INFORMADA` ALERTA
- [x] Critério sem `min_hours` não muda de comportamento (testes existentes sem alteração); Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): enforce minimum hours in the scoring engine`

---

### T4: Motor: Grupo I em horas de PIT

**What**: As linhas do Grupo I ficam com `points = 0` e `pit_hours`; o resultado ganha `group1_hours_by_period` e `group1_total_hours`.
**Where**: `backend/app/domain/rules/scoring_engine.py`
**Depends on**: T3
**Reuses**: `CARGA_SEMANAL` de `scoring_points.py`
**Requirement**: PIT-01, PIT-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 68 h na graduação: 8,00 horas; 34 h: 4,00; 68 h na pós-graduação: 12,00
- [x] Horas somadas por período letivo (3 ofertas de 68 h: 24,00) e total de horas do Grupo I
- [x] Subtotal, pontos e total geral não recebem nada do Grupo I
- [x] Gate quick passa; 10+ testes; testes existentes do motor que codificavam o Grupo I em pontos são ajustados e registrados no commit

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): report group I as pit hours outside the total`

---

### T5: Recusar pontos informados no Grupo I

**What**: `CreateActivity` e `UpdateActivity` recusam `points_override` no Grupo I.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T4
**Reuses**: validações existentes
**Requirement**: PIT-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Atividade do Grupo I com `points_override`: 422 no campo `points_override`, na criação e na edição
- [x] Outros grupos e o ajuste manual de pontuação de itens que o permitem não mudam; Gate full passa; 4+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): reject informed points on group I activities`

---

### T6: Modelo e migração 0004

**What**: Coluna `scoring_criteria.min_hours` e migração `0004_min_hours.py`.
**Where**: `backend/app/infrastructure/database/models.py`
**Depends on**: T5
**Reuses**: `0003_documents.py`
**Requirement**: OFI-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `alembic upgrade head` e `downgrade -1` funcionam no Postgres de teste
- [x] Gate full passa; 3+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add minimum hours column to scoring criteria`

---

### T7: Repositório: carga mínima

**What**: Leitura e escrita de `min_hours` nos repositórios de tabela, inclusive cópia e duplicação de versão.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T6
**Reuses**: `SqlScoringTableRepository`
**Requirement**: OFI-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Ida e volta de um critério com `min_hours` = 20 e sem
- [x] Duplicar tabela e nova versão copiam o campo; Gate full passa; 4+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(db): persist minimum hours in scoring repositories`

---

### T8: Semente da tabela oficial

**What**: `ufpa.json` gerado da planilha `Modelos/tabela-progressao-docente.xlsx` (leitura local) com as decisões do usuário.
**Where**: `backend/app/infrastructure/database/seed_data/ufpa.json`
**Depends on**: None (fase anterior concluída)
**Reuses**: `ifch.json` e `fasi.json` como modelo de estrutura; `openpyxl` do ambiente de apoio em `/tmp/claude-1000/-home-nees-Documents-VSCodigo-ProgressaoFuncionalPiloto/a8b47bbc-b08f-41b6-a0a4-bd64fbec8d7d/scratchpad/venv/bin/python`
**Requirement**: OFI-01, OFI-02, OFI-03, OFI-04, OFI-05, OFI-06, OFI-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Contagem por grupo 2, 16, 9, 6, 5, 14, 11 e 37
- [x] Somas dos Grupos II a VIII: 158, 44, 40, 75, 332, 258 e 407 (total 1314)
- [x] II.10 = 10, VI.14 = 6, VIII.4 = 15, VIII.8 = 15, VIII.12 = 2; II.7 = 5, III.2 = 5, III.4 = 2, IV.1 = 15, VIII.9 = 25, VIII.24 = 10, VIII.33 = 15
- [x] IV.3, IV.4 e IV.5 com `min_hours` 20; VII.11 por bloco de 30 h; VIII.37 com 0 pontos; Grupo I com `CARGA_SEMANAL` (17 semanas, preparação 1 e 2) e `counts_in_total` falso
- [x] `minimums` por classe 60, 80, 100 e 120 com a referência da Res. 4.644, art. 12; Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(db): add official ufpa scoring table seed data`

---

### T9: Semeadura da tabela oficial

**What**: `seed_scoring_tables` semeia a tabela oficial, associa a FASI e IFCH, arquiva as antigas e não semeia mais IFCH e FASI.
**Where**: `backend/app/infrastructure/database/seed.py`
**Depends on**: T8
**Reuses**: `seed_scoring_tables` existente
**Requirement**: OFI-01, OFI-08, OFI-09, OFI-10, OFI-11, edge cases de banco com tabelas antigas

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Banco vazio: só a tabela oficial, `OFICIAL`, associada a FASI e IFCH
- [x] Banco com as tabelas antigas sem uso: arquivadas e sem unidades; com uma versão escolhida por processo: mantida sem alteração
- [x] Rodar duas vezes não duplica nada e não altera o que já existe
- [x] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): seed the official ufpa table and archive the old ones`

---

### T10: Remover as sementes antigas

**What**: Apaga `ifch.json` e `fasi.json` e substitui os testes que as validavam pelos da tabela oficial.
**Where**: `backend/app/infrastructure/database/seed_data/`
**Depends on**: T9
**Reuses**: testes de semente existentes
**Requirement**: OFI-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os dois arquivos não existem mais e nenhum código os lê
- [ ] Cada teste removido tem um equivalente para a tabela oficial (contagem, somas, itens de referência) e o commit lista os testes substituídos
- [ ] Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `refactor(db): remove the ifch and fasi seed data`

---

### T11: API: horas de PIT

**What**: O esquema e a rota de pontuação devolvem `pit_hours` por linha, `group1_hours_by_period` e `group1_total_hours`.
**Where**: `backend/app/presentation/schemas/scoring.py`
**Depends on**: T10
**Reuses**: `ScoreRowOut` existente
**Requirement**: PIT-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET /api/processes/{id}/scoring` traz os três campos, com decimais em texto de 2 casas
- [ ] Os testes de API existentes continuam passando (campos novos são aditivos); Build gate passa; 4+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(api): expose group I pit hours in the scoring result`

---

### T12: Regras de sugestão renumeradas

**What**: Aplica a tabela de mudanças do design às regras de sugestão.
**Where**: `backend/app/domain/rules/suggestion_rules.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: tabela "Regras de sugestão" do design de `inteligencia-documental` e a de mudanças do design desta feature
**Requirement**: MAP-01, MAP-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os 13 tipos do Grupo VIII têm os itens novos (ex.: `PALESTRA` VIII.24; `ARTIGO_INTERNACIONAL_INDEXADO` VIII.9 com alternativa VIII.11; `REGISTRO_SOFTWARE` VIII.33)
- [x] `BANCA_PROCESSO_SELETIVO` e `EXTENSAO_EVENTO_MINISTRANTE` sem item; `BANCA_SELECAO_POS` e `BANCA_SELECAO_BOLSAS` sem alternativa III.12
- [x] Os demais tipos (Grupos II, III, IV, V, VI, VII e livros e capítulos) mantêm item e alternativas; Gate quick passa; 30+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): renumber suggestion rules to the official table`

---

### T13: Quantidade por curso e evento

**What**: `derive_quantity`: cursos IV.3 a IV.5 e evento IV.6 com quantidade 1 e horas guardadas; estágio por horas.
**Where**: `backend/app/domain/rules/quantity_rules.py`
**Depends on**: T12
**Reuses**: `derive_quantity` existente
**Requirement**: MAP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Curso de 21 h: quantidade 1 e horas 21; evento coordenado: quantidade 1
- [x] `ESTAGIO_CAPACITACAO` continua com horas e sem quantidade
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): derive per course and per event quantities`

---

### T14: Regras contra a tabela semeada

**What**: Teste de integração que confere todos os itens de todas as regras contra a tabela oficial semeada.
**Where**: `backend/tests/integration/test_rules_match_official_table.py`
**Depends on**: T13
**Reuses**: `seed_scoring_tables`
**Requirement**: MAP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Todo item principal e alternativo existe na tabela oficial
- [ ] Uma regra apontando para item inexistente faria o teste falhar (verificado ao inserir uma regra falsa temporária)
- [ ] Gate full passa; 2+ testes

**Tests**: integration
**Gate**: full

**Commit**: `test(rules): check every suggestion rule against the official table`

---

### T15: Testes de integração da pontuação

**What**: Atualiza fixtures e testes que usam as tabelas da FASI e do IFCH.
**Where**: `backend/tests/integration/scoring`
**Depends on**: T14
**Reuses**: fixtures `world`, `reference`
**Requirement**: ACE-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os testes passam com a tabela oficial; cada valor que mudou (pontos, itens, total) é listado no corpo do commit
- [ ] Nenhuma asserção que não codificasse valor da tabela antiga é removida ou enfraquecida; Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `test(scoring): move scoring integration tests to the official table`

---

### T16: Testes de API

**What**: Atualiza fixtures e testes da API que usam as tabelas antigas.
**Where**: `backend/tests/integration/api`
**Depends on**: T15
**Reuses**: `conftest.py`, `factories.py`
**Requirement**: ACE-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os testes passam com a tabela oficial; valores que mudaram listados no commit
- [ ] Nenhuma asserção que não codificasse valor da tabela antiga é removida ou enfraquecida; Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `test(api): move api tests to the official table`

---

### T17: Demais testes dependentes

**What**: Atualiza testes de documentos e unitários que citam itens ou tabelas antigas.
**Where**: `backend/tests`
**Depends on**: T16
**Reuses**: testes de analisador e de casos de uso de documentos
**Requirement**: ACE-02, MAP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os testes passam com os itens novos (ex.: palestra em VIII.24, artigo internacional em VIII.9)
- [ ] Nenhuma asserção que não codificasse item ou valor antigo é removida ou enfraquecida; valores que mudaram listados no commit; Gate full passa

**Tests**: integration
**Gate**: full

**Commit**: `test: move remaining tests to the official table numbering`

---

### T18: Aceitação recalculada

**What**: Reescreve o teste de aceitação com o cenário derivado de 2022–2024 na tabela oficial.
**Where**: `backend/tests/integration/api/test_scoring_golden.py`
**Depends on**: T17
**Reuses**: `test_scoring_golden.py` existente
**Requirement**: ACE-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Subtotais II a VIII = 52, 7, 62, 0, 30, 4 e 56 e total 211
- [ ] Horas de PIT por período = 24, 24, 24 e 20 e total de 92 horas; o Grupo I não entra no total
- [ ] Atividade fora do interstício, duplicada e aguardando revisão continuam fora do total; Build gate passa

**Tests**: integration
**Gate**: build

**Commit**: `test(scoring): recompute the acceptance case with the official table`

---

### T19: Tipos da API no frontend

**What**: `api/types.ts` ganha `pit_hours`, `group1_hours_by_period` e `group1_total_hours`.
**Where**: `frontend/src/api/types.ts`
**Depends on**: None (fase anterior concluída)
**Reuses**: tipos existentes
**Requirement**: TELA-01, TELA-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os três campos estão tipados e os testes existentes compilam
- [ ] Gate quick (frontend) passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): type the group I pit hours fields`

---

### T20: Tabela com o Grupo I em horas

**What**: `ScoringTable` mostra o Grupo I com a coluna "horas (PIT)" e sem pontos.
**Where**: `frontend/src/components/ScoringTable.tsx`
**Depends on**: T19
**Reuses**: `ScoringTable` existente
**Requirement**: TELA-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Linhas do Grupo I mostram as horas com o rótulo "horas (PIT)" e nenhum valor em pontos
- [ ] Os demais grupos não mudam; Gate quick (frontend) passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): show group I rows in pit hours`

---

### T21: Resumo com horas de PIT

**What**: `ScoringSummary` rotula "Total geral (Grupos II a VIII)" e mostra as horas por período e o total de horas.
**Where**: `frontend/src/components/ScoringSummary.tsx`
**Depends on**: T20
**Reuses**: `ScoringSummary` existente
**Requirement**: TELA-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O total mostra o rótulo novo e não inclui o Grupo I
- [ ] Horas por período e total de horas aparecem à parte; Gate quick (frontend) passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): show pit hours and the new total label`

---

### T22: Página da Etapa 4

**What**: `ProcessScoring` usa os campos novos.
**Where**: `frontend/src/pages/ProcessScoring.tsx`
**Depends on**: T21
**Reuses**: `ProcessScoring` existente
**Requirement**: TELA-01, TELA-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A página mostra o Grupo I em horas e o resumo novo com a resposta simulada da API
- [ ] Build gate passa (lint, testes, build); 3+ testes

**Tests**: unit
**Gate**: build

**Commit**: `feat(frontend): wire pit hours into the scoring page`

---

### T23: Fontes e notas de substituição

**What**: Registra a planilha como única fonte em `FONTES.md` e as substituições nas specs e no design afetados.
**Where**: `docs/referencias/normas/FONTES.md`
**Depends on**: T22
**Reuses**: `FONTES.md` existente
**Requirement**: Metas da spec

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `FONTES.md` descreve a planilha, as decisões dos cinco itens, o Grupo I em horas e a lista de fontes que deixam de valer
- [ ] As specs de `pontuacao` e `inteligencia-documental` e o design da segunda recebem a nota de substituição e a tabela de regras renumerada
- [ ] Build gate passa

**Tests**: none
**Gate**: build

**Commit**: `docs: record the official table as the only scoring source`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 → T2 → T3 → T4 → T5 → T6 → T7
Phase 2:  T8 → T9 → T10 → T11
Phase 3:  T12 → T13 → T14 → T15 → T16 → T17 → T18
Phase 4:  T19 → T20 → T21 → T22 → T23
```

