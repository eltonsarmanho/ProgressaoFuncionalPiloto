# Pontuação Validation

**Verdict**: PASS ✅ (iteration 2 of 3)
**Date**: 2026-11-17
**Spec**: `.specs/features/pontuacao/spec.md`
**Diff range**: `bf770bc..2f16100` (implementation from `51b11e9`; fixes since iteration 1: `aaac64d`, `2f16100`)
**Verifier**: independent sub-agent (author ≠ verifier)

All 80 IDs have evidence with an asserted value equal to the spec outcome. The three iteration-1 survivors (M31, M32, M56) are now killed. The two survivors of this iteration are equivalent (proofs below). The only residual caveat, TELA-08, is now a recorded Assumption.

---

## Task Completion

41 of 41 tasks marked done in `tasks.md` (T40, T41 added in Phase 8). No partial tasks. The two fix commits change only test files (`backend/tests/integration/scoring/test_table_choice.py`, `test_admin_create.py`) plus `spec.md` (3 Assumption rows) and `tasks.md`; no production code changed since iteration 1. Appended tests do not shift earlier line numbers, so every `file:line` test citation from iteration 1 was re-checked and still holds (spot re-reads: `test_scoring_points.py:58-62`, `test_scoring_verification.py:99-103`, `styles.test.ts:30-36`, `test_activity_update.py:245-250`, `test_scoring_periods.py:76-86`).

## Gate Check

| Gate | Result |
| ---- | ------ |
| `cd backend && .venv/bin/ruff check .` | exit 0, "All checks passed!" |
| `cd backend && .venv/bin/pytest -q` | 731 passed, 0 failed, 0 skipped, 133 s (iteration 1: 728; +3 = T40 two tests, T41 one test) |
| `cd frontend && npm run lint` | exit 0 |
| `cd frontend && npm test -- --run` | 14 files, 67 tests passed |
| `cd frontend && npm run build` | exit 0 (vite built) |
| `./scripts/smoke_backend.sh` | PASS (health 200, alembic head 0002, uid 10001); port 8088 was free |
| `./scripts/smoke.sh` | PASS (login 200, data and storage preserved across restart) |
| Docker volumes before / after backend pytest | 64 / 64 (a transient 65 during the run was the Verifier's own sensor database container, removed afterwards; volume count 64 at the end); no leftover containers or networks; `progressao-funcional-*` images untouched |
| Real tree porcelain | baseline `?? requeriment.txt`, `?? test/`; identical after the sensor and worktree removal |

---

## Spec-Anchored Acceptance Criteria

Paths relative to `backend/tests/` (B) or `frontend/src/` (F). Result ✅ = assertion value equals the spec outcome.

### TAB - Catálogo

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| TAB-01 | versions with vigência, status, norm ref, groups I..VIII | B integration/test_scoring_schema.py:97-125 (unique/range constraints 1..8); unit/domain/test_scoring_entities.py:57-77; integration/test_scoring_repositories.py:127 round trip | ✅ |
| TAB-02 | criterion fields per mode | unit/domain/test_scoring_entities.py:77 `test_criterion_keeps_mode_specific_fields_and_review_note`; api/test_scoring_tables_api.py:82-92 (`weeks_per_semester == 17`, `prep_ratio == "1.00"`, `hours_per_block == "3.00"`) | ✅ |
| TAB-03 | IFCH OFICIAL, counts 3/16/12/7/6/14/11/66, ref text | unit/test_seed_ifch.py:25-27 `[len(g["criteria"])...] == COUNTS`; :83-84 exact norm_reference; :81 `status == "OFICIAL"`; integration/test_seed_scoring.py:57-61, 64-71 | ✅ (points verified by group sums :35-41 and 6 reference items :44-49, not item by item) |
| TAB-04 | FASI PENDENTE_VALIDACAO, same numbering, ref text | unit/test_seed_fasi.py:32-33, :93-98 exact ref text; :59-60 real-case points; integration/test_seed_scoring.py:74-83 | ✅ |
| TAB-05 | 17 divergences II-VII plus VIII.5,6,7,38,39 flagged with note | unit/test_seed_fasi.py:36-38 `flagged == DIVERGENT_II_TO_VII \| GROUP_VIII_ANOMALIES`; :41-48 only flagged differ from IFCH; :70-77 notes | ✅ |
| TAB-06 | Group I counts: IFCH no, FASI yes | unit/test_seed_ifch.py:54 `counts_in_total is False`; unit/test_seed_fasi.py:82; api/test_scoring_tables_api.py:99-100 | ✅ |
| TAB-07 | FASI I.1/I.2 CARGA_SEMANAL 17 weeks prep 1/2; informed value item of old tables (absent from the official table) VALOR_INFORMADO cap 10 | unit/test_seed_fasi.py:84-90 | ✅ |
| TAB-08 | list tables, versions, groups, criteria in order | api/test_scoring_tables_api.py:32-47, :68-79, :135 (every role reads) | ✅ |

### SEL - Tabela aplicada ao processo

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| SEL-01 | table linked to units; IFCH→IFCH, FASI→FASI | integration/test_seed_scoring.py:67, :77 `units == {"FASI"}`; :96-98; api/test_scoring_tables_api.py:39-40 | ✅ |
| SEL-02 | suggest the version of the professor's unit valid on the interstice END date, newest validity wins (Assumption), not applied before confirmation | integration/scoring/test_table_choice.py:32-37 `chosen is None`, `suggested.version.id == fasi_version.id`; NEW :148-161 `suggested.version.id == new.version.id` with a second version starting 2023-06-01 (between process start 2022-11-23 and end 2024-11-23); NEW :164-178 `suggested.table_name == "Outra tabela da FASI"` (tie-break); api/test_scoring_process_api.py:60-64 | ✅ (M31, M32 now killed) |
| SEL-03 | no version → `REQUER_ANALISE_NORMATIVA` `TABELA_NAO_ENCONTRADA` | integration/scoring/test_table_choice.py:46-48; api/test_scoring_process_api.py:76; unit/domain/test_scoring_table_choice.py:31 | ✅ |
| SEL-04 | store version, audit user, before, after, justification | test_table_choice.py:58-64 `event.changes == {"scoring_table_version_id": {"before": None, "after": ...}}`, `event.user_id == secretaria.id`; :77-89 previous version in `before` | ✅ |
| SEL-05 | other unit: 422 `justificativa` + `TABELA_DE_OUTRA_UNIDADE` `ALERTA` | test_table_choice.py:92-106; api/test_scoring_process_api.py:99-102 | ✅ |
| SEL-06 | `TABELA_PENDENTE_VALIDACAO` `REQUER_ANALISE_NORMATIVA` on every result | test_table_choice.py:72-74; test_process_score.py:99-101; api/test_scoring_golden.py:121 | ✅ |
| SEL-07 | `TABELA_FORA_DE_VIGENCIA` `ALERTA`; end date inclusive | unit/domain/test_scoring_table_choice.py:60-76; api/test_scoring_process_api.py:115 | ✅ |
| SEL-08 | 409 on criteria change while a process uses the version | integration/scoring/test_admin_criteria.py:64-74 (`Conflict`, "nova versão" in message, value unchanged); api/test_scoring_admin_api.py:305 | ✅ |
| SEL-09 | re-evaluate by group/item; `SEM_ENQUADRAMENTO` when missing | integration/scoring/test_process_score.py:210-220 (`group_subtotals[2] == 20`), :223-256 (`reasons == (SEM_ENQUADRAMENTO,)`) | ✅ |

### ATV - Atividades

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| ATV-01 | manual activity persisted, origin MANUAL, VALIDADA | integration/scoring/test_activity_create.py:59-69; api/test_activities_api.py:58 (201) | ✅ |
| ATV-02 | Group I: `AAAA.N`, level, hours required (422 on the field); item I.1 GRADUACAO, I.2 POS | test_activity_create.py:84-103 `(group, item) == (1, item)`; :106-123 fields `academic_period`, `level`, `horas`; api/test_activities_api.py:112; informed value item exemption :253-259 (recorded in spec Assumptions; removed by correcoes-auditoria) | ✅ |
| ATV-03 | non-MANUAL origin → `AGUARDANDO_REVISAO` | test_activity_create.py:72-81 `status is AGUARDANDO_REVISAO`; unit/domain/test_activity_entity.py:18-20; api/test_activities_api.py:78-90 (public API cannot set source) | ✅ |
| ATV-04 | only three stored statuses | unit/domain/test_activity_entity.py:31 `test_stored_status_admits_only_the_three_spec_values`, :35 unknown rejected | ✅ |
| ATV-05 | no group/item or unknown item → saved, `SEM_ENQUADRAMENTO` | test_activity_create.py:126-137 | ✅ |
| ATV-06 | 422 on `quantidade` for <0, >10000, non-integer in POR_UNIDADE | test_activity_create.py:139-151 (limits inclusive); api/test_activities_api.py:124-149 | ✅ |
| ATV-07 | 422 on `horas` for <0, >10000 | test_activity_create.py:154-156 (`-0.5`, `10001` → `"horas"`) | ✅ |
| ATV-08 | justification 422 on `justificativa` when group/item/qty/hours/informed points change; audit before and after | integration/scoring/test_activity_update.py:54-72 (5 parametrized changes), :75-99; :102-116 `event.changes == {"quantity": {"before": "4", "after": "5"}}` | ✅ |
| ATV-09 | status change needs justification and audit; REJEITADA→AGUARDANDO is a new review | test_activity_update.py:144-159, :162-179 | ✅ |
| ATV-10 | candidate items with justification; only the chosen item scores | test_activity_create.py:244-250; test_activity_update.py:225-242 (`group_subtotals[2] == 40`, `[4] == 0`) | ✅ |
| ATV-11 | 409 on CONCLUIDO/ARQUIVADO | test_activity_create.py:179-186; test_activity_update.py:268-284; api/test_activities_api.py:295 | ✅ |
| ATV-12 | 404 for foreign DOCENTE/SECRETARIA | test_activity_create.py:189-194; test_activity_update.py:287-298; test_activity_list.py:97; api/test_activities_api.py:318 | ✅ |
| ATV-13 | first write wins, second 409 | test_activity_update.py:245-265 (`StaleVersion` on update, status, distinct; quantity stays 5); api/test_activities_api.py:225 | ✅ |
| ATV-14 | list all, filters by group/status, ordered | integration/scoring/test_activity_list.py:48-89; api/test_activities_api.py:170-195 | ✅ |

### CALC - Cálculo

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| CALC-01 | deterministic, Decimal, no LLM | unit/domain/test_scoring_engine.py:426 `calculate(...) == calculate(...)`; api/test_scoring_golden.py:195; architecture/test_layers.py:52 (no forbidden imports in the domain) | ✅ |
| CALC-02 | qty × unit | unit/domain/test_scoring_points.py:33-41 `points == D("40")` | ✅ |
| CALC-03 | 21h/3h/5pts = 7 blocks, 35; 2h = 0 | test_scoring_points.py:44-48 `points == 35`, `effective_quantity == 7`; :51-55 `points == 0`; :58-62 (22h → 7) | ✅ |
| CALC-04 | 68h grad 8,00; 34h 4,00; 68h pós 12,00; 20h grad 2,35 (half up) | test_scoring_points.py:65-66 `D("8.00")`; :69-70 `D("4.00")`; :73-74 `D("12.00")`; :77-81 `D("2.35")`, exponent -2; :84-88 tie 0.125 → `D("0.13")` | ✅ |
| CALC-05 | informed points capped at the max | test_scoring_points.py:102-117 (`7` kept; `14` → `10`, `limited_from == 14`) | ✅ |
| CALC-06 | override in CARGA_SEMANAL only, `PONTOS_AJUSTADOS_MANUALMENTE` `ALERTA`, justification | test_scoring_points.py:91-95, :120-126; test_scoring_engine.py:341; test_activity_create.py:202-230; api/test_scoring_golden.py:136-138 | ✅ |
| CALC-07 | caps on criterion and group, `LIMITE_APLICADO` with before/after | test_scoring_engine.py:208-221 `(before, after) == (12, 10)`; :234-243 `(60, 50)`; :246-257 order; :260-266 no alert at/below limit; test_process_score.py:195-207 | ✅ |
| CALC-08 | counts only VALIDADA, existing criterion, not excluded, group counts | test_scoring_engine.py:78-86, :89-98, :101-136, :152-175 | ✅ |
| CALC-09 | non-counting group → `GRUPO_NAO_CONTA`, subtotal 0 | test_scoring_engine.py:139-149 | ✅ |
| CALC-10 | potential separate, not in total | test_scoring_engine.py:89-98 `potential_total == 30`, `total == 0`; golden:171 `potential_total == "10.00"` | ✅ |
| CALC-11 | subtotals I..VIII, total, potential, counters | test_scoring_engine.py:396-423; golden:106-112 `counters == {...}` | ✅ |
| CALC-12 | per-row criterion, unit points, effective qty, formula, points, status, reasons, alerts | test_scoring_engine.py:385; api/test_scoring_process_api.py:212-228; golden:139-141 `formula_text == "21 h ÷ 3 h = 7 blocos × 5"` | ✅ |
| CALC-13 | Group I percent, no alert | test_scoring_engine.py:404 (None at total 0); test_process_score.py:139 `D("20.00")`; golden:118 `"22.22"` | ✅ |
| CALC-14 | golden: 92,120,15,95,0,30,6,56; total 414 | api/test_scoring_golden.py:107-108 `[s["subtotal"]...] == ["92.00","120.00","15.00","95.00","0.00","30.00","6.00","56.00"]`, `total == "414.00"`; extras kept out of the total :168-171 | ✅ |

### VERIF - Verificações

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| VERIF-01 | month precision = first to last day | unit/domain/test_scoring_periods.py:24-43 `== (date(2022,5,1), date(2022,5,31))`, leap February; golden:187-192 | ✅ |
| VERIF-02 | event outside → `FORA_DO_INTERSTICIO`; limits inclusive | test_scoring_periods.py:76-86; test_scoring_engine.py:129-136; golden:174-176 | ✅ |
| VERIF-03 | partial overlap scored + `INTERSTICIO_PARCIAL` `ALERTA` | test_scoring_periods.py:56-63, :89-104; test_scoring_engine.py:304 | ✅ |
| VERIF-04 | no date → scored + `DATA_AUSENTE` | test_scoring_periods.py:119; test_scoring_engine.py:319 | ✅ |
| VERIF-05 | same normalized title + overlap → newer excluded `DUPLICIDADE` | unit/domain/test_scoring_duplicates.py:25-29 `== {newer.id}`; :79-83 touching day overlaps; :121-126 tie by id; test_scoring_periods.py:142-148; golden:177-178 | ✅ |
| VERIF-06 | distinct justification → both count, audited | test_scoring_duplicates.py:32-40; test_activity_update.py:191-222 (`[PONTUADA, PONTUADA]`, `group_subtotals[2] == 50`, audit `justification == "Outro aluno"`) | ✅ |
| VERIF-07 | Group VI member/president same title → duplicate | test_scoring_duplicates.py:43-59 `== {president.id}` | ✅ |
| VERIF-08 | no comprovante → `SEM_COMPROVANTE` `ALERTA`, stays in total | test_scoring_engine.py:328-338; api/test_scoring_process_api.py:218 | ✅ |
| VERIF-09 | DE/40H with IV+V = 0 → `SEM_EXTENSAO_OU_PESQUISA` `ALERTA`, art. 13, II | unit/domain/test_scoring_verification.py:67-75 (both regimes, `"art. 13, II" in norm_reference`); :78-86 (20H, with IV or V: none); test_process_score.py:172-192 | ✅ |
| VERIF-10 | minimums 60/80/100/120, art. 12, 4.644 only | test_scoring_verification.py:101-103; integration/test_seed_scoring.py:86-88; unit/test_seed_ifch.py:86-87 | ✅ |
| VERIF-11 | `ATINGE`/`NAO_ATINGE`/`NAO_DEFINIDO`, boundary | test_scoring_verification.py:89-98 (99 → NAO_ATINGE, 100 → ATINGE); test_process_score.py:145-157; golden:119 | ✅ |
| VERIF-12 | Lei 15.141 → `NAO_DEFINIDO` + `MINIMO_NAO_DEFINIDO` `REQUER_ANALISE_NORMATIVA` | test_scoring_verification.py:106-115; test_process_score.py:160-169 | ✅ |
| VERIF-13 | alerts have code, severity, message, norm ref; never change or block | unit/domain/test_scoring_alerts.py:21-55; test_scoring_engine.py:353-358; test_scoring_verification.py:129-133; api/test_activities_api.py:162 (saved without classification) | ✅ |

### TELA / ADMUI - Frontend

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| TELA-01 | Etapa 4 enabled, 2, 3, 5-9 "em breve" | F pages/ProcessStep1.test.tsx:131-156; :158-167 link `href == "/processos/proc-1/pontuacao"` | ✅ |
| TELA-02 | 8 columns, grouped I..VIII | F components/ScoringTable.test.tsx:31, :46-58, :69-76 (`cells == ["II","7","Palestra","4,00","10,00","40,00","Portaria 12/2023","Pontuada"]`) | ✅ |
| TELA-03 | subtotals, total, potential, %, minimum, counters | F components/ScoringSummary.test.tsx:36-48, :50-56, :58-70, :72-84 | ✅ |
| TELA-04 | fields per mode; Group I fields; justification before sending on edit | F components/ActivityForm.test.tsx:67-99, :141-150 (`calls` length 0, `aria-invalid`), :152-166 | ✅ |
| TELA-05 | 422 message next to the field | F components/ActivityForm.test.tsx:168-190 | ✅ |
| TELA-06 | suggestion, status, norm ref, confirm before computing | F components/TablePicker.test.tsx:38-62; pages/ProcessScoring.test.tsx:259-269 (no `PUT` before confirm) | ✅ |
| TELA-07 | alerts grouped by severity with norm ref | F pages/ProcessScoring.test.tsx:144-155 (regions "Requer análise normativa (1)", "Alerta (2)"); components/ScoringTable.test.tsx:84-105 | ✅ |
| TELA-08 | usable at 360 px, stacked cards | F styles.test.ts:30-36 (CSS regex on the 480 px media query) and ScoringTable.test.tsx:107-121 (`data-label`) | ⚠️ Accepted: jsdom cannot measure layout; the spec now records the static CSS test as the check and defers the real 360 px test to a browser (Assumption row, spec.md:49). Mutant FN3 (`data-label` removed) killed |
| ADMUI-01 | ADMIN sees tables/versions with validity, status, ref | F pages/ScoringAdmin.test.tsx:83-97 (`"23/11/2022 a 28/02/2026"`, "Pendente de validação"), :114-128 (non-ADMIN redirected) | ✅ |
| ADMUI-02 | duplicate, new version, CSV with per-line errors | F components/ScoringAdminForms.test.tsx:29-58, :61-93, :104-143 (`items.map(textContent) == [...]`) | ✅ |
| ADMUI-03 | highlight criteria marked for review | F components/ReviewHighlight.test.tsx:39-49 (`toHaveClass("review")`), :51-57; pages/ScoringAdmin.test.tsx:133-148 | ✅ |

### ADM - Administração

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| ADM-01 | ADMIN creates table: unique name, units, first version | integration/scoring/test_admin_create.py:41-54, :81-90 (422 on `name`), :98 | ✅ |
| ADM-02 | duplicate = new table, copies the LAST version, independent, no unit association unless given (Assumption) | test_admin_create.py:131-145 `groups == fasi_version.groups`; :147-154 `unit_ids == ()`; :157-172 independence; NEW :196-211 `copy_version.valid_from == date(2023, 6, 1)`, `norm_reference == "Nova norma da FASI, 2023"` on a two-version source | ✅ (M56 now killed) |
| ADM-03 | edit on unused version needs norm ref, audit before/after | integration/scoring/test_admin_criteria.py:32-61, :77-85 (`field == "change_reference"`) | ✅ |
| ADM-04 | version in use → 409 asking for a new version | test_admin_criteria.py:64-74 | ✅ |
| ADM-05 | new version copies, requires start and ref, closes open one on the day before | integration/scoring/test_admin_versions.py:33-44, :47-60 (`valid_to == date(2026, 2, 28)`), :117-123 | ✅ |
| ADM-06 | 409 if closing leaves a process (end ≥ new start) without its version | test_admin_versions.py:74-86 (process end 2024-11-23 = new start → `Conflict`, `valid_to is None`), :89-96 (new start 11-24 → allowed, `valid_to == 2024-11-23`) | ✅ |
| ADM-07 | overlap → 409 | test_admin_versions.py:99-114 ("sobrepõe"); api/test_scoring_admin_api.py:245 | ✅ |
| ADM-08 | CSV UTF-8 with 8 columns creates a version with all rows | integration/scoring/test_admin_import.py:45-64; unit/test_criteria_csv.py:21; api/test_scoring_admin_api.py:330, :354 (BOM) | ✅ |
| ADM-09 | invalid rows → 422 listing every line/field; nothing created | test_admin_import.py:116-137 `[(3,"grupo"),(4,"modo"),(5,"pontos")]`, `only.valid_to is None`; unit/test_criteria_csv.py:68; api:362 | ✅ |
| ADM-10 | history lists versions, validity, ref, audit; old versions read-only | api/test_scoring_admin_api.py:452, :481, :498; test_admin_criteria.py:127-137 ("somente leitura") | ✅ |
| ADM-11 | non-ADMIN → 403 | test_admin_create.py:119; test_admin_criteria.py:88; test_admin_versions.py:135; test_admin_import.py:166; api/test_scoring_admin_api.py:137 | ✅ |

**Status**: ✅ 80 of 80 IDs matched the spec outcome. SEL-02 and ADM-02 clauses closed by T40/T41. TELA-08 is covered by a static CSS test that the spec Assumptions (spec.md:49) accept. 0 open spec-precision gaps (iteration 1 gaps on the SEL-02 tie-break and zero-unit duplicates are now Assumptions, spec.md:47-48, and both match the code: `scoring.py:114` `max(..., key=valid_from)`; `test_admin_create.py:147-154`).

---

## Edge Cases

- [x] 22 h / 3 h → 7 blocks: `unit/domain/test_scoring_points.py:58-62`
- [x] Limit exceeded → limit applied + `LIMITE_APLICADO`: `unit/domain/test_scoring_engine.py:208-221`
- [x] Invalid interstice → `NAO_VERIFICAVEL`, no `FORA_DO_INTERSTICIO`: `test_scoring_periods.py:123-139`, `test_scoring_engine.py:365-373`
- [x] No table chosen → total 0, `SEM_TABELA`, suggestion or `TABELA_NAO_ENCONTRADA`: `api/test_scoring_process_api.py:168-183` (`total == "0.00"`, `reasons == ["SEM_TABELA"]`), `integration/scoring/test_process_score.py:45-72`
- [x] Title 301 / note 501 → 422 on `title` / `evidence_note`: `integration/scoring/test_activity_create.py:159-163`

5 of 5.

---

## Discrimination Sensor

Depth: expanded (49 mutations: 44 backend + 5 frontend; isolated `git worktree` of HEAD under the session scratchpad, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, shared throwaway PostgreSQL via `TEST_DATABASE_URL`, `frontend/node_modules` symlinked). Source lines below are from HEAD; the iteration-1 numbering of source lines had drifted a few lines, so they are re-anchored by code text.

| # | File | Mutation | Result |
| - | ---- | -------- | ------ |
| M31 | use_cases/scoring.py:112 | suggestion by `process.start_date` instead of `end_date` | ✅ killed (`test_suggestion_uses_the_interstice_end_date_not_the_start`) |
| M32 | use_cases/scoring.py:114 | `max` → `min` on the candidate versions | ✅ killed (`test_suggestion_picks_the_newest_validity_when_several_tables_fit_the_unit`) |
| M56 | use_cases/scoring_admin.py:136 | `latest_version` returns the first version | ✅ killed (`test_duplicate_of_a_table_with_two_versions_copies_the_latest`) |
| M34 | use_cases/scoring.py:394 | use-case optimistic-lock check `if False` | ◻ survived, equivalent (see Equivalence) |
| K01 | domain/rules/scoring_points.py:41 | block floor → half-up | ✅ killed |
| K02 | scoring_points.py:55 | half-up → floor | ✅ killed (`rounds_half_up_not_half_even`) |
| K03 | scoring_points.py:55 | preparation ratio dropped | ✅ killed |
| K04 | scoring_periods.py:48 | FORA test made inclusive of the limits | ✅ killed |
| K05 | scoring_periods.py:50 | DENTRO start strict | ✅ killed |
| K06 | scoring_duplicates.py:38 | overlap strict `<` | ✅ killed |
| K07 | scoring_duplicates.py:31 | newest-first order | ✅ killed |
| K08 | scoring_duplicates.py:33 | distinct justification ignored | ✅ killed |
| K09 | scoring_engine.py:167 | AGUARDANDO_REVISAO counts in total | ✅ killed |
| K10 | scoring_engine.py:191 | criterion cap not applied | ✅ killed |
| K11 | scoring_engine.py:204 | group cap not applied | ✅ killed |
| K12 | scoring_verification.py:57 | `>=` → `>` | ✅ killed |
| K13 | use_cases/scoring.py:87 | read access check removed | ✅ killed |
| K14 | use_cases/scoring.py:93 | closed process writable (create/choose) | ✅ killed |
| K14b | use_cases/scoring.py:389 | closed process writable (existing activity) | ✅ killed |
| K15 | scoring_admin.py:398 | open version closed on the new start, not the day before | ✅ killed |
| K16 | scoring_admin.py:538 | CSV errors do not stop creation | ✅ killed |
| K17 | use_cases/users.py:20 | `require_admin` disabled | ✅ killed |
| K18 | use_cases/scoring.py:248 | quantity limit exclusive | ✅ killed |
| K19 | scoring_engine.py:229 | Group I percent from Group II | ✅ killed |
| K20 | domain/entities/scoring.py:63 | validity end exclusive | ✅ killed |
| K21 | use_cases/scoring.py:172 | other-unit table needs no justification | ✅ killed |
| N01 | scoring.py:455 | same-status change accepted | ✅ killed |
| N02 | scoring.py:452 | status change without justification | ✅ killed |
| N03 | scoring.py:466 | status event audited as UPDATE instead of STATUS | ✅ killed |
| N04 | scoring.py:353 | `points_override` without justification | ✅ killed |
| N05 | scoring.py:481 | "distinct" mark without justification | ✅ killed |
| N06 | scoring.py:493 | distinct audit before/after emptied | ✅ killed |
| N07 | scoring_admin.py:620 | history events in reverse chronological order | ✅ killed |
| N08 | scoring_admin.py:587 | `set_table_units` not persisted | ✅ killed |
| N09 | services/criteria_csv.py:122 | unknown CSV columns not reported | ✅ killed |
| N10 | criteria_csv.py:119 | missing CSV columns not reported | ✅ killed |
| N11 | criteria_csv.py:107 | parser BOM strip removed | ✅ killed (`test_utf8_bom_is_accepted`) |
| N11b | presentation/api/scoring_tables_admin.py:104 | `utf-8-sig` → `utf-8` alone | ◻ survived, equivalent (see Equivalence) |
| N12 | scoring_engine.py:191 | criterion `LimitAdjustment` before/after swapped | ✅ killed |
| N13 | scoring_engine.py:204 | group `LimitAdjustment` before/after swapped | ✅ killed |
| N14 | use_cases/scoring.py:273 | candidate item without justification accepted | ✅ killed |
| N15 | use_cases/scoring.py:507 | listing ignores the event date | ✅ killed |
| N16 | presentation/api/activities.py:94 | "distinct" route passes version 0 | ✅ killed |
| N17 | scoring_verification.py:54 | class minimums ignored | ✅ killed |
| F01 | frontend ActivityForm.tsx:94 | edit without justification | ✅ killed |
| F02 | frontend labels.ts:75 | decimal dot not turned into a comma | ✅ killed |
| FN1 | ActivityForm.tsx:117 | `expected_version: activity.version + 1` | ✅ killed |
| FN2 | TablePicker.tsx:52 | justification prompt never shown | ✅ killed |
| FN3 | ScoringTable.tsx:43 | `data-label` attribute renamed (TELA-08 card labels) | ✅ killed |

**Equivalence proofs**
- M34: with the use-case check off, `uow.activities.update(updated, expected_version)` runs `_versioned_update` (repositories.py:77-90), whose `WHERE version = expected` raises the same `StaleVersion` (HTTP 409); only the message text differs and the spec fixes none (ATV-13: "a segunda falha com 409"). The repository twin (iteration 1 M35) is killed.
- N11b: `criteria_csv.parse_criteria_csv` strips the BOM again (`removeprefix`). Mutating only the API decode leaves behavior identical. Mutating both layers fails `test_scoring_admin_api.py::test_csv_with_bom_is_accepted` (probe run in the scratch), so the BOM assertion discriminates when the defense is really gone.

**Totals**: 49 injected; 47 killed; 2 survived, both equivalent; 0 non-equivalent survivors. Scratch worktree removed; real porcelain equals the baseline.
**Result**: ✅ PASS

---

## Author Choices Checked Against the Spec

| Choice | Verdict |
| ------ | ------- |
| SEL-02 tie-break: newest `valid_from` | Now an Assumption (spec.md:47); matches `scoring.py:114`; asserted at `test_table_choice.py:164-178`. |
| Duplicate table born without units | Now an Assumption (spec.md:48); the suggestion only considers tables of the professor's unit, so a unit-less copy is never suggested; asserted at `test_admin_create.py:147-154`. No contradiction with SEL-01 as scoped by the Assumption. |
| 360 px verified by static CSS test | Now an Assumption (spec.md:49); accepted. A browser test is still advisable at deployment. |
| quantity None counts as 1 in POR_UNIDADE | Spec silent (CALC-02); no contradiction. |
| `points_override` only in CARGA_SEMANAL | Matches CALC-06 (`test_scoring_points.py:120-126`). |
| `potential_total` plain sum without caps; `group1_percent` null at total 0 | Spec silent; no contradiction. |
| Informed value item of old tables (absent from the official table) exempt from the Group I period/level/hours rule | Spec Assumption (spec.md:46). |
| New tables/versions/imports default to `PENDENTE_VALIDACAO` | Spec silent; consistent with TAB-04's cautious intent. |
| Criteria edit on a superseded version → 409 "somente leitura" | Stricter than ADM-03, supported by ADM-10. Accepted. |
| CSV upload bypasses `api/client.ts` | Behavior verified (`ScoringAdminForms.test.tsx:119`, `:139`). Accepted. |

No author choice contradicts a spec AC.

---

## Ranked Gaps

None blocking. Advisory only:
1. TELA-08: real horizontal-scroll behavior at 360 px is not machine-checked (jsdom). Spec Assumption defers it to a browser test at deployment (`spec.md:49`).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| No scope creep (iteration-2 delta is two tests plus spec/tasks bookkeeping) | ✅ |
| Matches existing patterns | ✅ |
| Tests map to ACs and edge cases; no unclaimed tests | ✅ |
| Spec-anchored outcome check (asserted values match spec outcomes) | ✅ |
| Documented guidelines | none - strong defaults applied |

## Requirement Traceability Update

Not applied automatically (the Verifier does not edit `spec.md`). Recommended: all 80 IDs Verified.

## Iteration History

| Iteration | Verdict | Findings |
| --------- | ------- | -------- |
| 1 | FAIL ❌ | 60 mutants, 3 non-equivalent survivors (M31, M32, M56); SEL-02 and ADM-02 clauses not discriminated; 2 spec-precision gaps; TELA-08 caveat |
| 2 | PASS ✅ | T40/T41 added 3 tests; 49 mutants (4 re-runs, 22 prior-killed re-runs, 18 new, 5 frontend), 2 equivalent survivors; gaps recorded as Assumptions |

## Summary

**Overall**: ✅ Ready.
**Spec-anchored check**: 80/80 IDs matched; 0 open spec-precision gaps.
**Sensor**: 47/49 killed, 2 equivalent, 0 non-equivalent survivors.
**Gate**: backend 731 passed; frontend 67 passed, lint and build exit 0; both smokes PASS.
