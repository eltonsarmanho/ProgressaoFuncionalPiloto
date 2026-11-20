# Gestão de processos Verification

**Date**: 2026-11-19
**Spec**: `.specs/features/gestao-processos/spec.md` (GP-ARQ-01..06, GP-DEL-01..10), `design.md`, `tasks.md` (T1-T6)
**Diff range**: `938ad8d..1454c4b` (feature commits `9be5f6a` T1, `9630068` T2, `b88b178` T3, `ced34c2` T4, `1454c4b` T5+T6). Code at `1454c4b` is unchanged at HEAD (`eab6d36` and `4743abd` touch only `.specs/`, `CLAUDE.md`).
**Verifier**: independent sub-agent (author != verifier). It did not edit code or tests; the sensor ran in a scratch git worktree that was removed afterwards.

---

## Verdict: PASS (with 1 Medium and 3 Low gaps)

All 16 requirements have an asserting test that targets the spec-defined outcome. 21 mutants were injected, 20 killed, 1 survived (a Medium test gap in the API wiring of the generated-file storage, no production defect found). No Blocker or High finding.

| Item | Result |
| --- | --- |
| Spec-anchored check | 16 of 16 requirements covered with `file:line` evidence; GP-DEL-01 passes with the accepted deviation (see notes); 4 spec-precision notes |
| Gate backend | `ruff check .`: All checks passed. `pytest -q` (full, real PostgreSQL 16 via Docker): **5048 passed, 3 deselected** (`maritalk_live`, by `addopts`), 0 failed, 636 s |
| Gate frontend | `npm test -- --run`: **387 passed (387)**; `npm run build`: ok (371.45 kB js); `npx eslint .`: exit 0, no output |
| Sensor | 21 mutants (14 backend, 7 frontend): **20 killed, 1 survived** |
| Real tree | `git status --porcelain` before and after: only `?? requeriment.txt` and `?? test/`; worktree removed and pruned; nothing pushed, deployed or committed; VM untouched |

Feature tests: 59 backend tests in the four delete test files (`test_process_purge_repository.py`, `test_delete_process.py`, `test_process_delete_api.py`, `test_process_purge_trigger.py`) and 14 in `frontend/src/pages/Dashboard.test.tsx` (13 new).

---

## Task completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 migration 0007 | Done | `backend/alembic/versions/0007_process_purge.py:19-56`, downgrade `:59-87` |
| T2 purge repository | Done | `repositories.py:2006-2111` |
| T3 DeleteProcess + preview | Done | `use_cases/processes.py:254-312` |
| T4 routes | Done | `presentation/api/processes.py:81-95`, wiring `presentation/dependencies.py:280-281` |
| T5 front archive | Done | `ProcessDialogs.tsx:8-58`, `Dashboard.tsx` |
| T6 front delete | Done | `ProcessDialogs.tsx:60-153` |
| T7, T8 | T7 landed as docs commits `eab6d36`; T8 is this report | |

---

## Spec-anchored acceptance criteria

Production references: `UC` = `backend/app/application/use_cases/processes.py`, `REPO` = `backend/app/infrastructure/database/repositories.py`, `DLG` = `frontend/src/components/ProcessDialogs.tsx`, `DASH` = `frontend/src/pages/Dashboard.tsx`. Backend tests are under `backend/tests/integration/`, front tests in `frontend/src/pages/Dashboard.test.tsx` (`FT`).

### Arquivar

| Req | Spec-defined outcome | Production | Test `file:line` + assertion | Result |
| --- | --- | --- | --- | --- |
| GP-ARQ-01 | Button "Arquivar" on a card whose status is not ARQUIVADO | `DASH` (button guarded by `p.status !== "ARQUIVADO"`) | `FT:82-90` `getByRole("button", {name: "Arquivar processo de Docente Alfa"})` has text "Arquivar" for EM_ANDAMENTO | PASS |
| GP-ARQ-02 | Modal with the exact text "Arquivar o processo de <docente>? Ele fica somente leitura."; nothing sent before confirming; no justification field | `DLG:41-56` | `FT:92-105` text match, `queryByRole("textbox")` absent, `calls.filter(method !== "GET")` equals `[]` before and after Cancelar | PASS |
| GP-ARQ-03 | POST `/status` with `ARQUIVADO` and the current version; card shows "Arquivado" without reloading | `DLG:27-32`, `DASH` `archived()` | `FT:107-126` body `toEqual({status:"ARQUIVADO", expected_version: 4})`; "Arquivado" text; `total("Arquivado")` is "1"; list GET count is 1 | PASS |
| GP-ARQ-04 | No "Arquivar" button when already ARQUIVADO | `DASH` | `FT:89` `queryByRole("button", {name: /Arquivar/})` absent on the ARQUIVADO card | PASS |
| GP-ARQ-05 | 403 for non-ADMIN/non-owner; modal shows the message | server: `check_status_change` `UC:200-210`; front `DLG:33-36` | server `api/test_process_updates_api.py:191-200` `by_colleague.status_code == 403`; front `FT:128-142` alert has "Apenas ADMIN ou o dono do processo podem arquivá-lo" and the card stays "Rascunho" | PASS |
| GP-ARQ-06 | 409 on a changed version: modal shows the error and the list reloads | server `api/test_process_updates_api.py:182-187` (`409`); front `DLG:36` `onStale` | `FT:144-167` alert has the 409 text, card turns "Em andamento" after reload, list GET count is 2 | PASS |

### Excluir

| Req | Spec-defined outcome | Production | Test `file:line` + assertion | Result |
| --- | --- | --- | --- | --- |
| GP-DEL-01 | "Excluir" on every card in any status for ADMIN or owner | `DASH` (always rendered) | `FT:173-181` button "Excluir processo de <name>" for CONCLUIDO and ARQUIVADO. The role/owner part cannot be asserted in the front (see note 1) | PASS with accepted deviation |
| GP-DEL-02 | Modal says the deletion is final and lists documents, activities and generated documents; deletes only on "Excluir definitivamente" | `DLG:105-139` | `FT:183-201` "12 documentos de entrada", "30 atividades", "3 documentos gerados", "A exclusão é definitiva", no DELETE before confirming; `FT:294-304` button disabled when the preview failed; server preview `doc_usecases/test_delete_process.py:336-343` `counts == ProcessDeletionCounts(2, 2, 1)` and `api/test_process_delete_api.py:129-137` JSON equals `{"documents":2,"activities":0,"generated_documents":0}` | PASS |
| GP-DEL-03 | One transaction removes activities, candidates, evidences, inputs (runs, pages, jobs), generated documents with files, report draft, Comprovante layout, wording jobs and the process; 204 | `REPO:2070-2111` (order of deletes), `UC:287-302`, route `api/processes.py:81-84`, trigger exception `0007:19-56` | `documents/test_process_purge_repository.py:144-157` all 12 tables `== 0` after `purge`, each `> 0` before (`:148`); `:255-282` pg_constraint scan: the 6 direct FKs to `functional_processes` (`activities`, `documents`, `generated_documents`, `report_wording_jobs`, `report_drafts`, `comprovante_layouts`; `models.py:283,333,460,516,538,558`) equal `HANDLED_DIRECT`, and every non-cascade child FK is only `generated_files`; `:160-170` another process untouched; API 204 `api/test_process_delete_api.py:47-59` | PASS |
| GP-DEL-04 | After commit, input and generated files leave the disk; a failing removal only logs a warning with no full path or personal data, and the deletion stands | `UC:303-312`, `REPO:2080-2096` | `doc_usecases/test_delete_process.py:133-138` `disk_files == []` (4 files before); `:281-308` `PermissionError` on one file: process gone, one warning, file id in message, `internal_name`, `storage_root` and "Docente" absent from `caplog.text`; API `api/test_process_delete_api.py:67-74`; file of an already concluded document skipped `test_process_purge_repository.py:191-204` | PASS |
| GP-DEL-05 | `DELETE` audit event with the previous values; earlier audit events always kept | `UC:298-300` (`AuditAction.DELETE`, `audit_view(process)`), `0007:21`; `audit_logs` has no FK to the process (`models.py:188-200`) | `test_delete_process.py:250-261` one DELETE event, `user_id == admin`, `changes["current_class"] == {before, after: None}`, `changes["status"] == {before: before.status.value, after: None}`; `:264-278` `events[:-1] == earlier` and last action DELETE; `test_process_purge_trigger.py:110-127` enum has DELETE | PASS |
| GP-DEL-06 | 403 for non-ADMIN non-owner; 404 for missing or unreadable | `UC:254-263` | `test_delete_process.py:162-170` Forbidden "Apenas ADMIN ou o dono" and nothing deleted; `:141-159` owner docente and creator secretaria succeed; `:173-185` unreadable actors and unknown id raise NotFound; API `api/test_process_delete_api.py:91-100` 403 + message, `:110-117` 404 for outside unit and random id | PASS |
| GP-DEL-07 | 409 `OPERACAO_EM_ANDAMENTO` for a PROCESSING job, a GERANDO generation or a wording in progress; nothing deleted | `REPO:2019-2056`, `UC:292-297` | use case `test_delete_process.py:209-247` (`expect_busy`: `raised.value.code == "OPERACAO_EM_ANDAMENTO"`, process, documents, generated files, disk files and audit rows unchanged) for PENDENTE and PROCESSANDO jobs, GERANDO generation and wording; repo `test_process_purge_repository.py:294-333` each reason alone, `:352-366` all together; API `api/test_process_delete_api.py:77-88` `409` + `json()["code"] == "OPERACAO_EM_ANDAMENTO"` for the queued-document case | PASS |
| GP-DEL-08 | Card leaves the list and totals update without reloading | `DASH` `deleted()` | `FT:216-239` Alfa card absent, Beta present, `total("Total de processos")` "1", `total("Em andamento")` "0", list GET count 1; Edge 404 `FT:273-292` modal closes, card gone, list loaded twice | PASS |
| GP-DEL-09 | Any failing step: nothing deleted, no file removed | `REPO:2070-2111` (one session, no commit inside), `UC:301-312` (files only after `commit`) | `test_process_purge_repository.py:221-241` forced error on `DELETE FROM DOCUMENTS`: all rows and the process stay; `:244-252` no commit by itself; `test_delete_process.py:311-333` `commit` raises: process, documents, generated files, audit rows and the 4 disk files unchanged | PASS |
| GP-DEL-10 | After deletion every route of the process answers 404 | `_readable` in every use case | `api/test_process_delete_api.py:47-59` GET `""`, `/documents`, `/activities`, `/history`, `/delete-preview` and a second DELETE all 404, list empty; `test_delete_process.py:197-206` read and second delete NotFound | PASS (sample of routes, see gap 3) |

Additional spec lines checked: CSRF and auth `api/test_process_delete_api.py:120-126` (no CSRF 403, anonymous 401); `ProcessSummary.version` `:150-153` and `frontend/src/api/types.ts`; any status deletable `test_delete_process.py:187-194` (parametrized over `ProcessStatus`); trigger exception limited to `app.process_purge = 'on'`, UPDATE still blocked, setting gone after the transaction, downgrade restores `test_process_purge_trigger.py:28-107`; Edge "processo sem documentos" `test_process_purge_repository.py:207-213`.

---

## Discrimination sensor

Depth: P0-style (data-destroying, irreversible operation), 21 manual mutants, one at a time, in a scratch worktree (`git worktree add --detach`, node_modules symlinked, removed with `git worktree remove --force` and `prune`). Backend runs used the four delete test files (59 tests); frontend runs used `Dashboard.test.tsx`.

| # | File | Fault | Killed? | Killed by |
| --- | --- | --- | --- | --- |
| M1 | `REPO:2101` | skip `delete(ReportDraftModel)` | Killed | `test_delete_all_leaves_no_row_of_the_process_in_any_dependent_table` |
| M2 | `REPO:2099` | skip `delete(ReportWordingJobModel)` | Killed | same test |
| M3 | `REPO:2100` | skip `delete(ComprovanteLayoutModel)` | Killed | same test |
| M4 | `REPO:2042` | busy generation check compares to PRONTO instead of GERANDO | Killed | `test_busy_reasons_is_empty_for_a_quiet_process` (incidental: the quiet process has PRONTO generations) |
| M5 | `REPO:2033` | busy ignores PENDENTE jobs | Killed | `test_a_queued_or_running_extraction_makes_the_process_busy[PENDENTE]` |
| M6 | `UC:261-262` | ownership check removed | Killed | `test_a_reader_who_is_not_the_owner_gets_403_and_nothing_is_deleted` |
| M7 | `UC:301-303` | files removed before `commit` | Killed | `test_a_file_that_cannot_be_removed_only_logs_and_the_deletion_stands` |
| M8 | `REPO:2097` | previous audit events deleted (`DELETE FROM audit_logs WHERE entity_id`) | Killed | `test_an_admin_deletes_the_process_and_everything_below_it` (first failure; the audit-survival test also guards it) |
| M9 | `UC:298-300` | DELETE audit event not recorded | Killed | `test_the_deletion_writes_a_delete_event_with_the_previous_values` |
| M10 | `UC:292` | busy check skipped (`if False`) | Killed | `test_a_document_being_processed_blocks_the_deletion[PENDENTE]` |
| M11 | `UC:307` | `except OSError` replaced, so a removal failure is not swallowed | Killed | `test_a_file_that_cannot_be_removed_only_logs_and_the_deletion_stands` |
| M12 | `presentation/dependencies.py:280` | DELETE use case wired with `storage` instead of `generated_storage` | **Survived** | 59 passed |
| M13 | `REPO:2046` | busy never reports GERANDO generations | Killed | `test_a_generation_in_progress_makes_the_process_busy` |
| M14 | `REPO:2055` | busy never reports wording in progress | Killed | `test_a_wording_in_progress_makes_the_process_busy` |
| F1 | `DASH` `deleted()` | card not removed after 204 | Killed | `GP-DEL-08` test (`total("Total de processos")` stays 2) |
| F2 | `DLG:96` | 404 treated as an error | Killed | Edge 404 test (modal never closes) |
| F3 | `DLG:146` | 409 shows the server text instead of the label | Killed | `GP-DEL-07` front test |
| F4 | `DLG:30` | archive sends `version + 1` | Killed | `GP-ARQ-03` test |
| F5 | `DASH` | "Excluir" hidden when ARQUIVADO | Killed | `GP-DEL-01` test |
| F6 | `DLG:36` | 409 on archive does not reload the list | Killed | `GP-ARQ-06` test |
| F7 | `DLG:129` | "Excluir definitivamente" enabled before the preview loads | Killed | "falha ao carregar a prévia" test (`toBeDisabled`) |

**Result**: 20 of 21 killed. Survivor: M12.

Surviving mutant M12 is a real behavior fault, not an equivalent mutant: `LocalGeneratedStorage` roots at `<root>/generated` (`infrastructure/storage/generated_storage.py:25`) while `LocalFileStorage` roots at `<root>` (`local_storage.py:26`), so with the wrong instance the generated files would never be unlinked and stay on the server disk as orphans, silently (`unlink(missing_ok=True)`). The use-case tests inject the correct storages directly (`test_delete_process.py:73-77`), and the only API test that checks the disk (`api/test_process_delete_api.py:67-74`) uses an input document, never a generated one.

---

## Gaps, ranked

1. **Medium - generated-file removal is not tested through the real container wiring (GP-DEL-04, M12 survived).** `dependencies.py:280` passes `generated_storage` as the fifth argument; swapping it for `storage` leaves every test green and would leave generated documents on disk after a deployed delete. Fix task: an API test that creates a generated document with a file (see `generated_support.py` / `test_generated_documents_api.py` helpers), calls DELETE, and asserts the `generated/` directory holds no file.
2. **Low - GP-DEL-10 is asserted on 5 read routes and a repeated DELETE only** (`api/test_process_delete_api.py:56`). Mutating and generated-document routes (`POST /status`, report draft, Comprovante layout, conclusion, generated documents) are not exercised after deletion. They all go through `_readable` (404), so no defect is expected; add a parametrized sweep to pin it.
3. **Low - `GP-DEL-02` test title does not match its assertion** (`FT:203-214` "só habilita depois da prévia" asserts only `toBeEnabled()` after the preview). The disabled-before-preview behavior is protected only indirectly by `FT:294-304` (mutant F7 killed), not by an explicit assertion before the preview resolves.
4. **Low - DeleteProcess logs only `OSError` after the commit** (`UC:307`). An unexpected non-`OSError` from storage would surface as a 500 although the process is already deleted. Not required by the spec text ("algum arquivo não puder ser removido"), no test pins it; consider catching `Exception` for this loop. Observation only, not a spec violation.

## Spec-precision notes

1. **GP-DEL-01 (accepted deviation).** The spec says the button shows "WHEN o usuário é ADMIN ou dono". `ProcessSummary` has no ownership field, so the front shows "Excluir" to every user and relies on the 403 (and on the preview's 403, which already blocks the confirm button, `FT:294-304`). The test asserts presence for any status only. The deviation is consistent with design GP-D8 ("o servidor decide o 403 e a mensagem aparece no modal") and is not a failure. If the spec is kept literal, add `can_delete`/`is_owner` to `ProcessSummary`.
2. **GP-DEL-05** does not name the audited fields. The test asserts `current_class` and `status` (`test_delete_process.py:260-261`) out of the full `audit_view(process)`; "valores anteriores" is covered in part. Name the required fields in the spec to make the test exact.
3. **GP-DEL-07** says "tarefa `PROCESSING`"; the model enum is `PENDENTE`/`PROCESSANDO` and the design counts queued jobs as busy (GP-D4). Tests assert both states, so the implementation matches the design, which is stricter than the spec text. Align the spec wording.
4. **GP-DEL-08** says "totais" without naming them; the test asserts "Total de processos" and the status counter of the removed card.
5. Concurrency (row lock taken in `busy_reasons` and `delete_all`, `REPO:2022-2026,2073-2077`) is a design choice beyond the spec and has no test; not a requirement gap.

## Code quality

| Principle | Status |
| --- | --- |
| Minimum code, no scope creep | Pass: new port, repository, two use cases, two routes, one dialog file; `ProcessSummary.version` is needed by GP-ARQ-03 |
| Matches existing patterns (`_ProcessUseCase`, `PurgeRepository`, `Modal`, `GENERATION_CODE_LABELS`) | Pass |
| Spec-anchored outcome check | Pass, with the notes above |
| Per-layer coverage (repository 1:1 with tables and FKs, use case with each error, API with each status) | Pass; gap 1 and 2 above |
| Tests only on synthetic data; no `Documentos/` or `Modelos/` opened | Pass |
| Documented guidelines | `CLAUDE.md` gates followed (ruff, pytest, frontend test, build, eslint) |

## Requirement traceability (proposed)

All of GP-ARQ-01..06 and GP-DEL-01..10: Verified (GP-DEL-01 with the accepted deviation; GP-DEL-04 and GP-DEL-10 with Low/Medium follow-up tests above). T7's table update is the author's task; this report changes no other file.

## Resolução (2026-11-19)

- Lacuna 1 (média, `generated_storage` não testado pela ligação real): corrigida com `backend/tests/integration/api/test_process_delete_generated.py`, que apaga um processo com a Tabela gerada pela API e confere que os arquivos saem do disco e as linhas somem; trocando `generated_storage` por `storage` em `dependencies.py` o teste falha (2 falhas), com o código restaurado em seguida.
- Lacuna 2 (baixa, GP-DEL-10): o mesmo arquivo confere 404 nas rotas de pontuação, tabela escolhida, rascunho do relatório, arranjo do Comprovante, conclusão e documentos gerados depois da exclusão.
- Lacunas 3 e 4 (baixas): aceitas; a 4 (exceção diferente de `OSError` na remoção, depois do commit) fica como observação.
