# Fundação Validation

**Verdict**: FAIL ❌ (escalate: iteration 3 of 3)

**Iteration**: 3 of 3
**Date**: 2026-11-16
**Spec**: `.specs/features/fundacao/spec.md` (60 requirement IDs, 5 edge cases)
**Diff range**: `3387587..6c022e1` (branch `feat/fundacao`). Fix commits since iteration 2: `6b8a2c7..6c022e1` (T33 `4ddebbf`, T34 `6c022e1`)
**Verifier**: independent sub-agent (author ≠ verifier), evidence-or-zero

Why FAIL: all three iteration-2 gaps are closed (N4 and N5 are killed, and the pytest volume leak is fixed). But three new boundary mutants on the same career-version code survive. Each one is non-equivalent and violates a spec outcome:

- **K1** (`backend/app/application/use_cases/career.py:80`, `b.valid_from <= a.valid_to` → `<`). Posting a version valid 31/12/2024–31/12/2024 should return 409, because it shares 31/12/2024 with the closed Res. 4.644 version. The mutant returns 201, so two versions then cover one date. This violates the confirmed Assumption that overlapping validities are refused, and CARR-01's single applicable version.
- **K2** (`career.py:77`, `a.valid_from <= b.valid_to` → `<`). Posting a version valid 01/01/2025–01/01/2025 should return 409, because it shares 01/01/2025 with the open Lei version. The mutant returns 201.
- **K3** (`career.py:125`, `process.end_date >= new.valid_from` → `>= new.valid_from - 1 day`). Take a process ending 31/12/2030 and a new version starting 01/01/2031. Closing Lei on 31/12/2030 still covers that process, so CARR-10 does not apply and CARR-09 requires the close (201). The mutant returns 409.

The real code is correct in all three scenarios. A probe test run in the scratch worktree passed 3/3 unmutated, and each mutant failed exactly its own probe. The gap is in the tests, not the implementation.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T32 | ✅ Done | Unchanged since iteration 2 |
| T33 | ✅ Done | CARR-10 "em" boundary (`test_career_api.py:224-239`) and CARR-09 same-start boundary (`:243-252`). Kills N4 and N5 |
| T34 | ✅ Done | `backend/tests/integration/conftest.py:70` now `docker rm -f -v`; volume count 64 → 64 across the backend gate |

`tasks.md`: 0 unchecked `Done when` boxes.

---

## Spec-Anchored Acceptance Criteria

Test paths are relative to `backend/tests/` unless they start with `frontend/` or `scripts/`. Since `e6875e4`, the only test files that changed are `integration/api/test_career_api.py` (lines appended after 220) and `integration/conftest.py` (line 70). All other citations keep their iteration-2 line numbers. They were spot-checked at HEAD `6c022e1`, including `test_processes_api.py:69,171,197-198`, `test_process_verification.py:105,282-283,303-304`, `test_auth_api.py:59-60`, `test_process_updates_api.py:109-111`, `test_migrations.py:86-93`, `test_repositories.py:236`, `frontend/src/styles.test.ts:22` and `scripts/smoke.sh:55`.

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
| CARR-08 | ADMIN registers a version with a mandatory reference, without editing versions used by processes; overlapping validities refused (confirmed Assumption) | `integration/api/test_career_api.py:197` - 201 while the Lei version is in use; `:105-106` reference required → 422 `["norm_reference"]`; `:167-168` PUT on a used version → 409, `valid_to is None`; `:177` overlap inside a closed version → 409 | ⚠️ Outcome matches, but the overlap rule is not discriminated on a single shared day (K1, K2 survive) |
| CARR-09 | New version starting **after** the open one's start → open version closed the day before; audit UPDATE `valid_to` null → new | `integration/api/test_career_api.py:197-204` - `201`, `versions[LEI]["valid_to"] == "2030-12-31"`, audit `changes == {"valid_to": {"before": None, "after": "2030-12-31"}}`; boundary `:249-252` - same start day 01/01/2025 → `409`, `(lei["valid_from"], lei["valid_to"]) == ("2025-01-01", None)`, new version absent | ⚠️ "Depois" boundary now pinned (N5 killed). The close is not proven when a process ends on the last day the closed version still covers (K3 survives) |
| CARR-10 | Closing would leave a process with end date **on or after** the new start → 409, nothing created, open version unchanged | `integration/api/test_career_api.py:217-220` (end 23/11/2026 vs start 01/01/2026); boundary `:232-239` - process ends 01/01/2031, new start 01/01/2031 → `409`, `versions[LEI]["valid_to"] is None`, `"Versão futura" not in versions` | ✅ PASS for the "em" boundary (N4 killed). The day-before side belongs to CARR-09 (K3) |

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

**Status**: 60/60 IDs have evidence whose asserted value matches the spec outcome. 0 spec-precision gaps. Not discriminating at a boundary day: the CARR-08 overlap rule on a single shared day (K1, K2) and the CARR-09 close when a process ends on the day before the new start (K3). UI-06 still rests on proxy evidence (static CSS scan), which does not block.

---

## Edge Cases

- [x] End 31/12/2024 → Res. 4.644; end 01/01/2025 → Lei 15.141: `unit/domain/test_career.py:38-43` (M2 and K6 killed)
- [x] 29/02/2024 → 28/02/2026 = 24 months: `unit/domain/test_interstice.py:18,23`; 27/02 → 23 at `:29` (M1 killed)
- [x] Concurrent save → first wins, second 409: `integration/test_repositories.py:236` (`pytest.raises(StaleVersion)`), `:241-242`; `integration/api/test_process_updates_api.py:120-122`
- [x] Archived professor → reading kept, new process 422: `integration/api/test_process_updates_api.py:228-230`
- [x] Empty optional fields → saved plus `ALERTA` `DADOS_INCOMPLETOS` listing them: `unit/domain/test_process_verification.py:282-283` (each of 5 fields), `:260-265`; `integration/api/test_processes_api.py:117-120`

5/5 covered.

---

## Discrimination Sensor

Expanded tier. Run in an isolated `git worktree` at `6c022e1` under the session scratchpad. Tests ran against a dedicated throwaway `postgres:16-alpine` container (`TEST_DATABASE_URL`, removed with `-v`), reusing the real `backend/.venv` read-only. Imports were confirmed to resolve from the worktree, and the unmutated worktree was green (286 passed). Each mutant was applied by exact single-occurrence replacement. The full backend suite then ran with `-x`, and the file was reverted with `git checkout`.

| # | File:line | Mutation | Killed? |
| - | --------- | -------- | ------- |
| N4 | `backend/app/application/use_cases/career.py:125` | `process.end_date >= new.valid_from` → `>` (iteration-2 survivor) | ✅ Killed by `test_process_ending_on_new_version_start_day_blocks_close` |
| N5 | `career.py:121` | `new.valid_from <= open_version.valid_from` → `<` (iteration-2 survivor) | ✅ Killed by `test_version_starting_on_open_version_start_day_returns_409` |
| N1 | `career.py:130` | Close at `new.valid_from` instead of the day before | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| N3 | `career.py:163` | Audit record of the closing skipped | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| M1 | `backend/app/domain/rules/interstice.py:23` | `end.day < start.day` → `<=` | ✅ Killed |
| M2 | `backend/app/domain/entities/career.py:35` | `moment <= valid_to` → `<` | ✅ Killed by `test_select_version_end_date_31_12_2024_uses_old_structure` |
| M6 | `backend/app/application/services/access_policy.py:25` | DOCENTE may read any process | ✅ Killed by `test_docente_sees_only_processes_of_linked_professor` |
| M7 | `backend/app/application/use_cases/processes.py:161` | Justification not required in `EM_ANDAMENTO` | ✅ Killed |
| M9 | `interstice.py:32` | `moment <= end` → `<` | ✅ Killed |
| M10 | `backend/app/application/use_cases/auth.py:14` | `MAX_FAILURES` 5 → 6 | ✅ Killed by `test_sixth_attempt_after_five_failures_returns_429` |
| M12 | `backend/app/domain/entities/process.py:20` | `is_read_only` always False | ✅ Killed |
| M20 | `backend/app/domain/rules/process_verification.py:148` | `if dates_ok and minimum` → `if minimum` | ✅ Killed |
| K4 (new) | `auth.py:124` | Idle expiry `>= IDLE_TIMEOUT` → `>` (AUTH-05) | ✅ Killed by `test_session_idle_for_30_minutes_gets_401` |
| K5 (new) | `interstice.py:32` | `start < moment` → `<=` (CARR-05 "começa antes") | ✅ Killed |
| K6 (new) | `entities/career.py:34` | `valid_from <= moment` → `<` (CARR-01, edge case 01/01/2025) | ✅ Killed |
| K7 (new) | `process_verification.py:150` | `months < minimum` → `<=` (PROC-09) | ✅ Killed |
| K8 (new) | `process_verification.py:176` | `end_date > opening_date` → `>=` (PROC-06) | ✅ Killed by `test_end_equal_to_opening_is_not_alert` |
| K9 (new) | `auth.py:67` | Failure window `(now−15min, now]` → `[now−15min, now]` (AUTH-04) | ✅ Killed |
| K1 (new) | `career.py:80` | `_overlaps`: `b.valid_from <= a.valid_to` → `<` | ❌ **Survived** (286 passed) |
| K2 (new) | `career.py:77` | `_overlaps`: `a.valid_from <= b.valid_to` → `<` | ❌ **Survived** (286 passed) |
| K3 (new) | `career.py:125` | `process.end_date >= new.valid_from` → `>= new.valid_from - timedelta(days=1)` | ❌ **Survived** (286 passed) |

Non-equivalence proof (probe tests in the scratch worktree only, deleted afterwards; 3/3 passed on unmutated code):
- **K1**: POST `{valid_from: 2024-12-31, valid_to: 2024-12-31}`. Real → 409. Mutant → 201, and 31/12/2024 is now covered by two versions.
- **K2**: POST `{valid_from: 2025-01-01, valid_to: 2025-01-01}`. Real → 409. Mutant → 201, and 01/01/2025 is now covered by two versions.
- **K3**: process ending 31/12/2030, then POST `NEW_VERSION` (starts 01/01/2031). Real → 201, with Lei `valid_to == "2030-12-31"`. Mutant → 409.

**Sensor depth**: expanded (21 mutations: 2 iteration-2 survivors, 10 earlier kills re-run across domain, auth, access policy, audit and career, and 9 new boundary mutants)
**Result**: 18/21 killed. FAIL ❌
**Isolation**: real-tree `git status --porcelain` was empty before and after. The worktree was removed and pruned, the sensor container was removed with its volume, and no containers or networks remain. Volume count is 64, the session baseline.

---

## Gate Check

- **Backend**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` → ruff: All checks passed; pytest **286 passed**, 0 failed, 0 skipped (1 Starlette deprecation warning). `docker volume ls -q`: **64 before, 64 after**. The T34 leak is fixed
- **Frontend**: `npm run lint && npm test -- --run && npm run build` → lint exit 0; vitest **14 passed** (6 files); build OK
- **smoke_backend**: `./scripts/smoke_backend.sh` → **PASS** (health 200, alembic at head 0001, uid 10001); volumes 64 → 64
- **smoke**: `./scripts/smoke.sh` → **PASS** (health 200 via nginx after 13 s, only nginx publishes a port, SPA and deep links, login, data and storage survive `down`/`up`); volumes 64 → 64
- **Test count**: 284 at iteration 2, now 286 (+2: T33). Frontend unchanged at 14. No test deleted or weakened
- **Skipped tests**: none

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code / surgical changes / no scope creep | ✅ Fix diff: 2 tests appended, 1 flag added, `tasks.md` Phase 9 |
| Matches patterns | ✅ Reuses `process_payload`, `NEW_VERSION`, `versions_by_name` |
| Spec-anchored outcome check | ✅ 60/60; ⚠️ K1, K2 and K3 boundaries not discriminated |
| Per-layer coverage | ✅ |
| Every test maps to a spec requirement | ✅ New tests are tagged `# CARR-10 boundary` and `# CARR-09 boundary` |
| Documented guidelines: `.specs/STATE.md` decisions; otherwise strong defaults applied | ✅ |
| Hygiene | ✅ No volume leak in any gate |

---

## Fix Plans

### Fix 1: Pin the overlap rule on a single shared day (Major, kills K1 and K2)
- **Root cause**: the only overlap test (`test_career_api.py:171-178`) posts 2020-01-01..2020-12-31, which sits deep inside the Res. 4.644 validity. No test makes two validities share exactly one day.
- **Fix task**: in `backend/tests/integration/api/test_career_api.py`, add a parametrized test that posts `{**NEW_VERSION, "valid_from": "2024-12-31", "valid_to": "2024-12-31"}` (touches the closed version's last day) and `{**NEW_VERSION, "valid_from": "2025-01-01", "valid_to": "2025-01-01"}` (touches the open version's first day). Assert 409, the new version is absent, and both seeded versions keep their validity.
- **Done when**: K1 and K2 are killed.

### Fix 2: Pin the CARR-09 close when a process ends on the day before the new start (Major, kills K3)
- **Root cause**: the CARR-09 success test uses a process ending 23/11/2026, years before the new start. Nothing checks that a process ending on the closed version's new last day still allows the close.
- **Fix task**: add a test that creates a process ending 31/12/2030 and posts `NEW_VERSION` (01/01/2031). Assert 201, Lei `valid_to == "2030-12-31"`, and that the process still resolves to the Lei version.
- **Done when**: K3 is killed.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INFRA-01..07, AUTH-01..11, DOC-01..05, PROC-01..14, CARR-01..07, CARR-10, AUD-01..04, UI-01..05, UNIT-01..03 | Implementing | ✅ Verified |
| UI-06 | Implementing | ⚠️ Verified (proxy evidence) |
| CARR-08, CARR-09 | Implementing / Needs Fix | ❌ Needs Fix (boundary not discriminated: K1, K2, K3) |

---

## Iteration History

| Iteration | Verdict | Summary |
| --------- | ------- | ------- |
| 1 (`3387587..cc9c41d`) | FAIL ❌ | 57/58 ACs. CARR-08 unreachable once the open version was in use. M14, M15 and M20 survived (17/20 killed). Spec-precision gaps on PROC-02, PROC-04, PROC-09 and CARR-08. Smoke backend leaked a volume |
| 2 (`3387587..e6875e4`) | FAIL ❌ | User added CARR-09/CARR-10 and confirmed Assumptions; T29–T32 implemented them. CARR-08 reachable, M14/M15/M20 killed, spec-precision gaps closed, smoke leak fixed. N4 and N5 survived on the CARR-10/CARR-09 boundary days (14/16 killed). The pytest fixture leaked a volume |
| 3 (`3387587..6c022e1`) | FAIL ❌ | T33/T34 kill N4 and N5 and fix the pytest leak. All gates are green and volumes are stable at 64. 9 new boundary mutants: 6 killed, 3 survived on the same career-version code (K1 and K2 on `_overlaps`, K3 on the day before the CARR-10 guard). 18/21 killed. Loop limit reached, so escalate to the user |

---

## Summary

**Overall**: ❌ Not Ready. The 3-iteration fix loop is exhausted, so this escalates to the user.

**Spec-anchored check**: 60/60 IDs matched the spec outcome; 0 spec-precision gaps; CARR-08 overlap and CARR-09 day-before boundaries not discriminated
**Sensor**: 18/21 mutations killed (K1, K2 and K3 survived)
**Gate**: backend 286 passed, frontend 14 passed, smoke_backend PASS, smoke PASS, volumes 64 → 64 throughout

**What works**: every iteration-1 and iteration-2 gap is closed. The implementation behaves correctly in all three surviving-mutant scenarios. Auth, access-policy, interstice, alert and audit boundaries are all discriminated.

**Issues found**: two missing test groups in `test_career_api.py`: the overlap rule on a single shared day (Fix 1), and the close when a process ends on the day before the new start (Fix 2). Both are test-only changes.

**Next steps**: the user decides whether to approve a fourth fix round (Fix 1 and Fix 2, about 3 test cases, no production code) or to accept the residual risk.
