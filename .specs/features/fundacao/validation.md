# Fundação Validation

**Verdict**: PASS ✅ (iteration 5, the extra round approved by the user)

**Iteration**: 5
**Date**: 2026-11-17
**Spec**: `.specs/features/fundacao/spec.md` (60 requirement IDs, 5 edge cases)
**Diff range**: `3387587..87114db` (branch `feat/fundacao`). Fix commit since iteration 4: `87114db` (T37)
**Verifier**: independent sub-agent (author ≠ verifier), evidence-or-zero

Why PASS: X6 is now killed by `test_in_use_is_decided_per_version`, and so are K1, K2, K3, N4 and N5. Every gate is green and 60/60 IDs match the spec outcome. The sensor injected 41 mutants (expanded tier): 40 killed, and 1 (Y1) survived but is behaviourally equivalent (a redundant guard, proof below), so it is not a test gap. UI-06 still rests on proxy evidence and does not block.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T32 | ✅ Done | Unchanged since iteration 2 |
| T33 | ✅ Done | CARR-10 "em" boundary (`test_career_api.py:224-239`) and CARR-09 same-start boundary (`:243-252`). Kills N4 and N5 |
| T34 | ✅ Done | `backend/tests/integration/conftest.py:70` now `docker rm -f -v`; volume count 64 → 64 across the backend gate |
| T35 | ✅ Done | CARR-08 single-shared-day overlap (`test_career_api.py:259-273`). Kills K1 and K2 |
| T36 | ✅ Done | CARR-09/CARR-10 last allowed day (`test_career_api.py:276-292`). Kills K3 |
| T37 | ✅ Done | CARR-08 per-version "in use" rule (`test_career_api.py:295-309`). Kills X6 |

`tasks.md`: 0 unchecked `Done when` boxes (T1–T37).

---

## Spec-Anchored Acceptance Criteria

Test paths are relative to `backend/tests/` unless they start with `frontend/` or `scripts/`. Since iteration 4 the only code change is `integration/api/test_career_api.py` (lines 293-309 appended, 18 lines, no production code), so all other citations keep their line numbers. They were re-read at HEAD `87114db`, including `test_processes_api.py:69,171,197-198`, `test_process_verification.py:105,282-283,303-304`, `test_auth_api.py:59-60`, `test_process_updates_api.py:109-111`, `test_migrations.py:86-93`, `test_repositories.py:236`, `frontend/src/styles.test.ts:22` and `scripts/smoke.sh:55`.

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
| CARR-08 | ADMIN registers a version with a mandatory reference, without editing versions used by processes; overlapping validities refused (confirmed Assumption) | `integration/api/test_career_api.py:105-106` reference required → 422 `["norm_reference"]`; `:163-168` used version → `in_use is True`, PUT-close → 409, `valid_to is None`; `:177` overlap inside a closed version → 409; `:272-273` one-day versions 31/12/2024 and 01/01/2025 → `409` and `client.get(URL).json() == before`; per-version rule `:304-305` - process ends 23/11/2026, `versions[RES_4644]["in_use"] is False` and `versions[LEI]["in_use"] is True`; `:307-309` PUT on the unused Res. 4.644 → `200` | ✅ PASS (K1, K2, X6, X6b killed) |
| CARR-09 | New version starting **after** the open one's start → open version closed the day before; audit UPDATE `valid_to` null → new | `integration/api/test_career_api.py:197-204` - `201`, `versions[LEI]["valid_to"] == "2030-12-31"`, audit `changes == {"valid_to": {"before": None, "after": "2030-12-31"}}`; same-start boundary `:249-252` → `409`, Lei `("2025-01-01", None)`; last allowed day `:289-292` - process ends 31/12/2030, new start 01/01/2031 → `201`, Lei `valid_to == "2030-12-31"` | ✅ PASS (N1, N5, K3, X10 killed) |
| CARR-10 | Closing would leave a process with end date **on or after** the new start → 409, nothing created, open version unchanged | `integration/api/test_career_api.py:217-220` (end 23/11/2026 vs start 01/01/2026); "em" boundary `:236-239` - process ends 01/01/2031, new start 01/01/2031 → `409`, `versions[LEI]["valid_to"] is None`, `"Versão futura" not in versions`; day-before side `:289-292` | ✅ PASS (N4, K3 killed) |

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

**Status**: 60/60 IDs have evidence whose asserted value matches the spec outcome. 0 spec-precision gaps. UI-06 still rests on proxy evidence (static CSS scan), which does not block.

---

## Edge Cases

- [x] End 31/12/2024 → Res. 4.644; end 01/01/2025 → Lei 15.141: `unit/domain/test_career.py:38-43` (M2 killed; re-run in iterations 4 and 5)
- [x] 29/02/2024 → 28/02/2026 = 24 months: `unit/domain/test_interstice.py:18,23`; 27/02 → 23 at `:29` (M1 killed)
- [x] Concurrent save → first wins, second 409: `integration/test_repositories.py:236` (`pytest.raises(StaleVersion)`), `:241-242`; `integration/api/test_process_updates_api.py:120-122`
- [x] Archived professor → reading kept, new process 422: `integration/api/test_process_updates_api.py:228-230`
- [x] Empty optional fields → saved plus `ALERTA` `DADOS_INCOMPLETOS` listing them: `unit/domain/test_process_verification.py:282-283` (each of 5 fields), `:260-265`; `integration/api/test_processes_api.py:117-120`

5/5 covered.

---

## Discrimination Sensor

Expanded tier. Isolated `git worktree` at `87114db` under the session scratchpad (the frontend `node_modules` linked, link removed before the worktree). Backend tests ran against a dedicated throwaway `postgres:16-alpine` container (`TEST_DATABASE_URL`, removed with `-v`), reusing the real `backend/.venv`; imports resolve from the worktree and the unmutated worktree was green (290 backend). Each mutant was applied by exact single-occurrence replacement (the runner skips a mutant whose pattern is not unique), the full suite ran with `-x`, and the file was restored. The worktree had no tracked change after the run.

| # | File:line | Mutation | Killed? |
| - | --------- | -------- | ------- |
| X6 | `backend/app/application/use_cases/career.py:89` | `_in_use`: `and version.covers(process.end_date)` removed | ✅ Killed by `test_in_use_is_decided_per_version` |
| X6b (new) | `career.py:89` | `version.covers(process.end_date)` → `True` | ✅ Killed by `test_in_use_is_decided_per_version` |
| K1 | `career.py:80` | `_overlaps`: `b.valid_from <= a.valid_to` → `<` | ✅ Killed by `test_single_day_overlap_returns_409[last-day-of-res-4644]` |
| K2 | `career.py:77` | `_overlaps`: `a.valid_from <= b.valid_to` → `<` | ✅ Killed by `test_single_day_overlap_returns_409[first-day-of-open-lei]` |
| K3 | `career.py:125` | `process.end_date >= new.valid_from` → `>= new.valid_from - 1 day` | ✅ Killed by `test_process_ending_day_before_new_version_allows_close` |
| N4 | `career.py:125` | `>=` → `>` | ✅ Killed by `test_process_ending_on_new_version_start_day_blocks_close` |
| N5 | `career.py:121` | `new.valid_from <= open_version.valid_from` → `<` | ✅ Killed by `test_version_starting_on_open_version_start_day_returns_409` |
| N1 | `career.py:130` | Close at `new.valid_from` instead of the day before | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| X10 | `career.py:162` | Closed version not substituted into `existing` | ✅ Killed by `test_creating_next_version_closes_open_ended_version` |
| X7 | `backend/app/application/services/audit_service.py:34` | `diff` records unchanged fields (`if old != new` → `if True`) | ✅ Killed by `test_editing_unused_version_is_audited_with_before_after` |
| M1 | `backend/app/domain/rules/interstice.py:23` | `end.day < start.day` → `<=` | ✅ Killed (first failure `test_rascunho_update_without_justification_is_saved_and_audited`) |
| X2 | `interstice.py:28` | `days()` made inclusive (`+ 1`) | ✅ Killed by `test_proc10_fasi_case_has_24_months_and_no_alerts` |
| M2 | `backend/app/domain/entities/career.py:35` | `moment <= valid_to` → `<` | ✅ Killed by `test_select_version_end_date_31_12_2024_uses_old_structure` |
| M12 | `backend/app/domain/entities/process.py:20` | `is_read_only` always False | ✅ Killed by `test_read_only_process_rejects_changes_with_409[CONCLUIDO]` |
| M20 | `backend/app/domain/rules/process_verification.py:148` | `if dates_ok and minimum` → `if minimum` | ✅ Killed by `test_invalid_dates_do_not_also_emit_insufficient_interstice[end0]` |
| X5 | `process_verification.py:133` | Promotion check drops `current_level == last level` | ✅ Killed by `test_promotion_rules[changes1]` |
| M6 | `backend/app/application/services/access_policy.py:25` | DOCENTE may read any process | ✅ Killed by `test_docente_sees_only_processes_of_linked_professor` |
| X1 | `access_policy.py:16` | SECRETARIA covers every unit | ✅ Killed by `test_history_and_updates_of_unreadable_process_return_404` |
| M7 | `backend/app/application/use_cases/processes.py:161` | Justification not required in `EM_ANDAMENTO` | ✅ Killed by `test_em_andamento_update_without_justification_returns_422[missing]` |
| M10 | `backend/app/application/use_cases/auth.py:14` | `MAX_FAILURES` 5 → 6 | ✅ Killed by `test_sixth_attempt_after_five_failures_returns_429` |
| K4 | `auth.py:124` | Idle expiry `>= IDLE_TIMEOUT` → `>` | ✅ Killed by `test_session_idle_for_30_minutes_gets_401` |
| X4 | `auth.py:125` | Absolute expiry `>=` → `>` | ✅ Killed by `test_session_older_than_8_hours_gets_401` |
| K9 | `auth.py:67` | Failure window start moved by 1 microsecond | ✅ Killed by `test_sixth_attempt_after_five_failures_returns_429` |
| X9 | `backend/app/infrastructure/database/repositories.py:180` | Failure count ignores the e-mail | ✅ Killed by `test_block_applies_only_to_the_same_email` |
| X3 | `backend/app/presentation/csrf.py:35` | CSRF compare replaced by `not sent` | ✅ Killed by `test_write_without_valid_csrf_token_returns_403[wrong]` |
| X8 | `backend/app/application/use_cases/users.py:65` | Password minimum `< 10` → `<= 10` | ✅ Killed by `test_password_with_exactly_10_characters_is_accepted` |
| F1 | `frontend/src/components/StepNav.tsx:9` | Steps 1 and 2 both active | ✅ Killed by `ProcessStep1.test.tsx` UI-04 |
| F2 | `frontend/src/components/AlertList.tsx:22` | Norm reference text dropped | ✅ Killed by `ProcessStep1.test.tsx` UI-03 |
| Y1 (new) | `processes.py:143` | `_check_version`: `process.version != expected` → `<` | ⚠️ Survived, **equivalent** (see below) |
| Y2 (new) | `backend/app/domain/entities/process.py:23-26` | `_FORWARD` drops EM_ANDAMENTO → CONCLUIDO | ✅ Killed by `test_read_only_process_rejects_changes_with_409[CONCLUIDO]` |
| Y3 (new) | `process.py:36` | Archive allowed for anyone (`return True`) | ✅ Killed by `test_only_admin_or_owner_archive` |
| Y4 (new) | `backend/app/application/use_cases/professors.py:19` | SIAPE regex `\d{7}` → `\d{7,8}` | ✅ Killed by `test_siape_without_exactly_7_digits_returns_422_on_siape[12345678]` |
| Y5 (new) | `auth.py:15` | Rate-limit window 15 → 16 minutes | ✅ Killed by `test_sixth_attempt_after_five_failures_returns_429` |
| Y6 (new) | `processes.py:138` | List filter by profile dropped (`if True`) | ✅ Killed by `test_secretaria_sees_only_processes_of_its_units` |
| Y7 (new) | `processes.py:160` | PUT justification not stripped (blank accepted) | ✅ Killed by `test_em_andamento_update_without_justification_returns_422[blank]` |
| Y8 (new) | `career.py:51` | Reference not stripped (blank accepted) | ✅ Killed by `test_version_without_norm_reference_returns_422[blank]` |
| Y9 (new) | `career.py:56` | `valid_to < valid_from` → `<=` | ✅ Killed by `test_single_day_overlap_returns_409[last-day-of-res-4644]` |
| Y10 (new) | `repositories.py:63` | Version bump `+ 1` → `+ 2` | ✅ Killed by `test_rascunho_update_without_justification_is_saved_and_audited` |
| Y11 (new) | `auth.py:16` | Idle timeout 30 → 31 minutes | ✅ Killed by `test_session_idle_for_30_minutes_gets_401` |
| Y12 (new) | `career.py:58` | `progression_min_months <= 0` → `< 0` | ✅ Killed by `test_invalid_definition_returns_422[zero-interstice]` |
| Y13 (new) | `repositories.py:66` | Optimistic-lock `WHERE` drops `version == expected` | ✅ Killed by `test_editing_with_stale_version_returns_409` |

Y1 equivalence: `_check_version` (`processes.py:142-144`) is a pre-check in front of `_versioned_update` (`repositories.py:54-80`), whose `WHERE ... version == expected_version` raises the same `StaleVersion` (HTTP 409) when the row moved. With `<`, a stale (lower) request still reaches the repository guard and gets 409, and a request claiming a future version is raised by the pre-check as before. The only difference is the exception text ("O processo foi alterado..." vs "Processo foi alterado..."), which the spec does not define. The real lock is pinned by Y13. A `Y14` attempt (`rowcount == 0` → `< 0`) was skipped by the runner because the pattern is not unique, and was not run.

**Sensor depth**: expanded (41 mutations: 6 mandatory re-runs, X6b, 21 earlier kills re-run across domain, auth, access policy, audit, career and frontend, 13 new Y mutants)
**Result**: 40/41 killed, 1 equivalent (not a test gap). PASS ✅
**Isolation**: real-tree `git status --porcelain` was empty before and after (matches the baseline). The worktree was removed and pruned, the sensor container was removed with its volume, no containers remain, and the real `frontend/node_modules` is intact. Volume count is 64, the session baseline.

---

## Gate Check

- **Backend**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q` → ruff: All checks passed; pytest **290 passed**, 0 failed, 0 skipped (1 Starlette deprecation warning). `docker volume ls -q`: **64 before, 64 after**
- **Frontend**: `npm run lint && npm test -- --run && npm run build` → lint exit 0; vitest **14 passed** (6 files); build OK
- **smoke_backend**: `./scripts/smoke_backend.sh` → **PASS** (health 200, alembic at head 0001, uid 10001); volumes 64 → 64
- **smoke**: `./scripts/smoke.sh` → **PASS** (port 8088 free; health 200 via nginx after 12 s, login, data and storage survive `down`/`up`); volumes 64 → 64
- **Test count**: 289 at iteration 4, now 290 (+1: T37). Frontend unchanged at 14. No test deleted or weakened
- **Skipped tests**: none

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code / surgical changes / no scope creep | ✅ Fix diff: 1 test function (18 lines), `tasks.md` Phase 11; no production code |
| Matches patterns | ✅ Reuses `_create_requerimento_process`, `NEW_VERSION`, `versions_by_name` |
| Spec-anchored outcome check | ✅ 60/60 |
| Per-layer coverage | ✅ |
| Every test maps to a spec requirement | ✅ New test is tagged `# CARR-08` |
| Documented guidelines: `.specs/STATE.md` decisions; otherwise strong defaults applied | ✅ |
| Hygiene | ✅ No volume leak in any gate |

---

## Fix Plans

None. UI-06 (proxy evidence, a static CSS scan at 360 px) is a non-blocking improvement that fits the `implantacao` feature (a headless-browser check).

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INFRA-01..07, AUTH-01..11, DOC-01..05, PROC-01..14, CARR-01..10, AUD-01..04, UI-01..05, UNIT-01..03 | Implementing | ✅ Verified |
| UI-06 | Implementing | ⚠️ Verified (proxy evidence) |

---

## Iteration History

| Iteration | Verdict | Summary |
| --------- | ------- | ------- |
| 1 (`3387587..cc9c41d`) | FAIL ❌ | 57/58 ACs. CARR-08 unreachable once the open version was in use. M14, M15 and M20 survived (17/20 killed). Spec-precision gaps on PROC-02, PROC-04, PROC-09 and CARR-08. Smoke backend leaked a volume |
| 2 (`3387587..e6875e4`) | FAIL ❌ | User added CARR-09/CARR-10 and confirmed Assumptions; T29–T32 implemented them. CARR-08 reachable, M14/M15/M20 killed, spec-precision gaps closed, smoke leak fixed. N4 and N5 survived on the CARR-10/CARR-09 boundary days (14/16 killed). The pytest fixture leaked a volume |
| 3 (`3387587..6c022e1`) | FAIL ❌ | T33/T34 kill N4 and N5 and fix the pytest leak. 9 new boundary mutants: 6 killed, 3 survived on the career-version code (K1 and K2 on `_overlaps`, K3 on the day before the CARR-10 guard). 18/21 killed. Loop limit reached |
| 4 (`3387587..360eefb`) | FAIL ❌ | User approved one extra round. T35/T36 kill K1, K2 and K3. All gates green. 11 new mutants: 10 killed, 1 survived (X6, the `_in_use` date-coverage condition). 27/28 killed |
| 5 (`3387587..87114db`) | PASS ✅ | User approved a fifth round. T37 kills X6 (and the stronger X6b). K1, K2, K3, N4, N5 stay killed. All gates green, volumes stable at 64, 290 backend and 14 frontend tests. 13 new mutants across status transitions, optimistic lock, rate-limit window, session expiry, justification rule, list filtering, request validation and career validation: 12 killed, 1 equivalent (Y1). 40/41 killed, 0 real survivors |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 60/60 IDs matched the spec outcome; 0 spec-precision gaps (UI-06 on proxy evidence, non-blocking)
**Edge cases**: 5/5
**Sensor**: 40/41 killed; the survivor (Y1) is equivalent by proof
**Gate**: backend 290 passed, frontend 14 passed, smoke_backend PASS, smoke PASS, volumes 64 → 64 throughout

**What works**: every gap from iterations 1 to 4 is closed. The CARR-08 "in use" rule is pinned per version, on both the report (`in_use`) and the PUT guard.

**Issues found**: none blocking.

**Next steps**: none required for this feature. Optional: a headless 360 px check for UI-06 under `implantacao`.
