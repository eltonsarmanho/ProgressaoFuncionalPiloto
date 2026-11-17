# Tabela Oficial Validation

**Date**: 2026-11-17
**Spec**: `.specs/features/tabela-oficial/spec.md`
**Diff range**: `483ab7e..HEAD` (HEAD = `5c61623`, 23 commits, T1 to T23)
**Verifier**: independent sub-agent (author != verifier). Worked in detached git worktrees under the scratchpad (`verifier/wt`, `verifier/mut`, `verifier/old` = `483ab7e`); the real tree was never touched (porcelain before/after: only the pre-existing `?? requeriment.txt`, `?? test/`, plus this file).

## Validation: Tabela Oficial - PASS

**Verdict: PASS (with 1 medium gap, 4 low gaps and 1 spec drift to record).** 22 of 23 requirements PASS; ACE-02 is PARTIAL by its own definition (process criterion, no dedicated test), and the evidence for it holds.

---

## Task Completion

| Task | Commit | Status | Notes |
| ---- | ------ | ------ | ----- |
| T1 | `4989a85` | Done | `ScoringCriterion.min_hours` |
| T2 | `72c4f92` | Done | `CARGA_HORARIA_INSUFICIENTE`, `CARGA_HORARIA_NAO_INFORMADA` |
| T3 | `2731233` | Done | engine rule, 19,99 h / 20 h boundary |
| T4 | `f12d0ac` | Done | Group I as PIT hours |
| T5 | `98a5a11` | Done | 422 on `points_override` in Group I (only where Group I is in PIT hours, see Gap 3) |
| T6 | `ddd72f1` | Done | migration 0004 |
| T7 | `45de245` | Done | repositories |
| T8 | `14f8770` | Done | `ufpa.json` (100 criteria) |
| T9 | `d63116e` | Done | seed + archive legacy |
| T10 | `ead93f5` | Done | old seeds removed; replaced tests listed in the body |
| T11 | `5118b37` | Done | API fields |
| T12 | `6ddad77` | Done | suggestion rules |
| T13 | `ccbf1ff` | Done | quantity per course/event |
| T14 | `2d4fbde` | Done | rules vs seeded table |
| T15 | `829d7eb` | Done | integration tests moved; changed values listed |
| T16 | `7228804` | Done | API tests moved; changed values listed |
| T17 | `695e45a` | Done | docstrings only (committed after T18, reordering disclosed) |
| T18 | `a506cb4` | Done | golden 211 |
| T19 to T22 | `d54d05e`, `49b9ad8`, `ccafb4c`, `690357b` | Done | frontend |
| T23 | `5c61623` | Done | docs; `validate_tasks.py` WARN T23 "Tests: none" is expected (matrix says docs = none) |

All `- [ ]` in `tasks.md`: 0. `validate_spec.py`: 0 errors, 0 warnings. `validate_tasks.py`: 0 errors, 1 warning (T23, expected).

---

## Ground truth: independent re-derivation from the xlsx

Read `Modelos/tabela-progressao-docente.xlsx` with openpyxl (venv under the scratchpad, formulas and cached values, all 348 non-empty cells, merged cells and hidden rows checked), parsed item by item (`parsex.py`), then compared with `backend/app/infrastructure/database/seed_data/ufpa.json` (`wt` at HEAD).

| Check | xlsx (derived) | ufpa.json | Result |
| ----- | -------------- | --------- | ------ |
| Items per group I..VIII | 2, 16, 9, 6, 5, 14, 11, 37 (numbers contiguous 1..N in every group) | 2, 16, 9, 6, 5, 14, 11, 37 | match |
| Sum of formulas II..VIII (raw) | 150, 44, 40, 75, 332, 258, 426 = 1325 | n/a | the 5 divergences explain the delta |
| Sum with the 5 user decisions | 158, 44, 40, 75, 332, 258, 407 = 1314 | 158, 44, 40, 75, 332, 258, 407 = 1314 | match |
| Text vs formula scan, all 97 numbered rows II..VIII | exactly 5 divergences: II.10 (text 10, formula x2), VI.14 (3 vs x6), VIII.4 (15 vs x20), VIII.8 (15, 15 vs x25), VIII.12 (2 vs x6). VIII.7, VIII.13, VIII.14 repeat the same number twice in the text (consistent with the formula). VIII.37 has no formula (literal 0). No formula references a neighbouring row; no merged-cell or hidden-row surprises. | decisions II.10=10, VI.14=6, VIII.4=15, VIII.8=15, VIII.12=2, VIII.37=0 each with a `review_note` | **no divergence beyond the five known ones** |
| Per item (100 criteria): description, unit_points, mode, min_hours | n/a | all 97 pointed items equal the xlsx (or the user decision); descriptions equal after whitespace normalization except VIII.7/8/13/14, where the duplicated trailing "(N pontos)" of the sheet was collapsed (benign, Gap 5) | match |
| VII.11 | "cada 30 horas = 1 ponto" | `POR_BLOCO_DE_HORAS`, block 30, 1 point | match |
| IV.3, IV.4, IV.5 | "carga horária mínima de 20 h" / "mínimo de 20 h"; IV.6 has none | `min_hours` 20 on IV.3-5 only | match |
| Group I | rows 3-4 "(HORAS)", TOTAL formula `=D138+D96+D80+D60+D48+D38+D24` excludes Group I | `CARGA_SEMANAL`, 17 weeks, prep 1 and 2, `counts_in_total` false | match |
| Golden (ACE-01) recomputed from xlsx values | subtotals II..VIII = 52, 7, 62, 0, 30, 4, 56, total 211 | spec says the same | match |

---

## Spec-Anchored Acceptance Criteria

Evidence paths are relative to `backend/` unless noted (`fe/` = `frontend/src/`). Line numbers are at HEAD.

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| OFI-01 | seeded table "Tabela de Pontuação da UFPA", `OFICIAL`, valid_from 2015-03-24, norm_reference text | `tests/integration/test_seed_scoring.py:113` (`list(tables) == [OFFICIAL]`, `[v.status.value...] == ["OFICIAL"]`) and `:123` (`version.valid_from == date(2015,3,24)`, `norm_reference == "Tabela oficial de pontuação ... 2026-11-17)"`); `tests/unit/test_seed_ufpa.py:109` | PASS |
| OFI-02 | 2,16,9,6,5,14,11,37 criteria with sheet descriptions | `tests/unit/test_seed_ufpa.py:24` (`[len(g["criteria"])...] == COUNTS`), `:29` (sequential numbers), `tests/integration/test_seed_scoring.py:123` (`[len(g.criteria)...] == COUNTS` read back from Postgres). Descriptions checked by the verifier against the xlsx (the repo test pins only 3 prefixes, `:128`) | PASS |
| OFI-03 | sheet values and II.10=10, VI.14=6, VIII.4=15, VIII.8=15, VIII.12=2 | `tests/unit/test_seed_ufpa.py:42` (parametrized `unit_points == points` for the 5), `:47` (review_note records divergence), `:58` (II.7=5, III.2=5, III.4=2, IV.1=15, VIII.9=25, VIII.24=10, VIII.33=15); mutations D8, D9, D9b, D9c, D9d killed | PASS |
| OFI-04 | sums 158,44,40,75,332,258,407; 1314 | `tests/unit/test_seed_ufpa.py:35` (`sums == GROUP_SUMS`, `sum(sums) == 1314`); verified independently against the xlsx | PASS |
| OFI-05 | VII.11 per 30 h; rest per unit; VIII.37 0 points with text | `tests/unit/test_seed_ufpa.py:72` (`mode == "POR_BLOCO_DE_HORAS"`, block 30, 1), `:79` (all others POR_UNIDADE), `:84` (VIII.37 `== 0`, text starts "Afastamento de docente"); `tests/integration/test_seed_scoring.py:143` (survives DB) | PASS |
| OFI-06 | `min_hours` 20 on IV.3-5; hours < 20 => `NAO_PONTUADA` + `CARGA_HORARIA_INSUFICIENTE`; exactly 20 scores | `tests/unit/test_seed_ufpa.py:63` (`min_hours == 20` for IV.3/4/5), `:67` (only those three); `tests/unit/domain/test_scoring_engine.py:500` (19,99 h: `reasons == (CARGA_HORARIA_INSUFICIENTE,)`, `points == 0`), `:511` (20 h: `PONTUADA`, `points == 5`), `:546` (0 h is insufficient). Engine-only coverage: no integration test drives the seeded IV.x item through the use case (Gap 2) | PASS |
| OFI-07 | no hours => scores and `CARGA_HORARIA_NAO_INFORMADA` ALERTA | `tests/unit/domain/test_scoring_engine.py:531` (`PONTUADA`, `points == 5`, code present, `severity is Severity.ALERTA`, total 5) | PASS |
| OFI-08 | IFCH/FASI not seeded any more | `tests/integration/test_seed_scoring.py:168` (names after seed do not intersect legacy names); `ls seed_data/` = only `ufpa.json`; `app/infrastructure/database/seed.py` has no reference to `ifch.json` or `fasi.json` | PASS |
| OFI-09 | on a DB with IFCH/FASI: archive + detach units, except versions chosen by a process | `tests/integration/test_seed_scoring.py:173` (`archived is True`, `acronyms == set()`, `len(versions) == 1`), `:192` (`list_versions_for_unit` returns only the official), `:206` (used table: `archived is False`, units `{"FASI"}`, same version ids). Real-Postgres simulation on the pre-change seed in Section "Deployed-DB simulation" below | PASS |
| OFI-10 | FASI and IFCH associated; minimums 60/80/100/120 with art. 12 reference | `tests/integration/test_seed_scoring.py:113` (`acronyms == {"FASI","IFCH"}`), `:138` (`versions[0].minimums == MINIMUMS`); mutation C7 killed | PASS |
| OFI-11 | seeding twice duplicates nothing | `tests/integration/test_seed_scoring.py:154` (table/unit/version/group/criteria counts `== first`, and `== {1,2,1,8,100}`), `:221` (re-run with archived legacy changes nothing); mutation C6 killed; simulation: state identical after 2nd boot | PASS |
| OFI-12 | `min_hours` persisted via migration | `tests/integration/test_migration_min_hours.py:52` (nullable Numeric(9,2)), `:60` (stores "20.00" and NULL), `:71` (downgrade -1 drops, upgrade restores); `tests/integration/scoring/test_min_hours_persistence.py:59` round trip; mutations C8, C9, C9b, C10 killed | PASS |
| PIT-01 | 68 h grad = 8,00; 34 h = 4,00; 68 h pós = 12,00; half-up 2 places | `tests/unit/domain/test_scoring_engine.py:630` (`pit_hours == D("8.00")`), `:641` (`4.00`), `:647` (`12.00`); half-up proven by `tests/unit/domain/test_scoring_points.py:84` (true tie 0.125 => 0.13) and engine `:653`; API through the seeded table `tests/integration/api/test_scoring_pit_hours_api.py:48` (`["12.00","4.00","8.00"]`) | PASS |
| PIT-02 | hours per period and total reported; points, subtotal, total contribution 0 | `tests/unit/domain/test_scoring_engine.py:659` (`group1_hours_by_period == {"2023.1": 28.00, "2023.2": 12.00}`), `:693` (subtotal 0, total 20, potential 0); `tests/integration/api/test_scoring_golden.py:122` (`group1_hours_by_period == EXPECTED_HOURS_BY_PERIOD`, `group1_total_hours == "92.00"`, `subtotals[0] == {1, "0.00"}`); `tests/integration/api/test_scoring_pit_hours_api.py:61,66` | PASS |
| PIT-03 | `points_override` in Group I => 422 on `points_override` | `tests/integration/scoring/test_activity_group1_pit.py:77` (create), `:90` (pós), `:104` (update); `:161` documents that a table whose Group I counts in points keeps accepting it. Implementation refuses only where Group I is in PIT hours (`app/application/use_cases/scoring.py:317`, `# SPEC_DEVIATION`); the spec text says unconditionally (Gap 3) | PASS (with spec drift) |
| MAP-01 | 13 Group VIII types on the official numbers; books/chapters VIII.1-4 | `tests/unit/domain/test_suggestion_rules.py:228` (13 principals + alternatives), `:245` books/chapters, parametrized row table `:16-84`; mutations M9a, M9b, M9c killed | PASS |
| MAP-02 | BANCA_PROCESSO_SELETIVO and EXTENSAO_EVENTO_MINISTRANTE without item; no III.12 | `tests/unit/domain/test_suggestion_rules.py:251` (no rule uses III.11, III.12, IV.7), `:257` (selection boards have no alternative), `:262`; the no-item taxonomies parametrized in the `principal is None` test | PASS |
| MAP-03 | every principal/alternative exists in the seeded official table, enforced by a test | `tests/integration/test_rules_match_official_table.py:44` (`_missing(official) == []`), `:55` and `:62` (injected bad principal/alternative is reported: the check has teeth) | PASS |
| MAP-04 | course/event quantity 1 per document with hours kept; internship by hours | `tests/unit/domain/test_quantity_rules.py:89` (`quantity == D(1)`, `hours == D("21")`), `:81` (internship `quantity is None`, `hours == 60`); analyzer `tests/unit/application/test_document_analyzer_classification.py:322` (`quantity == 1`); mutation M14 killed | PASS |
| ACE-01 | subtotals 52,7,62,0,30,4,56; total 211; PIT 24,24,24,20 | `tests/integration/api/test_scoring_golden.py:110` (`subtotals == EXPECTED_SUBTOTALS`, `total == "211.00"`), `:122` (`24.00,24.00,24.00,20.00`, total 92.00); 211 re-derived from the xlsx by the verifier; mutations D7g, E1, E3, D1g killed | PASS |
| ACE-02 | old tests green on the official table; no asserts weakened; changed values in commit bodies | Process criterion. Evidence: Gate 2028 passed; AST comparison of every modified test file at `483ab7e` vs HEAD: asserts+raises 1114 -> 1227, no test lost an assertion except `test_lists_the_seeded_tables...` (11 -> 10, the FASI/IFCH-specific `status`/`norm_reference` pair collapsed into the official one); commit bodies of `829d7eb`, `7228804`, `ead93f5` list each changed value. Spec marks it Pending; no dedicated test is possible | PARTIAL (by definition) |
| TELA-01 | Group I column "horas (PIT)", hours per period, total hours, never as points | `fe/components/ScoringTable.test.tsx:138` (hours with label, no points), `:153` (group header shows total hours); `fe/pages/ProcessScoring.test.tsx:307`; mutations F4, F5 killed | PASS |
| TELA-02 | total labelled "Total geral (Grupos II a VIII)"; PIT hours apart | `fe/components/ScoringSummary.test.tsx:114` (label, Group I subtotal absent), `:122` (per period, ordered), `:134` (total hours apart); `fe/pages/ProcessScoring.test.tsx:318`; mutations F1, F2, F3, F7 killed | PASS |

**Status**: all 23 covered with `file:line` evidence; 22 PASS, 1 PARTIAL (ACE-02, by definition). Spec-precision gaps: PIT-03 (see Gap 3).

**Edge cases**
- [x] exactly 20 h scores, 19,99 h does not: `test_scoring_engine.py:511`, `:500`; mutation M2 (`<` to `<=`) killed.
- [x] DB with official + archived old tables, re-initialized: nothing changes: `test_seed_scoring.py:221`; simulation state identical after 2nd boot.
- [x] process that chose an old version keeps version and calculation: `test_seed_scoring.py:206`; simulation shows identical results (below).

---

## Discrimination Sensor

Run in an isolated worktree (`verifier/mut`, reset with `git checkout -- .` after each mutant, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`), against targeted test selections. Depth: full manual mutation (P0 data-integrity feature): 64 mutants.

| Area | Mutants | Killed | Notes |
| ---- | ------- | ------ | ----- |
| `min_hours` enforcement: rejection removed (M1), boundary `<` to `<=` (M2), missing-hours alert removed (M3), missing hours not scored (M3b) | 4 | 4 | `test_scoring_engine.py:500/511/531` |
| PIT hours: HALF_UP to HALF_DOWN (M6r), hours doubled (M6b), Group I points leak into total (M10b, E1), pending offers counted (M20), periods collapsed (E3), informed points replace hours (E5) | 7 | 7 | rounding by `test_scoring_points.py:84`; golden by `test_scoring_golden.py:110,122` |
| Rejection of `points_override` in Group I removed (C1), wrong error field (C1b) | 2 | 2 | `test_activity_group1_pit.py:77` |
| Archive-old-tables: archive not called (C3), units not detached (C4), used-version protection inverted (C5) or removed (C5b), LEGACY list shortened (C7b) | 5 | 5 | `test_seed_scoring.py:173,206` |
| Seed: non-idempotent (C6), only FASI associated (C7), `min_hours` dropped from JSON (C13) | 3 | 3 | `:154`, `:113`, `:143` |
| Migration 0004: downgrade no-op (C8), scale (C9), not-null (C9b); repository field (C10) | 4 | 4 | `test_migration_min_hours.py`, `test_min_hours_persistence.py` |
| API: `group1_total_hours` zero (C11), `pit_hours` None (C11b), admin `min_hours` not editable (C14), CSV ignores `min_hours` (M15) | 4 | 4 | |
| Suggestion rules: PALESTRA 24 to 28 (M9a), ARTIGO_INTERNACIONAL 9 to 12 (M9b), REGISTRO_SOFTWARE 33 to 63 (M9c); course quantity back to hours (M14) | 4 | 4 | note: M9a keeps a valid item (VIII.28 exists), killed only because the unit table pins every row; the integration check alone would not catch it |
| Seed data: weeks 17 to 16 (D1, D1u, D1g), pós prep 2 to 1 (D2, D2u), IV.3/IV.4/IV.5 minimum (D3, D3b, D3c), VII.11 block (D4), VIII.37 points (D6), IV.1 15 to 16 (D7, D7g), the five decided values reverted (D8, D9, D9b, D9c, D9d), drop VIII.37 (D10), Group I counts (D11) | 20 | 20 | `D2g` (golden only, no pós offer) survives by design, killed by `test_seed_ufpa.py:91` |
| Frontend: label constant (F1), Group I subtotal not filtered (F2), PIT block removed (F3), points shown instead of hours (F4), total hours not passed (F5), old-table flag forced (F6), period label (F7) | 7 | 7 | |
| Data compensating pairs: II.1<->II.2 swap (D12), VIII.20 +1 / VIII.21 -1 (D13), sums unchanged | 2 | 0 | **survivors** (Gap 1); both combined also survive the entire backend suite (2028 passed with the mutated seed) |
| Narrow selections that survive but are killed elsewhere: E2 (min_hours never enforced) vs integration+golden, E4 (pending PIT offers counted) vs golden, D2g | 3 | 0 in-scope, killed by the unit suite (M1, M20, D2) | not counted as survivors |

Invalid mutant discarded and redone: M6 (`ROUND_HALF_DOWN` not imported -> NameError) redone as M6r.

**Result**: 62 killed of 64 injected by the tests that own the behavior; 2 survivors (D12, D13), both in seed-data value integrity (Gap 1). Isolation: porcelain of the real tree before and after the sensor is identical (`?? requeriment.txt`, `?? test/`).

---

## Gate Check

- **Gate command** (Build): `cd backend && ruff check . && pytest -q && cd ../frontend && npm run lint && npm test -- --run && npm run build`, run in worktree `verifier/wt` at HEAD, own venv, `PYTHONDONTWRITEBYTECODE=1`, Postgres 16 container started by the project's own conftest (`docker run postgres:16-alpine`, removed by the fixture).
- **Result**: ruff clean; backend **2028 passed, 0 failed, 0 skipped** (268 s); frontend lint clean, **87 passed (15 files)**, build OK.
- **Test count before feature (`483ab7e`, collected)**: backend 1880, frontend 67. **After**: backend 2028 (+148), frontend 87 (+20).
- **Skipped tests**: none.
- Containers: none left running (`docker ps -a` empty after every run).

### Test integrity (T15 to T17 and T10)

- AST comparison (assert and `pytest.raises` per test function, old vs new, 31 modified test files): no function lost an assertion except `test_lists_the_seeded_tables_with_versions_validity_status_and_reference` (11 -> 10: the FASI `PENDENTE_VALIDACAO`/FASI norm_reference and IFCH `OFICIAL`/IFCH norm_reference pairs became the single official version's status/reference; values that only the old tables had). Totals 1114 -> 1227.
- Tests renamed or removed and their replacements reviewed: `test_seed_fasi.py` (100 lines) and `test_seed_ifch.py` (87) deleted; the commit body of `ead93f5` maps each to `test_seed_ufpa.py`; the FASI-vs-IFCH comparisons encoded only old-table values and have no equivalent, which is correct. `test_scoring_golden.py` lost three old-value tests, replaced by four official-table tests with the spec values.
- Fixture rename `fasi_chosen` to `official_chosen`; tests that need informed points in Group I (`test_points_override_only_for_weekly_load...`, `test_group_one_student_evaluation_item_keeps_informed_points`, Group I percentage, limit adjustments) were moved to `points_chosen` (a copy of the table whose Group I counts in points, `tests/support/scoring_variants.py`), assertions unchanged. This keeps the legacy behavior covered.
- Changed numbers (II.7 10 to 5, II.8 10 to 3, totals, group counts, interstice 2018-2020 to 2010-2012 because the table is valid from 2015-03-24) were all re-derived and are consistent with the xlsx.
- No weakening found.

### Deployed-DB simulation (real Postgres 16, pre-change data)

Procedure (`sim/run.sh`, three scenarios, one fresh container each, removed afterward): check out `483ab7e` (`old`), `alembic upgrade head` (0003) + `python -m app.infrastructure.database.seed` (creates IFCH and FASI tables from the old JSON), create a process with 10 activities (II.7, II.8, II.12, III.2, IV.1, IV.4 21 h, VIII.11, VIII.4, two Group I offers, plus a Group I `points_override` for FASI), choose the old version, calculate with the OLD code and dump; then, on the same database, HEAD code: `alembic upgrade head` (0004) + the seed (the container entrypoint path), calculate with the NEW code and dump; second boot; `downgrade -1` then `upgrade head`.

| Scenario | Before (old code, 0003) | After upgrade + seed | Result |
| -------- | ----------------------- | -------------------- | ------ |
| A: process chose FASI version | FASI 1 unit, IFCH 1 unit, both active, 135 criteria each | FASI table untouched (active, unit FASI, 135 criteria, process still points to its version); IFCH archived, 0 units, 135 criteria kept; UFPA created (100 criteria, units FASI+IFCH); alembic 0004 | PASS |
| B: process chose IFCH version | same | IFCH untouched; FASI archived, 0 units; UFPA created | PASS |
| C: no process chose any version | same | FASI and IFCH archived with 0 units, nothing deleted (versions and 135 criteria each still there); UFPA the only active table | PASS |

For A, B and C: second boot leaves the full state identical (`cmp` of the table/version/criteria/unit/process dumps); `downgrade -1` + `upgrade head` returns to the same state; **the process calculation is byte-identical before and after** (A: total 257.0000, subtotals 1..8 = 32.00/110/10/65/0/0/0/40, G1 percent 12.45, 11 rows, alert `TABELA_PENDENTE_VALIDACAO`, including the legacy Group I `points_override`; B: total 182.0000, G1 0 because the old IFCH Group I is out of the total; C: no table, total 0). So the VM-deployed process using FASI/IFCH tables would keep computing the same results, provided the VM data resembles the pre-change seed.

---

## Interface behavior with old-table versions

- `ProcessScoring.tsx` passes `group1InHours = !group1.counts_in_total`; for the old FASI version (counts in total) the page keeps "Total geral", Group I subtotal and points (`ScoringSummary.test.tsx:148`, `ScoringTable.test.tsx:172`; mutation F6 killed).
- For an old IFCH-type version (Group I outside the total, informed value, rows not scored) the flag is true: the total is relabelled "Total geral (Grupos II a VIII)", Group I subtotal hidden, and a "Total de horas de PIT: 0,00 horas" block is shown. Numerically correct, slightly misleading wording (Gap 4).
- The scoring page lists only non-archived tables for choosing (`ProcessScoring.tsx:141`); archived ones are reachable only through a process that already chose them.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | PASS (engine change is one `is_pit_criterion` predicate + one row branch) |
| Surgical changes | PASS (80 files, all tied to a task; `.specs` changes limited to this feature plus the replacement notes of T23) |
| No scope creep | PASS (CSV `min_hours` and admin editing are in T11 "What") |
| Matches patterns | PASS (ruff clean; Decimal-only arithmetic; layers respected, architecture test green) |
| Spec-anchored outcome check | PASS except the PIT-03 wording (Gap 3) |
| Per-layer coverage (domain 1:1, routes happy+edge+error) | PASS, with Gap 2 on end-to-end min_hours |
| Every test maps to a requirement | PASS |
| Guidelines followed | AD-001 (architecture test green), AD-004 (real Postgres), tlc commit/test rules |

---

## Gaps (ranked)

1. **Medium, test strength (surviving mutants D12, D13).** Seed values are pinned by tests only through the group sums and about 15 named items. Two compensating errors that keep the sums intact (II.1 <-> II.2, or VIII.20 +1 / VIII.21 -1) pass every test. The current `ufpa.json` is correct for all 97 pointed items (verified against the xlsx), so this is a regression-protection gap, not a data error. Fix: a test that pins every item's `unit_points` (a checked-in expected table, cross-checked once against the xlsx) and the description of every item.
2. **Low, coverage (OFI-06/07 not end to end).** The minimum-hours rule is covered at unit level and the seed carries `min_hours`; no integration or API test sends a 19 h / 21 h / no-hours IV.4 activity through the seeded official table. Mutation E2 (rule never enforced) survives the integration suite and the golden case (killed only by the unit tests). Fix: one API test with IV.4 at 19 h (not scored, `CARGA_HORARIA_INSUFICIENTE`) and one without hours (scored, `CARGA_HORARIA_NAO_INFORMADA`).
3. **Low, spec drift (PIT-03).** The spec and the Assumptions row say Group I `points_override` is refused (422); the code refuses it only where Group I is in PIT hours (the `# SPEC_DEVIATION` comment at `app/application/use_cases/scoring.py:317`), so old FASI-type versions keep working (the simulation confirms the legacy points keep computing). Behavior is right and tested (`test_activity_group1_pit.py:161`) but `spec.md` still states the unconditional rule. Update PIT-03 and the Assumptions row.
4. **Low, UI wording.** An old IFCH-type version (Group I outside total, not in PIT hours) shows the "Total de horas de PIT: 0,00 horas" block. Cosmetic; optionally drive `group1InHours` from the presence of `CARGA_SEMANAL` criteria in Group I rather than `counts_in_total`.
5. **Low, fidelity.** Descriptions of VIII.7, VIII.8, VIII.13 and VIII.14 collapse the sheet's duplicated trailing "(N pontos)"; no test pins descriptions beyond three prefixes. `test_the_old_ifch_and_fasi_seeds_are_gone` checks table names, not file absence (files are absent: `ls` verified).
6. **Info, deployment.** The success criterion "on the VM `GET /api/scoring-tables` lists only the official table as active" holds only if no process on the VM chose an old version; otherwise that old table stays active and still associated to its unit (scenarios A and B), so the unit gets two tables. No VM access: not verified. Also: spec traceability still reads "Implemented" (ACE-02 "Pending"); it can move to Verified after the gaps are triaged.
7. **Process note.** T17 was committed after T18 (disclosed in the commit body, gate green). The Verifier did not write `.specs/LESSONS.md`/`lessons.json` because this run was restricted to writing only this file; the two grounded lessons are (a) pin per-item values, not only sums, for seed data; (b) a domain rule needs at least one end-to-end test through seeded data.

**Closed by T24 to T27** (author fixes, 2b6bc59, 985de8f, af1664e, 87dab27; Build gate after them: backend 2235 passed, frontend 88 passed, ruff, eslint and build clean):

- Gap 1 and Gap 5: closed by T24 (`2b6bc59`, `backend/tests/unit/test_seed_ufpa_items.py`, 203 cases). Per-item points, unit, mode, minimum hours and the start and end of every description are pinned against a table written from the xlsx. Mutants D12 (II.1 <-> II.2) and D13 (VIII.20 +1 / VIII.21 -1) now fail (2 cases each) while `test_seed_ufpa.py` alone still passes them; extra mutants (VIII.7 duplicated text restored, III.1 unit label, IV.5 minimum removed) are killed too. The mutations were applied locally and reverted.
- Gap 2: closed by T25 (`985de8f`, `backend/tests/integration/api/test_scoring_min_hours_api.py`, 4 tests): IV.4 at 19 h, 20 h, 21 h and without hours through the seeded table and the scoring endpoint. Dropping the IV.4 minimum from the seed fails 2 of them.
- Gap 3: closed by T26 (`af1664e`): PIT-02, PIT-03, the assumption row and the edge cases state the conditional rule; the `SPEC_DEVIATION` marker in `scoring.py` now cites PIT-03.
- Gap 4: closed by T27 (`87dab27`): `group1InHours` requires a `CARGA_SEMANAL` criterion in group I; new test in `ProcessScoring.test.tsx`.
- Gap 6 stays open until the deploy (needs VM data).

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| OFI-01 to OFI-12 | Implemented | Verified |
| PIT-01, PIT-02 | Implemented | Verified |
| PIT-03 | Implemented | Verified (spec text to be aligned, Gap 3) |
| MAP-01 to MAP-04 | Implemented | Verified |
| ACE-01 | Implemented | Verified |
| ACE-02 | Pending | Verified by evidence (process criterion; Gate, assertion diff, commit bodies) |
| TELA-01, TELA-02 | Implemented | Verified |

(Statuses in `spec.md` were not edited by the Verifier.)

---

## Summary

**Overall**: Ready, with the gaps above as follow-up (none blocks).

**Spec-anchored check**: 23/23 ACs with `file:line` evidence; 22 PASS, ACE-02 PARTIAL by definition; 1 spec-precision drift (PIT-03).
**Sensor**: 62/64 killed by the owning tests; 2 survivors (seed-data compensating errors).
**Gate**: backend 2028 passed, frontend 87 passed, ruff/eslint/build clean, 0 skipped.
**Deployed-state simulation**: archive, idempotency, migration up/down and process results verified on real Postgres with pre-change data.

**Next steps**: add the per-item value pin test (Gap 1) and the end-to-end min_hours API test (Gap 2); align `spec.md` PIT-03 (Gap 3); confirm on the VM whether any process chose an old table before expecting a single active table (Gap 6).
