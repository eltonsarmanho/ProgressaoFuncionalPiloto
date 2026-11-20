# Correções da auditoria de requisitos Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: sem `design.md` (Design pulado: nenhuma decisão de arquitetura nova; a rota de status, o caso de uso de edição e o motor já existem; as escolhas de comportamento estão nas Assumptions da spec)
**Spec**: `.specs/features/correcoes-auditoria/spec.md`
**Status**: Approved (usuário, 2026-11-20: "aprovado com as recomendações")

Regras de execução desta feature: cada tarefa com código escreve primeiro os testes que derivam dos critérios de aceitação da spec e só então o código (os itens `Done when` começam pelo teste); só dados sintéticos; `Documentos/`, `Modelos/`, `requeriment.txt`, `test/` e `corpus-reports/` nunca são abertos; um commit por tarefa (Conventional Commits, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, como manda o `CLAUDE.md`), marcando a tarefa neste arquivo e a rastreabilidade da spec no mesmo commit; sem push, deploy nem acesso à VM sem autorização explícita. Nenhum arquivo escrito por estas tarefas contém a sigla que a CAREF-05 proíbe: quando o texto precisar falar do caso, diga "item de valor informado de tabelas antigas, inexistente na tabela oficial". Sem migração.

---

## Test Coverage Matrix

> Generated from project guidelines, spec and the existing suites. Guidelines found: `CLAUDE.md` (regras de negócio, gate, dados sintéticos, regra 11 sobre tabelas de teste), AD-001 (teste de arquitetura), AD-004 (integração em PostgreSQL real). Existing tests sampled: `backend/tests/integration/api/test_process_updates_api.py`, `backend/tests/integration/scoring/test_activity_create.py`, `test_activity_update.py`, `test_process_score.py`, `backend/tests/unit/domain/test_scoring_engine.py`, `frontend/src/pages/Dashboard.test.tsx`, `ProcessStep1.test.tsx`, `ProcessGenerated.test.tsx`, `frontend/src/components/ScoreEditor.test.tsx`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain (rules, engine) | unit | All branches touched; 1:1 to spec ACs (CAREF-02) | `backend/tests/unit/domain/test_*.py` | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` |
| Use cases (activities, processes) | integration | Happy + every listed edge case + error paths (422 por campo, 404, 409); auditoria do valor anterior | `backend/tests/integration/scoring/test_*.py` | `cd backend && .venv/bin/pytest tests/integration/scoring -q` |
| API routes and schemas | integration | Rotas tocadas: happy + edge + erro (404, 409, 422), com o corpo que o frontend envia | `backend/tests/integration/api/test_*.py` | `cd backend && .venv/bin/pytest tests/integration/api -q` |
| Test support (tabelas sintéticas) | integration | Os testes que as usam passam com os nomes e o critério novos | `backend/tests/support/*.py` | `cd backend && .venv/bin/pytest tests/integration -q` |
| Frontend components/pages | unit | Cada CAINI e CATXT-01: render, interação, chamada da API simulada com o corpo exato, mensagem de erro em `role="alert"` | `frontend/src/**/*.test.tsx` | `cd frontend && npm test -- --run` |
| Docs (`.specs/`, `CLAUDE.md`, `docs/`) | none | O `grep` e a conferência citados no `Done when`; `validate_spec.py` quando a spec muda | - | gate quick (sem mudança de código) |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Tarefas só com teste unitário ou só de documentação | `cd backend && .venv/bin/pytest tests/unit tests/architecture -q` (frontend: `cd frontend && npm test -- --run`) |
| Full | Tarefas com teste de integração | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` |
| Frontend | Tarefas de frontend | `cd frontend && npm run lint && npm run build && npm test -- --run` |
| Build | Fim de fase e Verifier | `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order. A tarefa que depende de fase anterior lista a dependência em `Depends on`, e o diagrama da fase mostra essa aresta de entrada com a fase de origem anotada.

### Phase 1: Iniciar o processo

```
T1
T2 → T3
T2 → T5
T4
```

### Phase 2: Grupo I, textos e edição de atividade

```
T6 → T8 → T9 → T11
T7
T10
```

### Phase 3: Nomes de teste

```
T7 → T12        (origem na Fase 2)
T13
```

### Phase 4: Remoção da sigla nos documentos

```
T14
T15
T16
T17
T18
```

### Phase 5: Documentação de estado

```
T19 → T25
T20 → T25
T21 → T25
T22 → T25
T23 → T25
T24 → T25
T25 → T26
```

### Phase 6: Verificação independente

```
T26 → T27       (origem na Fase 5)
```

---

## Task Breakdown

### T1: Caracterização da transição de rascunho para em andamento

**Status**: Done

**What**: Testes de API que fixam o que o servidor já faz ao iniciar: DOCENTE vinculado e ADMIN iniciam sem justificativa (200, versão + 1, evento `STATUS` com justificativa vazia); SECRETARIA de outra unidade e DOCENTE de outro docente recebem 404 e o processo não muda. Sem mudança de código de produção (se algum teste falhar, PARE e registre: a spec assume que o backend já aceita).
**Where**: `backend/tests/integration/api/test_process_updates_api.py` (modify)
**Depends on**: None
**Reuses**: `set_status` (`test_process_updates_api.py:40`), `act_as`, `test_status_follows_rascunho_em_andamento_concluido` (`:131`), `test_history_and_updates_of_unreadable_process_return_404` (`:231`)
**Requirement**: CAINI-08, CAINI-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Teste: DOCENTE vinculado envia `{"status": "EM_ANDAMENTO", "expected_version": 1}` sem `justificativa` → 200, `status == "EM_ANDAMENTO"`, `version == 2`, e o último evento de auditoria do processo é `STATUS` com `{"status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"}}` e justificativa `None`
- [x] Teste: ADMIN faz o mesmo → 200 e `version == 2`
- [x] Teste: SECRETARIA de outra unidade e DOCENTE de outro docente → 404, e um `GET` do dono mostra `RASCUNHO` e `version == 1`
- [x] Nenhum arquivo de `backend/app/` muda
- [x] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [x] Test count: contagem antes e depois registrada; só testes novos

**Tests**: integration
**Gate**: full

**Commit**: `test(processes): characterize starting a draft process`

---

### T2: Modal "Iniciar processo"

**Status**: Pending

**What**: Componente `StartProcessDialog` (props: `processId`, `version`, `onStarted(status, version)`, `onStale()`, `onClose()`) com o título "Iniciar processo", o texto de CAINI-03, os botões "Iniciar" e "Cancelar", sem justificativa; "Iniciar" envia o `POST` de CAINI-04, desabilita o botão enquanto espera, mostra a mensagem do servidor em `role="alert"` em erro e chama `onStale` só em 409.
**Where**: `frontend/src/components/ProcessDialogs.tsx` (modify; os testes ficam no arquivo de teste novo ao lado, citado no Done when)
**Depends on**: None
**Reuses**: `ArchiveProcessDialog` e `isConflict` do mesmo arquivo, `Modal`, `request`, `errorMessage`
**Requirement**: CAINI-03, CAINI-04, CAINI-06, CAINI-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/components/ProcessDialogs.test.tsx` (novo): o modal mostra o título, o texto exato de CAINI-03, "Iniciar" e "Cancelar" e nenhum campo com rótulo de justificativa; "Iniciar" chama `request("POST", "/api/processes/<id>/status", {status: "EM_ANDAMENTO", expected_version: <versão>})` sem a chave `justificativa`; 200 chama `onStarted("EM_ANDAMENTO", <versão devolvida>)`; 409 mostra a mensagem do servidor em `role="alert"` e chama `onStale`; 404 e 422 mostram a mensagem, não chamam `onStale` e deixam "Iniciar" habilitado; "Cancelar" chama `onClose` sem requisição
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem antes e depois registrada; nenhum teste apagado

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): add the start process dialog`

---

### T3: Botão "Iniciar processo" na Etapa 1

**Status**: Pending

**What**: A Etapa 1 mostra "Iniciar processo" ao lado da etiqueta de status só com processo em `RASCUNHO`, abre o `StartProcessDialog`, com 200 troca a etiqueta para "Em andamento", esconde o botão e guarda a versão nova (o próximo "Salvar" a usa) sem tocar nos campos digitados; com 409 recarrega o processo pelo `GET`.
**Where**: `frontend/src/pages/ProcessStep1.tsx` (modify; testes no arquivo de teste da página)
**Depends on**: T2
**Reuses**: `StartProcessDialog` (T2), `STATUS_LABELS`, o carregamento do processo já existente na página
**Requirement**: CAINI-01, CAINI-02, CAINI-05, CAINI-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/pages/ProcessStep1.test.tsx`: com processo `RASCUNHO` o botão aparece; com `EM_ANDAMENTO`, `CONCLUIDO`, `ARQUIVADO` e na criação (sem `id`) não aparece; confirmar com 200 mostra "Em andamento", esconde o botão, e o `PUT` seguinte de "Salvar" leva `expected_version` igual à versão devolvida; um campo digitado antes de iniciar continua com o valor digitado; 409 dispara um novo `GET /api/processes/<id>` e a etiqueta mostra o status devolvido por ele
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem antes e depois registrada; nenhum teste apagado

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): start the process from step 1`

---

### T4: Etapa 5 explica a conclusão de processo em rascunho

**Status**: Pending

**What**: Com processo `RASCUNHO`, a Etapa 5 mostra a seção "Concluir o processo" com o texto "Inicie o processo na Etapa 1 para poder concluir." e o link "Ir para a Etapa 1" para `/processos/{id}`, sem o botão de concluir; `EM_ANDAMENTO` segue como hoje.
**Where**: `frontend/src/pages/ProcessGenerated.tsx` (modify; testes no arquivo de teste da página)
**Depends on**: None
**Reuses**: a seção `conclude-title` existente (`ProcessGenerated.tsx:120-133`), `Link` do roteador
**Requirement**: CAINI-10, CAINI-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/pages/ProcessGenerated.test.tsx`: `RASCUNHO` mostra o título "Concluir o processo", o texto exato, o link com `href` `/processos/<id>` e nenhum botão "Concluir e excluir documentos de entrada"; `EM_ANDAMENTO` mostra o botão e não o texto de rascunho; `CONCLUIDO` e `ARQUIVADO` não mostram nenhum dos dois
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem antes e depois registrada; nenhum teste apagado

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): explain on step 5 that a draft process must be started`

---

### T5: Botão "Iniciar" no Painel

**Status**: Pending

**What**: A linha do Painel com processo `RASCUNHO` ganha o botão "Iniciar" (`aria-label` e `title` "Iniciar processo de {nome}"), que abre o `StartProcessDialog`; com 200 a linha e a contagem por status mudam sem recarregar; com 409 a lista é recarregada.
**Where**: `frontend/src/pages/Dashboard.tsx` (modify; testes no arquivo de teste da página)
**Depends on**: T2
**Reuses**: `StartProcessDialog` (T2), o padrão de `archived` e `load` do próprio Painel
**Requirement**: CAINI-12, CAINI-13, CAINI-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `frontend/src/pages/Dashboard.test.tsx`: o botão aparece só nas linhas `RASCUNHO`, com o `aria-label` exato; confirmar com 200 mostra "Em andamento" na linha e a contagem de "Rascunho" cai 1 e a de "Em andamento" sobe 1 sem novo `GET /api/processes`; 409 mostra a mensagem no modal e faz um novo `GET /api/processes`
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem antes e depois registrada; nenhum teste apagado

**Tests**: unit
**Gate**: quick

**Commit**: `feat(frontend): start a draft process from the dashboard`

---

### T6: Tabelas sintéticas de teste com nome sintético e item de valor informado fora do Grupo I

**Status**: Pending

**What**: Em `scoring_variants.py`, `OTHER_TABLE` passa a "Tabela Sintética Alternativa de Teste" e `POINTS_TABLE` a "Tabela Sintética com Grupo I em Pontos"; o critério `VALOR_INFORMADO` deixa o grupo 1 e vai para o grupo 8, com o número seguinte ao último item do grupo 8 da oficial, descrição "Item de valor informado (sintético)" e limite de 10 pontos; o grupo 1 da tabela sintética fica só com os dois critérios de carga semanal. Os testes que usavam o item no grupo 1 passam a usar o item sintético do grupo 8 com a mesma asserção de valor.
**Dependentes** (mudam no mesmo commit, senão o gate quebra): o dicionário `informed` de `:281-300` e o teste de `:325-330` de `backend/tests/integration/scoring/test_activity_create.py` (renomeado para `test_informed_value_item_keeps_informed_points`); `:201-212` de `backend/tests/integration/scoring/test_process_score.py` (o ajuste de limite passa a ser do grupo 8 e a asserção de subtotal vai para `group_subtotals[8]`); a docstring de `backend/tests/integration/api/conftest.py:147`; `OTHER_NAME` em `backend/tests/integration/api/test_scoring_tables_api.py:12`.
**Where**: `backend/tests/support/scoring_variants.py` (modify; os testes dependentes estão listados em Dependentes)
**Depends on**: None
**Reuses**: `_with_criteria`, `add_points_table`, `add_other_table`
**Requirement**: CAREF-02, CAREF-03, CAREF-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes ajustados primeiro: o item sintético grava `informed_points == 8` (grupo 8); `unit_points_override` nele dá 422 em `unit_points_override`; 15 pontos informados viram o ajuste `("ATIVIDADE", 15, 10)` e `group_subtotals[8]` inclui 10; a troca de tabela continua mostrando o II.12 a 10 na tabela sintética alternativa
- [ ] `grep -rnE "\bI\.3\b|student.?evaluation" backend/tests` e `grep -rniE "avalia[cç][aã]o (pelo corpo )?discente" backend/tests/support backend/tests/integration` sem saída
- [ ] `grep -rn "Tabela Alternativa de Teste\|Tabela de Teste com Grupo I" backend/tests` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: igual ao anterior (renomes e ajustes, nenhum teste apagado)

**Tests**: integration
**Gate**: full

**Commit**: `test(scoring): move the synthetic informed value item out of group I`

---

### T7: Item de valor informado sintético fora do Grupo I nos testes do motor

**Status**: Pending

**What**: `test_informed_value_above_the_criterion_cap_is_reported_per_activity` passa a usar um critério `ScoringCriterion(8, <n>, "Item de valor informado (sintético)", "pontos", VALOR_INFORMADO, max_points=10)` num grupo 8, com a atividade em `g=8`; a asserção do ajuste de limite não muda.
**Where**: `backend/tests/unit/domain/test_scoring_engine.py` (modify, `:294-300`)
**Depends on**: None
**Reuses**: `table`, `group`, `act` do próprio arquivo
**Requirement**: CAREF-02, CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O teste usa o grupo 8 e mantém as mesmas asserções de limite (antes 14, depois 10)
- [ ] `grep -niE "avalia[cç][aã]o (pelo corpo )?discente" backend/tests/unit/domain/test_scoring_engine.py` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [ ] Test count: igual ao anterior

**Tests**: unit
**Gate**: quick

**Commit**: `test(scoring): move the engine informed value item out of group I`

---

### T8: O Grupo I sempre exige período letivo, nível e horas

**Status**: Pending

**What**: `_apply_group1` perde o ramo que devolvia a atividade sem checagem quando o critério do grupo 1 era `VALOR_INFORMADO`, e a docstring perde o `SPEC_PRECISION` sobre esse item; o Grupo I sempre exige `AAAA.N`, nível e horas e o item segue o nível.
**Where**: `backend/app/application/use_cases/scoring.py` (modify, `:271-290`)
**Depends on**: T6
**Reuses**: `group1_item`, `ACADEMIC_PERIOD`; tabela sintética montada no teste a partir da oficial com `_with_criteria` (nome com "Sintética")
**Requirement**: CAREF-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/scoring/test_activity_create.py`: numa tabela sintética cujo grupo 1 tem um critério `VALOR_INFORMADO` no item 3, criar atividade `group_number=1, item_number=3, informed_points=8` sem período → 422 em `academic_period`; com período `2023.1` e sem nível → 422 em `level`; com nível e sem horas → 422 em `horas`; com os três (graduação) → `item_number == 1`; o mesmo vale na edição
- [ ] O teste falha antes da mudança e passa depois
- [ ] `grep -nE "VALOR_INFORMADO" backend/app/application/use_cases/scoring.py` não mostra mais a checagem dentro de `_apply_group1`; `grep -niE "student" backend/app/application/use_cases/scoring.py` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: contagem antes e depois registrada

**Tests**: integration
**Gate**: full

**Commit**: `fix(scoring): require period, level and hours for every group I activity`

---

### T9: Mensagens de pontuação manual

**Status**: Pending

**What**: O rótulo de faixa de `points_override` passa a "Pontuação manual" (o de `informed_points` continua "Pontos informados"); a recusa de `points_override` fora de critério de carga semanal passa à mensagem de CATXT-02.
**Where**: `backend/app/application/use_cases/scoring.py` (modify, `:264-265` e `:323-329`)
**Depends on**: T8
**Reuses**: `_range`, `ValidationFailed`
**Requirement**: CATXT-02, CATXT-03, CATXT-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/scoring/test_activity_create.py`: `points_override` num item por unidade da oficial e numa atividade sem item → 422 em `points_override` com a mensagem exata de CATXT-02; `points_override = 10001` → mensagem "Pontuação manual deve estar entre 0 e 10000"; `informed_points = -1` → "Pontos informados deve estar entre 0 e 10000"; `points_override` em item PIT continua com a mensagem das horas de PIT
- [ ] `grep -n "só se aplicam a critérios de carga semanal" backend/app` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: contagem antes e depois registrada

**Tests**: integration
**Gate**: full

**Commit**: `fix(scoring): reword the manual points messages`

---

### T10: Nota do item de valor informado no editor de pontuação

**Status**: Pending

**What**: `noteFor` devolve, para `VALOR_INFORMADO`, "Neste item a pontuação é um valor informado na atividade, não calculado pela tabela: esta tela não o altera."
**Where**: `frontend/src/components/ScoreEditor.tsx` (modify, `:15-17`; teste no arquivo de teste do componente, linha 134)
**Depends on**: None
**Reuses**: o `it.each` de notas já existente em `ScoreEditor.test.tsx`
**Requirement**: CATXT-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Teste primeiro em `frontend/src/components/ScoreEditor.test.tsx`: o caso `VALOR_INFORMADO` espera o texto exato novo, e um teste afirma que nenhum texto do editor contém "lidos do documento"
- [ ] `grep -rn "lidos do documento" frontend/src` sem saída
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem antes e depois registrada

**Tests**: unit
**Gate**: quick

**Commit**: `fix(frontend): stop saying informed points are read from the document`

---

### T11: Editar atividade com pontuação manual gravada que o item não aceita

**Status**: Pending

**What**: `UpdateActivity` passa a `normalize_activity` o `points_override` gravado; quando o corpo reenvia o mesmo valor e o critério não o aceita (PIT, não `CARGA_SEMANAL`, sem item), a atividade é gravada com `points_override` nulo em vez de 422; valor diferente segue recusado; critério que aceita mantém o valor. A auditoria `UPDATE` já guarda antes e depois.
**Where**: `backend/app/application/use_cases/scoring.py` (modify: `UpdateActivity`, `:515-547`, e a checagem de `_check_criterion_inputs`)
**Depends on**: T9
**Reuses**: `activity_audit_view`, `is_pit_criterion`; `pit_world` e `points_chosen` dos `conftest.py` de `tests/integration/scoring`; `points_chosen` de `tests/integration/api/test_activities_api.py`
**Requirement**: CAEDI-01, CAEDI-02, CAEDI-03, CAEDI-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Testes primeiro em `backend/tests/integration/scoring/test_activity_update.py`: atividade da oficial com `points_override = 24` gravado pelo repositório (item por unidade, item PIT e sem item) editada com o mesmo valor → sucesso, `points_override is None`, título novo gravado e o evento `UPDATE` com `points_override` antes `"24"` e depois `None`; reenvio com `25` → 422 em `points_override` e nada gravado; na tabela sintética com Grupo I em pontos (carga semanal não PIT), reenvio igual mantém `24`
- [ ] Teste em `backend/tests/integration/api/test_activities_api.py`: `PUT /api/activities/{id}` com o corpo no formato de `activityBody` (todos os campos, inclusive `informed_points` e `points_override`) e título novo → 200, título novo e `points_override` nulo
- [ ] Os testes falham antes da mudança e passam depois
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: contagem antes e depois registrada

**Tests**: integration
**Gate**: full

**Commit**: `fix(activities): clear a refused stored manual score on edit`

---

### T12: Cenário em miniatura com nome de cenário derivado

**Status**: Pending

**What**: `test_real_case_fasi_2022_2024_in_miniature` passa a `test_derived_scenario_2022_2024_in_miniature_with_a_synthetic_table`, `_fasi_miniature` a `_synthetic_miniature_table`, e o comentário de seção a "cenário derivado em miniatura (CALC-14), tabela sintética"; o total esperado não muda e o comentário diz que ele vem da tabela sintética.
**Where**: `backend/tests/unit/domain/test_scoring_engine.py` (modify, `:522-560`)
**Depends on**: T7
**Reuses**: o próprio teste
**Requirement**: CADOC-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -niE "real[ _]case|caso real" backend/tests/unit/domain/test_scoring_engine.py` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`
- [ ] Test count: igual ao anterior

**Tests**: unit
**Gate**: quick

**Commit**: `test(scoring): name the miniature scenario as derived`

---

### T13: Fixtures `real_case` passam a `derived_case`

**Status**: Pending

**What**: `add_real_case` e a fixture `real_case` passam a `add_derived_case` e `derived_case`, com docstring "cenário derivado de 2022–2024 (sintético), 211 pontos"; os importadores mudam junto; `scenario_211.py` diz "cenário derivado" na docstring.
**Where**: `backend/tests/integration/api/test_scoring_golden.py` (modify; os importadores mudam no mesmo commit: o teste de caracterização e o de aceitação da Tabela gerada, em `backend/tests/integration/api/`, e a docstring do cenário de 211 em `backend/tests/unit/domain/`)
**Depends on**: None
**Reuses**: os próprios testes
**Requirement**: CADOC-04, CADOC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -rniE "real[ _]case|caso real" backend/tests/integration/api/test_scoring_golden.py backend/tests/integration/api/test_scoring_characterization.py backend/tests/integration/api/test_generated_table_acceptance.py` sem saída
- [ ] Toda docstring de teste que cita 211 ou 303 pontos diz "cenário derivado" na mesma frase (`grep -rnE "\b(211|303)\b" backend/tests`)
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q`
- [ ] Test count: igual ao anterior

**Tests**: integration
**Gate**: full

**Commit**: `test(scoring): rename the real case fixtures to the derived case`

---

### T14: Regra 11 do `CLAUDE.md`

**Status**: Pending

**What**: Na regra 11, a frase sobre o Grupo I passa a "O Grupo I tem só os itens I.1 e I.2, em horas de PIT."; o resto da regra não muda.
**Where**: `CLAUDE.md` (modify, linha 23)
**Depends on**: None
**Reuses**: o texto atual da regra
**Requirement**: CAREF-06, CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -n "O Grupo I tem só os itens I.1 e I.2, em horas de PIT." CLAUDE.md` mostra a linha da regra 11
- [ ] `grep -nE "\bI\.3\b" CLAUDE.md` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs: state that group I has only two items in the project rules`

---

### T15: Relatório de auditoria sem a sigla

**Status**: Pending

**What**: O título da seção 3 passa a "Inconsistências (do tipo do item de valor informado de tabelas antigas)"; a linha C3 descreve o achado como "item de valor informado de tabelas antigas, inexistente na tabela oficial, citado como item existente", com os arquivos sem a sigla; a C9 troca a expressão que a CAREF-05 proíbe por "item de valor informado". Nenhum achado muda de sentido.
**Where**: `.specs/audits/2026-11-19-auditoria-requisitos.md` (modify, linhas 42, 48 e 54)
**Depends on**: None
**Reuses**: o texto atual
**Requirement**: CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -nE "\bI\.3\b" .specs/audits/2026-11-19-auditoria-requisitos.md` e `grep -niE "avalia[cç][aã]o (pelo corpo )?discente" .specs/audits/2026-11-19-auditoria-requisitos.md` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(audits): remove the reference to the old informed value item`

---

### T16: Feature `pontuacao` sem a sigla

**Status**: Pending

**What**: Reescreve sem a sigla e sem a expressão que a CAREF-05 proíbe: a linha de Assumptions de `spec.md:48` (passa a dizer que o item de valor informado de tabelas antigas, inexistente na tabela oficial, era exceção do Grupo I até a `correcoes-auditoria`, que a removeu); `tasks.md:422` e `:449`; `validation.md:47` e `:243`. Registro histórico: muda só o texto que nomeia o item.
**Where**: `.specs/features/pontuacao/spec.md` (modify; também os registros de tarefas e de validação da mesma feature, mesmo commit)
**Depends on**: None
**Reuses**: o texto atual
**Requirement**: CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -rnE "\bI\.3\b" .specs/features/pontuacao` e `grep -rniE "avalia[cç][aã]o (pelo corpo )?discente" .specs/features/pontuacao` sem saída
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py pontuacao` sem erro novo
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): remove the old informed value item from the scoring feature`

---

### T17: Design de `grupo-i-no-total` sem a sigla

**Status**: Pending

**What**: As linhas 74, 215, 228 e 307 de `grupo-i-no-total/design.md` dizem "a tabela oficial não tem item de valor informado" (ou "item de valor informado de tabelas antigas, inexistente na tabela oficial") no lugar da sigla; a linha 74 registra que, desde a `correcoes-auditoria`, o grupo 1 só aceita os itens de carga semanal (CAREF-01). Nenhuma decisão do design muda.
**Where**: `.specs/features/grupo-i-no-total/design.md` (modify)
**Depends on**: None
**Reuses**: o texto atual
**Requirement**: CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -nE "\bI\.3\b" .specs/features/grupo-i-no-total/design.md` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): remove the old informed value item from the group I design`

---

### T18: Design da revisão simplificada sem a sigla

**Status**: Pending

**What**: A pergunta "Itens de valor informado" de `revisao-simplificada/design.md:180` deixa de citar a sigla e a expressão que a CAREF-05 proíbe; diz que a tabela oficial não tem item de valor informado e que o item de valor informado de tabelas antigas só existia na tabela antiga do IFCH e no rascunho da FASI.
**Where**: `.specs/features/revisao-simplificada/design.md` (modify, linha 180)
**Depends on**: None
**Reuses**: o texto atual
**Requirement**: CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -nE "\bI\.3\b" .specs/features/revisao-simplificada/design.md` e `grep -niE "avalia[cç][aã]o (pelo corpo )?discente" .specs/features/revisao-simplificada/design.md` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): drop the old informed item from the review design`

---

### T19: Decisões e dívidas do `STATE.md`

**Status**: Pending

**What**: AD-017 e AD-019 ganham a nota de CADOC-02 (a "linha de 0 ponto" foi substituída pela AD-022: rejeitada e fora do interstício vão para as não válidas e não chegam à Etapa 4); a pergunta aberta (1) da AD-022 é reescrita como pede CADOC-11; a dívida "Grupo I do caso real com 16 pontos sem explicação" vira o texto de CADOC-06. O Handoff fica para a T26.
**Where**: `.specs/STATE.md` (modify, seção Decisions e a linha "Dívidas")
**Depends on**: None
**Reuses**: o formato de "Status: superseded in part" da AD-017
**Requirement**: CADOC-02, CADOC-06, CADOC-11, CAREF-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] AD-017 e AD-019 citam a AD-022 na nota; a dívida tem o texto exato de CADOC-06
- [ ] `grep -nE "\bI\.3\b" .specs/STATE.md`, `grep -niE "avalia[cç][aã]o (pelo corpo )?discente" .specs/STATE.md` e `grep -n "16 pontos" .specs/STATE.md` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(state): mark superseded zero point rows and rewrite a debt`

---

### T20: Coluna Quantidade do design da inteligência documental

**Status**: Pending

**What**: Na tabela de taxonomias, IV.1 e IV.2 passam a "1 por ação" (observação "Por ação, qualquer duração"); V.1, VI.10 e VI.12 passam a "anos completos do período no interstício (`QUANTIDADE_ESTIMADA`)", conforme `_PER_YEAR` em `quantity_rules.py:26-41`.
**Where**: `.specs/features/inteligencia-documental/design.md` (modify, linhas 173, 178, 183 e 184)
**Depends on**: None
**Reuses**: `backend/app/domain/rules/quantity_rules.py`, `test_quantity_rules_units`
**Requirement**: CADOC-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] As cinco linhas batem com `_PER_YEAR` e com o "por ação" do comentário de `quantity_rules.py:23-25` (conferência citada na mensagem do commit)
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): align the quantity column with the quantity rules`

---

### T21: Rastreabilidade da inteligência documental

**Status**: Pending

**What**: Para cada requisito de `inteligencia-documental/spec.md` com status `Implementing` ou `In Tasks`, procurar em `validation.md` (passagens 1 a 4 e "Requirement Traceability Update") e em `verification-fora.md` uma linha do Verifier independente com PASS; só esses passam a `Verified`, e a nota de cobertura lista quais mudaram e a passagem que comprova (arquivo e seção). QUA-01..06, CER-01..05 e qualquer requisito sem PASS registrado ficam como estão.
**Where**: `.specs/features/inteligencia-documental/spec.md` (modify, tabela de rastreabilidade e nota de cobertura)
**Depends on**: None
**Reuses**: `inteligencia-documental/validation.md`, `verification-fora.md`
**Requirement**: CADOC-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cada requisito que mudou para `Verified` tem a passagem e a seção citadas; QUA-01..06 e CER-01..05 continuam `Implementing`
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py inteligencia-documental` sem erro novo
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): verify document intelligence requirements with a pass`

---

### T22: Rastreabilidade e nota de substituição da tabela oficial

**Status**: Pending

**What**: Os 22 requisitos `Implemented` passam a `Verified` citando `tabela-oficial/validation.md` (veredito PASS e a linha por requisito); ACE-02 fica `Pending` com a nota PARTIAL; o cabeçalho ganha a nota de substituição: PIT-01..03 e TELA-01..02 são substituídos pela feature `grupo-i-no-total` (AD-023) quando ela for implementada.
**Where**: `.specs/features/tabela-oficial/spec.md` (modify)
**Depends on**: None
**Reuses**: a nota de `grupo-i-no-total/spec.md:3`; `tabela-oficial/validation.md`
**Requirement**: CADOC-08, CADOC-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 22 `Verified`, 1 `Pending` (ACE-02), nota de cobertura citando a validação; nota de substituição no topo com PIT-01..03, TELA-01..02, `grupo-i-no-total` e AD-023
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py tabela-oficial` sem erro novo
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): verify official table requirements and note group I`

---

### T23: Nota de substituição e cenário derivado nos documentos gerados

**Status**: Pending

**What**: O cabeçalho de `documentos-gerados/spec.md` ganha a nota de substituição de TAB-03 e TAB-05 pela `grupo-i-no-total` (AD-023); as citações de 211 pontos (linhas 100 e 399) dizem "cenário derivado".
**Where**: `.specs/features/documentos-gerados/spec.md` (modify)
**Depends on**: None
**Reuses**: a nota de `grupo-i-no-total/spec.md:3`
**Requirement**: CADOC-10, CADOC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Nota de substituição no topo com TAB-03, TAB-05, `grupo-i-no-total` e AD-023; `grep -nE "\b211\b" .specs/features/documentos-gerados/spec.md` mostra "cenário derivado" em cada linha
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py documentos-gerados` sem erro novo
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): note group I in the total on the generated table`

---

### T24: Estados reais na GP-DEL-07

**Status**: Pending

**What**: O critério 7 da exclusão de processo troca "tarefa `PROCESSING`" por "tarefa de leitura `PENDENTE` ou `PROCESSANDO`", como `_ACTIVE_JOB` (`repositories.py:1121`).
**Where**: `.specs/features/gestao-processos/spec.md` (modify, linha 45)
**Depends on**: None
**Reuses**: `backend/app/infrastructure/database/repositories.py:1121`
**Requirement**: CADOC-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -n "PROCESSING" .specs/features/gestao-processos/spec.md` sem saída e a linha cita `PENDENTE` e `PROCESSANDO`
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs(specs): name the real job states in the process deletion guard`

---

### T25: Varredura final da sigla e das citações de 211 e 303

**Status**: Pending

**What**: Roda na raiz os `grep` de CAREF-05 e `grep -rnE "\b(211|303)\b"` em `.specs/features/*/spec.md`, `.specs/features/*/design.md`, `.specs/STATE.md` e `docs/` (mesmas exclusões de CAREF-05); corrige o que restar: sigla em qualquer arquivo, e citação de 211 ou 303 pontos sem "cenário derivado" na mesma frase. Hoje a lista conhecida da sigla é: `CLAUDE.md`, `backend/app/application/use_cases/scoring.py`, `backend/tests/integration/api/conftest.py`, `backend/tests/support/scoring_variants.py`, `.specs/STATE.md`, `.specs/audits/2026-11-19-auditoria-requisitos.md`, `.specs/features/grupo-i-no-total/design.md`, `.specs/features/revisao-simplificada/design.md`, `.specs/features/pontuacao/spec.md`, `.specs/features/pontuacao/tasks.md` e `.specs/features/pontuacao/validation.md` (cobertos por T6, T8, T14 a T19); a varredura confirma zero.
**Where**: arquivos apontados pela varredura (esperado: nenhum além dos já tratados)
**Depends on**: T19, T20, T21, T22, T23, T24
**Reuses**: os comandos de CAREF-05 e CADOC-05
**Requirement**: CAREF-05, CADOC-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `grep -rnE "\bI\.3\b" . --exclude-dir={node_modules,.venv,Documentos,Modelos,test,corpus-reports,.git,dist} --exclude=requeriment.txt` sem saída
- [ ] O mesmo comando com `-iE "avalia[cç][aã]o (pelo corpo )?discente"` e com `-iE "student.?evaluation"` sem saída
- [ ] Toda linha de `grep -rnE "\b(211|303)\b"` nos arquivos de CADOC-05 que cita pontos diz "cenário derivado"
- [ ] Se nada sobrou, a tarefa registra a saída vazia neste arquivo e o commit leva só a marcação
- [ ] Gate check passes: `cd backend && .venv/bin/pytest tests/unit tests/architecture -q`

**Tests**: none
**Gate**: quick

**Commit**: `docs: label every 211 and 303 point citation as a derived scenario`

---

### T26: Handoff do `STATE.md`

**Status**: Pending

**What**: Reescreve a seção Handoff com o conteúdo de CADOC-01, medido no momento: `git rev-parse --short HEAD`, `git branch --show-current`, `git log --oneline origin/feat/inteligencia-documental..HEAD` (commits locais não enviados), VM em `a136faf` com a migração `0008` (registro do deploy em `920c658`), feature corrente `correcoes-auditoria` e a seguinte `grupo-i-no-total`, gate atual com as contagens do backend e do frontend, decisões pendentes ainda abertas (as de `inteligencia-documental` e as `n` desta spec); remove a lista de arquivos "uncommitted" e o deploy de `documentos-gerados` como pendente; mantém Deploy, MariTalk e Documentos reais atualizados.
**Where**: `.specs/STATE.md` (modify, seção Handoff)
**Depends on**: T25
**Reuses**: o formato atual do Handoff; `docs/deploy/vm.md`
**Requirement**: CADOC-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] O HEAD, a branch e a lista de commits locais do Handoff batem com os comandos rodados (citados na mensagem do commit)
- [ ] `grep -n "Uncommitted files\|ainda não foi feito" .specs/STATE.md` sem saída
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagens do backend e do frontend registradas no Handoff

**Tests**: none
**Gate**: build

**Commit**: `docs(state): rewrite the handoff with the current head, VM and gate`

---

### T27: Verificador independente

**Status**: Pending

**What**: Agente diferente do autor confere os 39 requisitos com evidência (`arquivo:linha` de teste e de código), checa que cada teste afirma o valor que a spec define, roda os `grep` de CAREF-05 e CADOC-04, e roda o sensor de mutação em cópia isolada (worktree temporário, nunca `git stash`), com mutantes de comportamento, por exemplo: o botão "Iniciar processo" aparecendo em `EM_ANDAMENTO`; enviar `justificativa` no início; não recarregar em 409; a Etapa 5 mostrando o botão de concluir em `RASCUNHO`; devolver o ramo de valor informado em `_apply_group1`; limpar `points_override` também quando o valor muda; manter o 422 com valor igual; limpar o valor que o critério aceita; voltar a mensagem antiga de CATXT-02. Confere que a árvore real volta ao estado anterior ao sensor. Escreve o relatório; mutantes sobreviventes e lacunas viram tarefas de correção (no máximo 3 voltas de corrigir e reverificar).
**Where**: `.specs/features/correcoes-auditoria/validation.md` (novo)
**Depends on**: T26
**Reuses**: `references/validate.md` e `sub-agents.md` do skill; `validate_state.py`
**Requirement**: CAINI-01, CAINI-02, CAINI-03, CAINI-04, CAINI-05, CAINI-06, CAINI-07, CAINI-08, CAINI-09, CAINI-10, CAINI-11, CAINI-12, CAINI-13, CAINI-14, CAREF-01, CAREF-02, CAREF-03, CAREF-04, CAREF-05, CAREF-06, CATXT-01, CATXT-02, CATXT-03, CATXT-04, CAEDI-01, CAEDI-02, CAEDI-03, CAEDI-04, CADOC-01, CADOC-02, CADOC-03, CADOC-04, CADOC-05, CADOC-06, CADOC-07, CADOC-08, CADOC-09, CADOC-10, CADOC-11

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven` (validate)

**Done when**:

- [ ] `validation.md` com o veredito PASS, a evidência `arquivo:linha` por requisito, o resultado do sensor de mutação (mortos, sobreviventes, equivalentes) e o intervalo de commits
- [ ] Mutantes sobreviventes e lacunas viram tarefas de correção neste arquivo; o ciclo corrigir e reverificar tem no máximo 3 voltas
- [ ] Rastreabilidade da spec atualizada para `Verified` só nos requisitos com PASS
- [ ] `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_state.py correcoes-auditoria` sem erro
- [ ] Gate check passes: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && npm test -- --run`
- [ ] Test count: contagem final registrada

**Tests**: none
**Gate**: build

**Commit**: `docs(specs): verify the audit corrections`

---

## Phase Execution Map

```
Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6 (nesta ordem)

Phase 1:  T1, T2, T3, T4, T5            (frontend + caracterização da API)
Phase 2:  T6, T7, T8, T9, T10, T11      (backend e um texto do frontend)
Phase 3:  T12, T13                      (nomes de teste)
Phase 4:  T14, T15, T16, T17, T18       (sigla nos documentos)
Phase 5:  T19 a T26                     (documentação de estado)
Phase 6:  T27                           (Verifier)
```

Execução estritamente sequencial. 27 tarefas: em lotes de ~7 por fases inteiras, Fases 1 e 2 (11), Fases 3 e 4 (7), Fase 5 (8) e o Verifier; com mais de um lote, o orquestrador oferece sub-agentes antes de executar.

---

## Requirement coverage

| Requisito | Tarefas | Requisito | Tarefas |
| --- | --- | --- | --- |
| CAINI-01 | T3, T27 | CATXT-01 | T10, T27 |
| CAINI-02 | T3, T27 | CATXT-02 | T9, T27 |
| CAINI-03 | T2, T27 | CATXT-03 | T9, T27 |
| CAINI-04 | T2, T27 | CATXT-04 | T9, T27 |
| CAINI-05 | T3, T27 | CAEDI-01 | T11, T27 |
| CAINI-06 | T2, T3, T27 | CAEDI-02 | T11, T27 |
| CAINI-07 | T2, T27 | CAEDI-03 | T11, T27 |
| CAINI-08 | T1, T27 | CAEDI-04 | T11, T27 |
| CAINI-09 | T1, T27 | CADOC-01 | T26, T27 |
| CAINI-10 | T4, T27 | CADOC-02 | T19, T27 |
| CAINI-11 | T4, T27 | CADOC-03 | T20, T27 |
| CAINI-12 | T5, T27 | CADOC-04 | T12, T13, T27 |
| CAINI-13 | T5, T27 | CADOC-05 | T13, T23, T25, T27 |
| CAINI-14 | T5, T27 | CADOC-06 | T19, T27 |
| CAREF-01 | T8, T27 | CADOC-07 | T21, T27 |
| CAREF-02 | T6, T7, T27 | CADOC-08 | T22, T27 |
| CAREF-03 | T6, T27 | CADOC-09 | T24, T27 |
| CAREF-04 | T6, T27 | CADOC-10 | T22, T23, T27 |
| CAREF-05 | T7, T14, T15, T16, T17, T18, T19, T25, T27 | CADOC-11 | T19, T27 |
| CAREF-06 | T14, T27 | | |

39 requisitos, 39 mapeados, 0 sem tarefa.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1 | 1 arquivo de teste | ✅ Granular |
| T2 | 1 componente (+ seu teste) | ✅ Granular |
| T3 | 1 página | ✅ Granular |
| T4 | 1 página | ✅ Granular |
| T5 | 1 página | ✅ Granular |
| T6 | 1 módulo de suporte + os testes que leem os nomes e o critério que ele muda | ⚠️ Coeso: renomear sem ajustar os dependentes quebra o gate |
| T7 | 1 teste | ✅ Granular |
| T8 | 1 função | ✅ Granular |
| T9 | 2 mensagens na mesma função de validação | ✅ Granular |
| T10 | 1 função de texto | ✅ Granular |
| T11 | 1 caso de uso | ✅ Granular |
| T12 | 1 teste | ✅ Granular |
| T13 | 1 fixture + importadores | ⚠️ Coeso: renomear sem os importadores quebra o gate |
| T14 a T24 | 1 arquivo de documentação cada (T16: os três registros da mesma feature) | ✅ / ⚠️ T16 coeso |
| T25 | varredura (esperado: nenhum arquivo) | ✅ |
| T26 | 1 seção | ✅ Granular |
| T27 | relatório | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | sem aresta | ✅ Match |
| T2 | None | sem aresta de entrada | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | sem aresta | ✅ Match |
| T5 | T2 | T2 → T5 | ✅ Match |
| T6 | None | sem aresta de entrada | ✅ Match |
| T7 | None | sem aresta | ✅ Match |
| T8 | T6 | T6 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | None | sem aresta | ✅ Match |
| T11 | T9 | T9 → T11 | ✅ Match |
| T12 | T7 (Fase 2) | T7 → T12 | ✅ Match |
| T13 | None | sem aresta | ✅ Match |
| T14 a T18 | None | sem aresta | ✅ Match |
| T19 a T24 | None | sem aresta de entrada | ✅ Match |
| T25 | T19, T20, T21, T22, T23, T24 | T19..T24 → T25 | ✅ Match |
| T26 | T25 | T25 → T26 | ✅ Match |
| T27 | T26 (Fase 5) | T26 → T27 | ✅ Match |

Nenhuma tarefa depende de fase posterior.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | API routes (só teste) | integration | integration | ✅ OK |
| T2 | Frontend component | unit | unit | ✅ OK |
| T3 | Frontend page | unit | unit | ✅ OK |
| T4 | Frontend page | unit | unit | ✅ OK |
| T5 | Frontend page | unit | unit | ✅ OK |
| T6 | Test support | integration | integration | ✅ OK |
| T7 | Domain (só teste) | unit | unit | ✅ OK |
| T8 | Use cases | integration | integration | ✅ OK |
| T9 | Use cases | integration | integration | ✅ OK |
| T10 | Frontend component | unit | unit | ✅ OK |
| T11 | Use cases + API | integration | integration | ✅ OK |
| T12 | Domain (só teste) | unit | unit | ✅ OK |
| T13 | API (só teste) | integration | integration | ✅ OK |
| T14 a T25 | Docs | none | none | ✅ OK |
| T26 | Docs | none | none (gate build) | ✅ OK |
| T27 | Relatório | none | none (gate build) | ✅ OK |

---

## Tools

MCPs e skills por tarefa: nenhum MCP é necessário (todas as tarefas leem e editam arquivos locais); a skill `tlc-spec-driven` conduz a execução e o Verifier. Confirmar com o usuário na aprovação se quer outra ferramenta em alguma tarefa.
