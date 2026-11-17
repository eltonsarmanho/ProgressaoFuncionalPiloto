# Fundação Validation

**Verdict**: FAIL ❌

**Date**: 2026-11-16
**Spec**: `.specs/features/fundacao/spec.md`
**Diff range**: `3387587..cc9c41d` (branch `feat/fundacao`, 29 commits, 144 files)
**Verifier**: independent sub-agent (author ≠ verifier), evidence-or-zero

Why FAIL: two discrimination-sensor mutants survived on the `DADOS_INCOMPLETOS` edge case (M14, M15). CARR-08 cannot be met once the open-ended version is in use. A third survivor (M20) shows that the author's choice on a spec-precision gap is not pinned by any test. Every gate is green, and the other 57 ACs match the outcome the spec defines.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T28 | ✅ Done | 28 tasks in `tasks.md`, 0 unchecked `Done when` boxes |

---

## Spec-Anchored Acceptance Criteria

Test paths are relative to `backend/tests/` unless they start with `frontend/` or `scripts/`.

### P1: Stack executável

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| INFRA-01 | 4 services up; `GET /api/health` via nginx → 200 `{"status":"ok","database":"ok"}` ≤ 120 s | `scripts/smoke.sh:55` - `[ "$body" = '{"status":"ok","database":"ok"}' ]` inside a `SECONDS - start <= 120` loop (`:61` fails otherwise); `integration/api/test_health_api.py:14-15` - `status_code == 200`, `json() == {"status": "ok", "database": "ok"}` | ✅ PASS (smoke run: 200 after 12 s) |
| INFRA-02 | Pending Alembic migrations applied before serving | `scripts/smoke_backend.sh:57` - `[ "$db_rev" = "$head_rev" ]`; `backend/docker-entrypoint.sh` runs `alembic upgrade head` before `exec uvicorn`; `integration/test_migrations.py:40,46` - `_tables(...) == TABLES` | ✅ PASS |
| INFRA-03 | DB unreachable → 503 `{"status":"degraded","database":"unavailable"}` | `integration/api/test_health_api.py:27-28` - `status_code == 503`, exact body | ✅ PASS |
| INFRA-04 | pgdata and `storage/` survive `down` without `-v` | `scripts/smoke.sh:129` - professor found after restart; `:130` - `cat /app/storage/smoke.txt` = `smoke` | ✅ PASS |
| INFRA-05 | `.env.example` lists every variable used, with no real secret | `scripts/smoke.sh:80` - every `${VAR}` in compose has a `^VAR=` line in `.env.example`; secret values are empty in `.env.example` (checked by inspection) | ✅ PASS (the no-secret half is checked by inspection only) |
| INFRA-06 | `MARITALK_API_KEY` never in HTTP responses, bundle or logs | `unit/test_config.py:65-68` - `API_KEY not in repr/str/model_dump/model_dump_json`; no reference in `frontend/src` (grep) | ✅ PASS (no automated check on the bundle) |
| INFRA-07 | Missing required var → exit naming it, no other values | `unit/test_config.py:44-47` - `"DATABASE_URL" in message`, `ADMIN_PASS not in message`, `API_KEY not in message`; `:55-56` each name | ✅ PASS |

### P1: Autenticação e controle de acesso

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| AUTH-01 | 200 with id, name, role; cookie HttpOnly/Secure/SameSite=Strict | `integration/api/test_auth_api.py:24-31` - `json() == {"id","name","role"}`, `"httponly"`, `"samesite=strict"`, `"secure" in attributes` | ✅ PASS |
| AUTH-02 | 401 "Usuário ou senha inválidos", same text for unknown user and wrong password | `integration/api/test_auth_api.py:59-60` (parametrized wrong-password/unknown-user) - `status_code == 401`, `json() == {"detail": "Usuário ou senha inválidos"}` | ✅ PASS |
| AUTH-03 | No session on `/api/*` (except health and login) → 401 | `integration/api/test_auth_api.py:90` - `status_code == 401` for 4 routes; `:96` forged token | ✅ PASS |
| AUTH-04 | 5 failures in 15 min → 429 until the window ends | `integration/api/test_auth_api.py:71` - `blocked.status_code == 429`; `:75` 200 after 15 min; `integration/test_auth_use_cases.py:106-112` - still blocked at T0+15min−ε, allowed at T0+15min | ✅ PASS |
| AUTH-05 | 30 min idle or 8 h absolute → 401 | `integration/api/test_auth_api.py:154` (30 min) and `:162,166` (active every 20 min, 401 at 8 h); `integration/test_auth_use_cases.py:122-176` boundary tests | ✅ PASS |
| AUTH-06 | Authenticated write without valid CSRF → 403 | `integration/api/test_auth_api.py:130` - `status_code == 403` (missing and wrong token) | ✅ PASS |
| AUTH-07 | Argon2id only | `unit/test_security.py:14-15` - `startswith("$argon2id$")`; `integration/api/test_users_api.py:48` - stored hash `$argon2id$` | ✅ PASS |
| AUTH-08 | DOCENTE reading another professor's process → 404 | `integration/api/test_processes_api.py:197-198` - `other.status_code == 404`, `{"detail": "Processo não encontrado"}` | ✅ PASS |
| AUTH-09 | SECRETARIA reading a process of another unit → 404 | `integration/api/test_processes_api.py:185` - `other.status_code == 404`; `integration/api/test_process_updates_api.py:211-213` | ✅ PASS |
| AUTH-10 | Unique e-mail, name, role, password ≥ 10; 422 naming the field | `integration/api/test_users_api.py:91-92` - 422, `[field]` for password/email/name/role; `:112-113` duplicate e-mail → 422 `["email"]`; `:102` 10 characters accepted | ✅ PASS (author decision 4, 422 rather than 409, is what the AC says) |
| AUTH-11 | Logout invalidates the session on the server | `integration/api/test_auth_api.py:141-145` - 204, `get_by_token_hash(...) is None`, replayed cookie → 401 | ✅ PASS |

### P1: Cadastro de docente

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| DOC-01 | All 9 functional fields persisted | `integration/api/test_professors_api.py:47` - `{k: body[k] for k in payload} == payload` after reopening | ✅ PASS |
| DOC-02 | SIAPE not exactly 7 digits → 422 on `siape` | `integration/api/test_professors_api.py:60-61` - 422, `== ["siape"]` (5 cases) | ✅ PASS |
| DOC-03 | Duplicate SIAPE → 409, no duplicate | `integration/api/test_professors_api.py:73-75` - 409, `[p.siape ...] == ["1234567"]` | ✅ PASS |
| DOC-04 | Titration ∈ {GRADUACAO, ESPECIALIZACAO, MESTRADO, DOUTORADO}; regime ∈ {20H, 40H, DE} | `integration/api/test_professors_api.py:89-90` (422 outside the sets), `:111` (all accepted); `unit/domain/test_process_entities.py:65-77` | ✅ PASS |
| DOC-05 | Edit → audit event (AUD-01) | `integration/api/test_professors_api.py:131-138` - `[CREATE, UPDATE]`, actor, `changes == {titration, work_regime before/after}` | ✅ PASS |

### P1: Processo e interstício

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| PROC-01 | All fields persisted, unique id, status `RASCUNHO` | `integration/api/test_processes_api.py:38-43` - 201, payload round-trip, `status == "RASCUNHO"` | ✅ PASS |
| PROC-02 | Duration in full civil months and in days | `integration/api/test_processes_api.py:69` - `interstice == {"months": 24, "days": 731}`; `unit/domain/test_interstice.py:23,41` | ⚠️ Spec-precision gap: the spec does not define how days are counted (implementation: end − start, 730 for the PROC-11 case) |
| PROC-03 | Saved exactly as informed despite alerts, never auto-changed | `integration/api/test_processes_api.py:107` - `{k: stored[k] for k in payload} == payload` for the PROC-11 payload; `unit/domain/test_process_verification.py:298` snapshot unchanged | ✅ PASS |
| PROC-04 | Checks run on save and on read; each alert has code, severity, PT message, norm reference | `integration/api/test_processes_api.py:102,108` - `all(a["message"] and a["norm_reference"])`, `codes(stored) == codes(body)`; `unit/domain/test_process_verification.py:287-289` | ⚠️ Spec-precision gap: `DADOS_INCOMPLETOS` cites a generic "Res. 4.644/2015-CONSEPE" because no norm requires the institutional fields (author decision 3) |
| PROC-05 | end ≤ start → `ERRO` `INTERSTICIO_DATAS_INVALIDAS` | `unit/domain/test_process_verification.py:97-98` - `find(...)`, `severity is Severity.ERRO` (equal and earlier) | ✅ PASS |
| PROC-06 | end > opening → `ALERTA` `INTERSTICIO_NAO_CONCLUIDO` | `unit/domain/test_process_verification.py:104-105`; `:110` equal → no alert | ✅ PASS |
| PROC-07 | PROGRESSAO with class change or level ≠ +1 → `ERRO` `MODALIDADE_INCOMPATIVEL` | `unit/domain/test_process_verification.py:124-125` (class change, +2, 0) | ✅ PASS |
| PROC-08 | PROMOCAO rules (next class, last level, first level) → `ERRO` `MODALIDADE_INCOMPATIVEL` | `unit/domain/test_process_verification.py:161-162` (3 cases); `:142` valid promotion → `[]` | ✅ PASS |
| PROC-09 | months < minimum → `ERRO` `INTERSTICIO_INSUFICIENTE` with months and minimum | `unit/domain/test_process_verification.py:178-182` (24 vs 36, B in the new structure), `:187-190` (23 vs 24) | ⚠️ Spec-precision gap: the code skips this check when the dates are invalid (author decision 3), the spec does not say whether it should, and mutant M20 shows no test pins the choice |
| PROC-10 | FASI case: Res. 4.644 applied, 24 months, zero `ERRO` | `unit/domain/test_process_verification.py:263-269`; `integration/api/test_processes_api.py:69-72` - `months: 24`, no ERRO, `codes == set()` | ✅ PASS |
| PROC-11 | Requerimento case: Lei 15.141 applied, exactly the 5 codes | `unit/domain/test_process_verification.py:274-285` - `select_version is LEI_15141_2025`, `len == 5`, exact code→severity map; `integration/api/test_processes_api.py:85-101` | ✅ PASS |
| PROC-12 | `CONCLUIDO`/`ARQUIVADO` → 409 on change | `integration/api/test_process_updates_api.py:109-111` - 409, stored status and level unchanged | ✅ PASS |
| PROC-13 | `EM_ANDAMENTO` without justification → 422 on `justificativa` | `integration/api/test_process_updates_api.py:76-78` - 422, `== ["justificativa"]` (missing/empty/blank) | ✅ PASS |
| PROC-14 | List scoped by profile, with status, professor, modality, interstice, alert counts | `integration/api/test_processes_api.py:165-173` - `alert_counts == {"ERRO": 2, "ALERTA": 2, "REQUER_ANALISE_NORMATIVA": 1}` and the other fields; `:183`, `:195` scoping | ✅ PASS |

### P1: Estruturas de carreira versionadas

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| CARR-01 | Version whose validity contains the end date | `unit/domain/test_career.py:38-43` - 31/12/2024 → old, 01/01/2025 → new | ✅ PASS |
| CARR-02 | Two seeded versions, with names, validity, classes and norm reference | `unit/domain/test_career_catalog.py:20-21,25-29,33,43,65-66`; `integration/test_seed.py:48-53` - persisted == catalog | ✅ PASS |
| CARR-03 | Progression 24/24; promotion 24 (old); new: B 36, C/D 24 | `unit/domain/test_career_catalog.py:33-49,53-54` (exact class tuples incl. `promotion_min_months`); `unit/domain/test_career.py:75-78` | ✅ PASS |
| CARR-04 | Class or level missing → `ERRO` `CLASSE_INEXISTENTE_NA_ESTRUTURA` | `unit/domain/test_process_verification.py:203-204` | ✅ PASS |
| CARR-05 | Starts before and ends on or after 01/01/2025 → `REQUER_ANALISE_NORMATIVA` `INTERSTICIO_CRUZA_REESTRUTURACAO`, citing Lei 15.141/2025 | `unit/domain/test_process_verification.py:211-213`; `unit/domain/test_interstice.py:55` boundaries | ✅ PASS |
| CARR-06 | Denomination mismatch → `ALERTA` `DENOMINACAO_DIVERGENTE`, showing the expected one | `unit/domain/test_process_verification.py:226-228` - `"Adjunto" in alert.message`; `:290-291` | ✅ PASS |
| CARR-07 | No version in force → `REQUER_ANALISE_NORMATIVA` `ESTRUTURA_NAO_CADASTRADA`, skip structure checks | `unit/domain/test_process_verification.py:244-245` - `codes(alerts) == [ESTRUTURA_NAO_CADASTRADA]` | ✅ PASS |
| CARR-08 | ADMIN can register a new version (mandatory reference) without editing versions used by processes | `integration/api/test_career_api.py:62-73` (create after closing an **unused** version), `:105-106` (reference required), `:167` (used → 409), `:176` (overlap → 409) | ❌ GAP + ⚠️ spec-precision gap: once any process ends on or after 01/01/2025, the open-ended Lei version is in use. Closing its `valid_to` then returns 409 and any new version overlaps (409), so the ADMIN can never register a new version (author decision 6) |

### P1: Trilha de auditoria

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| AUD-01 | Event with user, UTC time, entity, id, changed fields before/after, justification | `integration/api/test_users_api.py:50-61` (incl. `utcoffset() == 0`); `integration/api/test_process_updates_api.py:92-95`; `integration/api/test_professors_api.py:235-237` (archive); `integration/api/test_career_api.py:86-87`; `integration/api/test_units_api.py:70-71` | ✅ PASS (no test asserts the audit event of a process archived via status `ARQUIVADO`; it shares the STATUS path tested at `test_process_updates_api.py:135-138`) |
| AUD-02 | No change or deletion of audit events via the API | `integration/test_migrations.py:86-93` - UPDATE/DELETE raise `append-only`, row unchanged; no PUT/DELETE route on audit exists (`app/presentation/api/*`) | ✅ PASS (SPEC_DEVIATION from design: trigger instead of REVOKE. It is stronger than the AC requires) |
| AUD-03 | History in chronological order | `integration/api/test_process_updates_api.py:197-203` - `["CREATE","STATUS","UPDATE"]`, `times == sorted(times)` | ✅ PASS |
| AUD-04 | Logs carry identifiers only, never name or SIAPE | `integration/api/test_logging_api.py:62-63` - `leaked == []` across the full flow plus a failure path | ✅ PASS |

### P1: Interface web

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| UI-01 | No session → redirect to login | `frontend/src/App.test.tsx:28-29` - heading "Entrar", location `/login` | ✅ PASS |
| UI-02 | Total, per status, list with alert counts per severity | `frontend/src/pages/Dashboard.test.tsx:43-58` | ✅ PASS |
| UI-03 | After save: duration, plus alerts grouped by severity with norm reference | `frontend/src/pages/ProcessStep1.test.tsx:84-106` | ✅ PASS |
| UI-04 | 9 steps, step 1 active, 2–9 disabled and labelled "em breve" | `frontend/src/pages/ProcessStep1.test.tsx:139-148` | ✅ PASS |
| UI-05 | 422 → message next to the field | `frontend/src/pages/ProfessorForm.test.tsx:68-71` (siape); `frontend/src/pages/ProcessStep1.test.tsx:171-173` (justificativa) | ✅ PASS |
| UI-06 | Usable at 360 px without horizontal scroll | `frontend/src/styles.test.ts:22` - no fixed/min width > 360 px; `:26-27` fluid container and device viewport | ⚠️ Proxy evidence only: a static CSS scan, no real browser at 360 px (author decision 7). It cannot catch content overflow such as long tables or `nowrap` |

### P2: Unidades acadêmicas

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| UNIT-01 | ADMIN creates, edits and archives units (name, acronym, kind, optional parent) | `integration/api/test_units_api.py:31-39,50-56,65-71`; `:116` non-admin → 403 | ✅ PASS |
| UNIT-02 | Archived unit in a new professor or process → 422 | `integration/api/test_professors_api.py:167-170`; `integration/api/test_processes_api.py:135-138` | ✅ PASS |
| UNIT-03 | Seed Campus Tocantins/Cametá, FASI, IFCH | `integration/test_seed.py:62-76` | ✅ PASS |

**Status**: ❌ Gaps present. 57/58 ACs match the spec-defined outcome, CARR-08 does not. 4 spec-precision gaps flagged (PROC-02, PROC-04, PROC-09, CARR-08); UI-06 has proxy evidence only.

---

## Edge Cases

- [x] End date 31/12/2024 → Res. 4.644; 01/01/2025 → Lei 15.141: `unit/domain/test_career.py:38-43`, `unit/domain/test_career_catalog.py:28-29`
- [x] 29/02/2024 → 28/02/2026 = 24 months: `unit/domain/test_interstice.py:18,23`; 27/02 → 23 at `:29`
- [x] Concurrent save → first wins, second 409: `integration/test_repositories.py:221-243` (two open UoWs, `StaleVersion`), `integration/api/test_process_updates_api.py:120-122`
- [x] Archived professor → reading kept, new process 422: `integration/api/test_process_updates_api.py:228-230`
- [~] Empty optional fields → saved plus `ALERTA` `DADOS_INCOMPLETOS` **listing the empty fields**: `unit/domain/test_process_verification.py:252-258`, `integration/api/test_processes_api.py:117-120`. Covered but not discriminating. Mutants M14 and M15 removed "unidade administrativa responsável" and "cargo do responsável" from the check and survived

5/5 covered, 1 weak.

---

## Discrimination Sensor

Expanded tier (foundation, auth, data integrity). Isolated `git worktree` under the scratchpad at HEAD, with a dedicated throwaway Postgres (`TEST_DATABASE_URL`) and the real `.venv`/`node_modules` reused read-only. The unmutated worktree was green (275 passed) before any fault was injected.

| # | File | Mutation | Killed? |
| - | ---- | -------- | ------- |
| M1 | `backend/app/domain/rules/interstice.py` | Off-by-one in civil month count: `end.day < start.day` → `<=` | ✅ Killed |
| M2 | `backend/app/domain/entities/career.py` | Version boundary `moment <= valid_to` → `<` (31/12/2024 falls through) | ✅ Killed |
| M3 | `backend/app/domain/rules/process_verification.py` | Dropped `INTERSTICIO_NAO_CONCLUIDO` (`if False:`) | ✅ Killed |
| M4 | same | PROGRESSAO across classes allowed (removed `target_class != current_class`) | ✅ Killed |
| M5 | `backend/app/presentation/csrf.py` | CSRF check disabled | ✅ Killed |
| M6 | `backend/app/application/services/access_policy.py` | DOCENTE may read any process | ✅ Killed |
| M7 | `backend/app/application/use_cases/processes.py` | Justification no longer required in `EM_ANDAMENTO` | ✅ Killed |
| M8 | same | Audit event skipped on process update | ✅ Killed |
| M9 | `backend/app/domain/rules/interstice.py` | `crosses`: `moment <= end` → `<` (ends on 01/01/2025) | ✅ Killed |
| M10 | `backend/app/application/use_cases/auth.py` | `MAX_FAILURES` 5 → 6 | ✅ Killed |
| M11 | same | `IDLE_TIMEOUT` 30 → 31 min | ✅ Killed |
| M12 | `backend/app/domain/entities/process.py` | `is_read_only` always False | ✅ Killed |
| M13 | `backend/app/application/services/access_policy.py` | SECRETARIA covers every unit | ✅ Killed |
| M14 | `backend/app/domain/rules/process_verification.py` | `resp_admin_unit` removed from the `DADOS_INCOMPLETOS` fields | ❌ Survived (275 passed) |
| M15 | same | `resp_position` removed from the `DADOS_INCOMPLETOS` fields | ❌ Survived (275 passed) |
| M16 | `backend/app/presentation/api/health.py` | Degraded health returns 200 instead of 503 | ✅ Killed |
| M17 | `frontend/src/components/AlertList.tsx` | Norm reference not rendered | ✅ Killed |
| M18 | `frontend/src/components/StepNav.tsx` | Steps 2–9 lose `aria-disabled` | ✅ Killed |
| M19 | `frontend/src/components/FieldError.tsx` | Field error never rendered | ✅ Killed |
| M20 | `backend/app/domain/rules/process_verification.py` | `INSUFICIENTE` also emitted when dates are invalid (removed `dates_ok and`) | ❌ Survived. This mutant is closer to the literal PROC-09 text, so the gap is that the author's choice is not pinned by a test (see PROC-09) |

**Sensor depth**: expanded (20 mutations)
**Result**: 17/20 killed. FAIL ❌
**Isolation**: real-tree `git status --porcelain` was empty before and after the sensor. The worktree was removed, the sensor container removed, and the dangling volumes the sensor created were deleted.

---

## Gate Check

- **Backend**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` → ruff: All checks passed; pytest: **275 passed**, 0 failed, 0 skipped (1 Starlette deprecation warning)
- **Frontend**: `npm run lint && npm test -- --run && npm run build` → lint exit 0; vitest **14 passed** (6 files); build OK
- **E2E**: `./scripts/smoke.sh` → **PASS** (health 200 after 12 s, only nginx publishes a port, SPA plus deep link, admin login, data and storage survive `down`/`up`); `./scripts/smoke_backend.sh` → **PASS** (alembic at head 0001, uid 10001)
- **Test count before feature**: 0 (greenfield). **After**: 275 backend + 14 frontend + 2 smoke scripts
- **Skipped tests**: none

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code / surgical changes / no scope creep | ✅ |
| Matches patterns (clean layers enforced by `architecture/test_layers.py`) | ✅ |
| Spec-anchored outcome check | ⚠️ 4 spec-precision gaps; CARR-08 ❌ |
| Per-layer coverage (domain 1:1 ACs; routes happy, edge and error) | ✅ |
| Every test maps to a spec requirement | ✅ |
| Documented guidelines: `.specs/STATE.md` decisions; otherwise strong defaults applied | ✅ |
| Hygiene | ⚠️ `scripts/smoke_backend.sh` cleanup (`docker rm -f` without `-v`) leaves an anonymous postgres volume on each run |

---

## Author Decisions Scrutinized

| # | Decision | Verdict |
| - | -------- | ------- |
| 1 | AUD-02 via trigger (SPEC_DEVIATION from design.md) | Accepted. It is stronger than the spec, which only requires blocking changes "pela API". Recorded as a spec_deviation lesson |
| 2 | Days = end − start | Spec-precision gap (PROC-02). Plausible, but unconfirmed |
| 3 | `INSUFICIENTE` skipped on invalid dates; generic norm for `DADOS_INCOMPLETOS` | Spec-precision gaps (PROC-09, PROC-04). The first is unpinned (M20) |
| 4 | Duplicate e-mail → 422 on `email` | Matches AUTH-10 as written |
| 5 | Half-open 15-min window; success does not reset failures | Consistent with AUTH-04; boundary tested |
| 6 | Overlap → 409; in use = an end date inside the validity | **CARR-08 unreachable after the first post-2025 process.** Needs a user decision |
| 7 | UI-06 via static CSS test | Proxy evidence; recommend a headless-browser check at 360 px |
| 8 | Business routes 500 (not 503) when DB is down | Not a spec AC; no finding |

---

## Fix Plans

### Fix 1: Discriminate every `DADOS_INCOMPLETOS` field (Major)
- **Root cause**: tests empty `notes`, `resp_name` and `resp_appointment` only. No test empties `resp_position` or `resp_admin_unit` on its own.
- **Fix task**: in `backend/tests/unit/domain/test_process_verification.py`, add a test parametrized over all 5 optional fields. Each case empties one field and asserts `DADOS_INCOMPLETOS` whose message contains that field's label.
- **Done when**: M14 and M15 are killed.

### Fix 2: Make CARR-08 reachable (Blocker, needs a user decision)
- **Root cause**: "never edit a version used by processes" plus "no overlap" plus an open-ended version means no new version can be added once that version is in use.
- **Options for the user**: (a) allow closing `valid_to` of an in-use version as long as every process end date stays inside the new validity (the version selected for every existing process is unchanged); or (b) creating a successor version auto-closes the open-ended predecessor under the same condition.
- **Done when**: an API test creates a process ending in 2026, then registers a version starting in 2031 → 201. Existing processes still resolve to the Lei 15.141 version.

### Fix 3: Pin PROC-09 behaviour on invalid dates (Minor, needs a user decision)
- Confirm whether `INTERSTICIO_INSUFICIENTE` is suppressed when `INTERSTICIO_DATAS_INVALIDAS` fires, record the answer in spec Assumptions, and add a test asserting the chosen code set (kills M20 or its inverse).

### Fix 4: Confirm the spec-precision defaults (Minor)
- Add to spec Assumptions: day count = end − start (PROC-02), and the norm reference to use for `DADOS_INCOMPLETOS` (PROC-04).
- Optional: a Playwright check at 360 px for UI-06 (could be done in the `implantacao` feature); add `-v` to the `docker rm -f` cleanup in `scripts/smoke_backend.sh`.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INFRA-01..07, AUTH-01..11, DOC-01..05, PROC-01, PROC-03, PROC-05..08, PROC-10..14, CARR-01..07, AUD-01..04, UI-01..05, UNIT-01..03 | Implementing | ✅ Verified |
| PROC-02, PROC-04, PROC-09 | Implementing | ⚠️ Verified with spec-precision gap |
| UI-06 | Implementing | ⚠️ Verified (proxy evidence) |
| CARR-08 | Implementing | ❌ Needs Fix |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 57/58 ACs match the spec outcome; 4 spec-precision gaps (PROC-02, PROC-04, PROC-09, CARR-08)
**Sensor**: 17/20 mutations killed (M14, M15, M20 survived)
**Gate**: backend 275 passed, frontend 14 passed, smoke PASS, smoke_backend PASS

**What works**: stack and health; session auth with CSRF, rate limit and expiry; profile scoping (404); the career-version boundary; the PROC-10 and PROC-11 real cases (exact codes and severities); append-only audit with history; no personal data in logs; the Step 1 UI.

**Issues found**: weak `DADOS_INCOMPLETOS` assertions (Fix 1); CARR-08 unreachable once the version is in use (Fix 2); unpinned PROC-09 choice (Fix 3); unconfirmed defaults (Fix 4).

**Next steps**: route Fix 1 to an implementer now; ask the user to decide Fix 2 and Fix 3; then re-verify (iteration 1 of 3).
