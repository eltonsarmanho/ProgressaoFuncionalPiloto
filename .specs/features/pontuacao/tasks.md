# Pontuação Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/pontuacao/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from project guidelines, spec and the existing suites. Guidelines found: requisitos do usuário, seção 19; AD-001 (teste de arquitetura); AD-004 (integração em PostgreSQL real); suites e comandos de `fundacao`. Existing tests sampled: `backend/tests/unit/domain`, `backend/tests/integration/api`, `frontend/src/**/*.test.tsx`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (entities, rules, engine) | unit | All branches; 1:1 to spec ACs; every listed edge case | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` |
| Seed data (JSON) | unit | Counts, per-group checksums and key items checked against the source PDFs | `backend/tests/unit/test_seed_*.py` | `cd backend && .venv/bin/pytest tests/unit -q` |
| Repositories / migrations / seed | integration | Key query paths + error paths (unique, optimistic lock, idempotency) | `backend/tests/integration/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Use cases + API routes | integration | All routes in scope: happy + every listed edge case + error paths (401/403/404/409/422) | `backend/tests/integration/api/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend components/pages | unit | Each TELA/ADMUI AC: render + interaction + error display | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Ports / config | none | build gate only | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | After tasks with integration tests | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Build | After phase completion or config-only tasks | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm test -- --run && npm run build` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Domínio da pontuação

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8
```

### Phase 2: Verificações e persistência

```
T9 → T10 → T11 → T12 → T13 → T14 → T15
```

### Phase 3: Casos de uso da pontuação

```
T16 → T17 → T18 → T19 → T20
```

### Phase 4: API da pontuação

```
T21 → T22 → T23 → T24
```

### Phase 5: Etapa 4 na interface

```
T25 → T26 → T27 → T28 → T29 → T30
```

### Phase 6: Administração das tabelas (API)

```
T31 → T32 → T33 → T34 → T35 → T36
```

### Phase 7: Interface de administração

```
T37 → T38 → T39
```

---

## Task Breakdown

### T1: Entidades da tabela de pontuação

**What**: `ScoringMode`, `TableStatus`, `ScoringCriterion`, `ScoringGroup` (com `counts_in_total` e limite) e `ScoringTableVersion` com `get_criterion` e `covers`.
**Where**: `backend/app/domain/entities/scoring.py`
**Depends on**: None
**Reuses**: padrão de `CareerVersion`
**Requirement**: TAB-01, TAB-02, TAB-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Busca por (grupo, item) devolve o critério ou `None`; `covers` correto nos dois limites da vigência
- [x] Grupo com `counts_in_total` falso é representável; nada importa framework (teste de arquitetura verde)
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add scoring table entities`

---

### T2: Entidade de atividade

**What**: `Activity`, `ActivityStatus`, `ActivitySource`, `Level`, `PeriodPrecision`, `initial_status(source)` e `group1_item(level)`.
**Where**: `backend/app/domain/entities/activity.py`
**Depends on**: T1
**Reuses**: enums de `entities/process.py`
**Requirement**: ATV-02, ATV-03, ATV-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `initial_status`: `MANUAL` dá `VALIDADA`; `SUGERIDA_IA` e `IMPORTADA` dão `AGUARDANDO_REVISAO`
- [x] `group1_item`: `GRADUACAO` dá 1, `POS_GRADUACAO` dá 2
- [x] O status armazenado só admite os três valores da spec
- [x] Gate quick passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add activity entity and status rules`

---

### T3: Códigos de alerta da pontuação

**What**: `ScoringAlertCode` com os 11 códigos do design e `Alert.code` alargado para aceitar os dois enums.
**Where**: `backend/app/domain/rules/scoring_alerts.py`
**Depends on**: T2
**Reuses**: `Alert`, `Severity` de `process_verification.py`
**Requirement**: VERIF-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Os 11 códigos existem com o nome exato do design
- [x] `Alert(code=ScoringAlertCode.X, ...)` é aceito e os testes de `fundacao` continuam passando
- [x] Gate quick passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add scoring alert codes`

---

### T4: Avaliação de período e título

**What**: `expand_month_dates`, `evaluate_period(activity, interstice)` (`DENTRO`, `PARCIAL`, `FORA`, `SEM_DATA`, `NAO_VERIFICAVEL`) e `normalize_title`.
**Where**: `backend/app/domain/rules/scoring_periods.py`
**Depends on**: T3
**Reuses**: `Interstice` de `interstice.py`
**Requirement**: VERIF-01, VERIF-02, VERIF-03, VERIF-04, edge case de datas inválidas

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] "Mai/22 a Mai/22" vira 01/05/2022 a 31/05/2022; "Nov/22" contra interstício que começa em 23/11/2022 dá `PARCIAL`
- [x] Evento antes ou depois do interstício dá `FORA`; sem data dá `SEM_DATA`; interstício inválido dá `NAO_VERIFICAVEL`
- [x] `normalize_title` ignora maiúsculas, acentos e espaços repetidos
- [x] Gate quick passa; 12+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add activity period evaluation`

---

### T5: Pontos por critério

**What**: `criterion_points(criterion, activity)` nos quatro modos, com `points_override`, quantidade efetiva e texto da fórmula.
**Where**: `backend/app/domain/rules/scoring_points.py`
**Depends on**: T4
**Reuses**: `Decimal`, `ScoringMode`
**Requirement**: CALC-02, CALC-03, CALC-04, CALC-05, CALC-06, edge case de blocos de horas

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `POR_UNIDADE`: 4 × 10 = 40
- [x] `POR_BLOCO_DE_HORAS`: 21 h, bloco 3, 5 pontos = 35; 2 h = 0; 22 h = 7 blocos
- [x] `CARGA_SEMANAL`: 68 h graduação = 8,00; 34 h = 4,00; 68 h pós = 12,00; 20 h graduação = 2,35
- [x] `VALOR_INFORMADO` respeita o limite; `points_override` substitui o cálculo e marca o ajuste
- [x] Gate quick passa; 12+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add scoring points calculation by mode`

---

### T6: Detecção de duplicidade

**What**: `find_duplicates(activities)`: mesmo título normalizado e períodos sobrepostos; a criada depois sai; justificativa de "distinta" libera; sem datas nunca duplica.
**Where**: `backend/app/domain/rules/scoring_duplicates.py`
**Depends on**: T5
**Reuses**: `normalize_title`, períodos expandidos
**Requirement**: VERIF-05, VERIF-06, VERIF-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Mesmo título, períodos sobrepostos: a atividade mais nova sai
- [x] Com `distinct_justification`: ambas contam
- [x] Membro e presidente da mesma comissão (Grupo VI) são duplicidade
- [x] Mesmo título sem datas ou em períodos separados não duplica
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add duplicate activity detection`

---

### T7: Motor de pontuação

**What**: `calculate(version, activities, interstice) -> ScoringResult`: critério, status, período, grupo que conta, duplicidade, pontos, limites, subtotais, total, potencial, percentual do Grupo I e contadores.
**Where**: `backend/app/domain/rules/scoring_engine.py`
**Depends on**: T6
**Reuses**: `criterion_points`, `evaluate_period`, `find_duplicates`
**Requirement**: CALC-01, CALC-07, CALC-08, CALC-09, CALC-10, CALC-11, CALC-12, CALC-13, VERIF-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Só `VALIDADA` dentro do interstício, com critério, sem duplicidade e em grupo que conta entra no total; `AGUARDANDO_REVISAO` vira `POTENCIAL` fora do total
- [x] Grupo que não conta dá subtotal 0 e razão `GRUPO_NAO_CONTA`; sem critério dá `SEM_ENQUADRAMENTO`; fora do interstício dá `FORA_DO_INTERSTICIO`
- [x] Limite por critério e por grupo corta a soma e gera `LIMITE_APLICADO` com antes e depois
- [x] Alertas por linha: `INTERSTICIO_PARCIAL`, `DATA_AUSENTE`, `SEM_COMPROVANTE`, `PONTOS_AJUSTADOS_MANUALMENTE`
- [x] Caso real em miniatura: subtotais 92, 120, 15, 95, 0, 30, 6, 56 e total 414
- [x] Mesma entrada dá o mesmo resultado; contadores corretos; Gate quick passa; 25+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add deterministic scoring engine`

---

### T8: Portas de repositório da pontuação

**What**: Protocols `ScoringTableRepository` e `ActivityRepository`, e `set_scoring_table_version` em `ProcessRepository`.
**Where**: `backend/app/domain/repositories/ports.py`
**Depends on**: T7
**Reuses**: portas existentes do arquivo
**Requirement**: SEL-08, ATV-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] As portas existem com os métodos do design (lista, leitura, criação, `version_in_use`, bloqueio por versão)
- [x] Teste de arquitetura continua passando
- [x] Build gate passa

**Tests**: none
**Gate**: build

**Commit**: `feat(domain): add scoring repository ports`

---

### T9: Verificações de processo

**What**: `verify_scoring` e `reference_minimum`: `SEM_EXTENSAO_OU_PESQUISA`, comparação com o mínimo (`ATINGE`, `NAO_ATINGE`, `NAO_DEFINIDO`) e `MINIMO_NAO_DEFINIDO`.
**Where**: `backend/app/domain/rules/scoring_verification.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `Alert`, `Severity`, `select_version`
**Requirement**: VERIF-09, VERIF-10, VERIF-11, VERIF-12, VERIF-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] DE ou 40H com subtotais IV + V = 0 dá `SEM_EXTENSAO_OU_PESQUISA` ALERTA, com referência ao art. 13, II
- [x] Estrutura Res. 4.644: classe atual C com total 414 dá `ATINGE` (mínimo 100); 99 dá `NAO_ATINGE`
- [x] Estrutura Lei 15.141: `NAO_DEFINIDO` e `MINIMO_NAO_DEFINIDO` REQUER_ANALISE_NORMATIVA
- [x] Todo alerta traz código, severidade, mensagem em português e referência; nada é alterado
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add scoring process verification`

---

### T10: Verificação da tabela escolhida

**What**: `verify_table_choice`: `TABELA_NAO_ENCONTRADA`, `TABELA_DE_OUTRA_UNIDADE`, `TABELA_PENDENTE_VALIDACAO` e `TABELA_FORA_DE_VIGENCIA`.
**Where**: `backend/app/domain/rules/scoring_table_choice.py`
**Depends on**: T9
**Reuses**: `Alert`, `ScoringTableVersion.covers`
**Requirement**: SEL-03, SEL-05, SEL-06, SEL-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem versão para a unidade e a data: `TABELA_NAO_ENCONTRADA` REQUER_ANALISE_NORMATIVA
- [x] Tabela de outra unidade: `TABELA_DE_OUTRA_UNIDADE` ALERTA; versão pendente: `TABELA_PENDENTE_VALIDACAO` REQUER_ANALISE_NORMATIVA
- [x] Versão que não cobre a data final do interstício: `TABELA_FORA_DE_VIGENCIA` ALERTA
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): add scoring table choice verification`

---

### T11: Modelos ORM e migração 0002

**What**: Modelos das tabelas do design, coluna `functional_processes.scoring_table_version_id` e migração Alembic `0002_scoring.py`.
**Where**: `backend/app/infrastructure/database/models.py`
**Depends on**: T10
**Reuses**: `Base`, padrão dos modelos de `fundacao`
**Requirement**: TAB-01, TAB-02, SEL-01, ATV-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `alembic upgrade head` e `downgrade -1` funcionam no Postgres de teste
- [x] Constraints: único (versão, número do grupo), único (grupo, item), número do grupo de 1 a 8
- [x] Gate full passa; 5+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add scoring schema and migration 0002`

---

### T12: Repositórios da pontuação

**What**: `SqlScoringTableRepository` e `SqlActivityRepository`, com `version_in_use` por `EXISTS` e bloqueio otimista por `version`.
**Where**: `backend/app/infrastructure/database/repositories.py`
**Depends on**: T11
**Reuses**: padrão de `SqlProcessRepository`
**Requirement**: SEL-08, ATV-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Ida e volta de versão com grupos e critérios, e de atividade com candidatas
- [x] `version_in_use` verdadeiro só depois de um processo escolher a versão
- [x] Gravar atividade com versão antiga dá `StaleVersion`
- [x] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add scoring and activity repositories`

---

### T13: Semente da tabela do IFCH

**What**: Transcrição do PDF oficial para JSON: 8 grupos, critérios 3, 16, 12, 7, 6, 14, 11 e 66, pontuações, modos, `counts_in_total` falso no Grupo I e limite 10 em I.3.
**Where**: `backend/app/infrastructure/database/seed_data/ifch.json`
**Depends on**: T12
**Reuses**: `Modelos/TABELA-DE-PONTUACAO-DO-IFCH.pdf` (somente leitura local)
**Requirement**: TAB-03, TAB-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Contagem por grupo exatamente 3, 16, 12, 7, 6, 14, 11, 66
- [x] Soma das pontuações por grupo conferida contra o PDF (valor da soma registrado no teste)
- [x] Itens de referência conferidos: II.2 = 30, III.2 = 8, IV.4 = 2, VI.10 = 7, VII.10 = 1, VIII.1 = 50
- [x] Gate quick passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(db): add ifch scoring table seed data`

---

### T14: Semente da tabela da FASI

**What**: Transcrição da tabela preenchida para JSON pela numeração do Anexo I, situação `PENDENTE_VALIDACAO`, `counts_in_total` verdadeiro, I.1 e I.2 em `CARGA_SEMANAL` (17 semanas; preparação 1 e 2), I.3 com limite 10, `review_note` nas divergências.
**Where**: `backend/app/infrastructure/database/seed_data/fasi.json`
**Depends on**: T13
**Reuses**: `seed_data/ifch.json` como base; `Modelos/Tabela de Pontuação.pdf`
**Requirement**: TAB-04, TAB-05, TAB-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Contagem por grupo exatamente 3, 16, 12, 7, 6, 14, 11, 66
- [x] Lista exata dos 17 itens II a VII com `review_note` de divergência (II.9, II.12, II.16, III.2, III.6, III.7, III.8, III.9, IV.2, IV.4, IV.5, IV.7, VI.10, VI.11, VI.12, VII.9, VII.10) e dos itens VIII.5, VIII.6, VIII.7, VIII.38, VIII.39
- [x] Pontos do caso real: II.7 = 10, II.8 = 10, II.12 = 10, III.2 = 10, III.3 = 5, IV.1 = 15, IV.4 = 5, VI.6 = 30, VII.10 = 3, VIII.11 = 25, VIII.12 = 20, VIII.13 = 6, VIII.66 = 5
- [x] Gate quick passa; 8+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(db): add fasi scoring table seed data`

---

### T15: Seed idempotente das tabelas

**What**: `seed_scoring_tables(uow)`: cria as duas tabelas, versões, grupos, critérios, mínimos de referência (60/80/100/120, Res. 4.644, art. 12) e associações IFCH e FASI às suas unidades.
**Where**: `backend/app/infrastructure/database/seed.py`
**Depends on**: T14
**Reuses**: `seed_reference_data`
**Requirement**: TAB-03, TAB-04, TAB-06, SEL-01, VERIF-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Rodar duas vezes não duplica tabelas, versões nem critérios
- [x] IFCH: situação `OFICIAL`, Grupo I não conta; FASI: `PENDENTE_VALIDACAO`, Grupo I conta
- [x] Cada tabela associada à sua unidade; mínimos gravados com a referência normativa
- [x] Build gate passa; 6+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(db): seed ifch and fasi scoring tables`

---

### T16: Sugerir e escolher a tabela do processo

**What**: `SuggestScoringTable` e `ChooseProcessTable` com auditoria e justificativa.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `AccessPolicy`, `AuditService`, `verify_table_choice`
**Requirement**: SEL-02, SEL-04, SEL-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem tabela escolhida: sugere a versão da unidade vigente na data final, sem gravar
- [x] Escolher grava a versão no processo com evento de auditoria (anterior, nova, justificativa)
- [x] Tabela de outra unidade sem justificativa: 422 no campo `justificativa`
- [x] Processo fora do acesso: 404
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add table suggestion and choice use cases`

---

### T17: Criar atividade

**What**: `CreateActivity` com validações do Grupo I, status inicial por origem, `SEM_ENQUADRAMENTO` e limites de entrada.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T16
**Reuses**: `initial_status`, `group1_item`
**Requirement**: ATV-01, ATV-02, ATV-03, ATV-05, ATV-06, ATV-07, ATV-11, ATV-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Manual vira `VALIDADA`; origem `SUGERIDA_IA` vira `AGUARDANDO_REVISAO`
- [x] Grupo I exige período letivo `AAAA.N`, nível e horas e deriva o item (graduação I.1, pós I.2)
- [x] Sem grupo e item ou item inexistente: salva como `SEM_ENQUADRAMENTO`
- [x] Quantidade negativa, maior que 10000 ou não inteira em `POR_UNIDADE`: 422 em `quantidade`; horas inválidas: 422 em `horas`
- [x] Processo `CONCLUIDO` ou `ARQUIVADO`: 409; sem acesso: 404
- [x] Gate full passa; 14+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add activity creation use case`

---

### T18: Alterar atividade, status e distinta

**What**: `UpdateActivity`, `ChangeActivityStatus` e `MarkActivitiesDistinct` com justificativa, auditoria, candidatas e bloqueio otimista.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T17
**Reuses**: `AuditService`
**Requirement**: ATV-08, ATV-09, ATV-10, ATV-13, ATV-11, ATV-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Mudar grupo, item, quantidade, horas ou pontos sem justificativa: 422 em `justificativa`; com justificativa: auditoria com anterior e novo
- [x] Mudar status exige justificativa e audita; `REJEITADA` para `AGUARDANDO_REVISAO` vale como nova revisão
- [x] Itens candidatos com justificativa gravados; só o item escolhido pontua
- [x] Versão antiga: 409; processo concluído: 409; sem acesso: 404
- [x] Gate full passa; 14+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add activity update, status and distinct use cases`

---

### T19: Listar atividades

**What**: `ListActivities` por processo, com filtros por grupo e status e ordem por grupo, item e data.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T18
**Reuses**: `AccessPolicy`
**Requirement**: ATV-14, ATV-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Devolve todas as atividades do processo em ordem de grupo, item e data
- [x] Filtros por grupo e por status funcionam isolados e combinados
- [x] Sem acesso: 404
- [x] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add activity listing use case`

---

### T20: Calcular a pontuação do processo

**What**: `CalculateProcessScore`: carrega processo, docente, carreira, tabela e atividades, chama o motor e as verificações e reavalia na troca de tabela.
**Where**: `backend/app/application/use_cases/scoring.py`
**Depends on**: T19
**Reuses**: `calculate`, `verify_scoring`, `verify_table_choice`
**Requirement**: CALC-01, CALC-08, CALC-09, CALC-10, CALC-11, CALC-12, CALC-13, SEL-09, edge case sem tabela, VERIF-09, VERIF-11, VERIF-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem tabela escolhida: total 0, razão `SEM_TABELA` e sugestão
- [x] Trocar de tabela reavalia por (grupo, item); inexistente vira `SEM_ENQUADRAMENTO`
- [x] Resultado traz subtotais, total, potencial, percentual do Grupo I, contadores, alertas de linha e de processo e a comparação com o mínimo
- [x] Build gate passa; 12+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(scoring): add process score calculation use case`

---

### T21: Rotas de leitura das tabelas

**What**: `GET /api/scoring-tables`, `.../versions` e `GET /api/scoring-versions/{id}` com esquemas.
**Where**: `backend/app/presentation/api/scoring_tables.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: padrão de `presentation/api/career.py`
**Requirement**: TAB-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Lista as duas tabelas semeadas com versões, vigência, situação e referência
- [x] A versão devolve os 8 grupos e os critérios em ordem de grupo e item
- [x] Sem sessão: 401; decimais como texto com 2 casas
- [x] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add scoring table read routes`

---

### T22: Rotas de pontuação do processo

**What**: `GET` e `PUT /api/processes/{id}/scoring/table` e `GET /api/processes/{id}/scoring`.
**Where**: `backend/app/presentation/api/scoring.py`
**Depends on**: T21
**Reuses**: casos de uso de T16 e T20
**Requirement**: SEL-02, SEL-03, SEL-04, SEL-05, SEL-06, SEL-07, SEL-08, CALC-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `GET .../scoring/table` devolve a escolhida, a sugestão e os alertas de tabela
- [x] `PUT` grava com justificativa quando exigida e responde 422 sem ela
- [x] Versão em uso: critérios imutáveis (409 na administração, testado em T36)
- [x] `GET .../scoring` devolve o resultado com linhas, razões e alertas
- [x] Gate full passa; 10+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add process scoring routes`

---

### T23: Rotas de atividades

**What**: `GET` e `POST /api/processes/{id}/activities`, `GET` e `PUT /api/activities/{id}`, `POST .../status` e `POST .../distinct`.
**Where**: `backend/app/presentation/api/activities.py`
**Depends on**: T22
**Reuses**: casos de uso de T17 a T19
**Requirement**: ATV-01, ATV-05, ATV-06, ATV-07, ATV-08, ATV-09, ATV-11, ATV-12, ATV-13, ATV-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cada rota: caminho feliz e erros 401, 404, 409 e 422 com campo
- [x] Datas com mês e ano (`2022-05`) viram `MONTH`
- [x] Origem fora de `MANUAL` não é aceita pela API pública
- [x] Gate full passa; 20+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add activity routes`

---

### T24: Aceitação do caso real FASI 2022–2024

**What**: Teste de ponta a ponta pela API com o caso real: processo, tabela da FASI, atividades e resultado.
**Where**: `backend/tests/integration/api/test_scoring_golden.py`
**Depends on**: T23
**Reuses**: fixtures de `tests/integration/api/factories.py`
**Requirement**: CALC-14, CALC-13, SEL-06, VERIF-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Subtotais I a VIII exatamente 92, 120, 15, 95, 0, 30, 6 e 56 e total 414
- [x] Percentual do Grupo I 22,22%; comparação com o mínimo `ATINGE` (classe C, 100)
- [x] Alerta `TABELA_PENDENTE_VALIDACAO` presente; atividades fora do interstício ou duplicadas ficam fora do total
- [x] Build gate passa; 4+ testes

**Tests**: integration
**Gate**: build

**Commit**: `test(scoring): add real case acceptance test for fasi 2022-2024`

---

### T25: Navegação com Etapa 4 habilitada

**What**: `StepNav` recebe as etapas habilitadas; Etapa 4 abre, as outras seguem "em breve".
**Where**: `frontend/src/components/StepNav.tsx`
**Depends on**: None (fase anterior concluída)
**Reuses**: `StepNav`, teste UI-04 de `ProcessStep1.test.tsx`
**Requirement**: TELA-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Etapa 1 e Etapa 4 habilitadas; etapas 2, 3 e 5 a 9 desabilitadas com "em breve"
- [x] Teste UI-04 ajustado de forma explícita, sem enfraquecer
- [x] Gate quick (frontend) passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): enable step 4 in the process navigation`

---

### T26: Tabela de pontuação

**What**: Componente com as colunas Grupo, Item, Atividade, Quantidade, Pontuação unitária, Total, Comprovante e Status, agrupado de I a VIII, em cartões abaixo de 480 px.
**Where**: `frontend/src/components/ScoringTable.tsx`
**Depends on**: T25
**Reuses**: `styles.css`
**Requirement**: TELA-02, TELA-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Renderiza as linhas por grupo com as 8 colunas
- [x] Em largura estreita vira cartões, sem largura fixa maior que 360 px (teste de estilo)
- [x] Gate quick (frontend) passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add scoring table component`

---

### T27: Resumo da pontuação

**What**: Subtotais, total, potencial, percentual do Grupo I, comparação com o mínimo e contadores.
**Where**: `frontend/src/components/ScoringSummary.tsx`
**Depends on**: T26
**Reuses**: -
**Requirement**: TELA-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Exibe subtotais de cada grupo, total geral, potencial e percentual
- [x] Exibe ATINGE, NAO_ATINGE ou NAO_DEFINIDO e os cinco contadores
- [x] Gate quick (frontend) passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add scoring summary component`

---

### T28: Formulário de atividade

**What**: Campos por modo do critério (Grupo I: período letivo, nível, horas), justificativa obrigatória na edição e erro junto ao campo.
**Where**: `frontend/src/components/ActivityForm.tsx`
**Depends on**: T27
**Reuses**: `FieldError`
**Requirement**: TELA-04, TELA-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Campos mudam conforme o modo; Grupo I mostra período letivo, nível e horas
- [x] Edição sem justificativa não envia
- [x] 422 mostra a mensagem junto ao campo
- [x] Gate quick (frontend) passa; 6+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add activity form`

---

### T29: Seletor de tabela

**What**: Sugestão, situação e referência da tabela, e confirmação antes de calcular.
**Where**: `frontend/src/components/TablePicker.tsx`
**Depends on**: T28
**Reuses**: -
**Requirement**: TELA-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Exibe nome, situação (`PENDENTE_VALIDACAO` em destaque) e referência normativa
- [x] Pede justificativa para tabela de outra unidade
- [x] Gate quick (frontend) passa; 4+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add scoring table picker`

---

### T30: Página da Etapa 4

**What**: Reúne seletor, tabela, resumo, alertas por severidade e formulário; rota do processo.
**Where**: `frontend/src/pages/ProcessScoring.tsx`
**Depends on**: T29
**Reuses**: `AlertList`, `api/client.ts`
**Requirement**: TELA-07, TELA-02, TELA-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Carrega e exibe a pontuação e os alertas agrupados por severidade com a referência
- [x] Cria e edita atividade e atualiza o resultado
- [x] Build gate passa (lint, testes, build)

**Tests**: unit
**Gate**: build

**Commit**: `feat(frontend): add process scoring page`

---

### T31: Criar e duplicar tabela

**What**: `CreateScoringTable` e `DuplicateScoringTable` com auditoria.
**Where**: `backend/app/application/use_cases/scoring_admin.py`
**Depends on**: None (fase anterior concluída)
**Reuses**: `require_admin`, `AuditService`
**Requirement**: ADM-01, ADM-02, ADM-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Cria tabela com nome único, unidades e primeira versão com vigência e referência
- [x] Duplicar copia a última versão e as duas tabelas ficam independentes
- [x] Não ADMIN: 403; nome repetido: 409/422 com campo
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add scoring table creation and duplication`

---

### T32: Alterar critérios

**What**: `UpdateVersionCriteria` exige a referência da alteração; versão em uso dá 409.
**Where**: `backend/app/application/use_cases/scoring_admin.py`
**Depends on**: T31
**Reuses**: `version_in_use`
**Requirement**: ADM-03, ADM-04, SEL-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Versão sem uso: altera com referência e audita valores anterior e novo
- [x] Versão usada por processo: 409 orientando a criar nova versão
- [x] Sem referência: 422 no campo; não ADMIN: 403
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add version criteria update with in-use guard`

---

### T33: Nova versão a partir de outra

**What**: `CreateVersionFrom` copia os critérios, exige vigência e referência e fecha a versão aberta no dia anterior.
**Where**: `backend/app/application/use_cases/scoring_admin.py`
**Depends on**: T32
**Reuses**: `_close_open_version` de `career.py`
**Requirement**: ADM-05, ADM-06, ADM-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nova versão copia grupos e critérios; a versão aberta termina no dia anterior ao início da nova
- [x] Processo que perderia a versão escolhida: 409 sem criar nada
- [x] Vigência sobreposta: 409
- [x] Gate full passa; 8+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add version creation with automatic closing`

---

### T34: Parser do CSV de critérios

**What**: `parse_criteria_csv(text)` com colunas `grupo`, `item`, `descricao`, `unidade`, `modo`, `pontos`, `horas_por_bloco`, `limite`, e lista de todos os erros por linha.
**Where**: `backend/app/application/services/criteria_csv.py`
**Depends on**: T33
**Reuses**: módulo `csv` da biblioteca padrão
**Requirement**: ADM-08, ADM-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] CSV válido vira critérios com tipos corretos
- [x] Linhas inválidas: erro lista todas as linhas e campos, sem parar na primeira
- [x] Coluna ausente e UTF-8 com BOM tratadas
- [x] Gate quick passa; 10+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(scoring): add criteria csv parser`

---

### T35: Importar CSV como nova versão

**What**: `ImportCriteriaCsv`: tudo ou nada; adiciona `python-multipart` às dependências.
**Where**: `backend/app/application/use_cases/scoring_admin.py`
**Depends on**: T34
**Reuses**: `parse_criteria_csv`, `CreateVersionFrom`
**Requirement**: ADM-08, ADM-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] CSV válido cria a nova versão com todas as linhas
- [x] Qualquer linha inválida: 422 listando todas e nenhuma versão criada
- [x] Gate full passa; 6+ testes

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): add csv import as new version`

---

### T36: Rotas de administração

**What**: `POST` de tabela, duplicar, versão, importação e `PUT` de critério e unidades; histórico de versões.
**Where**: `backend/app/presentation/api/scoring_tables_admin.py`
**Depends on**: T35
**Reuses**: casos de uso de T31 a T35
**Requirement**: ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, ADM-10, ADM-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cada rota de escrita: ADMIN passa, SECRETARIA e DOCENTE recebem 403
- [ ] Histórico lista versões, vigências, referências e eventos de auditoria; versões anteriores só leitura
- [ ] Versão em uso: 409 na alteração dos critérios
- [ ] Build gate passa; 14+ testes

**Tests**: integration
**Gate**: build

**Commit**: `feat(api): add scoring table administration routes`

---

### T37: Lista de tabelas e versões

**What**: Página para ADMIN com tabelas, versões, vigência, situação e referência.
**Where**: `frontend/src/pages/ScoringAdmin.tsx`
**Depends on**: None (fase anterior concluída)
**Reuses**: `api/client.ts`
**Requirement**: ADMUI-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] ADMIN vê a lista; outros perfis não veem a rota
- [ ] Gate quick (frontend) passa; 3+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add scoring tables admin page`

---

### T38: Duplicar, nova versão e CSV

**What**: Formulários para duplicar tabela, criar versão e enviar CSV, com erros por linha.
**Where**: `frontend/src/components/ScoringAdminForms.tsx`
**Depends on**: T37
**Reuses**: `FieldError`
**Requirement**: ADMUI-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Duplicar e criar versão chamam a API e atualizam a lista
- [ ] CSV com erro mostra linha e campo de cada erro
- [ ] Gate quick (frontend) passa; 5+ testes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add scoring admin forms`

---

### T39: Destacar critérios para revisão

**What**: Critérios com `review_note` aparecem destacados na tabela da FASI.
**Where**: `frontend/src/components/ReviewHighlight.tsx`
**Depends on**: T38
**Reuses**: -
**Requirement**: ADMUI-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os itens marcados mostram a anotação da diferença
- [ ] Build gate passa (lint, testes, build); 3+ testes

**Tests**: unit
**Gate**: build

**Commit**: `feat(frontend): highlight scoring criteria marked for review`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7

Phase 1:  T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8
Phase 2:  T9 → T10 → T11 → T12 → T13 → T14 → T15
Phase 3:  T16 → T17 → T18 → T19 → T20
Phase 4:  T21 → T22 → T23 → T24
Phase 5:  T25 → T26 → T27 → T28 → T29 → T30
Phase 6:  T31 → T32 → T33 → T34 → T35 → T36
Phase 7:  T37 → T38 → T39
```

