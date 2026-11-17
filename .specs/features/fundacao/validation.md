# Fundação Validation

**Verdict**: FAIL ❌

**Iteration**: 2 of 3
**Date**: 2026-11-16
**Spec**: `.specs/features/fundacao/spec.md` (60 requirement IDs)
**Diff range**: `3387587..e6875e4` (branch `feat/fundacao`, 34 commits). Fix commits since iteration 1: `af7e27d..e6875e4` (T29–T32)
**Verifier**: independent sub-agent (author ≠ verifier), evidence-or-zero

Why FAIL: two discrimination-sensor mutants survived on the new CARR-09/CARR-10 code in `backend/app/application/use_cases/career.py`. Both change a date comparison at the exact boundary day the spec names, and no test exercises that day:

- **N4** (`career.py:125`, `process.end_date >= new.valid_from` → `>`). CARR-10 says "data final **em ou após** o início da nova versão". With the mutant, a process ending exactly on the new version's start date no longer blocks the close. That process then silently moves to the new version, which is the outcome CARR-10 exists to prevent.
- **N5** (`career.py:121`, `new.valid_from <= open_version.valid_from` → `<`). CARR-09 applies only when the new version "começa **depois** do início" of the open one. With the mutant, a version that starts on the same day as the open version closes it to `valid_to = valid_from − 1 day`, an inverted validity. The overlap check then accepts the new version (201) instead of rejecting it (409).

Every other check passes: all 60 IDs have evidence whose asserted value matches the spec outcome, all 5 edge cases are covered, every gate is green, and the iteration-1 survivors (M14, M15, M20) are now killed.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T28 | ✅ Done | Unchanged since iteration 1 |
| T29 | ✅ Done | Auto-close of the open version (CARR-09) and 409 guard (CARR-10). Boundary days not tested (N4, N5) |
| T30 | ✅ Done | PROC-09 invalid-date rule pinned; kills M20 |
| T31 | ✅ Done | 5 parametrized `DADOS_INCOMPLETOS` cases; kills M14 and M15 |
| T32 | ✅ Done | `docker rm -f -v` in `scripts/smoke_backend.sh`; volume count 61 → 61 |

`tasks.md`: 0 unchecked `Done when` boxes.

---

## Spec-Anchored Acceptance Criteria

Test paths are relative to `backend/tests/` unless they start with `frontend/` or `scripts/`. Every citation below was re-read at HEAD `e6875e4`.

### P1: Stack executável

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| INFRA-01 | 4 services up; `GET /api/health` via nginx → 200 `{"status":"ok","database":"ok"}` within 120 s | `scripts/smoke.sh:55` - `[ "$body" = '{"status":"ok","database":"ok"}' ]` inside the 120 s loop; `integration/api/test_health_api.py:14-15` - `status_code == 200`, exact body | ✅ PASS (smoke run: 200 after 13 s) |
| INFRA-02 | Migrations applied before serving | `scripts/smoke_backend.sh:57` - `[ "$db_rev" = "$head_rev" ]`; `integration/test_migrations.py:40,46` | ✅ PASS (smoke_backend: "alembic at head (0001)") |
| INFRA-03 | DB down → 503 `{"status":"degraded","database":"unavailable"}` | `integration/api/test_health_api.py:27-28` - `status_code == 503`, exact body | ✅ PASS |
| INFRA-04 | pgdata and `storage/` survive `down` without `-v` | `scripts/smoke.sh:129-130` | ✅ PASS (smoke run: "professor and storage file preserved") |
| INFRA-05 | `.env.example` covers every variable, no real secret | `scripts/smoke.sh:80` | ✅ PASS (no-secret half checked by inspection) |
| INFRA-06 | `MARITALK_API_KEY` never exposed | `unit/test_config.py:65-68` - key not in `repr/str/model_dump/model_dump_json` | ✅ PASS |
| INFRA-07 | Missing var → exit naming it, no other values | `unit/test_config.py:44-47,55-56` | ✅ PASS |

### P1: Autenticação e controle de acesso

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| AUTH-01 | 200 with id, name, role; cookie HttpOnly/Secure/SameSite=Strict | `integration/api/test_auth_api.py:24-31` | ✅ PASS |
| AUTH-02 | 401 "Usuário ou senha inválidos", same for both causes | `integration/api/test_auth_api.py:59-60` - `json() == {"detail": "Usuário ou senha inválidos"}` (parametrized) | ✅ PASS |
| AUTH-03 | No session → 401 | `integration/api/test_auth_api.py:90,96` | ✅ PASS |
| AUTH-04 | 5 failures in 15 min → 429 until the window ends | `integration/api/test_auth_api.py:71` - `blocked.status_code == 429`; `:75`; `integration/test_auth_use_cases.py:106-112` | ✅ PASS (M10 killed) |
| AUTH-05 | 30 min idle or 8 h absolute → 401 | `integration/api/test_auth_api.py:154,162,166`; `integration/test_auth_use_cases.py:122-176` | ✅ PASS |
| AUTH-06 | Write without valid CSRF → 403 | `integration/api/test_auth_api.py:130` - `status_code == 403` | ✅ PASS |
| AUTH-07 | Argon2id only | `unit/test_security.py:14-15`; `integration/api/test_users_api.py:48` | ✅ PASS |
| AUTH-08 | DOCENTE, other professor's process → 404 | `integration/api/test_processes_api.py:197-198` - `== 404`, `{"detail": "Processo não encontrado"}` | ✅ PASS (M6 killed) |
| AUTH-09 | SECRETARIA, other unit → 404 | `integration/api/test_processes_api.py:185`; `integration/api/test_process_updates_api.py:211-213` | ✅ PASS |
| AUTH-10 | Unique e-mail, name, role, password ≥ 10; 422 naming the field | `integration/api/test_users_api.py:91-92,102,112-113` | ✅ PASS |
| AUTH-11 | Logout invalidates the server session | `integration/api/test_auth_api.py:141-145` | ✅ PASS |

### P1: Cadastro de docente

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| DOC-01 | 9 fields persisted | `integration/api/test_professors_api.py:47` - round-trip `== payload` | ✅ PASS |
| DOC-02 | SIAPE not 7 digits → 422 on `siape` | `integration/api/test_professors_api.py:60-61` | ✅ PASS |
| DOC-03 | Duplicate SIAPE → 409, no duplicate | `integration/api/test_professors_api.py:73-75` | ✅ PASS |
| DOC-04 | Titration and regime enums | `integration/api/test_professors_api.py:89-90,111`; `unit/domain/test_process_entities.py:65-77` | ✅ PASS |
| DOC-05 | Edit → audit event | `integration/api/test_professors_api.py:131-138` | ✅ PASS |

### P1: Processo e interstício

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| PROC-01 | All fields persisted, unique id, `RASCUNHO` | `integration/api/test_processes_api.py:38-43` | ✅ PASS |
| PROC-02 | Full civil months and days; days = end − start (Assumption, agent default, `Confirmed? n`) | `integration/api/test_processes_api.py:69` - `interstice == {"months": 24, "days": 731}` (FASI, 23/11/2022→23/11/2024, includes 29/02/2024); `:171` - `{"months": 24, "days": 730}` (the Assumption's own example) | ✅ PASS. The day-count rule is now written in the spec. User confirmation is still pending |
| PROC-03 | Saved exactly as informed | `integration/api/test_processes_api.py:107` - `{k: stored[k] for k in payload} == payload`; `unit/domain/test_process_verification.py:323` - `REQUERIMENTO_2024_2026 == before` | ✅ PASS |
| PROC-04 | Checks on save and read; code, severity, PT message, norm reference | `integration/api/test_processes_api.py:102,108`; `unit/domain/test_process_verification.py:313-314` - `message.strip()`, `norm_reference.strip()` | ✅ PASS. The generic `DADOS_INCOMPLETOS` reference is now a spec Assumption (agent default, `Confirmed? n`) |
| PROC-05 | end ≤ start → `ERRO` `INTERSTICIO_DATAS_INVALIDAS` | `unit/domain/test_process_verification.py:98` - `severity is Severity.ERRO` for equal and earlier end dates; `:105` - `codes(alerts) == [INTERSTICIO_DATAS_INVALIDAS]` | ✅ PASS |
| PROC-06 | end > opening → `ALERTA` `INTERSTICIO_NAO_CONCLUIDO` | `unit/domain/test_process_verification.py:112`; `:117` (equal → none) | ✅ PASS |
| PROC-07 | PROGRESSAO rules → `ERRO` `MODALIDADE_INCOMPATIVEL` | `unit/domain/test_process_verification.py:132` (3 cases) | ✅ PASS |
| PROC-08 | PROMOCAO rules → `ERRO` `MODALIDADE_INCOMPATIVEL` | `unit/domain/test_process_verification.py:169` (3 cases); `:149` valid → `[]` | ✅ PASS |
| PROC-09 | months < minimum → `ERRO` `INTERSTICIO_INSUFICIENTE` with months and minimum; with invalid dates, only `INTERSTICIO_DATAS_INVALIDAS` (Assumption, confirmed) | `unit/domain/test_process_verification.py:186-189` (24 vs 36); `:195-197` (23 vs 24); `:105` - `codes(alerts) == [AlertCode.INTERSTICIO_DATAS_INVALIDAS]` for end 01/02/2025 and 15/01/2025 on a 24-month progression | ✅ PASS (M20 killed) |
| PROC-10 | FASI: Res. 4.644, 24 months, zero `ERRO` | `unit/domain/test_process_verification.py:288,290,294`; `integration/api/test_processes_api.py:69-72` | ✅ PASS |
| PROC-11 | Requerimento: Lei 15.141, exactly the 5 codes | `unit/domain/test_process_verification.py:299,303-304` - `len == 5`, exact code→severity map | ✅ PASS |
| PROC-12 | `CONCLUIDO`/`ARQUIVADO` → 409 | `integration/api/test_process_updates_api.py:109-111` | ✅ PASS (M12 killed) |
| PROC-13 | `EM_ANDAMENTO` without justification → 422 on `justificativa` | `integration/api/test_process_updates_api.py:76-77` | ✅ PASS (M7 killed) |
| PROC-14 | Scoped list with status, professor, modality, interstice, alert counts | `integration/api/test_processes_api.py:165-174` | ✅ PASS |

### P1: Estruturas de carreira versionadas

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| CARR-01 | Version containing the end date | `unit/domain/test_career.py:38-43` | ✅ PASS (M2 killed) |
| CARR-02 | Two seeded versions | `unit/domain/test_career_catalog.py:20-66`; `integration/test_seed.py:48-53` | ✅ PASS |
| CARR-03 | Minimum interstices | `unit/domain/test_career_catalog.py:33-54`; `unit/domain/test_career.py:75-78` | ✅ PASS |
| CARR-04 | Missing class/level → `ERRO` `CLASSE_INEXISTENTE_NA_ESTRUTURA` | `unit/domain/test_process_verification.py:211` | ✅ PASS |
| CARR-05 | Crosses 01/01/2025 → `REQUER_ANALISE_NORMATIVA`, cites Lei 15.141/2025 | `unit/domain/test_process_verification.py:219-220`; `:225`; `unit/domain/test_interstice.py:55` | ✅ PASS (M9 killed) |
| CARR-06 | Denomination mismatch → `ALERTA`, expected shown | `unit/domain/test_process_verification.py:234-235` | ✅ PASS |
| CARR-07 | No version → `ESTRUTURA_NAO_CADASTRADA`, skip dependent checks | `unit/domain/test_process_verification.py:251-252` | ✅ PASS |
| CARR-08 | ADMIN registers a version with a mandatory reference, without editing versions used by processes | `integration/api/test_career_api.py:197` - 201 **while the Lei version is in use** (now reachable); `:105-106` reference required → 422 `["norm_reference"]`; `:167-168` PUT on a used version → 409, `valid_to is None`; `:177` overlap with a closed version → 409 | ✅ PASS (the iteration-1 blocker is resolved) |
| CARR-09 | New version starting **after** the open one's start → open version closed the day before; audit UPDATE `valid_to` null → new | `integration/api/test_career_api.py:197-204` - `201`, `versions[LEI]["valid_to"] == "2030-12-31"`, `(event.action, event.user_id) == (UPDATE, actor.id)`, `event.changes == {"valid_to": {"before": None, "after": "2030-12-31"}}` | ⚠️ Outcome matches; boundary not discriminated. No test posts a version starting on the same day as the open version, so N5 survives |
| CARR-10 | Closing would leave a process with end date **on or after** the new start → 409, nothing created, open version unchanged | `integration/api/test_career_api.py:217-220` - `409`, `versions[LEI]["valid_to"] is None`, `"Versão futura" not in versions` (new start 01/01/2026, process ends 23/11/2026) | ⚠️ Outcome matches; boundary not discriminated. No test uses an end date equal to the new start, so N4 survives |

### P1: Trilha de auditoria

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| AUD-01 | Event with user, UTC time, entity, id, before/after, justification | `integration/api/test_users_api.py:50-61`; `integration/api/test_process_updates_api.py:92-95,200-203`; `integration/api/test_career_api.py:86-87,203-204` | ✅ PASS (M8 killed in iteration 1) |
| AUD-02 | No change or deletion of audit events via the API | `integration/test_migrations.py:86-93` - `pytest.raises(DBAPIError, match="append-only")`, row unchanged | ✅ PASS |
| AUD-03 | Chronological history | `integration/api/test_process_updates_api.py:197-199` - `["CREATE","STATUS","UPDATE"]`, `times == sorted(times)` | ✅ PASS |
| AUD-04 | Logs carry identifiers only | `integration/api/test_logging_api.py:62-63` - `leaked == []` | ✅ PASS |

### P1: Interface web

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| UI-01 | No session → login | `frontend/src/App.test.tsx:28-29` | ✅ PASS |
| UI-02 | Dashboard totals, per status, alert counts | `frontend/src/pages/Dashboard.test.tsx:43-58` | ✅ PASS |
| UI-03 | Duration plus alerts by severity with reference | `frontend/src/pages/ProcessStep1.test.tsx:84-106` | ✅ PASS |
| UI-04 | 9 steps, step 1 active, 2–9 disabled "em breve" | `frontend/src/pages/ProcessStep1.test.tsx:139-148` | ✅ PASS |
| UI-05 | 422 → message next to the field | `frontend/src/pages/ProfessorForm.test.tsx:68-71`; `frontend/src/pages/ProcessStep1.test.tsx:171-173` | ✅ PASS |
| UI-06 | Usable at 360 px without horizontal scroll | `frontend/src/styles.test.ts:22` - `expect(tooWide).toEqual([])`; `:26-27` fluid container and device viewport | ⚠️ Proxy evidence (static CSS scan, no real browser at 360 px). Unchanged since iteration 1 and not blocking. A headless check fits the `implantacao` feature |

### P2: Unidades acadêmicas

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| UNIT-01 | ADMIN creates, edits and archives units | `integration/api/test_units_api.py:31-39,50-56,65-71,116` | ✅ PASS |
| UNIT-02 | Archived unit → 422 | `integration/api/test_professors_api.py:167-170`; `integration/api/test_processes_api.py:135-138` | ✅ PASS |
| UNIT-03 | Seed Cametá, FASI, IFCH | `integration/test_seed.py:62-76` | ✅ PASS |

**Status**: 60/60 IDs have evidence whose asserted value matches the spec outcome. 0 spec-precision gaps: PROC-02, PROC-04 and PROC-09 are now defined in the spec Assumptions, and CARR-08 is resolved by CARR-09/CARR-10. Two ACs (CARR-09, CARR-10) are not discriminating at the boundary day the spec names (sensor N5, N4). UI-06 still rests on proxy evidence.

---

## Edge Cases

- [x] End 31/12/2024 → Res. 4.644; end 01/01/2025 → Lei 15.141: `unit/domain/test_career.py:38-43`
- [x] 29/02/2024 → 28/02/2026 = 24 months: `unit/domain/test_interstice.py:18,23`; 27/02 → 23 at `:29`
- [x] Concurrent save → first wins, second 409: `integration/test_repositories.py:236` (`pytest.raises(StaleVersion)`), `:241-242`; `integration/api/test_process_updates_api.py:120-122`
- [x] Archived professor → reading kept, new process 422: `integration/api/test_process_updates_api.py:228-230`
- [x] Empty optional fields → saved plus `ALERTA` `DADOS_INCOMPLETOS` listing them: `unit/domain/test_process_verification.py:282-283` - for each of the 5 fields on its own, `severity is Severity.ALERTA` and `message == f"Campos não preenchidos: {label}."`; `:260-265` combined case; `integration/api/test_processes_api.py:117-120`. Now discriminating (M14 and M15 killed)

5/5 covered.

---

## Discrimination Sensor

Expanded tier. Run in an isolated `git worktree` at `e6875e4` under the session scratchpad, against a dedicated throwaway Postgres (`TEST_DATABASE_URL`, container removed with `-v`). The real `backend/.venv` was reused read-only, and imports were confirmed to resolve from the worktree. The unmutated worktree was green first (284 passed). Each mutant was applied by exact single-occurrence replacement, then the full backend suite ran with `-x`, then the file was reverted with `git checkout`.

| # | File:line | Mutation | Killed? |
| - | --------- | -------- | ------- |
| M14 | `backend/app/domain/rules/process_verification.py:74` | `resp_admin_unit` removed from `OPTIONAL_FIELDS` (re-run) | ✅ Killed by `test_each_empty_optional_field_is_reported[resp_admin_unit]` |
| M15 | `process_verification.py:72` | `resp_position` removed from `OPTIONAL_FIELDS` (re-run) | ✅ Killed by `[resp_position]` |
| M20 | `process_verification.py:148` | `if dates_ok and minimum` → `if minimum` (re-run) | ✅ Killed by `test_invalid_dates_do_not_also_emit_insufficient_interstice[end0]` |
| N1 | `backend/app/application/use_cases/career.py:130` | Close at `new.valid_from` instead of the day before | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| N2 | `career.py:125` | Process end-date check skipped (`and False`) | ✅ Killed by `test_closing_that_would_move_an_existing_process_returns_409` |
| N3 | `career.py:163` | Audit record of the closing skipped | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| N4 | `career.py:125` | `process.end_date >= new.valid_from` → `>` | ❌ **Survived** (284 passed) |
| N5 | `career.py:121` | `new.valid_from <= open_version.valid_from` → `<` | ❌ **Survived** (284 passed) |
| N6 | `career.py:162` | Closed version not substituted into `existing` before the overlap check | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| M1 | `backend/app/domain/rules/interstice.py:23` | Month count `end.day < start.day` → `<=` (re-run) | ✅ Killed |
| M2 | `backend/app/domain/entities/career.py:35` | `moment <= valid_to` → `<` (re-run) | ✅ Killed |
| M6 | `backend/app/application/services/access_policy.py:25` | DOCENTE may read any process (re-run) | ✅ Killed |
| M7 | `backend/app/application/use_cases/processes.py:161` | Justification not required in `EM_ANDAMENTO` (re-run) | ✅ Killed |
| M9 | `interstice.py:32` | `crosses`: `moment <= end` → `<` (re-run) | ✅ Killed |
| M10 | `backend/app/application/use_cases/auth.py:14` | `MAX_FAILURES` 5 → 6 (re-run) | ✅ Killed |
| M12 | `backend/app/domain/entities/process.py:20` | `is_read_only` always False (re-run) | ✅ Killed |

Why N4 and N5 are not equivalent mutants:
- **N4**: take a process ending 01/01/2031 and a new version starting 01/01/2031. The real code returns 409. The mutant closes the Lei version on 31/12/2030 and returns 201, so that process now resolves to the new version. This violates CARR-10 ("em ou após").
- **N5**: with no processes, post a version starting 01/01/2025, the open Lei version's start date. The real code skips the close, the overlap check fires, and the API returns 409. The mutant closes the Lei version to `valid_to = 2024-12-31 < valid_from = 2025-01-01`. That inverted range overlaps nothing, so the API returns 201 and leaves corrupt data. This violates CARR-09 ("começa depois do início").

**Sensor depth**: expanded (16 mutations: 3 iteration-1 survivors, 6 on new code, 7 iteration-1 kills re-run)
**Result**: 14/16 killed. FAIL ❌
**Isolation**: real-tree `git status --porcelain` was empty before and after. The worktree was removed and pruned, the sensor container was removed with its volume, and the volume count is back to the session baseline of 60.

---

## Gate Check

- **Backend**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` → ruff: All checks passed; pytest **284 passed**, 0 failed, 0 skipped (1 Starlette deprecation warning)
- **Frontend**: `npm run lint && npm test -- --run && npm run build` → lint exit 0; vitest **14 passed** (6 files); build OK
- **smoke_backend**: `./scripts/smoke_backend.sh` → **PASS** (health 200, alembic at head 0001, uid 10001); `docker volume ls -q` **61 before, 61 after**. T32 is fixed
- **smoke**: `./scripts/smoke.sh` → **PASS** (health 200 via nginx after 13 s, only nginx publishes a port, SPA and deep links, login, data and storage survive `down`/`up`); volumes 60 → 60
- **Test count**: iteration 1 had 275 backend tests; now 284 (+9: 2 PROC-09, 5 DADOS_INCOMPLETOS, CARR-09, CARR-10; the old overlap test was rewritten, not deleted). Frontend unchanged at 14
- **Skipped tests**: none
- **Hygiene (non-AC)**: the backend pytest gate leaks one anonymous Postgres volume per run. `backend/tests/integration/conftest.py:70` runs `docker rm -f` without `-v` on a `--rm` container. Observed volume count went 60 → 61 after the gate run, and the verifier removed the leaked volume. This is the same defect class T32 fixed in the smoke script

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code / surgical changes / no scope creep | ✅ Fix diff touches 4 code/test files plus the smoke script |
| Matches patterns (reuses `_reject_overlap`, `AuditService`, `_audit_view`) | ✅ |
| Spec-anchored outcome check | ✅ 60/60; ⚠️ CARR-09/10 boundary days untested |
| Per-layer coverage | ✅ |
| Every test maps to a spec requirement | ✅ New tests are tagged `# CARR-09`, `# CARR-10`, `# PROC-09 + Assumption`, `# Edge case` |
| Documented guidelines: `.specs/STATE.md` decisions; otherwise strong defaults applied | ✅ |
| Hygiene | ⚠️ `backend/tests/integration/conftest.py:70` leaks a volume per run |

---

## Fix Plans

### Fix 1: Pin the CARR-10 boundary (Major, kills N4)
- **Root cause**: the CARR-10 test uses a process ending 23/11/2026 against a new start of 01/01/2026, about 11 months apart. Nothing exercises "em" (equal day).
- **Fix task**: in `backend/tests/integration/api/test_career_api.py`, add a test that creates a process whose interstice ends on the new version's start date (for example, end 01/01/2031 with `NEW_VERSION`). Assert 409, `versions[LEI]["valid_to"] is None` and `"Versão futura" not in versions`. Optionally add the day-before case (end 31/12/2030 → 201).
- **Done when**: N4 is killed.

### Fix 2: Pin the CARR-09 "depois" boundary (Major, kills N5)
- **Root cause**: no test posts a version starting on the same day as the open version.
- **Fix task**: add a test that posts `{**NEW_VERSION, "valid_from": "2025-01-01"}` with no processes. Assert 409, the Lei `valid_to` is still `None` and the new version is absent.
- **Done when**: N5 is killed.

### Fix 3: Stop the pytest volume leak (Minor, hygiene)
- Change `backend/tests/integration/conftest.py:70` to `docker rm -f -v`.
- **Done when**: `docker volume ls -q | wc -l` is the same before and after the backend gate.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INFRA-01..07, AUTH-01..11, DOC-01..05, PROC-01..14, CARR-01..08, AUD-01..04, UI-01..05, UNIT-01..03 | Implementing | ✅ Verified |
| UI-06 | Implementing | ⚠️ Verified (proxy evidence) |
| CARR-09, CARR-10 | Implementing | ❌ Needs Fix (boundary not discriminated: N5, N4) |

---

## Iteration History

| Iteration | Verdict | Summary |
| --------- | ------- | ------- |
| 1 (`3387587..cc9c41d`) | FAIL ❌ | 57/58 ACs. CARR-08 unreachable once the open version was in use. M14, M15 and M20 survived (17/20 killed). Spec-precision gaps on PROC-02, PROC-04, PROC-09 and CARR-08. Smoke backend leaked a volume |
| 2 (`3387587..e6875e4`) | FAIL ❌ | The user added CARR-09/CARR-10 and confirmed Assumptions; T29–T32 implemented them. CARR-08 now reachable, M14/M15/M20 killed, spec-precision gaps closed, smoke volume leak fixed. New survivors N4 and N5 on the boundary days of CARR-10 and CARR-09 (14/16 killed) |

---

## Summary

**Overall**: ❌ Not Ready (one more fix round needed; iteration 3 is the last before escalation)

**Spec-anchored check**: 60/60 IDs matched the spec outcome; 0 spec-precision gaps; CARR-09/CARR-10 boundaries not discriminated
**Sensor**: 14/16 mutations killed (N4, N5 survived)
**Gate**: backend 284 passed, frontend 14 passed, smoke_backend PASS (volumes 61/61), smoke PASS

**What works**: every iteration-1 gap is closed. CARR-08 is reachable through the auto-close, with audit and the 409 guard. The PROC-09 invalid-date rule is pinned. Each `DADOS_INCOMPLETOS` field is checked on its own. The smoke script no longer leaks a volume.

**Issues found**: two missing boundary-day tests in `test_career_api.py` (Fix 1, Fix 2); the pytest volume leak (Fix 3, hygiene).

**Next steps**: route Fix 1 and Fix 2 (and optionally Fix 3) to an implementer, then re-verify in iteration 3.
