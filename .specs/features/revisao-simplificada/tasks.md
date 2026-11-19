# Revisão simplificada das atividades Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/revisao-simplificada/design.md`
**Spec**: `.specs/features/revisao-simplificada/spec.md`
**Status**: Draft (aguarda a aprovação das tarefas)

Regras de execução desta feature: cada tarefa escreve primeiro os testes que derivam dos critérios de aceitação da spec e só então o código (os itens `Done when` começam pelo teste); só dados sintéticos; `Documentos/` e `Modelos/` nunca são abertos; um commit por tarefa (Conventional Commits, com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`), marcando a tarefa neste arquivo e a rastreabilidade da spec no mesmo commit; sem push, deploy nem acesso à VM sem autorização explícita (a migração `0008` vai à VM só no deploy autorizado). A fase 1 muda a regra do que entra nos documentos: as versões já geradas não mudam (AD-012).

---

## Test Coverage Matrix

> Generated from project guidelines, spec and the existing suites. Guidelines found: `CLAUDE.md` (regras de negócio, gate), AD-001 (teste de arquitetura), AD-004 (integração em PostgreSQL real), AD-006, AD-012, AD-019. Existing tests sampled: `backend/tests/unit/{domain,application,infrastructure}`, `backend/tests/integration/{api,doc_usecases,scoring}`, `frontend/src/**/*.test.tsx`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (entities, rules) | unit | All branches; 1:1 to spec ACs; every listed edge case and each boundary value (data no primeiro e no último dia do interstício, carga igual ao mínimo, cadeia de três duplicadas) | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` |
| Use cases + services | integration | Happy + every listed edge case + error paths (422, 404, 409); atomicidade e idempotência da mesclagem | `backend/tests/integration/{doc_usecases,scoring,api}/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| API routes and schemas | integration | All routes in scope: happy + edge + error paths (401/403/404/409/422); CSRF nas escritas | `backend/tests/integration/api/test_*.py` | `cd backend && .venv/bin/pytest tests/integration/api -q` |
| Repositories / migrations | integration | Key query paths, número de consultas, FK que não trava o `DELETE` do processo, `upgrade` e `downgrade` | `backend/tests/integration/test_*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend components/pages | unit | Each SEC, DUP, EDT, QTD AC: render + interação + exibição de erro, com a API simulada; 120 atividades; 360 px sem rolagem horizontal; teclado | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Types / labels / docs | none | build gate only (labels têm teste de texto) | - | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After tasks with unit tests only | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | After tasks with integration tests | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Build | After phase completion or config/type-only tasks | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order. A tarefa que depende de fase anterior lista a dependência em `Depends on`; o diagrama de cada fase mostra só as dependências da própria fase.

### Phase 1: Validade no domínio e no motor

```
T1 → T2 → T4
T3 → T4
T2 → T5 → T6 → T8
T7 → T8
```

### Phase 2: Mesclagem

```
T9 → T10 → T11 → T12
T13 → T14 → T15 → T16
T12 → T14
```

### Phase 3: Regras de escrita

```
T5 → T17 → T18 → T19 → T20 → T21 → T22
T14 → T21
```

### Phase 4: API da lista

```
T12 → T23 → T24 → T25 → T26
T22 → T25
```

### Phase 5: Frontend, peças da Etapa 3

```
T26 → T27 → T28 → T29 → T33
T28 → T30 → T33
T28 → T31
T28 → T32 → T33
```

### Phase 6: Frontend, a Etapa 3 montada

```
T31 → T34 → T36
T33 → T34
T33 → T35 → T36
T28 → T37 → T38
T36 → T38 → T39
```

### Phase 7: Frontend, formulário e Etapa 4

```
T30 → T40 → T41
T39 → T40
T39 → T42
```

### Phase 8: Documentação e verificação

```
T42 → T43 → T44
```

---

## Task Breakdown

### T1: `classify_activity` e `Validity` no domínio

**Status**: Done

**What**: Função pura que decide se a atividade é válida ou não válida, com o motivo, os parâmetros do motivo e se precisa de categoria.
**Where**: `backend/app/domain/rules/activity_validity.py` (novo)
**Depends on**: None
**Reuses**: `evaluate_period` e `is_yearly_unit` (`scoring_periods.py`), `NotScoredReason` (`scoring_alerts.py`), `is_pit_criterion`
**Requirement**: VAL-06, SEC-02, SEC-06, SEC-07, SEG-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes em `backend/tests/unit/domain/test_activity_validity.py`: rejeitada → `NAO_VALIDA/REJEITADA`; data um dia antes e um dia depois do interstício → `FORA_DO_INTERSTICIO` com `event_date` e `interstice_*` nos parâmetros, e o primeiro e o último dia são válidos; categoria por ano cujo período cruza o interstício → válida, e o que não o toca → fora; sem categoria → `VALIDA` com `needs_category`; grupo que não conta (sem ser PIT) → `GRUPO_NAO_CONTA`; duplicidade residual → `DUPLICIDADE`; carga igual ao mínimo → válida e abaixo → `CARGA_HORARIA_INSUFICIENTE` com `hours` e `min_hours`; sem carga informada → válida; sem tabela só avalia rejeitada, data como dia e categoria; a ordem dos motivos é a do motor
- [x] `classify_activity` não importa FastAPI nem SQLAlchemy (teste de arquitetura passa)
- [x] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [x] Test count: os testes novos passam e nenhum teste existente foi apagado

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): classify an activity as valid or not valid with the reason`

---

### T2: O motor avalia só as atividades válidas

**Status**: Done

**What**: `calculate` classifica cada atividade uma vez, avalia só as válidas, devolve o mapa `validity` no resultado e conta os contadores só sobre as válidas; `_evaluate` perde as saídas antecipadas que `classify_activity` cobre.
**Where**: `backend/app/domain/rules/scoring_engine.py` (modify)
**Depends on**: T1
**Reuses**: `classify_activity` (T1), `find_duplicates`, os testes de caracterização de `test_scoring_characterization.py` e `test_scoring_golden.py`
**Requirement**: VAL-01, SEG-01, SEG-03, SEG-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/unit/domain/test_scoring_engine_validity.py`: atividade fora do interstício, rejeitada, com carga insuficiente e duplicada não geram linha nem contam nos contadores `activities`, `not_scored` e `pending`; o total e os subtotais não mudam em relação à regra antiga para o mesmo conjunto de válidas; atividade sem categoria continua como linha `SEM_ENQUADRAMENTO`; atividade validada com categoria pontua com o valor unitário da tabela e a quantidade informada sem outra ação; `ScoringResult.validity` traz o estado de cada atividade
- [x] Os testes de caracterização e os golden existentes passam sem alteração de valor esperado, exceto os que listavam `NAO_PONTUADA` por motivo agora tratado como não válida (cada exceção é anotada no corpo do teste com o requisito SEG-01)
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: contagem antes e depois registrada; nenhum teste apagado sem substituto

**Tests**: unit
**Gate**: full

**Commit**: `feat(scoring): score only the valid activities`

---

### T3: Código de alerta `QUANTIDADE_ASSUMIDA`

**Status**: Done

**What**: Novo valor `QUANTIDADE_ASSUMIDA` em `ScoringAlertCode`.
**Where**: `backend/app/domain/rules/scoring_alerts.py` (modify)
**Depends on**: None
**Reuses**: os demais códigos do mesmo enum
**Requirement**: VAL-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste em `backend/tests/unit/domain/test_scoring_alerts.py`: o código existe com o texto `QUANTIDADE_ASSUMIDA` e o conjunto de códigos conhecidos do teste de contrato inclui o novo
- [x] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [x] Test count: o teste novo passa

**Tests**: unit
**Gate**: quick

**Commit**: `feat(scoring): add the assumed-quantity alert code`

---

### T4: O motor emite `QUANTIDADE_ASSUMIDA`

**Status**: Done

**What**: Quando o item é por unidade e a atividade não tem quantidade, a linha pontua com quantidade 1 e carrega o alerta `QUANTIDADE_ASSUMIDA`.
**Where**: `backend/app/domain/rules/scoring_engine.py` (modify)
**Depends on**: T2, T3
**Reuses**: `_row_alert`, `scoring_points._per_unit`
**Requirement**: VAL-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/unit/domain/test_scoring_engine_validity.py`: item por unidade sem quantidade → pontos de 1 unidade e o alerta; com quantidade informada → sem o alerta; item por bloco, por hora e por ano sem quantidade → sem o alerta (a regra é só do item por unidade)
- [x] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [x] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(scoring): warn when the quantity is assumed to be one`

---

### T5: A Etapa 4 usa a validade, com e sem tabela

**Status**: Done

**What**: `compute_process_score` e `_without_table` trazem só as atividades válidas nas linhas e nos contadores e repassam o mapa `validity` no resultado.
**Where**: `backend/app/application/use_cases/scoring.py` (modify)
**Depends on**: T2
**Reuses**: `classify_activity` (T1), `calculate`, `ProcessScore`
**Requirement**: SEG-01, SEG-04, VAL-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/integration/api/test_scoring_validity_api.py`: uma co-orientação de mestrado com categoria II.5, validada, aparece na Etapa 4 com 8,00 pontos sem outra ação; uma atividade fora do interstício, uma rejeitada e uma com carga insuficiente não aparecem nas linhas nem nos contadores; sem tabela escolhida, só as válidas contam e as demais não entram; trocar a data de uma atividade fora para dentro a inclui no cálculo seguinte
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam; os de `test_scoring_process_api.py` ajustados só nos casos de SEG-01 anotados

**Tests**: integration
**Gate**: full

**Commit**: `feat(scoring): compute the process score over the valid activities`

---

### T6: `eligible_activities` recebe a validade

**Status**: Done

**What**: A seleção das atividades dos documentos passa a exigir validada, com grupo e item, e válida; assim Tabela, Relatório e Comprovante usam a mesma regra.
**Where**: `backend/app/domain/rules/activity_order.py` (modify)
**Depends on**: T5
**Reuses**: `ScoringResult.validity` (T2)
**Requirement**: SEG-01, SEG-02, SEG-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/unit/domain/test_activity_order.py`: validada e válida entra; validada e não válida (por exemplo, fora do interstício) não entra; aguardando revisão não entra; sem categoria não entra; a ordem de `table_order` não muda
- [x] Todo chamador de `eligible_activities` passa a validade (o teste de arquitetura e o `ruff` pegam o que faltar)
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam

**Tests**: unit
**Gate**: full

**Commit**: `feat(documents): take only valid activities into the documents`

---

### T7: Código de recusa `ATIVIDADE_SEM_CATEGORIA`

**Status**: Done

**What**: Novo valor `ATIVIDADE_SEM_CATEGORIA` em `GenerationCode`.
**Where**: `backend/app/domain/entities/generated.py` (modify)
**Depends on**: None
**Reuses**: `GenerationCode.ATIVIDADE_SEM_DESCRICAO` como modelo
**Requirement**: SEG-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] O valor existe e o teste de contrato dos códigos (`test_generation_error_mapping.py`) inclui o novo com status 422
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: nenhum teste apagado

**Tests**: none
**Gate**: build

**Commit**: `feat(documents): add the refusal code for activities without category`

---

### T8: A geração usa a validade e recusa atividade sem categoria

**Status**: Done

**What**: `load_generation_inputs` seleciona as atividades pela validade, `_excluded` conta só as válidas que ficam de fora (aguardando validação) e a geração é recusada com `ATIVIDADE_SEM_CATEGORIA` quando há atividade válida sem categoria.
**Where**: `backend/app/application/services/generation_inputs.py` (modify)
**Depends on**: T6, T7
**Reuses**: `eligible_activities` (T6), `GenerationRefused`
**Requirement**: SEG-01, SEG-02, SEG-03, SEG-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/integration/api/test_generated_validity_acceptance.py`: com atividades fora do interstício, duplicadas, rejeitadas e com carga insuficiente, a Tabela, o Relatório e o Comprovante não trazem nenhuma delas, nem como "Não pontuada", e o Comprovante não inclui páginas cuja única atividade é não válida; corrigir a data de uma e gerar de novo a inclui; atividade válida sem categoria → 422 `ATIVIDADE_SEM_CATEGORIA` nos três documentos; as versões geradas antes continuam iguais (AD-012)
- [x] O snapshot `excluded` não lista mais rejeitadas nem sem categoria como "ficaram de fora" (a regra nova as trata como não válidas ou recusa a geração); ajustes nos testes existentes anotados com SEG-01
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam; nenhum teste apagado sem substituto

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): generate only from valid activities and refuse uncategorized ones`

---

### T9: Migração `0008_activity_merge`

**Status**: Done

**What**: Colunas `activities.merged_into_id` e `activity_evidences.origin_activity_id` (FK `NO ACTION`), índice parcial e o espelho das colunas nos modelos SQLAlchemy (a mesma mudança de esquema).
**Where**: `backend/alembic/versions/0008_activity_merge.py` (novo)
**Depends on**: None
**Reuses**: `0007_process_purge.py` como modelo; `test_migrations.py`
**Requirement**: DUP-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/integration/test_migration_activity_merge.py`: após o `upgrade`, as colunas e o índice existem e aceitam nulo; `downgrade` remove as duas colunas e o índice; a FK recusa um id inexistente; o `test_models_match_migrated_schema` passa
- [x] Cabeça do alembic é `0008`; os dados existentes não mudam
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add the merged-into and origin columns for activity merging`

---

### T10: Campo `merged_into_id` na entidade `Activity`

**Status**: Done

**What**: `Activity.merged_into_id` (nulo por padrão) e `Activity.is_merged`.
**Where**: `backend/app/domain/entities/activity.py` (modify)
**Depends on**: T9
**Reuses**: os campos opcionais existentes da entidade
**Requirement**: DUP-02, DUP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste em `backend/tests/unit/domain/test_activity_entity.py`: padrão nulo; `is_merged` verdadeiro só com o campo preenchido; `dataclasses.replace` preserva o campo
- [x] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [x] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): mark an activity as merged into another`

---

### T11: Porta do repositório para a mesclagem

**Status**: Done

**What**: Métodos da porta `ActivityRepository` para listar as mescladas numa atividade, gravar a mesclagem e mover provas, e `origin_activity_id` em `ActivityEvidence`.
**Where**: `backend/app/domain/repositories/ports.py` (modify)
**Depends on**: T10
**Reuses**: `ActivityEvidence` e `EvidenceRepository` existentes
**Requirement**: DUP-01, DUP-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Porta com `list_merged_into(activity_id)`, `set_merged_into(activity, target_id, expected_version)`, `list_for_process(..., include_merged=False)`, e `EvidenceRepository.move(evidence_ids, to_activity_id, origin_activity_id)` / `restore_from(origin_activity_id)`; `ActivityEvidence.origin_activity_id`
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` (o teste de arquitetura continua passando)
- [x] Test count: nenhum teste apagado

**Tests**: none
**Gate**: build

**Commit**: `feat(domain): extend the activity ports for merging`

---

### T12: Repositórios SQL da mesclagem

**Status**: Done

**What**: Implementação SQL das portas: a lista padrão deixa de trazer as mescladas, e as provas movem e voltam com a origem gravada.
**Where**: `backend/app/infrastructure/database/repositories.py` (modify)
**Depends on**: T11
**Reuses**: `SqlActivityRepository`, `SqlEvidenceRepository`, `_ACTIVITY_FIELDS`
**Requirement**: DUP-02, DUP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/integration/test_repositories_merge.py`: lista padrão sem mescladas e com `include_merged=True` com elas; `set_merged_into` respeita a versão esperada (409 se mudou); mover provas grava `origin_activity_id`, não repete o par documento e página que a mantida já tem, e `restore_from` devolve só as provas que vieram dela; excluir um processo com atividade mesclada pelo `DELETE` do caso de uso apaga tudo sem violar a FK
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): list, merge and restore activities and their evidences`

---

### T13: `duplicate_pairs` com cadeias

**Status**: Done

**What**: Função que devolve os pares (duplicada, original) pela mesma regra de `find_duplicates` e agrupa cadeias A, B, C num grupo só.
**Where**: `backend/app/domain/rules/scoring_duplicates.py` (modify)
**Depends on**: None
**Reuses**: `similar_titles`, `find_duplicates`
**Requirement**: DUP-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/unit/domain/test_scoring_duplicates.py`: o conjunto de duplicadas de `duplicate_pairs` é o mesmo de `find_duplicates` para as mesmas entradas; A~B e B~C formam um grupo de três; atividades `distinct_justification` não formam par; `duplicate_groups` devolve grupos ordenados por criação
- [x] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [x] Test count: os testes novos passam; os existentes de `find_duplicates` seguem verdes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(domain): group duplicate activities into chains`

---

### T14: `merge_process` (mesclagem do processo)

**Status**: Done

**What**: Mescla as duplicadas do processo: fica a validada mais antiga, ou a mais antiga se nenhuma ou todas estão validadas; as provas passam para a mantida; auditoria `MERGE`; idempotente e atômica.
**Where**: `backend/app/application/services/activity_merge.py` (novo)
**Depends on**: T12, T13
**Reuses**: `duplicate_groups` (T13), `uow.activities`, `uow.evidences`, `AuditService`
**Requirement**: DUP-01, DUP-02, DUP-03, DUP-05, DUP-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/integration/doc_usecases/test_activity_merge.py`: duas duplicadas viram uma com as provas das duas e sem par documento e página repetido; fica a validada mesmo se a outra é mais antiga; com as duas validadas ou nenhuma fica a mais antiga; cadeia de três vira uma; a mesclada permanece no banco com `merged_into_id` e um evento de auditoria com os dois ids; repetir não muda nada; uma falha no meio (repositório forçado a falhar) não deixa atividade nem prova alterada; processo somente leitura não é alterado
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): merge duplicate activities of a process`

---

### T15: `separate` ("Não é duplicada")

**Status**: Done

**What**: Restaura a atividade mesclada, devolve as provas que vieram dela e marca as duas como distintas.
**Where**: `backend/app/application/services/activity_merge.py` (modify)
**Depends on**: T14
**Reuses**: `MarkActivitiesDistinct`, `distinct_justification`
**Requirement**: DUP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Testes primeiro em `backend/tests/integration/doc_usecases/test_activity_separate.py`: depois de `separate` a atividade volta às listas, suas provas voltam, as duas ficam como distintas e `merge_process` não as mescla de novo; só uma atividade mesclada pode ser separada (outra → 422); auditoria do evento; versão desatualizada → 409
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): separate a merged activity back into two`

---

### T16: Rotas de mesclagem e de separação

**What**: `POST /api/processes/{id}/activities/merge-duplicates` → `{merged: n}` e `POST /api/activities/{id}/separate` → a atividade; o modelo de resposta `MergeOut` fica no módulo de esquemas de atividade.
**Where**: `backend/app/presentation/api/activities.py` (modify)
**Depends on**: T15
**Reuses**: `validate_batch` e `mark_distinct` como modelo de rota; `container.py`
**Requirement**: DUP-04, DUP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/api/test_activity_merge_api.py`: `merge-duplicates` devolve o número de mesclagens e uma segunda chamada devolve 0; processo somente leitura devolve 0 sem alterar; processo de outro usuário → 404; sem CSRF → 403; `separate` devolve a atividade restaurada, 422 numa atividade não mesclada, 404 fora do acesso
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): add the merge-duplicates and separate routes`

---

### T17: Validar exige categoria e atividade válida

**What**: `ChangeActivityStatus` recusa `VALIDADA` sem categoria (422 no campo `categoria`) e para atividade não válida (422 `ATIVIDADE_NAO_VALIDA` no campo `status`); rejeitar e reabrir seguem livres.
**Where**: `backend/app/application/use_cases/scoring.py` (modify)
**Depends on**: T5
**Reuses**: `classify_activity` (T1), `ValidationFailed`
**Requirement**: VAL-03, VAL-05, VAL-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/api/test_activity_validate_rules_api.py`: sem categoria → 422 com campo `categoria` e a mensagem "Escolha a categoria antes de validar" e a atividade intacta; atividade fora do interstício → 422 `ATIVIDADE_NAO_VALIDA`; atividade com categoria dentro do interstício → 200 e a auditoria do status gravada sem justificativa; rejeitar e reabrir uma atividade sem categoria funcionam
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam; os de `test_activities_api.py` que validavam sem categoria ajustados com anotação VAL-03

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): require a category and a valid activity to validate`

---

### T18: Validação em lote com `skipped`

**What**: `BulkValidateActivities` valida as que podem e devolve `skipped` com o motivo das que ficaram de fora; versão alterada (409) e atividade de outro processo (404) continuam derrubando tudo.
**Where**: `backend/app/application/use_cases/scoring.py` (modify)
**Depends on**: T17
**Reuses**: `classify_activity`, a regra de T17
**Requirement**: VAL-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/test_bulk_validate_skipped.py`: um lote com 3 atividades com categoria e 2 sem valida as 3 e devolve as 2 em `skipped` com o motivo `SEM_CATEGORIA`; uma não válida entra em `skipped` com o motivo da validade; um 409 de versão alterada não valida nenhuma; "Validar as confiáveis" (mesma rota) segue a regra
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): validate in batch and list what was skipped`

---

### T19: Rota do lote devolve `{activities, skipped}`

**What**: A rota `POST /api/processes/{id}/activities/validate` passa a responder `{activities, skipped}`; o modelo de resposta acompanha, no módulo de esquemas de atividade.
**Where**: `backend/app/presentation/api/activities.py` (modify)
**Depends on**: T18
**Reuses**: `validate_batch`, `ActivityOut`
**Requirement**: VAL-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/api/test_bulk_validate_api.py` (ajustado): o corpo novo traz `activities` e `skipped: [{id, reason}]`; o código 409 e o 404 seguem; sem CSRF → 403
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes de `test_bulk_validate_api.py` ajustados mantêm a cobertura

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): return the skipped activities from the batch validation`

---

### T20: Data dentro do interstício e quantidade válida na edição

**What**: A criação manual e `UpdateActivity` recusam data fora do interstício (422 no campo da data, com a faixa na mensagem); nas categorias por ano o período só precisa tocar o interstício; a criação a partir de documento não passa por essa checagem.
**Where**: `backend/app/application/use_cases/scoring.py` (modify)
**Depends on**: T19
**Reuses**: `evaluate_period`, `is_yearly_unit`, `ValidationFailed`, `_validate_basics`
**Requirement**: EDT-02, EDT-03, EDT-06, QTD-02, QTD-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/api/test_activity_edit_rules_api.py`: data de 2023 num processo de 2024 a 2026 → 422 em `event_date` com "A data deve estar entre dd/mm/aaaa e dd/mm/aaaa" e a atividade intacta; o primeiro e o último dia passam; categoria por ano cujo período cruza o interstício passa e o que não o toca → 422 em `period_start`/`period_end`; criação manual fora → 422; a criação a partir de documento (`source` `SUGERIDA_IA`) fora do interstício é aceita (nasce e fica não válida); quantidade negativa ou não numérica → 422 em `quantidade`; mudar a quantidade recalcula a pontuação e grava a auditoria sem justificativa; editar sem alterar a data de uma atividade já fora do interstício é recusado só se o corpo trouxer essa data
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam; os existentes que criavam atividades manuais com datas fora do interstício ajustados com anotação EDT-02

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): require the activity date inside the interstice on manual edits`

---

### T21: Criar e editar atividade mesclam as duplicadas

**What**: `CreateActivity` e `UpdateActivity` chamam `merge_process` depois de gravar, na mesma unidade de trabalho.
**Where**: `backend/app/application/use_cases/scoring.py` (modify)
**Depends on**: T14, T20
**Reuses**: `merge_process` (T14)
**Requirement**: DUP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/api/test_activity_merge_on_write_api.py`: criar uma atividade igual a outra mescla na hora e a lista mostra uma só com as duas provas; editar o título para igualar a outra mescla; editar até deixar de ser duplicada não desfaz a mesclagem; uma falha da mesclagem reverte também a criação
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): merge duplicates when an activity is created or edited`

---

### T22: A leitura de documentos mescla as duplicadas

**What**: `ProcessDocument` chama `merge_process` ao fim da leitura e do reprocessamento; a atividade criada de documento fora do interstício nasce e aparece como não válida.
**Where**: `backend/app/application/use_cases/document_processing.py` (modify)
**Depends on**: T21
**Reuses**: `merge_process` (T14), `ProcessDocument._store`
**Requirement**: DUP-04, SEC-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/doc_usecases/test_document_merge.py`: dois documentos que levam à mesma atividade resultam em uma só com as duas provas; reprocessar um documento que passa a duplicar mescla; uma atividade lida com data fora do interstício é criada (sem erro) e a validade a classifica como `FORA_DO_INTERSTICIO`; uma falha da mesclagem não perde a leitura do documento (o documento fica em erro tratável, sem atividade pela metade)
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam; os de `inteligencia-documental` seguem verdes

**Tests**: integration
**Gate**: full

**Commit**: `feat(documents): merge duplicate activities after reading a document`

---

### T23: Candidatos carregados em lote

**What**: `list_for_process` carrega os candidatos de todas as atividades numa consulta só, em vez de uma por atividade.
**Where**: `backend/app/infrastructure/database/repositories.py` (modify)
**Depends on**: T12
**Reuses**: `SqlActivityRepository._to_entity`
**Requirement**: SEC-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste primeiro em `backend/tests/integration/test_repositories_activity_queries.py`: listar 300 atividades com candidatos executa um número de consultas que não cresce com o número de atividades (contado com o evento do SQLAlchemy); os candidatos continuam na mesma ordem
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `perf(db): load the candidates of the activities in one query`

---

### T24: Esquema `ActivityOut` com validade, mescladas e pontos previstos

**What**: `ActivityOut` ganha `validity`, `merged` (`[{id, title}]`) e `predicted_points`; `ValidityOut` espelha o domínio.
**Where**: `backend/app/presentation/schemas/activities.py` (modify)
**Depends on**: T23
**Reuses**: `Validity` (T1), `Money`
**Requirement**: SEC-01, SEC-07, DUP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/unit/presentation/test_activity_schema.py`: a serialização traz `validity.state/reason/needs_category/params` com datas e horas em texto, `merged` e `predicted_points` (nulo quando não há previsão); campos extras seguem recusados; nenhum dado pessoal novo
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(api): add validity, merged activities and predicted points to the activity schema`

---

### T25: `ListActivities` devolve a validade

**What**: O caso de uso devolve cada atividade com a validade, as mescladas nela e os pontos previstos (da linha de cálculo, sem exigir validação); as mescladas não aparecem como linhas.
**Where**: `backend/app/application/use_cases/scoring.py` (modify)
**Depends on**: T24, T22
**Reuses**: `compute_process_score`, `ScoringResult.validity`, `list_merged_into`
**Requirement**: SEC-02, SEC-06, SEC-07, SEC-08, SEC-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/test_list_activities_validity.py`: cada motivo (rejeitada, fora do interstício, carga insuficiente) sai com `reason` e `params` corretos; sem categoria sai `VALIDA` com `needs_category`; `predicted_points` traz o valor previsto para atividade aguardando validação com categoria e nulo sem categoria; as mescladas ficam fora da lista e a mantida traz `merged`; ao corrigir uma atividade não válida, a listagem seguinte a traz como válida; reabrir uma rejeitada a devolve a `AGUARDANDO_REVISAO` e válida; sem tabela escolhida a validade sai sem carga horária e sem grupo
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): list activities with their validity and predicted points`

---

### T26: Rota da lista com os campos novos

**What**: `GET /api/processes/{id}/activities` e `GET /api/activities/{id}` montam `ActivityOut` com a validade, as mescladas e os pontos previstos.
**Where**: `backend/app/presentation/api/activities.py` (modify)
**Depends on**: T25
**Reuses**: `_present` e `ListActivities`
**Requirement**: SEC-02, SEC-06, SEC-08, SEG-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/api/test_activities_validity_api.py`: a lista de um processo com 120 atividades devolve todas, com a validade; uma mesclada não aparece e a mantida lista `merged`; `GET /api/activities/{id}` traz os mesmos campos; processo fora do acesso → 404; o fluxo da Etapa 4 (validar e pontuar) segue verde
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: os testes novos passam; `test_activities_api.py` ajustado só onde o corpo ganhou campos

**Tests**: integration
**Gate**: full

**Commit**: `feat(api): serve validity, merged and predicted points on the activity routes`

---

### T27: Tipos do frontend

**What**: `Validity`, `InvalidReason`, `MergedRef`, `BulkValidateResult` e os campos novos de `Activity` em `types.ts`.
**Where**: `frontend/src/api/types.ts` (modify)
**Depends on**: T26
**Reuses**: os tipos de `Activity` e `ScoringAlert` existentes
**Requirement**: SEC-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Tipos exportados conforme o Design (`state`, `reason`, `needs_category`, `params`), `GenerationCode` com `ATIVIDADE_SEM_CATEGORIA` e `ScoringAlertCode` com `QUANTIDADE_ASSUMIDA`
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: nenhum teste apagado

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): type the activity validity`

---

### T28: Rótulos dos motivos, selos e mensagens

**What**: Textos em `labels.ts`: motivos de não válida, selos "Precisa de categoria" e "Aguardando validação", mensagem do bloqueio, mensagem do alerta `QUANTIDADE_ASSUMIDA` e a recusa `ATIVIDADE_SEM_CATEGORIA`.
**Where**: `frontend/src/labels.ts` (modify)
**Depends on**: T27
**Reuses**: `GENERATION_CODE_LABELS`, `SCORING_ALERT_LABELS`
**Requirement**: SEC-07, VAL-02, SEG-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/labels.test.ts`: o texto de cada motivo bate com a spec ("Fora do interstício: data dd/mm/aaaa; interstício dd/mm/aaaa a dd/mm/aaaa", "Carga horária insuficiente: N h; o item exige M h", "Rejeitada por você"); cada código de `GenerationCode` e de `ScoringAlertCode` tem rótulo
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the labels of the validity reasons`

---

### T29: `ReasonText`

**What**: Componente que escreve o motivo de uma atividade não válida a partir de `validity.params`.
**Where**: `frontend/src/components/ReasonText.tsx` (novo)
**Depends on**: T28
**Reuses**: `formatDate` e os rótulos de T28
**Requirement**: SEC-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ReasonText.test.tsx`: cada motivo gera o texto exato da spec com as datas e horas dos parâmetros; período por ano usa início e fim; o motivo não depende só de cor (o texto está presente)
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): show why an activity is not valid`

---

### T30: `CategoryPicker`

**What**: Seletor de categoria com grupos e itens, usado na linha e no formulário.
**Where**: `frontend/src/components/CategoryPicker.tsx` (novo)
**Depends on**: T28
**Reuses**: a lista de critérios da tabela escolhida e o seletor de `ActivityReviewList`
**Requirement**: SEC-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/CategoryPicker.test.tsx`: lista os itens por grupo; escolher chama `onChange` na hora, sem justificativa; rótulo acessível; operável por teclado; sem tabela escolhida mostra a mensagem de escolher a tabela
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the category picker`

---

### T31: `ActivityFilters`

**What**: Busca por título, chips de situação com contagem (todas, aguardando validação, validadas, precisa de categoria) e filtro por grupo.
**Where**: `frontend/src/components/ActivityFilters.tsx` (novo)
**Depends on**: T28
**Reuses**: o padrão de chips de `DocumentList`
**Requirement**: SEC-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ActivityFilters.test.tsx`: cada chip mostra a contagem recebida; clicar marca `aria-pressed` e chama `onChange`; a busca chama `onChange` com o texto; o filtro por grupo lista só os grupos presentes; limpar volta ao padrão
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the activity filters`

---

### T32: `MergedNote`

**What**: Texto "N duplicadas mescladas" com o botão "Não é duplicada" por mesclada.
**Where**: `frontend/src/components/MergedNote.tsx` (novo)
**Depends on**: T28
**Reuses**: `Modal` (confirmação não é necessária: age na hora)
**Requirement**: DUP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/MergedNote.test.tsx`: mostra "1 duplicada mesclada" e "2 duplicadas mescladas" com os títulos; "Não é duplicada" chama `POST /api/activities/{id}/separate` e avisa o pai; erro 409/422 mostra a mensagem; sem mescladas não renderiza nada
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): show the merged duplicates of an activity`

---

### T33: `ActivityRow`

**What**: Linha responsiva da atividade: título, data, categoria, pontos previstos, selos e ações (Validar só na válida; Editar; Rejeitar; Reabrir; Vincular).
**Where**: `frontend/src/components/ActivityRow.tsx` (novo)
**Depends on**: T29, T30, T32
**Reuses**: `CategoryPicker`, `ReasonText`, `MergedNote`, as ações de `ActivityReviewList`
**Requirement**: VAL-06, SEC-04, SEC-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ActivityRow.test.tsx`: atividade válida com categoria mostra Validar; sem categoria mostra o selo "Precisa de categoria" com o seletor e sem Validar; não válida não mostra Validar e mostra o motivo; rejeitada mostra Reabrir; os pontos previstos aparecem; os selos têm texto; os botões têm nome acessível e a linha cabe em 360 px (classe responsiva sem largura fixa)
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the activity row with badges and actions`

---

### T34: Seção "Atividades válidas"

**What**: Seção com filtros, 25 por vez com "Mostrar mais", seleção, "Validar selecionadas", "Validar as confiáveis" (com a lista das puladas) e vínculo de documento.
**Where**: `frontend/src/components/ValidActivitiesSection.tsx` (novo)
**Depends on**: T31, T33
**Reuses**: `ActivityRow`, `ActivityFilters`, o lote de `ActivityReviewList`
**Requirement**: SEC-02, SEC-03, SEC-05, SEC-11, VAL-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ValidActivitiesSection.test.tsx`: com 120 atividades mostra 25 e "Mostrar mais" mostra mais 25; os chips contam sobre a lista inteira; a busca e o filtro por grupo funcionam; o título traz o total; "Nenhuma atividade válida ainda" quando vazia; validar em lote chama a rota e mostra "12 validadas; 3 ficaram sem categoria" com a lista; "N atividades precisam de categoria" aparece quando há selo
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the valid activities section`

---

### T35: Seção "Atividades não válidas"

**What**: Seção fechada ao abrir, com `aria-expanded`, total e contagem por motivo no título; cada linha com o motivo e Editar (e Reabrir nas rejeitadas).
**Where**: `frontend/src/components/InvalidActivitiesSection.tsx` (novo)
**Depends on**: T33
**Reuses**: `ActivityRow`, `ReasonText`
**Requirement**: SEC-06, SEC-07, SEC-09, SEC-10, SEC-11, SEC-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/InvalidActivitiesSection.test.tsx`: abre fechada; o botão alterna `aria-expanded` e é focável por teclado; o título mostra o total e a contagem por motivo; as linhas mostram o motivo em texto; Editar e Reabrir chamam os callbacks; "Nenhuma atividade não válida" quando vazia; 25 por vez com "Mostrar mais"
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the not valid activities section`

---

### T36: `ActivityWorkspace`

**What**: Monta as duas seções, divide a lista pela validade e move a atividade de seção quando a edição ou a reabertura muda a validade, sem recarregar a página.
**Where**: `frontend/src/components/ActivityWorkspace.tsx` (novo)
**Depends on**: T34, T35
**Reuses**: `ValidActivitiesSection`, `InvalidActivitiesSection`, `ActivityForm`, `activityBody`
**Requirement**: SEC-01, SEC-08, SEC-09, SEC-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ActivityWorkspace.test.tsx`: as duas seções com o total no título; editar a data de uma não válida para dentro do interstício a move para as válidas; reabrir uma rejeitada a move; uma mesclada não aparece; o layout não força rolagem horizontal em 360 px (sem largura mínima fixa); os títulos das seções são navegáveis por teclado
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): compose the two sections of the activity review`

---

### T37: `StepNav` com `blocked`

**What**: `StepNav` ganha `blocked` (passo e mensagem) e desabilita o avanço para a Etapa 4 e as seguintes enquanto bloqueado.
**Where**: `frontend/src/components/StepNav.tsx` (modify)
**Depends on**: T28
**Reuses**: `enabled` e `current` existentes
**Requirement**: SEC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/StepNav.test.tsx`: com `blocked` as etapas 4 e seguintes ficam desabilitadas com `aria-disabled` e a mensagem "N atividades precisam de categoria"; sem `blocked` o comportamento atual não muda; as etapas anteriores seguem ativas
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam; os existentes seguem

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): block the next steps while activities lack a category`

---

### T38: A página da Etapa 3 usa a nova tela

**What**: `ProcessActivities` chama `merge-duplicates` uma vez ao abrir, carrega a lista e mostra o `ActivityWorkspace`; o avanço fica bloqueado com atividade válida sem categoria.
**Where**: `frontend/src/pages/ProcessActivities.tsx` (modify)
**Depends on**: T36, T37
**Reuses**: `ActivityWorkspace`, `StepNav` com `blocked`, `usePolling`
**Requirement**: SEC-01, SEC-05, DUP-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/pages/ProcessActivities.test.tsx`: abrir a página chama `merge-duplicates` uma vez (não em recarga por validar) e depois a lista; com 3 atividades sem categoria o avanço para a Etapa 4 fica bloqueado com "3 atividades precisam de categoria"; escolher a categoria na linha libera o avanço sem recarregar; processo somente leitura não chama a mesclagem; a falha da mesclagem não impede carregar a lista
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): open the activity review with merging and the category gate`

---

### T39: Remover `ActivityReviewList`

**What**: Remove o componente antigo e o teste dele depois de conferir que cada comportamento foi portado.
**Where**: `frontend/src/components/ActivityReviewList.tsx` (remover)
**Depends on**: T38
**Reuses**: a lista dos 22 testes de `ActivityReviewList.test.tsx` como roteiro de cobertura
**Requirement**: SEC-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Uma tabela no corpo do commit mapeia cada um dos 22 testes antigos ao teste novo que cobre o comportamento (seleção, validar em lote, validar as confiáveis, vincular documento, rejeitar, reabrir, selo de revisão, filtros), ou à decisão da spec que o aposentou
- [ ] `ActivityReviewList.tsx` e `.test.tsx` removidos; nenhum import restante
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: o total cai só pelos 22 testes mapeados

**Tests**: none
**Gate**: build

**Commit**: `refactor(frontend): remove the single-table activity review list`

---

### T40: Formulário de edição enxuto

**What**: `ActivityForm` mostra Título, Data (ou Início e Fim nas categorias por ano), Categoria e Horas só quando a categoria tem carga mínima; nova atividade acrescenta Quantidade; oferta do Grupo I mostra só Título e Categoria; sem campo de comprovante.
**Where**: `frontend/src/components/ActivityForm.tsx` (modify)
**Depends on**: T30, T39
**Reuses**: `CategoryPicker`, `activityBody` (continua mandando o corpo completo)
**Requirement**: EDT-01, EDT-04, EDT-05, EDT-06, EDT-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ActivityForm.test.tsx`: os campos exibidos para cada caso (categoria comum, por ano, com carga mínima, Grupo I, nova manual); salvar manda o corpo completo e mantém Quantidade, Horas, descrição e pontos que não foram editados; salvar aplica na hora, sem campo de justificativa; nenhum campo de texto de comprovante
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes antigos de campos removidos substituídos por testes dos campos novos, contagem registrada

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): simplify the activity edit form`

---

### T41: Erros de data no formulário

**What**: O erro 422 de data fora do interstício aparece no campo da data com a faixa, e o formulário mantém o que o usuário digitou.
**Where**: `frontend/src/components/ActivityForm.tsx` (modify)
**Depends on**: T40
**Reuses**: `FieldError`, `ApiError.body`
**Requirement**: EDT-02, EDT-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ActivityForm.test.tsx`: 422 em `event_date` mostra "A data deve estar entre dd/mm/aaaa e dd/mm/aaaa" no campo; 422 em `period_start` ou `period_end` mostra no campo do período; o formulário não fecha e os valores seguem; 409 mostra a mensagem de versão alterada
- [ ] Gate check passes: `cd frontend && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): show the interstice date errors on the form`

---

### T42: Quantidade, horas e valor manual na Etapa 4

**What**: `ScoreEditor` oferece Quantidade (ou Horas nos itens medidos por horas) e o valor unitário manual, e mostra o erro 422 de `quantidade`.
**Where**: `frontend/src/components/ScoreEditor.tsx` (modify)
**Depends on**: T39
**Reuses**: `FieldError`, a chamada de edição de `ProcessScoring`
**Requirement**: QTD-01, QTD-02, QTD-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ScoreEditor.test.tsx`: item por unidade mostra Quantidade; item por horas mostra Horas; o valor unitário manual segue; salvar manda o corpo completo e recarrega o total; quantidade negativa mostra o erro do campo vindo do 422; sem campo de justificativa
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: os testes novos passam

**Tests**: unit
**Gate**: build

**Commit**: `feat(frontend): edit quantity and hours in the score editor`

---

### T43: Documentação da feature

**What**: AD-022 em `STATE.md` (coluna `merged_into_id`, validade no servidor, mesclagem na escrita), regra 10 em `CLAUDE.md` e rastreabilidade da spec marcada como `Implemented`.
**Where**: `.specs/STATE.md` (modify)
**Depends on**: T42
**Reuses**: AD-018 como modelo; o texto do Design
**Requirement**: DUP-02, SEG-01, VAL-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] AD-022 escrito em `STATE.md`; `CLAUDE.md` ganha a regra 10 (só as atividades válidas seguem; duplicadas mescladas; validar pontua); `spec.md` e `design.md` com o status atualizado; os 40 requisitos mapeados a tarefas
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py revisao-simplificada` sem erro
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem final registrada

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): record the simplified activity review decision`

---

### T44: Verificador independente

**What**: Agente diferente do autor confere os 40 requisitos com evidência (testes e leitura do código) e injeta mutantes (esquecer de excluir a não válida da Tabela, aceitar validar sem categoria, mesclar sem mover as provas, aplicar a checagem de data à leitura de documentos, não reverter a mesclagem que falha, paginar errado); escreve o relatório.
**Where**: `.specs/features/revisao-simplificada/validation.md` (novo)
**Depends on**: T43
**Reuses**: `references/validate.md` e `sub-agents.md` do skill; `validate_state.py`
**Requirement**: VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-07, SEC-08, SEC-09, SEC-10, SEC-11, SEC-12, DUP-01, DUP-02, DUP-03, DUP-04, DUP-05, DUP-06, DUP-07, SEG-01, SEG-02, SEG-03, SEG-04, SEG-05, EDT-01, EDT-02, EDT-03, EDT-04, EDT-05, EDT-06, EDT-07, QTD-01, QTD-02, QTD-03

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] `validation.md` com o veredito PASS, a evidência `arquivo:linha` por requisito, o resultado do sensor de mutação e o intervalo de commits
- [ ] Mutantes sobreviventes e lacunas viram tarefas de correção; o ciclo corrigir e reverificar tem no máximo 3 voltas
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_state.py revisao-simplificada` sem erro
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem final registrada

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): verify the simplified activity review`

---

## Requirement coverage

| Requisito | Tarefas | Requisito | Tarefas |
| --- | --- | --- | --- |
| VAL-01 | T2, T5 | SEC-12 | T33, T35, T36 |
| VAL-02 | T3, T4, T28 | DUP-01 | T13, T14 |
| VAL-03 | T17 | DUP-02 | T9, T10, T11, T12, T14 |
| VAL-04 | T18, T19, T34 | DUP-03 | T10, T12, T14 |
| VAL-05 | T17 | DUP-04 | T16, T21, T22, T38 |
| VAL-06 | T1, T17, T33, T34 | DUP-05 | T14 |
| SEC-01 | T23, T24, T27, T36, T38, T39 | DUP-06 | T14 |
| SEC-02 | T1, T25, T26, T34 | DUP-07 | T15, T16, T24, T32 |
| SEC-03 | T31, T34 | SEG-01 | T1, T2, T5, T6, T8 |
| SEC-04 | T30, T33 | SEG-02 | T6, T8 |
| SEC-05 | T34, T37, T38 | SEG-03 | T2, T6, T8, T26 |
| SEC-06 | T1, T22, T25, T35 | SEG-04 | T2, T5 |
| SEC-07 | T1, T24, T25, T28, T29, T35 | SEG-05 | T7, T8, T28 |
| SEC-08 | T25, T26, T36 | EDT-01 | T40 |
| SEC-09 | T25, T35, T36 | EDT-02 | T20, T41 |
| SEC-10 | T35 | EDT-03 | T20, T41 |
| SEC-11 | T34, T35 | EDT-04 | T40 |
| QTD-01 | T42 | EDT-05 | T40 |
| QTD-02 | T20, T42 | EDT-06 | T20, T40 |
| QTD-03 | T20, T42 | EDT-07 | T40 |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Domain rules | unit | unit | ✅ OK |
| T2 | Domain rules | unit | unit | ✅ OK |
| T3 | Domain rules | unit | unit | ✅ OK |
| T4 | Domain rules | unit | unit | ✅ OK |
| T5 | Use cases | integration | integration | ✅ OK |
| T6 | Domain rules | unit | unit | ✅ OK |
| T7 | Types | none | none | ✅ OK |
| T8 | Services | integration | integration | ✅ OK |
| T9 | Migration | integration | integration | ✅ OK |
| T10 | Domain entity | unit | unit | ✅ OK |
| T11 | Ports | none | none | ✅ OK |
| T12 | Repositories | integration | integration | ✅ OK |
| T13 | Domain rules | unit | unit | ✅ OK |
| T14 | Services | integration | integration | ✅ OK |
| T15 | Services | integration | integration | ✅ OK |
| T16 | API routes and schemas | integration | integration | ✅ OK |
| T17 | Use cases | integration | integration | ✅ OK |
| T18 | Use cases | integration | integration | ✅ OK |
| T19 | API routes and schemas | integration | integration | ✅ OK |
| T20 | Use cases | integration | integration | ✅ OK |
| T21 | Use cases | integration | integration | ✅ OK |
| T22 | Use cases | integration | integration | ✅ OK |
| T23 | Repositories | integration | integration | ✅ OK |
| T24 | API schemas | unit | unit | ✅ OK |
| T25 | Use cases | integration | integration | ✅ OK |
| T26 | API routes | integration | integration | ✅ OK |
| T27 | Types | none | none | ✅ OK |
| T28 | Labels | unit | unit | ✅ OK |
| T29-T38 | Frontend components/pages | unit | unit | ✅ OK |
| T39 | Removal of a component | none (build gate) | none | ✅ OK |
| T40-T42 | Frontend components | unit | unit | ✅ OK |
| T43, T44 | Docs | none | none | ✅ OK |
