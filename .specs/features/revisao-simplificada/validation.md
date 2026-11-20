# Revisão simplificada das atividades: Validation

## Validation: revisao-simplificada - PASS ✅

**Date**: 2026-11-19
**Spec**: `.specs/features/revisao-simplificada/spec.md` (40 requisitos: VAL 6, SEC 12, DUP 7, SEG 5, EDT 7, QTD 3; seção "Decisões do Verifier (rodada 1)" com as 11 decisões de precisão)
**Rodada**: reverificação, volta 1 de no máximo 3 (a volta 0 deu FAIL em `9ef7001` com G1 a G7, SP1 a SP10 e 3 mutantes sobreviventes: B27, B43, F3b)
**Diff range**: `9ef7001..69ec5ed` (9 commits: o plano T56 a T62, as 7 correções e a T43; 13 arquivos, 591 inserções, 63 remoções) sobre o intervalo da feature `39bbfd2..69ec5ed` (66 commits)
**Verifier**: sub-agente independente da reverificação; não escreveu nenhuma das correções; releu spec, testes e código e reaplicou os mutantes em worktree isolada.
**Result**: PASS (G1 a G7 fechadas com teste que falha contra o mutante; B27, B43 e F3b mortos; 12 mutantes novos: 8 mortos e 4 sobreviventes, todos equivalentes ou mascarados, nenhum com resultado observável diferente; gate completo verde)

**Spec-anchored check**: 40 de 40 requisitos com asserção que bate com o resultado da spec (os 7 requisitos com lacuna foram relidos nesta volta; os outros 33 seguem da volta 0, sem alteração nos testes além de acréscimos, e o gate completo e os mutantes novos não os contradizem); as 10 lacunas de precisão SP1 a SP10 foram decididas na spec (`spec.md`, "Decisões do Verifier") e cada decisão cita o teste que a guarda; 1 lacuna de precisão nova, baixa (SP11).
**Gate**: backend `ruff check .` limpo e `pytest -q` com 5281 passando, 3 `deselected`; frontend `npm run lint` limpo, `npm run build` (`tsc -b` e `vite build`) limpo e `vitest run` com 563 passando em 41 arquivos (o teste de `bundle`, pulado na volta 0, rodou depois do build).
**Sensor**: volta 1: 3 mutantes de volta e 4 de fechamento de lacuna reaplicados (todos mortos) mais 12 novos (8 mortos, 4 equivalentes); soma com a volta 0: 82 mutantes distintos (66 + 12 + 4 de lacuna), 0 sobreviventes não equivalentes.
**Limitação aceita**: a largura de 360 px (SEC-12) é verificada por medição manual em Chrome registrada em `design.md:184-191`; o projeto não tem teste de navegador e o jsdom não mede layout. Sem FAIL por isso.

---

## Task Completion

| Tarefa | Status | Notas |
| ------ | ------ | ----- |
| T1 a T42 | ✅ Done | commitadas (`e9125cd` a `c3b7189`), um commit por tarefa |
| T45 a T55 | ✅ Done | correções da revisão dos lotes 5 e 6 (`4837e2a` a `e1b06a0`) |
| T56 a T62 | ✅ Done | `3d033b0`, `f7c8563`, `0db5817`, `d467d98`, `c782be0`, `ee9d7c4`, `c71ce50`; o plano em `7897171`; todas as caixas de `tasks.md` marcadas |
| T43 | ✅ Done | `69ec5ed` (AD-022 em `STATE.md`, regra 10 em `CLAUDE.md`, rastreabilidade de `spec.md` e `design.md`); era "Partial" na volta 0 |
| T44 | este relatório | volta 1 |

Observação de documentação (não bloqueia): `tasks.md` T61 cita `test_run_generation_table.py` em **Where**, mas o teste do worker está em `test_run_generation_failure.py:60-77`.

---

## Fechamento das lacunas da volta 0

Cada linha: o teste novo existe, afirma o valor da spec e falha contra o mutante (worktree isolada, só o teste direcionado).

| Lacuna | Teste novo (`file:line`) | Asserção | Mutante reaplicado | Resultado |
| ------ | ------------------------ | -------- | ------------------ | --------- |
| G1 (B27) | `B/integration/doc_usecases/test_generation_inputs.py:54-66`; `B/integration/api/test_generated_validity_acceptance.py:126-146` | `inputs.excluded == {}`; `summary["excluded"] == {}`, `activity_count == 1` | `generation_inputs.py:89` sem `validity[activity.id].is_valid and` (a não válida aguardando passa a contar "pendentes") | ✅ morto por ambos (2 failed, 27 passed) |
| G2 (B43) | `B/integration/api/test_activity_edit_rules_api.py:158-199` | 201 com só início 2021 e 2023; 422 em `period_start` com só início 2025; edição idem | `scoring.py:422` com `yearly = False` | ✅ morto (`...only_a_start_is_open...[2021-01-01]` e `...keeps_the_open_period_rule`; 2 failed, 20 passed) |
| G3 (F3b) | `F/components/ValidActivitiesSection.test.tsx:158-168` | "3 atividades precisam de categoria" com busca e com filtro de grupo ativos | `ValidActivitiesSection.tsx:73` com `filtered.filter(...)` em vez de `activities.filter(...)` | ✅ morto (1 failed, 37 passed) |
| G4 | `B/integration/api/test_generated_validity_acceptance.py:219-238` e `:242-262` | Tabela e Relatório sem o título da mesclada, `activity_count == 1`; Comprovante com 2 e com 1 original conforme o caso | G4a: `repositories.py` `include_merged: bool = True` em `list_for_process`; G4b: `activity_merge.py:77` move `[]` em vez das provas | ✅ G4a morto por `:242`; G4b morto por `:219` |
| G5 | `design.md:184-191` | `scrollWidth == clientWidth` a 360 e 320 px com 127 linhas; controle negativo a 200 px | não aplicável (verificação manual) | ✅ aceita como limitação documentada (ver Result) |
| G6 | `B/integration/doc_usecases/test_run_generation_failure.py:60-77`; código em `generated_documents.py:317-319` | `error_code is ATIVIDADE_SEM_CATEGORIA`, mensagem fixa, `state is FALHOU` | entrada de `ATIVIDADE_SEM_CATEGORIA` removida de `_FAILURE_MESSAGES` (o estado da volta 0) | ✅ morto (1 failed, 5 passed; sem o mapeamento o código vira `ERRO_INTERNO`) |
| G7 | `B/integration/scoring/test_activity_update.py:82-108`; `B/integration/scoring/test_list_activities_validity.py:154-184` | `changed.status is VALIDADA`, `before == (PONTUADA, old*4, old*4)` e `after == (PONTUADA, new*4, new*4)`; `only.status is status` para `IMPORTADA/AGUARDANDO_REVISAO` e `MANUAL/VALIDADA` | `scoring.py` `replace(current, status=AGUARDANDO_REVISAO, **_fields(data))` em `UpdateActivity` | ✅ morto (10 failed, 34 passed, incluindo os dois testes novos) |

O teste de G7 calcula os pontos esperados pela tabela oficial (`unit_points * 4`) e afirma antes que os dois itens têm pontos diferentes (`test_activity_update.py:86-91`), sem o que não provaria nada.

---

## Spec-Anchored Acceptance Criteria

Convenção: `B/` = `backend/tests/`, `F/` = `frontend/src/`. "Mutantes" cita os mutantes da seção Sensor que guardam o requisito.

### P1: Validar pontua

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| VAL-01 validar com categoria e dentro do interstício pontua | II.5 validada = 8,00 na Etapa 4, sem outra ação | `B/integration/api/test_scoring_validity_api.py:89` `total == "0.00"` antes; `:100` `(row["status"], row["unit_points"], row["points"]) == ("PONTUADA","8.00","8.00")`; `:101` `body["total"] == "8.00"`. Também `B/unit/domain/test_scoring_engine_validity.py:146-150` (`row.points == D("8")`, `result.total == D("8")`), `B/integration/api/test_activities_validity_api.py:153,163,165` (previsto 8.00, total 0.00 → 8.00), `B/integration/api/test_activity_validate_rules_api.py:98-115` (200 e `VALIDADA`) | B4, B11, B23 | ✅ PASS |
| VAL-02 item por unidade sem quantidade | pontua com 1 e emite `QUANTIDADE_ASSUMIDA` | `B/unit/domain/test_scoring_engine_validity.py:223-230` `points == D("8")`, `effective_quantity == D("1")`, `ASSUMED in alert_codes(...)`; `:244-250` com quantidade informada não há alerta; `:253-260` só itens por unidade; `B/unit/domain/test_scoring_alerts.py:78`; `F/labels.test.ts:163-166` | B14, B35 | ✅ PASS (a gravidade `ALERTA`, a mensagem e a norma, afirmadas em `:233-241`, a spec não define: SP4) |
| VAL-03 validar sem categoria | 422 no campo `categoria`, "Escolha a categoria antes de validar", atividade como estava | `B/integration/api/test_activity_validate_rules_api.py:53-66` `detail == [{"field":"categoria","message":"Escolha a categoria antes de validar"}]` e `(after["status"], after["version"]) == ("AGUARDANDO_REVISAO", 1)`; `F/components/ActivityRow.test.tsx:148-158` | B11, B23 | ✅ PASS |
| VAL-04 lote | valida as com categoria, lista as sem | `B/integration/scoring/test_bulk_validate_skipped.py:40-54` `[a.id for a in result.activities] == [categorized...]`, `[(s.id, s.reason)...] == [(a.id,"SEM_CATEGORIA")...]`; `B/integration/api/test_bulk_validate_api.py:79-102`; `F/components/ValidActivitiesSection.test.tsx:165-184` ("3 validadas; 1 ficou sem categoria"), `:290-300` ("Validar as confiáveis") | B12, B12b | ✅ PASS (o lote também pula as não válidas, com `reason` própria: SP9) |
| VAL-05 auditoria do status, sem justificativa | 1 evento `STATUS`, `justification is None` | `B/integration/api/test_activity_validate_rules_api.py:98-115` `len(events) == 1`, `events[0].justification is None`; em lote `B/integration/api/test_bulk_validate_api.py:175-206` | B26 | ✅ PASS |
| VAL-06 "Validar" só para válida | nenhuma não válida oferece Validar | `F/components/ActivityRow.test.tsx:160-172` (`queryByRole("button",{name:/^Validar /})` ausente), `:174-184`; `F/components/InvalidActivitiesSection.test.tsx:98-109`; servidor recusa: `B/integration/api/test_activity_validate_rules_api.py:68-95` (`error["code"] == "ATIVIDADE_NAO_VALIDA"`) | B11b, F1b | ✅ PASS (a recusa no servidor não está na spec: SP4) |

### P1: Etapa 3 em duas seções

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| SEC-01 duas seções com o total | títulos "Atividades válidas (N)" e "Atividades não válidas (N)" | `F/components/ActivityWorkspace.test.tsx:70-75` `getByRole("heading",{level:2,name:"Atividades válidas (1)"})` e `name: /^Atividades não válidas \(2\)/` | F5 | ✅ PASS |
| SEC-02 seção de válidas | dentro do interstício, com ou sem categoria, carga suficiente, não rejeitadas; 25 por vez | `F/components/ValidActivitiesSection.test.tsx:80-87` `rowsShown() == 25`, depois 50, "Mostrando 50 de 120"; `:89-93`; classificação: `B/unit/domain/test_activity_validity.py:72-83,176-178,183-189`; `B/integration/api/test_activities_validity_api.py:60-87` (120 atividades) | B1, B3, F6, F16 | ✅ PASS |
| SEC-03 busca e filtros com contagem | chips todas/aguardando/validadas/precisa de categoria com a contagem, busca, grupo | `F/components/ValidActivitiesSection.test.tsx:103-119` ("Todas (120)", "Aguardando validação (80)", "Validadas (30)", "Precisa de categoria (10)"), `:121-135`, `:137-148`, `:405-414` (`["Todos os grupos","II · Orientação (1)","III · Bancas (2)"]`); `F/components/ActivityFilters.test.tsx:25-31` | F3a, F13, F17 | ✅ PASS |
| SEC-04 selo e seletor na linha | "Precisa de categoria" e seletor; aplica na hora, sem justificativa | `F/components/ActivityRow.test.tsx:100-107`, `:109-126` (`toMatchObject({group_number:3,item_number:2,expected_version:4})`, sem `justificativa`); `F/components/CategoryPicker.test.tsx:36-44`; `F/components/ActivityWorkspace.test.tsx:241-250` | F1 | ✅ PASS |
| SEC-05 bloqueio do avanço | avanço à Etapa 4 desabilitado e "N atividades precisam de categoria" | `F/pages/ProcessActivities.test.tsx:149-158` (`items[3]`/`items[4]` com `aria-disabled`, sem link), `:160-176` (libera ao escolher), `:187-196` (não válida sem categoria não bloqueia); `F/components/ValidActivitiesSection.test.tsx:153-156` (sem filtro: "3 atividades precisam de categoria"), **`:158-168` (volta 1: com a busca "Atividade 004" e depois com o filtro de grupo 3, `rowsShown() == 1` e o aviso segue "3 atividades precisam de categoria")**; `F/labels.test.ts:150-153` | F2, F14, F15, F19, **F3b** (mortos) | ✅ PASS (sem tabela o avanço fica livre: decisão 7 da spec, `spec.md`, "Decisões do Verifier") |
| SEC-06 seção de não válidas | fora do interstício, carga abaixo do mínimo, rejeitadas, cada uma com o motivo | `F/components/InvalidActivitiesSection.test.tsx:98-109`; `B/integration/scoring/test_list_activities_validity.py:42-76` (`validity.params == {...}`); `B/unit/domain/test_activity_validity.py:100-134,240-246` | B1, B2 | ✅ PASS (a implementação lista também grupo que não conta e duplicidade residual: SP2) |
| SEC-07 texto do motivo | "Fora do interstício: data dd/mm/aaaa; interstício dd/mm/aaaa a dd/mm/aaaa"; "Carga horária insuficiente: N h; o item exige M h"; "Rejeitada por você" | `F/labels.test.ts:95-98` `toBe("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025")`, `:107-111`, `:119-121`; `F/components/ReasonText.test.tsx:15-39` | F11 | ✅ PASS (período de categoria por ano e precisão de mês não estão na spec: SP3) |
| SEC-08 corrigir leva às válidas, sem recarregar a página | a atividade passa para a seção de válidas | `F/components/ActivityWorkspace.test.tsx:91-112` `getByRole("heading",{name:"Atividades válidas (2)"})` e não válidas `(1)`; `B/integration/scoring/test_list_activities_validity.py:136-151` | | ✅ PASS |
| SEC-09 reabrir rejeitada | vai a "aguardando validação" e a seção de válidas a lista | `B/integration/scoring/test_list_activities_validity.py:154-167` `only.status is AGUARDANDO_REVISAO`; `B/integration/api/test_activity_validate_rules_api.py:117-128`; `F/components/ActivityWorkspace.test.tsx:135-148`; `F/components/InvalidActivitiesSection.test.tsx:121-127` | | ✅ PASS |
| SEC-10 não válidas fechada, com total e contagem por motivo | `aria-expanded=false`, "Atividades não válidas (4)" com "Fora do interstício: 2" etc. | `F/components/InvalidActivitiesSection.test.tsx:54-64`, `:86-94` | F5 | ✅ PASS |
| SEC-11 seção vazia | "Nenhuma atividade válida ainda" / "Nenhuma atividade não válida" | `F/components/ValidActivitiesSection.test.tsx:95-99`; `F/components/InvalidActivitiesSection.test.tsx:131-135` | | ✅ PASS |
| SEC-12 sem rolagem horizontal a 360 px, teclado, não só cor | | teclado: `F/components/ActivityWorkspace.test.tsx:164-171` (`toggle` recebe foco por Tab), `F/components/InvalidActivitiesSection.test.tsx:66-74`; não só cor: `F/components/ActivityRow.test.tsx:255-262`, `F/components/ReasonText.test.tsx:41-44`; largura: regra de CSS em `F/components/ActivityWorkspace.test.tsx:173-179` (nenhum `width`/`min-width` fixo, nenhum `overflow-x: scroll`); **volta 1: medição em navegador registrada em `design.md:184-191` (Chrome 146 headless, `iframe` de 360 px, 120 atividades válidas, 12 sem categoria e 7 não válidas, tudo aberto: `scrollWidth` 345 = `clientWidth` 345; 320 px: 305 = 305; controle negativo a 200 px: 225 > 185)** | | ✅ PASS com limitação documentada: a medição é manual e fica fora do gate (o projeto não tem teste de navegador; o jsdom não mede layout); o registro tem método, resultado, controle negativo e passo a passo para repetir; o Chrome 146.0.7680.75 existe na máquina (`google-chrome --version`) |

### P1: Duplicadas mescladas

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| DUP-01 mesclar; fica a validada, senão a primeira; provas somadas sem repetir o par | | `B/integration/doc_usecases/test_activity_merge.py:38-53` (`visible == {older.id}`, páginas `{(a,1),(b,2),(c,5)}`, origem da prova), `:73-80` (validada fica, mesmo mais nova), `:83-91` (ambas ou nenhuma: a primeira), `:94-102`; `B/integration/test_repositories_merge.py:208-225` (não repete documento e página) | B5, B5b, B6, B21 | ✅ PASS (mais de duas validadas: SP6) |
| DUP-02 a outra fica no banco, marcada, com auditoria dos dois ids | | `B/integration/doc_usecases/test_activity_merge.py:56-70` (`merged_into_id == older.id`, `is_merged`), `:132-144` (`changes["merged_activity_id"]["after"] == str(newer.id)`, `kept_activity_id`); `B/integration/test_repositories_merge.py:117-131` | B6, B22 | ✅ PASS |
| DUP-03 mesclada fora das listas, totais, Tabela, Relatório e Comprovante | | listas e totais: `B/integration/scoring/test_list_activities_validity.py:119-133`, `B/integration/api/test_activity_merge_api.py:73-89` (sem linha na pontuação), `B/integration/test_repositories_merge.py:79-92`; **volta 1, os três documentos:** `B/integration/api/test_generated_validity_acceptance.py:219-238` (após `merge-duplicates` com `{"merged": 1}`, Tabela e Relatório sem o título da mesclada e com o da mantida, `activity_count == 1`, `text.count(...) == 1`; Comprovante com `len(originals) == 2`, páginas 1 e 4) e `:242-262` (mesclada com título próprio, só a marca a tira: `activity_count == 1`, `len(originals) == 1`) | B25, B46, **G4a (`include_merged=True`, morto por `:242`), G4b (mesclagem sem mover provas, morto por `:219`)** | ✅ PASS |
| DUP-04 mescla ao criar, editar, reprocessar e na primeira abertura da Etapa 3 | | criar `B/integration/api/test_activity_merge_on_write_api.py:77-95`; editar `:109-120`; leitura do documento `B/integration/doc_usecases/test_document_merge.py:52-58`, reprocessar `:74-87`; rota `B/integration/api/test_activity_merge_api.py:48-58`; abertura `F/pages/ProcessActivities.test.tsx:99-105` (`count(calls, MERGE) == 1`, antes da lista), `:107-120` (recarga não mescla), `:122-132` (somente leitura não mescla) | B18, B19, B20, F4, F7, F18 | ✅ PASS |
| DUP-05 repetir não muda nada | | `B/integration/doc_usecases/test_activity_merge.py:147-157` (`again.count == 0`, snapshot igual, `len(merge_events) == 1`); `B/integration/api/test_activity_merge_api.py:60-71` | B7 | ✅ PASS |
| DUP-06 falha no meio não altera nada | | `B/integration/doc_usecases/test_activity_merge.py:160-183` (falha forçada no 2º `move`, tudo igual a antes), `:186-195`; `B/integration/api/test_activity_merge_on_write_api.py:141-158`; `B/integration/doc_usecases/test_document_merge.py:120-153` | | ✅ PASS |
| DUP-07 "N duplicadas mescladas" e "Não é duplicada" | restaura, devolve as provas, marca as duas como distintas | `F/components/MergedNote.test.tsx:13-25`, `:32-46` (`POST /api/activities/m2/separate`); `B/integration/doc_usecases/test_activity_separate.py:52-64` (provas de volta, `origin_activity_id is None`), `:83-96` (`distinct_justification == DISTINCT_DEFAULT_TEXT` nas duas e `report.count == 0`), `:125-134`; `B/integration/api/test_activity_merge_api.py:140-154` | B9, B10, B10b, B32, B33, F10 | ✅ PASS |

### P1: Só as válidas seguem

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| SEG-01 cálculo, Tabela, Relatório, Comprovante e prévia da conclusão só com válidas | nenhuma linha das não válidas, nem "Não pontuada" | `B/integration/api/test_generated_validity_acceptance.py:108-116` (`title not in text`, `not re.search(r"Não pontuada(?!s)")`), `:119-123` (`activity_count == 1`, `excluded == {}`), `:129-137`; **volta 1: `:126-146` (fora do interstício e carga insuficiente em `AGUARDANDO_REVISAO`: `summary["excluded"] == {}`, `activity_count == 1`, títulos fora do texto, sem alerta `ATIVIDADES_FORA_DO_DOCUMENTO`) e `B/integration/doc_usecases/test_generation_inputs.py:54-66` (`inputs.activities == []`, `inputs.excluded == {}`)**; `:33-48` (as válidas pendentes contam `{"pendentes": 2}`); `B/unit/domain/test_activity_order.py:34-38`; `B/integration/api/test_scoring_validity_api.py:107-128` | B4, B17, B42, B45, **B27 (morto)**, N2 | ✅ PASS (a "prévia da conclusão" não lê atividades e não tem resultado observável: decisão 11 da spec) |
| SEG-02 Comprovante sem página cuja única atividade é não válida ou mesclada | | `B/integration/api/test_generated_validity_acceptance.py:143-153` (`len(originals) == 1`, títulos fora do texto); **mesclada, volta 1: `:242-262` (`len(originals) == 1`, `"Origem Alfa pagina 1" in originals[0]`) e `:236-238` (a prova da mesclada foi para a mantida: páginas 1 e 4)** | G4a, G4b | ✅ PASS |
| SEG-03 corrigida entra no cálculo e nas gerações seguintes | | `B/integration/api/test_scoring_validity_api.py:131-149` (`total == "8.00"`, `counters.activities == 1`); `B/integration/api/test_generated_validity_acceptance.py:159-174` (`second["summary"]["activity_count"] == 2`), `:177-191` (a versão anterior não muda) | B4 | ✅ PASS |
| SEG-04 contadores só sobre as válidas | | `B/integration/api/test_scoring_validity_api.py:126-127` (`counters.activities == 1`, `not_scored == 0`), `:172-173`; `B/unit/domain/test_scoring_engine_validity.py:103-105` | B24, B45 | ✅ PASS (o frontend só exibe `counters` do servidor; sem teste próprio: SP10c) |
| SEG-05 geração recusada com 422 `ATIVIDADE_SEM_CATEGORIA` | | `B/integration/api/test_generated_validity_acceptance.py:199-208` (3 documentos × 2 status: `(detail["field"], detail["code"]) == ("geracao","ATIVIDADE_SEM_CATEGORIA")`), `:211-216` (não válida sem categoria não recusa); `B/integration/api/test_generation_error_mapping.py:63`; `B/integration/doc_usecases/test_generation_inputs.py:51`; **volta 1, worker: `B/integration/doc_usecases/test_run_generation_failure.py:60-77` (`failed.state is FALHOU`, `failed.error_code is ATIVIDADE_SEM_CATEGORIA`, mensagem fixa, `version_number is None and files == ()`); mapeamento em `app/application/use_cases/generated_documents.py:317-319`** | B15, **G6 (entrada removida de `_FAILURE_MESSAGES`, morto)**, N3 | ✅ PASS (o texto da mensagem do worker não está na spec: SP11) |

### P1: Editar atividade com poucos campos

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| EDT-01 campos | Título, Data, Categoria; Início/Fim por ano; Horas só com carga mínima | `F/components/ActivityForm.test.tsx:57-63` (`noField` para Descrição, Comprovante, Quantidade, Horas...), `:65-70`, `:72-76` (`getByLabelText("Horas")`), `:78-86` | F9 | ✅ PASS |
| EDT-02 data fora do interstício | 422 em `event_date`, "A data deve estar entre dd/mm/aaaa e dd/mm/aaaa", atividade como estava | `B/integration/api/test_activity_edit_rules_api.py:71-79` (`message == "A data deve estar entre 23/11/2022 e 23/11/2024"`), `:82-97` (primeiro e último dia aceitos, vizinhos recusados), `:161-176` (`(event_date, version) == ("2023-05-10", 1)`), `:179-198`; `F/components/ActivityForm.test.tsx:242-253` | B13, B13b, B13c | ✅ PASS (data inalterada não é rejulgada e precisão de mês: SP5) |
| EDT-03 categoria por ano | aceita o período que cruza, recusa o que não toca | `B/integration/api/test_activity_edit_rules_api.py:121-130` (201), `:133-155` (422 em `period_end`/`period_start`), `:201-217`; **volta 1, período aberto: `:158-169` (só início 2021-01-01 e 2023-01-01: 201 e `period_start` devolvido), `:172-181` (só início 2025-01-01: 422 em `period_start` com a faixa, lista vazia), `:184-199` (edição: 2021 aceito, 2025 recusado, valor gravado intacto)** | B44, **B43 (morto)**, N1b | ✅ PASS (período aberto e precisão de mês: decisão 3 da spec) |
| EDT-04 nova manual pede Título, Data, Categoria, Quantidade | | `F/components/ActivityForm.test.tsx:184-200` (`toEqual({title, event_date:"2023-05", group_number:2, item_number:7, quantidade:4})`) | | ✅ PASS (Grupo I novo: SP10a) |
| EDT-05 oferta do Grupo I mostra só Título e Categoria | | `F/components/ActivityForm.test.tsx:88-94` | | ✅ PASS |
| EDT-06 aplica na hora, sem justificativa, com auditoria | | `B/integration/api/test_activity_edit_rules_api.py:262-284` (`update.justification is None`, `changes["quantity"] == {"before":"1","after":"3"}`); `B/integration/scoring/test_activity_update.py:65`; `F/components/ActivityForm.test.tsx:118-125` | | ✅ PASS |
| EDT-07 vínculo só pela ação "Vincular", sem campo de comprovante | | `F/components/ActivityForm.test.tsx:62` (`noField("Comprovante")`), `:118-125`; `F/components/ValidActivitiesSection.test.tsx:343-363` (`body == {document_id:"d2", page:3}`; o seletor não oferece documento fora do interstício) | | ✅ PASS |

### P1: Quantidade e valor manual na Etapa 4

| Critério | Resultado definido na spec | `file:line` + asserção | Mutantes | Resultado |
| -------- | -------------------------- | ---------------------- | -------- | --------- |
| QTD-01 "Editar pontuação" com Quantidade (ou Horas) e valor unitário | | `F/components/ScoreEditor.test.tsx:162-174` (Quantidade com valor 3 sem Horas; Horas sem Quantidade; `Valor unitário` presente) | | ✅ PASS |
| QTD-02 recalcula na hora, sem justificativa, com auditoria | | `B/integration/api/test_activity_edit_rules_api.py:278` `Decimal(after["total"]) == Decimal(before["total"]) * 3 > 0`, `:281-284`; `F/components/ScoreEditor.test.tsx:186-198` | | ✅ PASS |
| QTD-03 quantidade negativa ou não numérica | 422 no campo `quantidade` | `B/integration/api/test_activity_edit_rules_api.py:237-259` (`-1`, `-0.5`, `"abc"` na criação e na edição, 422 em `quantidade`, valor intacto `"1.00"`); `F/components/ScoreEditor.test.tsx:237-250` | | ✅ PASS (faixa 0 a 10000 e inteiro: SP8) |


**Status**: ✅ sem lacuna de cobertura (G1 a G7 fechadas); SP1 a SP10 decididas na spec; SP11 aberta, baixa.

---

## Edge Cases (spec.md, "Edge Cases")

- [x] Deixar de ser duplicada por edição não desfaz a mesclagem: `B/integration/api/test_activity_merge_on_write_api.py:123-138` (`listed == [kept]` e a linha da mesclada segue existindo).
- [x] Trocar a categoria de validada recalcula e mantém o status: `B/integration/scoring/test_activity_update.py:82-108` (`changed.status is VALIDADA`; pontos `old*4` para `new*4` e total igual; G7 morto).
- [x] Carga horária corrigida volta às válidas com o status que tinha: `B/integration/scoring/test_list_activities_validity.py:154-184` (`only.status is status` nos dois casos, `AGUARDANDO_REVISAO` importada e `VALIDADA` manual).
- [x] Prova em documento fora e outra em documento dentro: a atividade fica com a de dentro (AD-019), regra anterior à feature, fora do escopo do diff.

---

## Test Integrity

`git diff --numstat 9ef7001..HEAD` nos arquivos de teste: 7 arquivos, 267 inserções e 2 remoções. As duas remoções são linhas de `import` ampliadas (`from datetime import date` para `date, UTC, datetime`; `import ActivityData` para `ActivityData, compute_process_score`). Nenhum `skip`, `xfail` ou `.only` novo; nenhuma asserção alterada; 11 testes novos (`def test_`/`it(`), 12 execuções novas no backend (5269 para 5281) e 2 no frontend (561 para 563, contando o teste de `bundle` que agora roda depois do build).

---

## Discrimination Sensor

**Método**: worktree git isolada (`git worktree add --detach` em `scratchpad/verif1/wt`, HEAD `69ec5ed`), um mutante por vez, restaurado por `git checkout` a cada rodada, apenas testes direcionados (pytest do `backend/.venv`, PostgreSQL real em contêiner descartável; `vitest run <arquivo>` no frontend com `node_modules` ligado por link). Nunca dois pytest ao mesmo tempo; o gate completo rodou depois dos mutantes. Worktree removida (`git worktree remove --force` e `prune`); `git status --porcelain` da árvore real igual ao do início (`?? requeriment.txt`, `?? test/`) depois dos mutantes e depois do gate; o stash antigo (`stash@{0}`) não foi tocado.
**Profundidade**: completa (caminho crítico de pontuação e dados do processo).

### Volta 1: 12 mutantes novos (8 mortos, 4 sobreviventes equivalentes ou mascarados)

Nenhum repete os 66 da volta 0 (B1 a B47 e F1 a F19). Áreas tocadas pelas correções (worker de geração, contagem de pendentes, período aberto por ano, mesclada nos documentos, foco após falha na linha) e duas sem mutante antes (limites de quantidade da QTD-03 e contagem de citações por documento da Etapa 2; busca por título e limiar de confiança do lote).

| # | `file:line` | Mutação | Teste que matou | Resultado |
| - | ----------- | ------- | --------------- | --------- |
| N1 | `app/domain/rules/scoring_periods.py:94` | período aberto corre até o início do interstício (`interstice.start`) em vez do fim | nenhum (2686 passed) | ◻ Sobreviveu, **equivalente**: `max(start, open_end)` com `open_end = interstice.start` dá o mesmo estado (`FORA`, `DENTRO`, `PARCIAL`) que com `interstice.end` para qualquer início, porque `end < interstice.start` nunca ocorre e `DENTRO`/`PARCIAL` só dependem de `start`; o motor trata o período aberto em `scoring_engine.py:186-191`, não pelo estado |
| N1b | `scoring_periods.py:98` | `start >= interstice.end` em vez de `>` (último dia fora) | `test_activity_validity.py::test_the_first_and_the_last_day_of_the_interstice_are_valid`, `test_scoring_periods.py::test_event_on_interstice_limits_is_dentro[edge1]`, `test_activity_edit_rules_api.py::test_the_first_and_the_last_day_of_the_interstice_are_accepted[2024-11-23]` | ✅ Killed (3 failed) |
| N2 | `app/application/services/generation_inputs.py:91` | `excluded` devolve `{"pendentes": 0}` em vez de `{}` | `test_generation_inputs.py::...leave_no_trace_in_excluded`, `test_generated_validity_acceptance.py::test_the_summary_counts_only_the_valid_activity`, `::...leave_no_trace_in_the_summary` | ✅ Killed (3 failed) |
| N3 | `app/application/use_cases/generated_documents.py:317-319` | mensagem do worker para `ATIVIDADE_SEM_CATEGORIA` trocada pela de `ORIGINAIS_EXCLUIDOS` | `test_run_generation_failure.py::test_a_valid_activity_without_category_after_the_request_fails_with_its_code` | ✅ Killed |
| N4 | `generation_inputs.py:111` | a recusa `ATIVIDADE_SEM_CATEGORIA` vale também para atividade não válida (sem `found.is_valid and`) | nenhum (35 passed) | ◻ Sobreviveu, **equivalente**: `classify_activity` (`activity_validity.py:75-119`) só devolve `needs_category=True` junto de `VALIDA` (`:90`); toda saída não válida passa por `_invalid(...)`, então o `is_valid and` é guarda redundante |
| N5 | `frontend/src/components/ActivityRow.tsx:74` | `if (!refocus.current) return;` sem o teste de `busy` | nenhum (56 passed) | ◻ Sobreviveu, **equivalente**: `refocus.current` só é preenchido no `catch`, imediatamente antes de `setBusy(false)` no `finally`; o efeito de `[busy]` só vê `refocus.current` preenchido quando `busy` já é `false` |
| N6 | `frontend/src/components/ActivityWorkspace.tsx:72` | `remember(id)` também quando a falha não recarrega a lista | `ActivityWorkspace.test.tsx` "uma falha que não recarrega (5xx) não deixa foco pendente..." | ✅ Killed (1 failed) |
| N6b | `ActivityRow.tsx:118` | sem o recurso ao título quando o controle saiu da árvore (`back?.focus()`) | nenhum (56 passed) | ◻ Sobreviveu, **mascarado**: com a linha fora da seção, `ActivityWorkspace.tsx:89-102` leva o foco ao título ou à seção (teste "409 cuja recarga tira a linha da seção leva o foco ao título da seção, nunca ao body"); o recurso da linha é defesa em profundidade sem efeito observável na tela montada (baixa; ver lacuna L1) |
| N7 | `app/application/use_cases/scoring.py:241` | limite superior da quantidade e do valor exclusivo (`< MAX_VALUE`) | `test_activity_create.py::test_quantity_limits_are_inclusive`, `::test_unit_points_override_accepts_the_range_limits[value1]` | ✅ Killed (2 failed) |
| N8 | `app/infrastructure/database/repositories.py:1385` | a contagem de atividades por documento (Etapa 2) conta as mescladas | `test_repositories_merge.py::test_a_merged_activity_does_not_count_as_citing_the_document` | ✅ Killed (1 failed, 1023 passed) |
| N9 | `frontend/src/trust.ts:22` | limiar de confiança do lote `>` em vez de `>=` (0,70 sai) | `ValidActivitiesSection.test.tsx` "valida numa só chamada as de 0,91 e 0,70, deixa a de 0,69..." | ✅ Killed |
| N10 | `frontend/src/activityList.ts:44` | busca por título sem remover acentos | `ValidActivitiesSection.test.tsx` "a busca por título ignora maiúsculas e acentos..." | ✅ Killed |

### Mutantes de fechamento (volta 0 reaplicados e os de G4, G6, G7)

| # | Mutante | Resultado |
| - | ------- | --------- |
| B27 | `generation_inputs.py:89`, não válida aguardando conta "pendentes" | ✅ Killed (agora) |
| B43 | `scoring.py:422`, `yearly = False` | ✅ Killed (agora) |
| F3b | `ValidActivitiesSection.tsx:73`, aviso conta só as filtradas | ✅ Killed (agora) |
| G4a | `list_for_process(include_merged=True)` por padrão | ✅ Killed (`:242`) |
| G4b | mesclagem não move as provas (`move([], ...)`) | ✅ Killed (`:219`) |
| G6 | `_FAILURE_MESSAGES` sem `ATIVIDADE_SEM_CATEGORIA` | ✅ Killed |
| G7 | `UpdateActivity` força `AGUARDANDO_REVISAO` | ✅ Killed |

### Volta 0 (resumo)

66 mutantes (B1 a B47 e F1 a F19): 63 mortos e 3 sobreviventes (B27, B43, F3b), listados em `9ef7001` e fechados acima. Os 63 mortos não foram reexecutados um a um; o gate completo (5281 + 563 testes) cobre a regressão deles e nenhum teste da volta 0 foi apagado ou afrouxado.

**Resultado do sensor**: 82 mutantes distintos no total (66 da volta 0, 12 novos e G4a, G4b, G6 e G7, mutantes próprios das lacunas), 0 sobreviventes com comportamento observável diferente. Os 4 sobreviventes da volta 1 (N1, N4, N5, N6b) foram analisados no código e são equivalentes ou mascarados por outra camada; o sensor passa.

---

## Code Quality

| Princípio | Status |
| --------- | ------ |
| Mínimo de código, sem recursos além do pedido | ✅ (a única mudança de produção da volta 1 é a entrada de 3 linhas em `_FAILURE_MESSAGES`, `generated_documents.py:317-319`) |
| Mudanças cirúrgicas, padrões do projeto | ✅ (os testes novos reusam os fixtures e helpers de cada arquivo; `# fmt: skip` só nos blocos de chamada larga, como o arquivo já fazia) |
| Testes mapeiam requisitos e não espelham a implementação | ✅ (valores de pontos, textos e códigos vêm da spec e da tabela; G7 afirma pontos pela tabela oficial, não pelo código) |
| Cobertura por camada | ✅ domínio 1:1; rotas com caminho feliz, borda e erro; documentos gerados agora com caso de atividade mesclada |
| Teste sem requisito | ✅ nenhum órfão: cada teste novo cita SEG-01, SEG-05, EDT-03, DUP-03, SEC-05 ou uma borda da spec |
| Diretrizes documentadas | CLAUDE.md: dados sintéticos nos testes (confirmado: títulos e datas inventados), sem justificativa nas Etapas 2, 3 e 4 (confirmado: nenhum campo de justificativa nos testes novos), `Documentos/`, `Modelos/`, `requeriment.txt` e `test/` não abertos |

## Gate Check

- **Backend** (`cd backend && ruff check . && pytest -q`, sobre a árvore real em `69ec5ed`, executado uma vez por este Verifier): `ruff` limpo (`All checks passed!`); `5281 passed, 3 deselected, 1 warning in 677.47s`, `pytest exit 0`. Os 3 `deselected` são `maritalk_live` (`pyproject.toml`, `addopts`).
- **Frontend** (`frontend/`, por este Verifier): `npm run lint` sem aviso; `npm run build` (`tsc -b && vite build`) concluído; `npx vitest run` com `563 passed (563)`, nenhum pulado (o teste de `bundle` roda porque o build gerou `dist`).
- **Contagem de testes**: backend 5269 (`9ef7001`) para 5281 (+12); frontend 561 para 563 (+2, contando o `bundle` que na volta 0 estava pulado). Nenhum teste removido.

---

## Lacunas ranqueadas (restantes)

| # | Gravidade | Lacuna | Requisito | Evidência |
| - | --------- | ------ | --------- | --------- |
| L1 | Baixa | O recurso ao título em `ActivityRow.tsx:118` quando o controle saiu da árvore só é exercido pela camada de cima (`ActivityWorkspace`); sem o workspace, nenhum teste pega a remoção (N6b) | SEC-12 (foco) | `F/components/ActivityRow.tsx:118`; `F/components/ActivityWorkspace.test.tsx:385` (cobre via workspace); sem consequência na tela montada |
| SP11 | Baixa | O texto do `error_message` do worker para `ATIVIDADE_SEM_CATEGORIA` não está na spec (coincide com o da recusa do pedido, `generation_inputs.py:113-116`) | SEG-05 | `B/integration/doc_usecases/test_run_generation_failure.py:72-74` |
| D1 | Baixa | `tasks.md` T61 cita `test_run_generation_table.py` em **Where**, o teste está em `test_run_generation_failure.py` | documentação | `.specs/features/revisao-simplificada/tasks.md:1774` |
| Q1 | Informativa | Perguntas abertas do AD-022 (digitar pontos de `VALOR_INFORMADO`; telas de arranjo do Comprovante e rascunho do relatório respondem 422 com atividade válida sem categoria) seguem para decisão do usuário, fora desta feature | fora do escopo | `.specs/STATE.md` AD-022, "Open questions" |

Nenhuma lacuna bloqueia: não há requisito sem teste, mutante com efeito observável sobrevivente, nem teste que contradiga a spec.

## Requirement Traceability Update

| Requisito | Status anterior | Novo status |
| --------- | --------------- | ----------- |
| VAL-01 a VAL-06, SEC-01 a SEC-12, DUP-01 a DUP-07, SEG-01 a SEG-05, EDT-01 a EDT-07, QTD-01 a QTD-03 | Implemented (SEC-05, SEC-12, DUP-03, SEG-01, SEG-02, SEG-05 e EDT-03 com lacuna na volta 0) | ✅ Verified (as 7 lacunas fechadas; SEC-12 com a limitação manual documentada) |

O Verifier não altera `spec.md`; o líder marca `Verified` na coluna de status de `spec.md` e em `design.md` ("Verified pendente da reverificação").

## Summary

**Overall**: ✅ Ready (PASS na volta 1 de 3)

**Spec-anchored check**: 40 de 40 requisitos com asserção alinhada à spec; SP1 a SP10 decididas, SP11 aberta e baixa
**Sensor**: B27, B43 e F3b mortos; 12 mutantes novos, 8 mortos e 4 equivalentes ou mascarados
**Gate**: backend 5281 passando; frontend 563 passando; ruff, lint e build limpos

**What works**: tudo o que a volta 0 listou, mais: `excluded` sem rastro das não válidas aguardando validação, período aberto por ano na criação e na edição, aviso de categoria com busca e filtro, mesclada fora da Tabela, do Relatório e do Comprovante, `ATIVIDADE_SEM_CATEGORIA` no worker, status final depois de trocar categoria ou corrigir carga horária.

**Issues found**: L1, SP11, D1, Q1 (nenhuma bloqueia).

**Next steps**: o líder marca `Verified` em `spec.md` e `design.md`, decide as perguntas abertas Q1 e, com a autorização do usuário, push e PR; a migração `0008` só vai à VM num deploy autorizado.
