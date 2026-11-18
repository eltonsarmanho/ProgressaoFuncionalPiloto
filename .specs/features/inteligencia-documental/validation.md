# Inteligência Documental Validation

**Date**: 2026-11-17
**Spec**: `.specs/features/inteligencia-documental/spec.md` (117 requirements: DOC, PIPE, EXT, CLS, VINC, REV, TELA, ACC, REAL-01..20, VER-01..13, SEG-01..12), `design.md`, `tasks.md` (T1-T95), `STATE.md` AD-010
**Diff range**: pass 3 `eaf39a3..08cef5a` (16 commits: `335ddac` specs, T82-T95 = 14 commits `dde97b6..6b21415`, `08cef5a` specs; 52 files, +2634/-402). Pass 2 `76022d5..eaf39a3`; whole feature `369f710..08cef5a`. Branch `feat/inteligencia-documental`, HEAD `08cef5a`.
**Verifier**: independent sub-agent (author != verifier), third pass, focused on Phase 13 (SEG-01..12). Isolated git worktrees under the scratchpad (HEAD, `eaf39a3`, `4c608aa^`, a mutation copy; all removed at the end). The user's tree was not touched except for this file (`git status --porcelain` identical to the baseline: only the pre-existing `?? requeriment.txt` and `?? test/`). `Documentos/` and `corpus-reports/` were not opened; every fixture is synthetic. No MariTalk call (key empty, `maritalk_live` deselected). No VM, no push, no commit, no code change. Containers started (two PostgreSQL 16, memory runs) and the image built for the memory check were removed.

## Validation: Inteligência Documental - PASS ✅ (with fix tasks, none blocking)

**Verdict: PASS.** 11 of 12 new requirements PASS, 1 PARTIAL on the letter of the spec (SEG-01: a term written "um ano e meio" is read as one year and flagged derived instead of being left unread), 0 FAIL. All 105 earlier requirements keep their pass-2 result (gate green, no test deleted, no assertion weakened). The memory claim of T94 was reproduced independently: a synthetic 25-page scanned A4 300 dpi PDF is OOM-killed at `docker run -m 384m` before T94 (exit 137) and runs to the end after it (cgroup `memory.peak` 220-244 MB, `ru_maxrss` 116-169 MB). The 211-point acceptance test is unchanged and green. Sensor: 94 new faults injected on T82-T95 behavior (backend 87, frontend 7), 69 killed, 25 survived (3 equivalent, 22 weak assertions or unpinned behavior); 10 re-runs of pass-2 mutants all killed. Two behavior defects found by synthetic probes (G1 term "e meio", G2 past tense "coordenou"), none blocking; they are fix tasks FT-19..FT-27 below, together with the unpinned persistence of the dates of an AI-created activity (PE01, PE02).

`validate_state.py` is run on this report after writing it.

---

## History

| Pass | Commit | Verdict | Summary |
| ---- | ------ | ------- | ------- |
| 1 | `76022d5` | FAIL | 70 of 72 requirements PASS, 2 PARTIAL (DOC-04, EXT-07). G1: a 520-byte PDF with a 3000x3000 pt page passed upload validation and OOM-killed the backend at 384 MB. G2 job retry unbounded, G3 masking leaks, G4-G11 lower. Sensor 119/129. |
| 2 | `eaf39a3` | PASS | REAL-01..20 and VER-01..13 re-verified, G1-G9 closed and reproduced. 103 of 105 PASS, 2 PARTIAL on wording (REAL-02 partial name, REAL-12 PAPIM wording). Sensor 119/143; fix tasks FT-8..FT-18. |
| 3 | `08cef5a` | PASS | SEG-01..12 (T82-T95): N1 term and open end, N3 duplicates, N5, N4, FT-8..FT-18 and the memory fix. FT-8, FT-9, FT-10 closed and reproduced (REAL-02 and REAL-12 now PASS). 11 of 12 PASS, SEG-01 PARTIAL. Sensor 69/94 new killed, 10/10 re-runs killed; 22 weak assertions and 2 behavior defects become FT-19..FT-27. |

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1-T81 | ✅ Done | Verified in passes 1 and 2; unchanged. |
| T82-T95 (phase 13) | ✅ Done (14/14) | Each task has exactly one commit and every commit includes the `tasks.md` update (`git show --stat`). All Done-when boxes are checked (0 open). All 16 commit subjects pass `check_commit.py`. `validate_spec.py`: 0 errors, 0 warnings. `validate_tasks.py`: 0 errors, 2 warnings (T11 and T95 `Tests: none`, both docs/ports). Notes: the T87 commit subject drops the task's tail (", not a unit name"); the title of T94 ("render and recognize one page at a time") does not describe the change, which is only the MuPDF store release in `render.py` (the one-page loop and `OMP_THREAD_LIMIT=1` already existed; the commit body says so; `extractor.py`, `tesseract.py` and the `gc` between pages named in the task's What were not changed); the round-3 note says "3 deselected (`maritalk_live`)", the run deselects 6 (as in pass 2). |

---

## Spec-Anchored Acceptance Criteria (SEG-01..SEG-12)

Paths: `T/` = `backend/tests/`, `S/` = `backend/app/`, `FE/` = `frontend/`. Evidence below was read in the test files and re-executed (full gate green at HEAD).

| ID | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------- | ----------------------- | ------ |
| SEG-01 | Start with day + grounded `term` + no end -> `end = start + term`, `DATA_FIM_DERIVADA`, stored as the period; term not in the page, not read with certainty (digit/word disagree, no unit) or month-only start -> no end | `T/unit/application/test_document_analyzer_term.py:53` - `suggested.extracted.end_date == date(2026, 8, 9)`, `quantity == Decimal(1)`, `(6, 6)`; `:61` - `alerts(result, DATA_FIM_DERIVADA) == [("end_date", 0)]`; `:80` ungrounded term -> `term is None`, `end_date is None`, `NAO_ENCONTRADO_NO_TEXTO == [("term", 0)]`; `:89` "por 3 (dois) anos" derives nothing; `:96` month-only start; `:105` a grounded end wins; `:117` payload without `term` -> `RESPOSTA_INVALIDA`; `T/unit/domain/test_term_rules.py:26,43,58` (11 readings, 8 refusals, 6 `add_months` incl. month-end clamp). Independent probe: all of those reproduced, plus "um ano e meio" -> 12 months (see G1). Persistence of the derived end in the created activity: not pinned (survivors PE01, PE02 below: no test reads `period_start`/`period_end` of an AI-created activity) | ⚠️ PARTIAL (G1) |
| SEG-02 | Yearly item, start only, no end/term: open period cut at the interstice end (`DENTRO`/`PARCIAL`/`FORA`), quantity = complete years inside, `QUANTIDADE_ESTIMADA` + `DATA_FIM_AUSENTE`, review; non-yearly item keeps one day | `T/unit/domain/test_open_ended_period.py:47,52` - `evaluate_period(..., open_ended=True) is DENTRO / PARCIAL / FORA`; `:102,110,117` engine; `T/unit/application/test_document_analyzer_open_end.py:51` - `quantity == Decimal(0)`, `DATA_FIM_AUSENTE`, `needs_review is True`; `:64` - `quantity == Decimal(2)`; `:74` `FORA_DO_INTERSTICIO`; `:88` non-yearly: `FORA_DO_INTERSTICIO`, no `DATA_FIM_AUSENTE`; `T/unit/domain/test_quantity_rules.py:196-217` (warning tuples). Probe at HEAD (table `ufpa.json`, interstice 2024-11-23..2026-11-23): start 2024-08-09 no term -> VI.6 qty 2, review; start 2026-08-09 -> qty 0, review; term "por 2 (dois) anos" -> end 2026-08-09, qty 1 | ✅ PASS |
| SEG-03 | Portuguese labels for `DATA_FIM_DERIVADA` and `DATA_FIM_AUSENTE` | `FE/src/components/DocumentViewer.test.tsx:107` - `getByText(/Data final calculada do prazo da portaria: confira/)`, `getByText(/Sem data final na portaria: quantidade estimada até o fim do interstício/)`, `not.toHaveTextContent("DATA_FIM_DERIVADA")`; `FE/src/labels.ts:127-128`; sensors F01-F04 killed | ✅ PASS |
| SEG-04 | Same item, equal/overlapping dates, Jaccard >= 0.8 of normalized word sets -> later one `DUPLICIDADE` unless justified; other item, dates or titles stay apart | `T/unit/domain/test_scoring_duplicates_similar.py:28` `== {newer.id}`; `:38` exactly 0.8 is a duplicate; `:45` 15/19 = 0.789 is not; `:52` other item; `:57` disjoint dates; `:63` undated; `:68` justification; `:74` rejected; `S/domain/rules/scoring_duplicates.py:20,49`; sensors D01-D03, D08, D11 killed. Probe: two bancas of the same item and day whose titles differ by one word (student name) have Jaccard 0.82-0.87 and are duplicates (G3) | ✅ PASS (spec-conformant; G3 is a risk of the 0.8 rule) |
| SEG-05 | Same item, other documents with the same normalized page text -> later one `DUPLICIDADE`; never two activities of one document | `T/integration/scoring/test_process_score_content_duplicates.py:23` - `row(result, second).reasons == (NotScoredReason.DUPLICIDADE,)` (PostgreSQL, bytes differ, text equal); `:42` different text; `:59` same document; `T/unit/domain/test_scoring_duplicates_content.py:26,34,43,52,63,73`; `T/integration/documents/test_repositories.py:572` - `keys == {act1.id: {(doc1.id, content_hash(["pagina um", "pagina dois"]))}}`; sensors D05-D07, D09, R01-R03, S01, S02, E02 killed | ✅ PASS |
| SEG-06 | Course counts as extension (VII.9) only with "extensão" in a nature context; unit names (Pró-Reitoria, Diretoria, ..., PROEX) ignored; otherwise VII.10 | `T/unit/domain/test_extension_course_context.py:24` 8 texts -> `CURSO_CONCLUIDO`; `:44` 11 texts keep `CURSO_EXTENSAO_CONCLUIDO`; `:48` header unit plus body "curso de extensão"; `:61` VII.10 vs VII.9; `T/unit/application/test_document_analyzer_extension_unit.py:31` - `(found.group_number, found.item_number) == (7, 10)`, `:37` `(7, 9)`. The unit-stripping clause itself is not discriminated (survivors U01, U02, FT-21); probe: "Pró-Reitoria de Extensão Universitária ... curso de formação" -> VII.10 at HEAD, "Coordenadoria de Ações de Extensão" still confirms (G5) | ✅ PASS (clause unpinned) |
| SEG-07 | V.1/V.2 need coordination/coordinator/leader in the text with the professor's name near it; otherwise no item | `T/unit/domain/test_research_coordination_role.py:13` - `downgraded is T.OUTRA`, `suggest_item(downgraded).principal is None`; `:33` 4 texts keep the item; `:52` another coordinator / member only / role without the professor / professor without role -> `OUTRA`; `T/unit/application/test_document_analyzer_research_role.py:28` - `result.activities == ()`, alerts `== [SEM_ITEM_DE_PONTUACAO]`; `:39` `(5, 1)`; sensors A11, U08-U14 killed. Probe: "coordenou", "lidera", "liderou" are not read as a role (G2); the spec says "a poucas palavras do termo", the code uses the same sentence | ✅ PASS on the letter (G2 spec-precision and false-negative) |
| SEG-08 | Partial name (2+ names, no abbreviation) is the professor only with the full name or the SIAPE in the text; otherwise `DOCENTE_DIVERGENTE` | `T/unit/domain/test_partial_professor_name.py:12` - `same_person("Maria Souza", ..., text) is False` for 3 partial names; `:17` empty text; `:21` SIAPE in text; `:26` full name in text; `:31` complete name; `T/unit/domain/test_grounding.py:205`; sensors G02-G04 killed. Probe through the analyzer: partial name without support -> `REQUER_REVISAO`/`DOCENTE_DIVERGENTE`; with the full name or the SIAPE -> `PROCESSADO` | ✅ PASS (closes FT-9, REAL-02) |
| SEG-09 | "PAPIM"/"intervenção metodológica" without "extensão" confirm only IV.1 | `T/unit/domain/test_papim_wording.py:26` - `"PAPIM" in DESCRIPTION[1]`, `"PAPIM" not in DESCRIPTION[2]` (read from `ufpa.json`); `:33` coordination kept; `:40` participation -> `T.OUTRA`; `:44`; sensor U06 killed. Probe: PAPIM coordination -> (4, 1); PAPIM participation -> `SEM_ITEM_DE_PONTUACAO` | ✅ PASS (closes FT-10, REAL-12) |
| SEG-10 | Bundle scan test fails, not skips, with `REQUIRE_DIST` and no `dist`; Build gate builds first | `FE/tests/bundle.test.ts:30-31` - `skipIf(!REQUIRE_DIST && !existsSync(DIST))`, `expect(existsSync(DIST), "...").toBe(true)`; `tasks.md` Build gate line `npm run build && REQUIRE_DIST=1 npm test -- --run`. Reproduced by hand: no `dist` + `REQUIRE_DIST=1` -> 1 failed with the message; no `dist`, no variable -> 1 skipped; gate order -> 168 passed, 0 skipped. No automated test pins this behavior (a test of the test cannot run in the same gate); `REQUIRE_DIST=0` also counts as set (`Boolean("0")`) | ✅ PASS (closes FT-8) |
| SEG-11 | Tests pin the FT-11..FT-18 behaviors | `T/unit/domain/test_second_verification_gaps.py:26,30` (D04), `:35` (R03), `:42,48` (I05), `:63,67` (K08), `:72` (R09); `T/integration/scoring/test_bulk_validate_version.py:29` (B04); `T/unit/application/test_document_analyzer_gaps.py:27,36` (X02), `:44` (X03), `:74,82` (X05), `:91` (X07), `:107` (X08); `T/unit/infrastructure/test_image_coverage_off_page.py:32` (I02); `T/integration/api/test_documents_inspector_wiring.py:21` (W03); `FE/src/components/DocumentViewer.test.tsx:127` (F08, F09). 13 re-applied pass-2 mutants and 7 frontend label mutants: 10 of 10 backend and 7 of 7 frontend killed | ✅ PASS |
| SEG-12 | One page at a time, one Tesseract thread, peak memory not growing with pages; measured peak in `docs/deploy/vm.md` | `T/unit/infrastructure/test_ocr_memory.py:47,56` - `rss_mb() - start < MAX_GROWTH_MB` (40); measured here: growth 0.0 MB at HEAD, 124.5 MB at `4c608aa^`, 141.1 MB at `eaf39a3` (10 scanned pages); `T/unit/infrastructure/test_tesseract.py:96` (`OMP_THREAD_LIMIT`); sensors O01, O02, O06 killed. Container check below | ✅ PASS |

**Status**: ⚠️ 11 PASS, 1 PARTIAL (SEG-01, G1), spec-precision gaps flagged (SEG-02 manual activities, SEG-04 rule, SEG-06, SEG-07, SEG-10, SEG-12 `gc`/title).

---

## Independent reproduction (synthetic inputs, HEAD `08cef5a`)

### N1: Diretor portaria "por 2 (dois) anos, a partir de 09/08/2024"

Official table seed `ufpa.json` (VI.6 "por ano de exercício", 30 points, `POR_UNIDADE`), interstice 2024-11-23..2026-11-23, analyzer with a fake AI and the real rules:

| Case | Start | End | Qty | Alerts | Review |
| ---- | ----- | --- | --- | ------ | ------ |
| "por 2 (dois) anos" in the page and in `term` | 2024-08-09 | 2026-08-09 (derived) | 1 | `DATA_FIM_DERIVADA`, `QUANTIDADE_ESTIMADA` | no |
| "24 meses" | 2024-08-09 | 2026-08-09 | 1 | same | no |
| no term ("a partir de" only) | 2024-08-09 | none | 2 (upper bound) | `QUANTIDADE_ESTIMADA`, `DATA_FIM_AUSENTE` | yes |
| "por 3 (dois) anos" (digit and word disagree) | 2024-08-09 | none | 2 | `QUANTIDADE_ESTIMADA`, `DATA_FIM_AUSENTE` | yes |
| `term` "por 4 (quatro) anos" not in the page | 2024-08-09 | none, term nulled | 2 | `NAO_ENCONTRADO_NO_TEXTO` (`term`), `DATA_FIM_AUSENTE` | yes |
| term and month-only start ("agosto de 2024") | 2024-08-01 | none | 2 | `DATA_PARCIAL`, `DATA_FIM_AUSENTE` | yes |
| "por 2 (dois) anos, prorrogável por mais 2 (dois) anos" | 2024-08-09 | none (two amounts refused) | 2 | `DATA_FIM_AUSENTE` | yes |
| start 2026-08-09, no term | 2026-08-09 | none | 0 | `DATA_FIM_AUSENTE` | yes |
| start 2026-08-09, "por 2 (dois) anos" | 2026-08-09 | 2028-08-09 | 0 | `DATA_FIM_DERIVADA` | no |
| start 2024-11-24, "por 2 (dois) anos" | 2024-11-24 | 2026-11-24 | 1 (floor, N2) | `DATA_FIM_DERIVADA` | no |
| end 2026-08-08 in the page plus a term | 2024-08-09 | 2026-08-08 (the page wins) | 1 | none derived | no |
| **"por um ano e meio"** | 2024-08-09 | **2025-08-09** (should be 2026-02-09 or unread) | **0** | `DATA_FIM_DERIVADA` | no (G1) |
| "por 02 (dois) anos" | 2024-08-09 | none (refused: "2" != "02") | 2 | `DATA_FIM_AUSENTE` | yes |
| `term` that is not a string (2, list, dict, 2.5, true) | - | - | no activity | `RESPOSTA_INVALIDA` | - |

`parse_term_months`: "por dois anos e meio" -> 24, "um ano e meio" -> 12 ("e meio" is ignored), "por 2 (dois) anos e 6 (seis) meses" -> 30, "por 90 dias" -> None, "por 1 (um) ano" -> 12, "pelo período de doze meses" -> 12.

### Behavior change: hand-entered activity with only a start date in a "por ano" item (SEG-02, scoring engine)

`calculate()` on the official table, interstice 2024-11-23..2026-11-23, `eaf39a3` versus HEAD:

| Activity (user-entered quantity) | `eaf39a3` | HEAD |
| -------- | --------- | ---- |
| VI.6, start 2020-01-01, qty 3 | `NAO_PONTUADA`, `FORA_DO_INTERSTICIO`, 0 | `POTENCIAL`, 90 points, `INTERSTICIO_PARCIAL` |
| V.3, start 2019-01-01, qty 7 | `NAO_PONTUADA`, 0 | `POTENCIAL`, 70 points, `INTERSTICIO_PARCIAL` |
| VI.6, start 2025-03-01, qty 1 | 30 | 30 |
| VI.6, start 2027-03-01 | `FORA_DO_INTERSTICIO` | `FORA_DO_INTERSTICIO` |
| VII.10 (not yearly), start 2020-01-01 | `FORA_DO_INTERSTICIO` | `FORA_DO_INTERSTICIO` |
| VI.6, closed period 2024-08..2025-01, qty 1 | 30, `INTERSTICIO_PARCIAL` | same |

The engine applies the open end to every activity of a "por ano" item (`scoring_engine.py:163`), manual ones included. A hand-entered long-running function that used to be left out as outside the interstice is now scored with the quantity the user typed, which is not capped to the years inside the interstice (a closed period behaves the same since `PARCIAL` was introduced, so this is consistent, but it is a change that neither `spec.md` SEG-02 nor AD-010 states for manual activities; it is disclosed only in the tasks' scope notes). Duplicate detection and the manual verification are unchanged (`activity_interval(a)` without `open_end`). The acceptance test `T/integration/api/test_scoring_golden.py` (total 211, minimum `ATINGE`; `:115`, `:134`, `:181`) is unchanged since `eaf39a3` and its 6 tests pass; it holds no start-only yearly activity, so it neither proves nor disproves the change.

### Memory (T94, SEG-12): container evidence

Backend image built from the HEAD worktree `backend/Dockerfile`; `docker run -m 384m --memory-swap 384m` with a synthetic image-only PDF (A4, 2480x3508 px grayscale noise plus text, 300 dpi, one PNG per page, 8.7 MB per page; generated in an unlimited container first, so the generation is not in the peak). `DocumentTextExtractor` with the real Tesseract (`por`). Peak is the cgroup v2 `memory.peak` (it counts the reclaimable page cache of the 87-217 MB test file) and `ru_maxrss`.

| Code | Pages | Result | `memory.peak` | `ru_maxrss` | Exit |
| ---- | ----- | ------ | ------------- | ----------- | ---- |
| HEAD (`08cef5a`) | 10 | 10 pages `OCR`, 27003 chars | 166 MB | 116 MB | 0 |
| `4c608aa^` (before T94) | 10 | same text | 302 MB | 265 MB | 0 |
| HEAD | 25 | 25 pages `OCR`, 67953 chars | 244 MB | 116 MB | 0, not OOM-killed |
| `4c608aa^` | 25 | - | - | - | **137, `OOMKilled=true`** |
| HEAD, with `import app.main` first | 25 | 67953 chars | 220 MB | 169 MB | 0 |

The numbers in `docs/deploy/vm.md` (10 pages 342 -> 191 MB with the app, 25 pages OOM before, 139 MB extraction alone) are of the same order as these; the figures here differ because of the larger synthetic pages and the page cache. The recommendation (no change of `mem_limit` below 320 MB, 512 MB if real traffic kills the container) follows from the measurements. Not measured: concurrent requests, database connections, 100 pages (a 100-page file of this size would be 870 MB).

### Other probes

| Topic | Probe | Result |
| ----- | ----- | ------ |
| N5 extension course | 9 texts through `confirm_extension_course` | "Pró-Reitoria de Extensão Universitária", "Pró-Reitoria de Pesquisa e Extensão", "PROEX/UFPA", "ação extensionista", "(Extensão)" in parentheses and a bare "Extensão" line -> VII.10; "Modalidade: Curso de Extensão" and a header plus "Programa de Extensão" -> VII.9; **"Coordenadoria de Ações de Extensão certifica a oficina" -> VII.9** (G5) |
| N5 extension project | unit name only | "Pró-Reitoria de Extensão certifica a participação no projeto" still confirms IV.2 (author-declared residual, `test_suggestion_rules.py` pins it) |
| N4 research role | 10 verbs | "coordena", "coordenando", "coordenadora", "coordenação", "foi coordenadora", "lider" keep V.1; **"coordenou", "lidera", "liderou" -> no item**; "Fulana. Coordenadora. Projeto de pesquisa" (name and role in two sentences) -> no item (G2) |
| FT-9 partial name | analyzer, professor "Maria Aparecida de Souza", AI name "Maria Souza" | no support -> `DOCENTE_DIVERGENTE`; full name in text -> accepted; SIAPE in text -> accepted |
| FT-10 PAPIM | analyzer | coordination -> IV.1; participation -> `SEM_ITEM_DE_PONTUACAO` |
| Content hash | `content_hash([""])` for two documents | equal; documents whose pages are all empty (OCR failed) count as the same text (FT-26) |

---

## Changed existing tests (diff `eaf39a3..HEAD`)

No test definition was deleted. Existing tests edited, each justified by a requirement and none weaker:

| Change | Justification |
| ------ | ------------- |
| `test_quantity_rules.py` (parametrized with the expected warning tuple; start-only now also carries `DATA_FIM_AUSENTE`) | SEG-02; the assertion is stricter than before |
| `test_grounding.py:205` (`same_person("Ana Lima", ...)`: True without text -> True only with the full name in the text, False without) | SEG-08; stricter (adds two False assertions) |
| `test_suggestion_rules.py` (the PAPIM text removed from the list that confirms both extension items) | SEG-09; the new `test_papim_wording.py` pins it for IV.1 and refuses it for IV.2 |
| `test_document_analyzer_classification.py:310` (`"de EXTENSAO"` -> `"(curso de EXTENSAO)"`) | SEG-06; a bare "de EXTENSAO" no longer confirms (narrowing of acceptance, covered by `test_extension_course_context.py`) |
| `test_document.py` (alert codes 15 -> 17), `test_extraction.py`, `test_ai_schemas.py`, `analyzer_fakes.py` (`term`) | SEG-01 |

Test definitions: backend 1487 -> 1579 (+92), executed 2869 -> 3153 (+284); frontend executed 166 -> 168 (+2).

---

## Discrimination Sensor (pass 3)

Mutations applied to a copy of the HEAD worktree (`PYTHONDONTWRITEBYTECODE=1`), restored from the original text after each run, `pytest -x` over `tests/unit tests/architecture` (about 12 s) plus the integration directories for the repository and scoring mutants (PostgreSQL 16 container); frontend with `vitest` on `DocumentViewer.test.tsx`. One mutant at a time; `git status --porcelain` of the user's tree was identical to the baseline before and after.

| ID | File | Description | Result |
| -- | ---- | ----------- | ------ |
| N01 | `term_rules.py:29` | digit/word disagreement no longer refused | ✅ killed (`test_document_analyzer_term.py:89`) |
| N02 | `term_rules.py:33` | two year amounts ("2 anos ... mais 2 anos") no longer refused | ❌ survived (FT-19) |
| N03 | `term_rules.py:37` | two month amounts no longer refused | ❌ survived (FT-19) |
| N04 | `term_rules.py:42` | `months >= 12` -> `> 12` | ❌ survived (boundary, FT-19) |
| N05 | `term_rules.py:45` | `0 < total` -> `0 <= total` | ✅ killed |
| N06 | `term_rules.py:45` | exactly ten years refused (`<=` -> `<`) | ❌ survived (boundary, FT-19) |
| N07 | `term_rules.py:15` | ten-year cap lifted | ✅ killed |
| N08 | `term_rules.py:53` | no month-end clamp | ✅ killed (`:58`) |
| N09 | `term_rules.py:16` | digit lookbehind removed | ❌ survived (no test input needs the lookbehind; judged low, not shown to change a realistic result) |
| N10 | `term_rules.py:16` | singular unit "mes" dropped | ❌ survived (FT-19) |
| N11 | `term_rules.py:32` | years and months swapped | ✅ killed |
| N12 | `term_rules.py:44` | years not multiplied by 12 | ✅ killed |
| N13 | `term_rules.py:40` | empty-amount guard removed | ❌ survived, equivalent (the `0 < total` guard returns None) |
| N14 | `term_rules.py:26` | words never read as numbers | ✅ killed |
| N15 | `term_rules.py:51` | month index off by one | ✅ killed |
| N16 | `term_rules.py:16` | regex tail changed, behavior preserved (control) | survived, as expected |
| A01 | `document_analyzer.py:360` | term overrides a grounded end | ✅ killed (`:105`) |
| A02 | `document_analyzer.py:362` | month-only start derives an end | ✅ killed (`:96`) |
| A03 | `document_analyzer.py:288` | `DATA_FIM_DERIVADA` not emitted | ✅ killed (`:61`) |
| A04 | `document_analyzer.py:287` | derived end not applied | ✅ killed (`:53`) |
| A05 | `document_analyzer.py:471` | table unit of the item ignored (taxonomy list only) | ❌ survived (FT-20) |
| A14 | `document_analyzer.py:308` | analyzer passes no item/table to `_is_yearly` | ❌ survived (FT-20) |
| A06 | `document_analyzer.py:314` | non-yearly start-only also goes to review | ❌ survived (FT-20) |
| A07 | `document_analyzer.py:322` | open ended not sent to review | ✅ killed (`test_document_analyzer_open_end.py:51`) |
| A08 | `document_analyzer.py:539` | `term` type not validated | ❌ survived (FT-20; the refusal works at HEAD, probe above) |
| A09 | `document_analyzer.py:79` | `term` key not required | ✅ killed |
| A10 | `document_analyzer.py:309` | analyzer period check without the open end | ✅ killed (`:64`) |
| A11 | `document_analyzer.py:295` | research coordination check removed | ✅ killed (`test_document_analyzer_research_role.py:28`) |
| A12 | `document_analyzer.py:293` | extension course check removed | ✅ killed |
| A13 | `document_analyzer.py:285` | term never used | ✅ killed |
| G01 | `grounding.py:268` | `term` not grounded | ✅ killed (`:80`) |
| G02 | `grounding.py:225` | partial name accepted without text support | ✅ killed (`test_grounding.py:205`) |
| G03 | `grounding.py:200` | abbreviation path accepts a name in full | ✅ killed (`test_partial_professor_name.py:12`) |
| G04 | `grounding.py:223` | single-token partial name accepted | ✅ killed |
| Q01 | `quantity_rules.py:81` | no open end in the year count | ✅ killed (`:64`) |
| Q02 | `quantity_rules.py:63` | an event date no longer excludes the open end | ❌ survived (FT-20) |
| Q03 | `quantity_rules.py:115` | `DATA_FIM_AUSENTE` dropped | ✅ killed |
| Q04 | `quantity_rules.py:61` | `is_open_ended` flipped on the start | ✅ killed |
| P01 | `scoring_periods.py:29` | every "por ..." unit is yearly | ✅ killed (`test_open_ended_period.py:110`) |
| P02 | `scoring_periods.py:48` | start after the end gives an inverted interval | ✅ killed (`:42`) |
| P03 | `scoring_periods.py:40` | a dated event with a start becomes open | ✅ killed (`:33`) |
| P04 | `scoring_periods.py:47` | month-precision open start not floored to day 1 | ❌ survived: `test_open_ended_month_precision_...` (`:64`) uses a start that is already the 1st (FT-20) |
| P05 | `scoring_periods.py:67` | `evaluate_period` ignores `open_ended` | ✅ killed |
| P06 | `scoring_periods.py:44` | open-end condition flipped | ✅ killed |
| E01 | `scoring_engine.py:163` | engine never opens a yearly period | ✅ killed (`:102`) |
| E02 | `scoring_engine.py:318` | content keys dropped in `calculate` | ✅ killed by the PostgreSQL test (`test_process_score_content_duplicates.py:23`); survives the unit tests alone |
| D01 | `scoring_duplicates.py:20` | threshold 0.8 -> 0.9 | ✅ killed (`:38`) |
| D02 | `scoring_duplicates.py:20` | threshold 0.8 -> 0.7 | ✅ killed (`:45`) |
| D03 | `scoring_duplicates.py:51` | `>=` -> `>` | ✅ killed (`:38`) |
| D04 | `scoring_duplicates.py:56` | two unclassified activities count as the same item | ❌ survived (FT-22) |
| D05 | `scoring_duplicates.py:35` | duplicates inside the same document | ✅ killed |
| D06 | `scoring_duplicates.py:35` | different text duplicates | ✅ killed |
| D07 | `scoring_duplicates.py:28` | hash without normalization | ✅ killed (`:26`) |
| D08 | `scoring_duplicates.py:86` | similar titles of another item duplicate | ✅ killed (`:52`) |
| D09 | `scoring_duplicates.py:89` | same content in another item duplicates | ✅ killed (`:63`) |
| D10 | `scoring_duplicates.py:28` | page boundary lost in the hash | ❌ survived (FT-26, "ab"+"c" vs "a"+"bc") |
| D11 | `scoring_duplicates.py:80` | overlap test half dropped | ✅ killed |
| R01 | `repositories.py:1227` | pages hashed without page order | ✅ killed (`test_repositories.py:572`) |
| R02 | `repositories.py:1233` | document without text not skipped | ✅ killed |
| R03 | `repositories.py:1230` | only the first page hashed | ✅ killed |
| S01 | `scoring.py:669` | `calculate` without the content keys | ✅ killed (`:23`) |
| S02 | `scoring.py:655` | content keys never loaded | ✅ killed |
| U01 | `suggestion_rules.py:150` | unit names never stripped | ❌ survived (FT-21) |
| U02 | `suggestion_rules.py:130` | PROEX no longer a unit | ❌ survived (FT-21) |
| U03 | `suggestion_rules.py:135` | "extensão universitária" no longer a nature | ✅ killed |
| U04 | `suggestion_rules.py:136` | category/nature field no longer a nature | ✅ killed |
| U05 | `suggestion_rules.py:151` | extension course verdict flipped | ✅ killed |
| U06 | `suggestion_rules.py:183` | PAPIM accepted for IV.2 too | ✅ killed (`test_papim_wording.py:40`) |
| U07 | `suggestion_rules.py:205` | research wording no longer required | ❌ survived (FT-23) |
| U08 | `suggestion_rules.py:208` | "coordenado por" counts as the coordinator | ✅ killed (`test_research_coordination_role.py:52`) |
| U09 | `suggestion_rules.py:209` | professor not required in the sentence | ✅ killed |
| U10 | `suggestion_rules.py:209` | coordination word not required | ✅ killed |
| U11 | `suggestion_rules.py:207` | whole text as one sentence | ✅ killed |
| U12 | `suggestion_rules.py:190` | "lider" no longer a coordination word | ✅ killed (`:33`) |
| U13 | `suggestion_rules.py:207` | "Prof." abbreviation splits the sentence | ✅ killed |
| U14 | `suggestion_rules.py:203` | every type is checked | ✅ killed |
| O01 | `render.py:53` | MuPDF store never shrunk | ✅ killed (`test_ocr_memory.py:47`) |
| O02 | `render.py:53` | store shrunk to 50 percent only | ✅ killed |
| O06 | `render.py:53` | store shrink disabled (second form) | ✅ killed |
| O03 | `render.py:49` | intermediate image not closed | ❌ survived, equivalent (freed on return) |
| O04 | `render.py:45` | pixmap not released | ❌ survived, equivalent (freed on return) |
| O05 | `render.py:51` | behavior-preserving control | survived, as expected |
| M01 | `schemas.py:39` | `term` field renamed in the strict schema | ✅ killed |
| M02 | `maritalk.py:35` | prompt instruction on `term` removed | ❌ survived (prompt text unpinned, FT-24) |
| M03 | `maritalk.py:35` | "never compute the end date" removed | ❌ survived (FT-24) |
| C01 | `maritalk.py:35` | prompt says to compute the end date | ❌ survived (FT-24) |
| PE01 | `document_processing.py:107` | derived end not stored in the created activity (`period_end=None`); run over `tests/unit` plus the `doc_usecases`, `documents` and `api` integration directories | ❌ survived (FT-20) |
| PE02 | `document_processing.py:106` | start not stored in the created activity (`period_start=None`), same test set | ❌ survived (FT-20; pre-existing hole, no test reads the period of an AI-created activity) |
| OM01 | `tesseract.py:67` | Tesseract thread limit removed | ✅ killed (`test_tesseract.py::test_command_uses_portuguese_psm_3_tsv_nice_and_one_thread`) |
| F01-F04 | `frontend/src/labels.ts:127-128` | `DATA_FIM_DERIVADA` and `DATA_FIM_AUSENTE`, label removed or text shortened | ✅ 4 killed (`DocumentViewer.test.tsx:107`) |
| F05-F07 | `frontend/src/labels.ts` | `DATA_PARCIAL` and `CLAUSULA_DE_DISPENSA` label removed, text changed | ✅ 3 killed (`:127`) |
| Re-runs of pass-2 mutants | | D04 order (`document_type.py`), R03 initials, B04 bulk, I05 short words, I02 image clip, X03 level, X02 title-less, X05 half-open, K08 CPF follower, W03 `MAX_MEGAPIXELS` | ✅ 10 of 10 killed |

**Sensor depth**: expanded (SEG-01/02/04/05 are data-integrity and scoring paths: 94 new manual faults, 10 re-runs). **Result**: 94 new faults, 69 killed, 25 survived (3 equivalent: N13, O03, O04; 22 weak assertions or unpinned behavior); 2 controls (N16, O05) survived as expected; 10 of 10 re-runs killed. not clean on a strict reading: the survivors become the fix tasks below; none changes a spec outcome on a realistic input except through G1 and G2. Survivors are triaged in the Fix Plans (equivalent: N13, O03, O04; controls: N16, O05; the rest are weak assertions).

---

## Gate Check

- **Gate command**: Build gate from `tasks.md`, in an isolated worktree at `08cef5a`: `cd backend && ruff check . && pytest -q` with `TEST_DATABASE_URL` on a throwaway PostgreSQL 16 and `MARITALK_API_KEY` empty; then `cd frontend && npm run lint && npm run build && REQUIRE_DIST=1 npm test -- --run`; then `scripts/check_bundle_no_secrets.sh frontend/dist`.
- **Result**: backend `ruff` clean; `pytest`: **3153 passed, 6 deselected** (`maritalk_live`), 0 failed, 0 skipped, 263.5 s. Frontend `eslint` clean; `vite build` OK; `vitest` **23 files, 168 passed, 0 skipped** (with `REQUIRE_DIST=1`); bundle scan exit 0 (`bundle is clean`).
- **Test count before the phase** (`eaf39a3`): backend 1487 definitions / 2869 executed, frontend 166 executed. **After** (HEAD): backend 1579 / 3153, frontend 168.
- **Skipped tests**: none in the Build gate (the 6 `maritalk_live` tests are deselected by design, ACC-04).
- **Failures**: none.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | OK |
| Surgical changes | OK: 52 files, all inside the tasks' `Where`; `T94` touches `render.py` only (the task's other files were not needed) |
| No scope creep | OK; one wider rule flagged: the table-unit test `startswith("por ano")` also covers "por ano de obtenção" (V.4) and "por ano" items (PET, VI.8, VI.14) |
| Matches patterns (ports, use cases, unit of work) | OK: `content_keys_for_activities` is a port method with a SQL adapter; the rules stay pure |
| Spec-anchored outcome check | OK, with the precision gaps listed |
| Per-layer Coverage Expectation | OK; the analyzer-level table-unit path and the persistence of the dates of an AI-created activity are the exceptions (FT-20, PE01, PE02) |
| Every test maps to a requirement | OK |
| Documented guidelines followed | none - strong defaults applied |

---

## Edge Cases

- [x] Term and start both certain: end derived and flagged (`test_document_analyzer_term.py:53`)
- [x] Term uncertain, ungrounded or start month-only: no end invented (`:80,:89,:96`)
- [x] Start-only yearly item before, inside and after the interstice (`test_open_ended_period.py:47,52`)
- [x] Same text in two files of one process: duplicate; one file with two activities: not (`test_process_score_content_duplicates.py:23,59`)
- [x] 25-page scanned PDF under 384 MB: reproduced, not OOM-killed
- [ ] Term written "e meio": derived wrongly (G1)
- [ ] "coordenou"/"liderou": coordination not recognized (G2)

---

## Fix Plans (ranked gaps; none blocking)

1. **FT-19 (Medium, SEG-01, AD-010)**: `parse_term_months` ignores "e meio", so "um ano e meio" gives 12 months and "dois anos e meio" gives 24, flagged `DATA_FIM_DERIVADA` as if certain; AD-010 says a term written otherwise "cai no período aberto". Reproduced: derived end 2025-08-09 and quantity 0 instead of an unread term (open period, quantity 2, review). Fix: refuse a term followed by "e meio"/"meia"/fractions, or read it as +6 months; test both. Add the unpinned refusals found by N02, N03, N04, N06, N10: "por 2 (dois) anos, prorrogável por mais 2 (dois) anos" -> None (the common real wording), "1 ano e 12 meses", exactly 10 years, "1 mês". Where: `S/domain/rules/term_rules.py:19-45`, `T/unit/domain/test_term_rules.py`.
2. **FT-20 (Medium, SEG-01, SEG-02)**: analyzer-level tests never pass a `table_version`, so the table-unit path (`_is_yearly`, the user's "unit of the table item") is untested (A05, A14); also the review flag for non-yearly start-only (A06), a non-string `term` (A08), an event date with a start (Q02) and a month-precision start that is not the 1st (P04) are unpinned; and, most important, no test asserts that the dates of an AI-created activity reach `period_start`/`period_end` (PE01, PE02 survive: `document_processing.py:106-107` can drop both and the whole suite stays green), which leaves the headline of SEG-01 ("gravar a data derivada como período") and the T82 Done-when "gravado na atividade criada" unpinned. Add one analyzer case with the official table for VI.6 and one for a "por ação" item, and a `process_document` assertion `period_end == 2026-08-09`.
3. **FT-21 (Medium-Low, SEG-06)**: the unit-name stripping, the clause SEG-06 names, is not discriminated (U01, U02): every unit test passes without it. Add "Pró-Reitoria de Extensão Universitária ... curso de formação" -> VII.10 (HEAD gives VII.10) and "PROEX - curso de extensão" -> VII.9. Decide on "Coordenadoria de Ações de Extensão" (`_EXTENSION_UNIT` does not cover "ações de"; it confirms VII.9) and on the IV.1/IV.2 project check, which still accepts a unit name (author-declared).
4. **FT-22 (Medium-Low, SEG-02 scope)**: state in `spec.md` SEG-02 and AD-010 that the open end also applies to hand-entered activities of a "por ano" item, and decide whether the entered quantity should be capped at the years inside the interstice (today VI.6 from 2020 with quantity 3 is 90 points, was 0). Also D04: two unclassified activities (no group/item) must not be "the same item" (`scoring_duplicates.py:56`), add the test.
5. **FT-23 (Medium, SEG-07)**: `_COORDINATOR` (`suggestion_rules.py:190`) matches "coordena*", "lider", "lideranca" but not "coordenou", "lidera", "liderou"; a declaration "Fulana coordenou o projeto de pesquisa X" falls to `OUTRA` and loses V.1 (15 points per year). Name and role in two sentences ("Fulana. Coordenadora.") also fail. Fix the verb forms (`coordenou`, `coordenad*`, `lider*`) and decide the sentence rule versus the spec's "a poucas palavras do termo"; add the tests. U07: pin that a coordination text without "pesquisa/projeto/grupo" is refused.
6. **FT-24 (Low, SEG-01)**: prompt wording about `term` is unpinned (M02, M03, C01: even "calcule a data final" passes); add a test that the system prompt names `term` and forbids computing the end date.
7. **FT-25 (Low, SEG-04)**: a title that differs from another by one word (a student name) in the same item and on the same day has Jaccard 0.82-0.87 and the later one is `DUPLICIDADE` until justified. Spec-conformant; decide whether `distinct_justification` is enough or raise the limit for short or name-bearing titles.
8. **FT-26 (Info, SEG-05)**: `content_hash` of an all-empty text is equal across documents (two unreadable files with the same page count look identical); D10 (page boundary) unpinned. Skip empty hashes and join pages with a separator that cannot appear.
9. **FT-27 (Info)**: `REQUIRE_DIST=0` counts as set (`Boolean("0")`, `bundle.test.ts:16`); SEG-10 is verified only by hand (a test of the test is not possible in the same gate); T94 commit title and the "3 deselected" note are inexact; the pass-2 info items (PIPE-02/ACC-02 wording, `--fake-ai`, lock test, server nginx outside the repo, G-A end date inclusive, a `REJEITADA` activity in a bulk) remain open.

Lessons to distill (not written: the instructions limit this pass to this file, so `.specs/lessons.json` was not touched): (a) "a rule that reads a closed vocabulary of verb forms needs a test for each tense in the real wording ('coordena' is not 'coordenou')"; (b) "a parser that drops a trailing quantifier ('e meio') reads the wrong number instead of failing: pin the refusal of every unread suffix"; (c) "an analyzer or service whose helper takes an optional table or catalog needs at least one test that passes it, or the real path is dead to the suite"; (d) "a negative test for a stripped phrase must contain a phrase that only the stripping prevents from matching".

---

## Requirement Traceability Update

SEG-01 -> Needs Fix (FT-19, low: wording). SEG-02..SEG-12 -> Verified. REAL-02 and REAL-12 (PARTIAL in pass 2) -> Verified by SEG-08 and SEG-09. `spec.md` was not edited by this verifier.

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| SEG-02..SEG-12 | Implementing | Verified |
| SEG-01 | Implementing | Needs Fix (FT-19) |
| REAL-02, REAL-12 | Needs Fix | Verified (SEG-08, SEG-09) |
| DOC-01..VER-13 (other 103) | Verified | Verified (unchanged; gate green) |

---

## Summary

**Overall**: ✅ Ready, with fix tasks FT-19..FT-27 (three medium: FT-19, FT-20 and FT-23)

**Spec-anchored check**: 11/12 SEG requirements matched the spec outcome, SEG-01 PARTIAL (G1); spec-precision gaps flagged (SEG-02 manual activities, SEG-07 "a poucas palavras", SEG-04 limit, SEG-12 task text)
**Sensor**: 69/94 new faults killed (25 survivors: 3 equivalent, 22 weak or unpinned), 10/10 re-runs killed
**Gate**: backend 3153 passed, frontend 168 passed (0 skipped), ruff, eslint, build and bundle scan clean

**What works**: the term parse with grounding and the derived end (reproduced on "por 2 (dois) anos, a partir de 09/08/2024"), the open period for yearly items and the years counted inside the interstice, the `DATA_FIM_*` alerts and labels, near-duplicate titles and same-text duplicates through PostgreSQL, the extension-course context and the unit-name case of the Pró-Reitoria, the PAPIM rule, the partial professor name, the REQUIRE_DIST scan, and the OCR memory (25 scanned pages: OOM-killed before, 220-244 MB after, in `docker run -m 384m`).

**Issues found**: G1 "e meio" read as a whole number (FT-19), G2 "coordenou" not read as coordination (FT-23), unpinned unit-name stripping and table-unit path (FT-20, FT-21), a manual-activity behavior change that the spec does not state (FT-22), plus low items.

**Next steps**: land FT-19 and FT-23 and the cheap tests of FT-20/FT-21/FT-22; decide FT-22 (cap of the entered quantity) and FT-25 with the user; then run `python3 <skill-dir>/scripts/validate_state.py inteligencia-documental`.
