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

---

## Resolution (round 4)

Third real-environment findings (D2 article indexing, D4 repeated activity in a document) and the pass-3 gaps FT-19..FT-27 became TER-01..11 and tasks T96-T106 (Phase 14), each with one commit (`0b6fe66` adds the specs and this report). Tests use synthetic text only; no real document, MariTalk, VM, push or deploy. The independent Verifier has not re-run on these commits.

| Task | Commit | Closes | Proof (test, and the mutants re-applied to a file copy and killed) |
| ---- | ------ | ------ | ------------------------------------------------------------------ |
| T96 | `0de986b` | FT-19 | `test_term_rules.py`, `test_document_analyzer_term.py`: "um ano e meio" 18 months, "dois anos e meio" 30, "meio ano" 6, "por 2 (dois) anos, prorrogável por mais 2 (dois) anos" 24; "1 ano e 12 meses", "um mês e meio", two amounts, a bare "prorrogável por mais 2 anos" and decimals derive nothing; ten years exactly and "1 mês" read. N02, N03, N04, N06, N09, N10 killed (12 of 12 term mutants) |
| T97 | `470a93c` | FT-20 | `test_documents_flow.py::test_the_end_date_derived_from_the_term_is_the_period_of_the_created_activity` (API: `period_start` 2024-08-09, `period_end` 2026-08-09), `test_document_analyzer_table_unit.py` (official table, `table_version` passed), `test_open_ended_period.py` (P04, Q02). PE01, PE02, A05, A14, A06, A08, P04, Q02 killed |
| T98 | `8faee95` | FT-23 | `test_research_coordination_window.py`: coordenou, coordenador(a), coordena, lidera, liderou, líder, "responsável pelo projeto" keep V.1 with the name at most 8 words apart (8 accepted, 9 refused, both orders); a line break inside a paragraph is allowed, a blank line or a sentence end separates; another coordinator, "coordenado por", a member or collaborator between them, "Coordenadoria" and no research wording give no item. U07 and 11 more killed |
| T99 | `78fe3e1` | FT-21 | `test_extension_unit_names.py`: 16 unit names (Coordenadoria de Ações de Extensão, Diretoria, Pró-Reitoria, Centro, Núcleo, Departamento, Instituto, PROEX, "Universidade ... Extensão") confirm neither VII.9 nor IV.1/IV.2; with the nature of the activity they still do. U01, U02 and 7 more killed |
| T100 | `79d434c` | FT-22, D04 | `test_open_ended_quantity_cap.py`: VI.6 from 2020 with quantity 3 is 2 years and 60 points (was 90), quantity 1 stays 1, no quantity gives the complete years, a typed 0 stays 0, closed periods, dated events and "por ação" items unchanged, `DATA_FIM_AUSENTE` on the row; two unclassified activities are not one item. Frontend label test in `ProcessScoring.test.tsx` |
| T101 | `36931de` | D2 | `test_article_indexing.py`: VIII.9 and VIII.10 need a mention of Scopus, Web of Science, JCR, Qualis, SciELO, DOAJ, Latindex, PubMed, MEDLINE, "indexado/indexação/indexed"; an ISSN alone, "não indexada" and "sem indexação" do not count; without it VIII.11, `INDEXACAO_NAO_COMPROVADA`, review. The table wording of VIII.9/10/11 is read from `ufpa.json`. Frontend label test in `DocumentViewer.test.tsx` |
| T102 | `ec4b062` | FT-25 | `test_title_similarity.py`: two bancas of one item and day with titles that differ by a capitalized name on each side (Jaccard 0.82-0.89) are not duplicates; OCR typos, lowercase words, one-sided extra words, equal titles and equal text still are |
| T103 | `802f2ce` | D4 | `test_document_analyzer_collapse_similar.py`: "RPA na Gestao W A \| Academica" and "RPA na Gestao Academica" (Jaccard 0.67) become one activity with `ATIVIDADE_REPETIDA`; containment collapses; other dates, pages, proper names, a title-less activity and discipline lines stay apart; Jaccard 0.6 exactly collapses, 3/7 does not |
| T104 | `0b292bf` | FT-26 | `test_scoring_duplicates_content.py`, `test_repositories.py`, `test_process_score_content_duplicates.py`: a document with fewer than 50 normalized characters gets no content hash; D10 pinned (`"ab"+"c"` differs from `"a"+"bc"`) |
| T105 | `83a8e1b` | FT-24 | `test_maritalk_prompt.py`: the real request body names `term`, asks for the literal wording and forbids computing the end date. M02, M03, C01 killed |
| T106 | `ac93123` | FT-27 | `require-dist.test.ts` (13 values), checked by hand without `dist`: `REQUIRE_DIST=0` and `false` skip, `1` fails with the message |

**Gate** (Build gate at HEAD `ac93123`): backend `ruff` clean, `pytest` 3513 passed, 3 deselected (`maritalk_live`, with `MARITALK_MODEL=sabia-4-thinking` in the local `.env`; 6 in a clean checkout, see the correction in round 5), 0 failed, 0 skipped; frontend `eslint` clean, `vite build` OK, `REQUIRE_DIST=1 vitest` 183 passed, 0 skipped; bundle scan clean. The 211-point acceptance test (`test_scoring_golden.py`) is unchanged and green. Counts per commit: T96 3193, T97 3205, T98 3240, T99 3351, T100 3361 (frontend 169), T101 3476 (170), T102 3492, T103 3505, T104 3509, T105 3513, T106 frontend 183.

**Corrections to this report**: the T87 commit subject drops the tail of the task title and the T94 title ("render and recognize one page at a time") names more than the change (only the MuPDF store release in `render.py`); both are history and stay as committed. The round-3 note says "3 deselected"; the gate run here deselects 3 (`maritalk_live`), the pass-3 run reported 6 (the cause was not investigated; round 5 found it: the count depends on `MARITALK_MODEL`). The PIPE-02/ACC-02 wording, `--fake-ai` and the nginx of the server outside the repository (pass-2 info items) are not touched.

**Scope notes**
- Tests changed on purpose because the spec changed under them: `test_suggestion_rules` (a Pró-Reitoria de Extensão no longer confirms an extension project, TER-04), `test_scoring_alerts` and `test_document` (new alert codes `DATA_FIM_AUSENTE` of the scoring and `INDEXACAO_NAO_COMPROVADA`), `test_document_analyzer` ("Estudo Ficticio" is inside "Estudo Ficticio sobre Dados Abertos": a title that is not inside the other is used for the "different titles" case), `test_process_corpus_run` (NoItemAi uses three unrelated titles) and the repository test (pages of at least 50 characters).
- A bare "por mais 2 anos" (no "prorrogável", "renovável", "podendo ser") still reads as 24 months, as pinned by T82; with the extension words it is refused. Decide whether a bare "por mais" should be refused too.
- The coordination window counts words between the name and the role, so a label list without punctuation ("Coordenador: Beltrano / Membros: Fulana") relies on the "other role between them" guard (membro, colaborador, bolsista, participante, integrante, vice, aluno, estudante); another role word that is not on that list would pass for review.
- Proper names are recognized by a capital first letter; a name written in lowercase, or two names alike by 0.8 or more (João/Joana), still make titles duplicates until the user justifies the activity.
- The indexing evidence is searched in the whole text of the document, references included; the AI still chooses between VIII.9 and VIII.10 (international versus national), which the text does not prove either.
- D3 (date read with OCR noise), D5 (III.4 versus no item), D6 (line without item) and D7 (Vice `SEM_DATA`) of `ANALISE.md` are variation of the AI or data to review, not changed here.

**Open decisions for the user**: the fractional-year rule for the Vice (about 3.5 months, 20 points a year); the policy for a partial professor name (D1: five documents of the professor go to review because the text carries only two of the three names); rejected activities in a bulk validation; the VIII.36 unit ("por unidade" in the table, "ano/revista" in its text); the quantity-0 policy (a yearly item with less than a complete year scores 0 and `QUANTIDADE_ESTIMADA`); whether a bare "por mais N anos" is a term.


## Resolution (round 5)

Pass-4 gaps FT-28..FT-33 became QUA-01..06 and tasks T107-T112 (Phase 15), each with one commit (`9b7504a` adds the specs). Tests use synthetic text only; no real document, `Documentos/`, MariTalk call, VM, push or deploy. The independent Verifier has not re-run on these commits; QUA-01..06 stay `Implementing` in `spec.md` until it does.

| Task | Commit | Closes | Proof |
| ---- | ------ | ------ | ----- |
| T107 | `a9a2b90` | FT-28 | `test_research_coordination_labels.py` (42 cases): "Coordenador: Pedro Alves\nEquipe: Maria de Souza Lima" no longer confirms Maria as V.1 or V.2; "Pesquisadores:", "Autora:", "Orientando(a):" and a label right before the name ("Pesquisador(a): Maria ... Coordenador: Pedro") refuse; another full name between role and professor (two or more capitalized words without institution or title) refuses; plural roles ("coordenadores", "coordenaram"), "Profa. Dra.", "Universidade Federal do Pará" and "Instituto de Ciências Exatas e Naturais" between them do not. `test_research_coordination_window.py` and `test_research_coordination_role.py` unchanged and green |
| T108 | `abb9b8c` | FT-30 | `test_article_indexing.py`: "não indexada no Scopus", "sem indexação, apenas Qualis B2", "not indexed in Scopus", "Scopus: não indexada" and the SciELO after "nem" no longer prove indexing; a base named in another clause (period, semicolon or line break) still does. The negation removes up to 3 words before and 8 after it inside its clause |
| T109 | `a47c16d` | FT-29 | `test_extension_wordings.py` (39 cases): "Projeto Institucional de Extensão", "projeto de pesquisa e extensão", "projeto de ensino, pesquisa e extensão", "Extensão: projeto X", "atividade extensionista" confirm VII.9 and IV.1/IV.2; "Pró-Reitoria de Pesquisa e Extensão", "Ensino, Pesquisa e Extensão" alone and "Atividades de ensino, pesquisa e extensão da universidade" (a list of missions, the old `test_extension_course_context.py` case) still do not. The Pró-Reitoria header alone still does not confirm IV.2 |
| T110 | `0309ef3` | FT-32 | `test_surviving_mutant_pins.py` (7 tests). T02 (0.5), T03 (name length 4), T04 (length 2), T06 (typo ratio 0.7) and S16 (no "vice") re-applied to a file copy and killed. S11 is equivalent: "Departamento de Extensão" never matches the nature wording with or without `departamento` in the unit nouns, so no behavior tells them apart |
| T111 | `39d7d90` | FT-31 (guard only) | `test_numbered_variants.py`, `test_document_analyzer_collapse_similar.py`: "Nível 1"/"Nível 2", "Turma A"/"Turma B", "Cálculo I"/"Cálculo II", "Módulo III"/"IV" and "Edição 2024"/"2025" stay apart; "Curso de Python 2025" with "Curso de Python", the same numeral and OCR noise ("W A") still merge. Removing the guard fails 6 tests |
| T112 | this commit | FT-33 | this section, the corrected deselected count, `STATE.md` handoff |

**Gate** (HEAD `39d7d90`): backend `ruff` clean, `pytest` 3629 passed, 3 deselected (`maritalk_live`), 0 failed; frontend `eslint` clean, `vite build` OK, `REQUIRE_DIST=1 vitest` 24 files, 183 passed, 0 skipped. The 211-point acceptance test is unchanged and green. Quick gate (`tests/unit tests/architecture`) after each of T108-T110; the full backend gate ran after T107 (3555 passed) and after T111 (3629 passed).

**Correction (FT-33, deselected count)**: the `maritalk_live` tests are parametrized by the model list `[MARITALK_MODEL or "sabia-4-br-sp", "sabia-4-thinking"]` (`tests/live/test_maritalk_live.py:50-53`). With `MARITALK_MODEL=sabia-4-thinking` in the local `.env` the list has one model and 3 tests are deselected; in a clean checkout (no `.env`) it has two and 6 are deselected (`pytest --collect-only -m maritalk_live` gives 3 and 6). Both counts are right for their environment; none of them is a skipped test, `addopts = -m 'not maritalk_live'`.

**Decisions left for the user**
- FT-31, generic titles: a title contained in another ("Banca de TCC" inside "Banca de TCC de Ana Lima") on the same page, type, level and date still merges into one activity with `ATIVIDADE_REPETIDA`, as TER-07 says; the numbered or lettered variants no longer merge (T111). Decide whether containment should need a minimum number of words.
- Known limits of T107: a person who is "pesquisadora e coordenadora" ("Fulana, pesquisadora e coordenadora do projeto") is refused because "pesquisadora" sits between the name and the role; the item goes to review. A project title of two capitalized words between role and name ("Coordenadora do projeto Dados Abertos, Fulana") reads as another person and also goes to review. Both are fail-safe.
- Known limit of T108: a contradictory text ("indexada na Scopus, não indexada no Qualis") keeps the Scopus when it comes more than 3 words before the negation, and loses it when it is closer.
- Still open from round 4: the fractional-year rule for the Vice, the partial professor name (D1), rejected activities in a bulk validation, the VIII.36 unit, the quantity-0 policy, and whether a bare "por mais N anos" is a term.

## Resolution (round 6)

A one-page english certificate of participation that the user reported was not scored became CER-01..05 and tasks T113-T117 (Phase 16), each with one commit (`e08e95f` adds the specs). The cause had three links: `detect_document_type` knew only Portuguese markers and typed it `OUTRO`; the AI then read a research coordination or an extension project ("participant", 18 hours, term "six weeks (18 hours)"); the confirmations refused both, rightly (no coordination role, no extension nature), and the activity fell to `OUTRA` and was dropped. The user decided that such a certificate is a short course (VII.10). Tests use synthetic text only (an invented person and policy brief); no real document, `Documentos/`, MariTalk call, VM, push or deploy. The independent Verifier has not run on these commits; CER-01..05 stay `Implementing`.

| Task | Commit | Closes | Proof |
| ---- | ------ | ------ | ----- |
| T113 | `00b9311` | CER-01 | `test_document_type.py`: "this is to cerfy" (dropped "ti" glyphs), "hereby certif...", "certificate of participation/completion/attendance", a bare "CERTIFICATE" as a title line or last word give `CERTIFICADO`; the bare word does not count in an article (article text with "certificate" in the body, ending in it or as a line), in a plain text sentence, and a portaria keeps its type. Dropping the article guard fails 2 tests |
| T114 | `72f32be` | CER-02 (domain) | `test_participation_certificate.py`: `reclassify_participation_certificate` turns the four refused origins (V.1, V.2, IV.1, IV.2) into `CURSO_CONCLUIDO` only for a certificate with hours above 0; no hours, another document type, another taxonomy or a kept confirmation leave the result as it was. New `DocAlertCode.ENQUADRADO_COMO_CAPACITACAO` (19 codes), Portuguese label in `labels.ts`, frontend test in `DocumentViewer.test.tsx` |
| T115 | `905c99b` | CER-02, CER-04 | `test_document_analyzer_english_certificate.py` (14 cases, fake AI): the english text gives one VII.10 activity, `needs_review` true, quantity 1, 18 hours kept, the alert on activity 0, no `SEM_ITEM_DE_PONTUACAO`, no date and no derived end from "six weeks"; real coordination and real extension nature (Portuguese wording) keep V.1 and IV.2; no hours, an invented workload and another document type keep no item. Removing the review flag fails 4 tests |
| T116 | `84b6122` | CER-03 | `test_maritalk_prompt.py`: the prompt says the document may be in English and that fields are copied literally without translating, with and without the professor instruction. The prompt did not mention English before |
| T117 | this commit | CER-05 | this section and the `STATE.md` handoff |

**Existing tests changed (T115)**: `test_document_analyzer.py::test_certificate_of_a_project_without_the_word_extension_gets_no_item` and `test_document_analyzer_research_role.py::test_a_participation_certificate_creates_no_research_coordination` (SEG-07) expected no item for a certificate with 18 hours whose project nature or coordination role is missing. That is exactly the case CER-02 reclassifies, so both now expect VII.10 with `ENQUADRADO_COMO_CAPACITACAO` and `needs_review`; each keeps a variant without hours that still expects `SEM_ITEM_DE_PONTUACAO`. No test was weakened, skipped or deleted.

**Gate** (HEAD `84b6122`): backend `ruff` clean, `pytest` 3751 passed, 3 deselected (`maritalk_live`; 6 in a checkout without `.env`), 0 failed, including the integration suite (840) and the 211-point acceptance test, unchanged and green; frontend `eslint` clean, `vite build` OK, `REQUIRE_DIST=1 vitest` 24 files, 184 passed, 0 skipped.

**Decisions left for the user**
- English wordings are still unknown to the confirmations: `confirm_research_coordination` reads "coordenador/coordenou/líder" and `confirm_extension_project` reads "projeto de extensão", so an english certificate that really says "coordinator of the research project" or "extension project" is refused like the participation one and, with hours, also lands in VII.10 flagged `ENQUADRADO_COMO_CAPACITACAO` for the human to correct. Whether to teach those rules the english words is open.
- The reclassification needs hours above 0 grounded in the page; "six weeks" with no hours stays without an item.
- The activity keeps no date: VII.10 has no period rule here, the existing treatment of undated activities applies (the user types the date).
- Quantity is 1 per certificate (VII.10 is "no interstício", 2 points); the 18 hours stay on the extracted activity and are not used by the unit rule.
- The bare word "CERTIFICATE" counts as a certificate only outside articles; a non-article english text that merely ends in "certificate" is typed as certificate.
- Still open from round 5: generic-title containment (FT-31), the fractional-year rule for the Vice, the partial professor name (D1), rejected activities in a bulk validation, the VIII.36 unit, the quantity-0 policy, and whether a bare "por mais N anos" is a term.

## Resolution (round 7)

The interface round of stages 2, 3 and 4 became UIM-01..23 and tasks T118-T140 (Phase 17), each task one commit (`227f786` adds the specs, `f71e576` simplifies the scoring editor after the user's clarification). The user's brief: readable tables, short buttons that act at once, modals, no justification field in stages 2 to 4, the 70 percent confidence rule, bulk validation and a manual way to score an activity.

| Task | Commit | Closes | Proof |
| ---- | ------ | ------ | ----- |
| T118 | `5281541` | UIM-04 | `test_replace_delete.py` and `test_documents_file_api.py`: delete without `justificativa` gives 204 and the audit events (document and unlinks) have `justification is None`; with it, the text is kept |
| T119 | `c161216` | UIM-07 (API) | `test_repositories.py`, `test_read.py`, `test_documents_api.py`: `activity_count` counts distinct not-rejected activities per document, 0 when none |
| T120 | `417b4f8` | UIM-14 | status change, bulk validation and the distinct mark need no justification; a distinct mark without text stores "Marcada como distinta pelo usuário" because the duplicate rule reads that text |
| T121 | `daa7cfb` | UIM-16 | edits of item, quantity, hours and points, manual points, candidate items and the link of a document already linked elsewhere need no justification; audit before/after kept |
| T122 | `42de275` | UIM-18 (API) | `ChooseProcessTable` accepts another unit's table without justification; `TABELA_DE_OUTRA_UNIDADE` stays |
| T123 | `782cdc3` | UIM-21 | new `activities.unit_points_override` (migration 0005): the engine uses the typed unit value in per-unit and per-block items under the same limits, `VALOR_UNITARIO_MANUAL` alert, 422 in weekly-load, informed-value and PIT items and outside 0..10000 |
| T124 | `a64fd37` | UIM-05 | `Modal.test.tsx`: role, `aria-modal`, name, focus in and restored, Esc, Fechar, Tab trap |
| T125 | `5adbb06` | UIM-01, 02, 10, 19 (CSS) | `styles.test.ts`: variants, fixed short columns, ellipsis, justified text, cards below 960 px |
| T126 | `1e7e33b` | UIM-02, 03 | `DocumentList.test.tsx`: short labels with the name only in aria-label and title, Baixar, immediate Substituir and Reprocessar, delete confirmation without justification |
| T127 | `33898db` | UIM-06 | classification in a modal, 422 beside the field |
| T128 | `094766d` | UIM-08 | `ProcessDocuments.test.tsx`: viewer in a modal, `?documento=` kept, Fechar and Esc clear it |
| T129 | `68be221` | UIM-17 | `ActivityForm` without the justification field |
| T130 | `3801e7f` | UIM-07 | Criar atividade button for failed, review, no-AI, no-item and `activity_count` 0 documents; modal; page linked |
| T131 | `9e3a48b` | UIM-09 | no warning at 0.70 or more without a real alert, warning at 0.69, new intro sentence |
| T132 | `50a7367` | UIM-13 | stage 3 buttons, immediate validate and reject, edit and link in modals |
| T133 | `2ced9d3` | UIM-11 | select all (only awaiting review), header checkbox, clear selection, count |
| T134 | `1994aea` | UIM-12 | bulk validation by confidence through the atomic batch endpoint |
| T135 | `5d69873` | UIM-19, 20 | stage 4 columns and direct buttons, modals |
| T136 | `41fa752` | UIM-18 | `TablePicker` without the justification field |
| T137 | `8e4525e` | UIM-22 | `ScoreEditor`: one field, unit value, saved through the activity PUT |
| T138 | `c8a0526` | UIM-23 | Editar pontuação, Manual badge, Usar valor da tabela, totals reloaded |
| T139 | `afabf24` | UIM-01, 02, 03, 05, 10, 12, 17, 19, 21, 23 | tests that kill the surviving mutants of the independent verification below |
| T140 | this commit | UIM-15 | this section and the `STATE.md` handoff |

**Independent verification (Phase 17)**: a fresh sub-agent mapped UIM-01..23 to test assertions and injected 32 faults in a scratch worktree: 26 killed, 7 survived (the substitution picker, the button variant, the `text-block` and `wide-table` classes, the modal width, the no-item guard of the bulk validation and the scroll lock). T139 adds a test for each and the survivors were re-checked on file copies: they die. It also flagged weak negative assertions of the justification field (exact-label queries) and the lack of an explicit 0 and 10000 test of the unit value: both fixed in T139. Remaining weakness: the layout (columns, ellipsis, 360 px) is proven only by static CSS tests and markup class tests, as before (the 360 px test was already static); a browser smoke test would close it.

**Gate** (HEAD `afabf24`): frontend `eslint` clean, `tsc` and `vite build` OK, `REQUIRE_DIST=1 vitest` 236 passed (26 files); backend `ruff` clean and `pytest` 3783 passed, 3 deselected (`maritalk_live`), 0 failed. `test_worker.py::test_a_database_error_while_claiming_does_not_kill_the_thread` is timing-based and failed in two earlier full runs made while other agents also used the machine and the database; it passes 8 of 8 alone, 3 times in a row, and in this last full run, and does not touch this round's code.

**Rules relaxed (justification no longer required in stages 2, 3 and 4; the field is still accepted and stored when an API client sends it)**
- `DeleteDocument` (`documents.py`): justification was required to delete a document (DOC-10, 422 on `justificativa`).
- `ChangeActivityStatus` (`scoring.py`): required to validate, reject or reopen an activity (ATV-09).
- `BulkValidateActivities` (`scoring.py`): required for the batch (REV-04).
- `MarkActivitiesDistinct` (`scoring.py`): required for the distinct mark (VERIF-06); now a default text is stored when none is sent.
- `UpdateActivity` (`scoring.py`): required to change group, item, quantity, hours, informed points or manual points (ATV-08).
- `CreateActivity` (`scoring.py`): required to create with manual points (`points_override`) and, for manual activities, for each candidate item (ATV-12).
- `LinkEvidence` (`evidences.py`): required to link a document already linked to another activity (VINC-03).
- `ChooseProcessTable` (`scoring.py`): required to choose a table of another unit (Etapa 4; the alert stays).
- Not changed: altering a process in progress (Etapa 1, `processes.py`), the justifications of the scoring admin and the automatic justification of a reprocess.
- Frontend: no justification field in the delete confirmation, the classification, the activity form, validate, reject, link, bulk validation, the distinct mark and the table choice.

**Decisions left for the user**
- Stage 4 "Manter como distinta" (the old "Marcar como distinta"): the distinct mark still needs a text in the database because the duplicate rule reads it; a mark made by the button stores "Marcada como distinta pelo usuário". Say if the rule should read a flag instead.
- Bulk validation by confidence: the API keeps no confidence per activity, so the document's confidence is used (all cited documents read without failure at 0.70 or more) and an activity with candidate items, no item, no document, a scoring alert or a not-scored row stays out. Exposing the analyzer's `needs_review` per activity would be the exact rule; it is computed but not stored today.
- The manual score is a unit value and works only in per-unit and per-block items; weekly-load items keep their manual points in "Editar", informed-value items keep their informed points, and PIT hours stay automatic. Extending the unit value to those modes needs a rule per mode.
- The "Criar atividade" button treats `FALHOU`, `REQUER_REVISAO`, `EXTRAIDO_SEM_IA`, "sem item de pontuação" and `activity_count` 0 as "no usable activity" (a rejected activity does not count); a `REQUER_REVISAO` document that already has activities still shows it.
- Documents with status `REQUER_REVISAO` and no status code (professor name mismatch) show "Requer revisão: abra o documento e confira os avisos" even with confidence above 70 percent, since the status is a real alert.
- Tables below 960 px wide turn into cards (not only below 480 px) so the columns never squeeze the text.
- Deploy: this round adds migration 0005 (`activities.unit_points_override`); the VM needs `alembic upgrade head` with the new image.

## Resolution (round 8)

Round 8 is the rule of the document outside the interstice (FORA-01..09, tasks T141-T145, Phase 18), asked by the user on 2026-11-18. Each task is one commit. **The independent Verifier pass is pending**: the author wrote these lines and FORA-01..09 stay `Implementing` until a fresh Verifier confirms them and runs the mutants on the analyzer and on the screen.

| Task | Commit | Closes | Proof |
| ---- | ------ | ------ | ----- |
| T141 | `be7c11b` | FORA-01, 05, 06 | `test_document_period.py`: all `FORA` is outside; `FORA`+`DENTRO` and `FORA`+`PARCIAL` are inside; an empty list or no usable date does not apply; `test_repositories.py` stores the code in `status_code` and in the run warnings (no migration: `status_code` is `String(40)` and the warnings are JSONB) |
| T142 | `df59346` | FORA-01, 05, 06, 07, 09 | `test_document_analyzer_outside_interstice.py` (no activity, alert with the most recent date, month precision, outside next to inside or crossing, no date, no interstice) and `test_process_outside_interstice.py` (`PROCESSADO`, no `REQUER_REVISAO`, widening the interstice and reprocessing removes the alert and creates the activity, narrowing replaces the old draft) |
| T143 | `0c6fbff` | FORA-02, 03, 04, 08 | `test_documents_outside_interstice_api.py`: list fields, detail alert `detail`, 409 `DOCUMENTO_FORA_DO_INTERSTICIO` on classification and on linking, no activity or evidence of the document, Visualizar, Baixar, Reprocessar and Excluir still work |
| T144 | `a1b651c` | FORA-02, 04, 08, 09 | `DocumentList.test.tsx` (strip text with the dates, month precision, only four buttons, summary counts, no justification field) and `styles.test.ts` (alert colour, strip attached to the card) |
| T145 | this commit | all | this section, `AD-016` and the handoff |

**Where the document date lives**: in the `detail` of the `DOCUMENTO_FORA_DO_INTERSTICIO` alert stored in the active run warnings (`document_date` ISO, `date_precision` `DAY` or `MONTH`, `interstice_start`, `interstice_end`). The list use case reads it only for documents whose `status_code` is the new code (no extra query for the others) and the list API exposes `outside_interstice`, `document_date`, `document_date_precision`, `interstice_start` and `interstice_end`; the detail API exposes the alert with `detail`. The date is the latest of the event, start and end dates the page proves.

**Existing tests changed** (the rule changed the old single-activity expectation of SUG-09): six analyzer tests in `test_document_analyzer_classification.py` and `test_document_analyzer_open_end.py` that checked `FORA_DO_INTERSTICIO` on a document with one outside activity now put a second, inside activity in the same document (FORA-05); `test_process_corpus_run.py` expects the outside document with no activity and `interstice == "FORA"` (`scripts/process_corpus.py` reports it so); `test_documents_api.py` lists the new keys and the `detail: None` of the alerts; `test_read.py` reads `ListedDocument`.

**Gate** (HEAD `a1b651c` plus this commit): backend `ruff` clean and `pytest` 4613 passed, 3 deselected (`maritalk_live`), 0 failed; frontend `eslint` clean, `tsc` and `vite build` OK, `REQUIRE_DIST=1 vitest` 246 passed (26 files). `validate_spec.py` 0 errors, `validate_tasks.py` 0 errors (6 warnings, `Tests: none`), `validate_state.py` 0 errors. `CLAUDE.md` already described the final behavior and was not changed (the only detail it does not say: with month precision the warning shows `mm/aaaa`).

**Open points for the lead**
- The list stays an array: the count `outside_interstice_count` is summed by the screen, not sent by the API.
- A draft of an earlier reading, rejected by the reprocess, stays as a rejected zero-point row linked to the document (PIPE-09); a draft the user edited or validated before the document became outside also stays and keeps its link. Decided (AD-017): this non-destructive behavior stays and FORA-03 now says so. Superseded by AD-018 (T146): such activities are now rejected with audit when the document becomes outside.
- Substituir is hidden on the outside row (FORA-04 lists four buttons).
- The rule is decided before the professor check: a document of another professor that is wholly outside ends `PROCESSADO` with only the outside alert. `DOCENTE_DIVERGENTE` is not stored for it, because the analyzer returns at the outside rule before the professor check (corrected after the independent verification, `verification-fora.md` D3; accepted: the document is not processed and not pending either way).
- SUG-09 (spec line 167) read as if the outside activity were always kept; FORA-05 narrows it. SUG-09 now carries a note saying so.

## Pass 4 (independent Verifier, HEAD 9533966)

### Validation pass 4 - Phase 14 (T96-T106, TER-01..TER-11)

Verifier: independent (author != verifier), tlc-spec-driven, evidence-or-zero. Diff range `0b6fe66..9533966` (HEAD `9533966`), worktree `/tmp/verify-pass4` (plus `/tmp/verify-pass4-mut` for mutants and `/tmp/verify-pass4-base` at `0b6fe66` for before/after probes; all removed at the end). Main tree untouched (porcelain identical: `requeriment.txt`, `test/`). No `Documentos/`, no `Modelos/` outputs, no MariTalk call, no push/deploy/VM. Probes used synthetic text only.

## Verdict: PASS (no blocking finding; 1 medium and 4 low gaps, FT-28..FT-32)

## Gate (HEAD `9533966`, worktree)

| Gate | Result |
| ---- | ------ |
| `ruff check .` (backend) | All checks passed |
| `pytest -q` (backend, main venv, `pythonpath=.` resolved to the worktree) | 3513 passed, 6 deselected, 0 failed, 302.76 s |
| `test_scoring_golden.py` (211 points, `body["total"] == "211.00"`, `tests/integration/api/test_scoring_golden.py:115`) | 6 passed (also inside the full run) |
| `npm run lint` | clean |
| `npm run build` | built OK (`dist/assets/index-BN9QNOVB.js`) |
| `REQUIRE_DIST=1 npm test -- --run` | 24 files, 183 passed, 0 skipped |
| `validate_spec.py` / `validate_tasks.py` | 0 errors; 2 known warnings (T11, T95 `Tests: none`) |
| Commit subjects T96-T106 (`check_commit.py`) | 11/11 ok |
| tasks.md T96-T106 | 41 `[x]`, 0 `[ ]` |

Note: the Resolution (round 4) says "3 deselected"; the real count is 6 (all `maritalk_live`, `pytest --collect-only -m maritalk_live` = 6/3519). See FT-33.

## Per-requirement evidence

| Req | Task / commit | Spec outcome | Evidence (code, test, my probe) | Result |
| --- | ------------- | ------------ | -------------------------------- | ------ |
| TER-01 | T96 `0de986b` | "e meio/meia", "meio ano" read in months; refuse two same-type values, split years/months, "1 ano e 12 meses", "mês e meio", >10 years, extension as sole value; first value wins over a later extension; 10 years and "mês" read | `term_rules.py` `_AMOUNT`, `_EXTENSION`, `_HALF_YEAR`, `_BETWEEN_YEARS_AND_MONTHS`. Probe (`parse_term_months`): "um ano e meio" 18, "dois anos e meio" 30, "meio ano" 6, "por 2 (dois) anos, prorrogável por mais 2 (dois) anos" 24, "1 ano e 12 meses" None, "um mês e meio" None, "prorrogável por mais 2 anos" None, "10 anos" 120, "11 anos" None, "1 mês" 1, "2 anos, depois 6 meses" None, "1,5 ano" None, "2 anos e 6 meses e meio" None. Tests `test_term_rules.py`, `test_document_analyzer_term.py` pass. 12/12 term mutants killed (N01-N12) | Verified |
| TER-02 | T97 `470a93c` | creation-time dates reach the activity period and API; analyzer decides "por ano" by table unit | `test_documents_flow.py::test_the_end_date_derived_from_the_term_is_the_period_of_the_created_activity`, `test_document_analyzer_table_unit.py` (table version passed), `test_open_ended_period.py`; all green in the full run. Mutants E01-E09, Q2-Q4 (engine and period) killed | Verified |
| TER-03 | T98 `8faee95` | role within 8 words of the name, same paragraph, line break allowed, other coordinator / "coordenado por" / participant only give no item | `suggestion_rules.py::_role_near_name`, `_coordination_positions`, `COORDINATION_WINDOW_WORDS = 8`. Probe: "coordenou" -> V.1; "coordenado por Maria" -> OUTRA; "Coordenador:\n Maria" -> V.1; "Maria, membro; coordenador: Pedro" -> OUTRA. Mutants S04-S10, S17 killed. Regression found (FT-28) | Verified with gap FT-28 |
| TER-04 | T99 `78fe3e1` | unit names with "extensão" confirm neither VII.9 nor IV.1/IV.2; nature still confirms | `_EXTENSION_UNIT`, `_EXTENSION_NATURE`, `confirm_extension_project` now strips units then needs the nature wording. Probe: "Pró-Reitoria de Extensão certifica ... projeto" -> OUTRA; "Projeto de Extensão da Universidade Federal do Pará" -> kept; "Categoria: Extensão", "Programa de Extensão Universitária" kept. Mutants S12-S15, Q6 killed; S11 survives (near-equivalent). Narrower than before (FT-29) | Verified with gap FT-29 |
| TER-05 | T100 `79d434c` | start-only "por ano" item (hand-entered too): quantity = min(typed, complete years in the interstice), no typed -> complete years, never raised, `DATA_FIM_AUSENTE` on the row, two no-item activities not the same item | `scoring_engine.py::_open_quantity` and `open_ended` branch (lines ~139-208), `scoring_periods.py::is_start_only/complete_years_inside/open_period_years`; `quantity_rules.py` now reuses `complete_years_*` (behavior-equivalent: checked in the diff, and `test_quantity_rules.py` + `test_document_analyzer.py` pass). Tests `test_open_ended_quantity_cap.py`, `ProcessScoring.test.tsx` label. Mutants E01-E09, Q1-Q4 killed (min->max, ZERO instead of years, non-yearly, alert off, month precision, interstice clip, event_date guard, `<=` boundary) | Verified |
| TER-06 | T101 `36931de` | VIII.9/10 without proof of indexing -> VIII.11 + `INDEXACAO_NAO_COMPROVADA` + review; PT label | `suggestion_rules.py::confirm_article_indexing`, `document_analyzer.py` (alert, `flagged`), `DocAlertCode.INDEXACAO_NAO_COMPROVADA`, `labels.ts` `DOCUMENT_CODE_LABELS`. Probe: ISSN alone -> VIII.11; "não indexada" -> VIII.11; "Scopus", "SciELO", "DOAJ", "Web of Science" -> kept. Mutants S01-S03, S18, A03-A06, Q5 killed. Negation plus index name passes (FT-30) | Verified with gap FT-30 |
| TER-07 | T103 `802f2ce` | same page/type/level, equal or absent dates, Jaccard >= 0.6 or containment -> one activity + `ATIVIDADE_REPETIDA`; distinct dates/pages/names apart; Grupo I never merged by similarity | `document_analyzer.py::_same_activity`, `title_similarity.py::repeated_titles`. Mutants T01, T07-T09, T12, T13, A01, A02 killed; T02 (threshold 0.5) survives. Over-merge of numbered variants (FT-31) | Verified with gap FT-31 |
| TER-08 | T102 `ec4b062` | titles differing by a proper name on each side are not duplicates; exact equality and equal text still mark | `title_similarity.py::differ_by_proper_name/similar_titles`, used by `scoring_duplicates.py::find_duplicates`. Probe: "Banca de Mestrado de Ana Lima" vs "...Pedro Alves" (also upper-case) not similar; "João/Joana Silva" not similar. Mutants T05, T10, T11 killed; T03/T04/T06 survive (FT-32) | Verified |
| TER-09 | T104 `0b292bf` | text under 50 normalized chars gets no content hash | `scoring_duplicates.py::has_readable_text` (`>= 50`), `repositories.py:1231-1233`; D10 `"\n".join`. Mutants D01-D04, R01 (integration `test_repositories.py`) killed | Verified |
| TER-10 | T105 `83a8e1b` | prompt test pins literal `term` instruction and the ban on computing the end date | `tests/unit/infrastructure/test_maritalk_prompt.py` (4 tests; build the real request body, `maritalk.py:35` wording). No live call. (No app change: wording already present; the test pins it.) | Verified |
| TER-11 | T106 `ac93123` | `REQUIRE_DIST` set only when not empty, `0`, `false` | `frontend/tests/require-dist.ts`, `bundle.test.ts:17`, `require-dist.test.ts` (13 values). Manual run without `dist`: `0`, `false`, empty -> 6 passed, 1 skipped; `1` -> bundle test FAILS. Mutants F1-F5 (drop `0`, `false`, `trim`, `toLowerCase`, empty guard) and F6 (raw `Boolean`) killed | Verified |

## Regression hunt (areas touched)

- term_rules: lookbehind now also excludes `,` ("2,5 anos" refused); a term preceded by "renov/prorrog/podendo ser" in the same text is cut and refused ("Portaria renovada em 2025, por 2 anos" -> None). Fail-safe, noted as info. A bare "por mais 2 anos" still reads 24 months (T82, open decision in Resolution).
- suggestion_rules: coordination (FT-28), extension nature (FT-29), indexing (FT-30). "Vice-coordenadora Maria ..." still counts as coordination (pre-existing; "vice" guard only looks between name and role). "coordenado pela Profa. Maria" gives OUTRA (spec literal).
- quantity_rules: refactor to `complete_years_*` is equivalent; kill tests exist (E06, E08, Q2, Q3).
- scoring_engine: cap applies only to `yearly and is_start_only`; closed periods, event dates and non-yearly items untouched (tests + E03, E07).
- article indexing guard: guard runs before `suggest_item`; `needs_review` includes it; alert persisted as string (no DB enum for codes).
- duplicate title collapse: `DISCIPLINA_MINISTRADA` never merged by similarity; unequal known spans never merged (A01, A02).
- content hash: only the repository path calls `content_hash`; guarded by `has_readable_text`.
- REQUIRE_DIST and prompt: no regressions.
- 211-point acceptance test: green.

## Discrimination sensor (mutants applied in `/tmp/verify-pass4-mut`, file-level replace + restore, `tests/unit` per mutant, integration file for R01, vitest for F*)

Result: backend 64/70 killed (6 survived); frontend 6/6 killed. Worktree restored and clean after each run.

Killed: N01-N12, S01-S10, S12-S15, S17, S18, E01-E09, D01-D04, T01, T05, T07-T13, A01-A06, R01, Q1-Q7, F1-F6.

Survivors:

| Mutant | Change | Why it survives | Class |
| ------ | ------ | --------------- | ----- |
| T02 | `REPEATED_TITLE_JACCARD` 0.6 -> 0.5 | tests pin 0.6 (collapses) and 3/7 = 0.43 (does not), nothing between 0.43 and 0.6 | weak boundary (FT-32) |
| T03 | `MIN_NAME_LENGTH` 3 -> 4 | no test with a three-letter proper name ("Ana", "Eva") | unpinned (FT-32) |
| T04 | `MIN_NAME_LENGTH` 3 -> 2 | no test with a two-letter capitalized word that must not be a name | unpinned (FT-32) |
| T06 | `TYPO_RATIO` 0.8 -> 0.7 | tests pin 0.9 side only (T05 killed) | weak boundary (FT-32) |
| S16 | drop "vice" from `_OTHER_ROLE` | no test with "vice" between name and role | unpinned (FT-32) |
| S11 | drop "departamento" from `_UNIT_NOUN` | near-equivalent: "Departamento de Extensão" never matches `_EXTENSION_NATURE` anyway | equivalent in practice |

Clean-up: tests that pin a regex literal are not mirrored by the implementation; they assert spec-defined outcomes (18/30/6 months, 8-word window with 9 refused, 50 chars, 60 points instead of 90, Jaccard exactly 0.6).

## Gaps

| ID | Sev | Req | Finding | Fix |
| -- | --- | --- | ------- | --- |
| FT-28 | Medium | TER-03 | New false positive caused by the "line break inside the paragraph" rule. `confirm_research_coordination(PESQUISA_PROJETO_COORDENACAO, "Projeto de pesquisa. Coordenador: Pedro Alves\nEquipe: Maria de Souza Lima", "Maria de Souza Lima")` returns `PESQUISA_PROJETO_COORDENACAO`; at `0b6fe66` the same input returns `OUTRA` (the old split on `\n` separated them). "Equipe", "pesquisador(es)", "autor(es)" are not in `_OTHER_ROLE`, and another full name between the role and the professor is not a guard. The Resolution lists "another role word not on the list" as a known limit, but "equipe" is the most common one. Suggested V.1 points need human review of the item. | Add "equipe", "pesquisador*", "autor*", "orientando" to `_OTHER_ROLE`; consider refusing when another capitalized name sits between role and professor; add the test with `\nEquipe:`. Non-blocking: spec TER-03 mandates the line-break tolerance. |
| FT-29 | Low | TER-04 | `confirm_extension_project` now needs one of the `_EXTENSION_NATURE` wordings. "Projeto Institucional de Extensão", "Projeto de pesquisa e extensão", "Projeto de ensino, pesquisa e extensão", "Extensão: projeto X", "Atividade extensionista" now give `OUTRA` (review) where before any "extensão" confirmed. Fail-safe (goes to review) but a loss in recall. | Decide with the user whether "institucional/pesquisa e/ensino, pesquisa e extensão" wordings are nature; add them to the regex or pin the refusal in a test. |
| FT-30 | Low | TER-06 | Negation plus an index name counts as proof: "Revista não indexada no Scopus", "sem indexação, apenas Qualis B2", "not indexed in Scopus" keep VIII.9/10 (the `_NOT_INDEXED` strip removes only "não indexada", the name `Scopus` stays). Qualis alone (a classification, not an index) is proof by spec wording. | Strip the index name that follows the negation; or send these to review with the alert. Add the test. |
| FT-31 | Low | TER-07 | Jaccard 0.6 or containment merges numbered or lettered variants and generic titles: "Curso de Python Nível 1" / "Nível 2" (0.67), "Ensino de Cálculo I Turma A" / "Turma B" (0.71), "Banca de TCC" inside "Banca de TCC de Ana Lima" collapse into one activity when page, type, level and dates agree or are absent. The merge is alerted (`ATIVIDADE_REPETIDA`), and spec TER-07 is literal, so this is spec precision. | Add a digit/roman-numeral/single-letter guard and a minimum word count for containment, or ask the user to accept. |
| FT-32 | Low | TER-08/03 | Surviving mutants T02, T03, T04, T06, S16 (table above): boundaries of the proper-name guard (3-letter names, typo ratio 0.7-0.8), of the repeated-title threshold between 0.43 and 0.6 and the "vice" guard are unpinned. | Add one test per boundary (e.g. "Banca ... Ana Lima" vs "... Eva Lima"; Jaccard 0.5 not repeated). |
| FT-33 | Info | docs | validation.md Resolution says "3 deselected"; the run deselects 6 (all `maritalk_live`), so the "cause not investigated" is just those 6 live tests. TER-01..11 are still `Implementing` in `spec.md:492-502` and should be `Verified`. A bare "por mais N anos" still reads 24 months, "Portaria renovada ... por 2 anos" is refused (fail-safe); "Vice-coordenadora" counts as coordination (pre-existing). | Correct the count; move TER-01..11 to Verified; decide the open items. |

No blocking gap. Lessons to distill (not written; `.specs/lessons.json` untouched by instruction): (a) "tolerating a line break in a role window widens a label list into one paragraph; every other label word (Equipe, Pesquisadores) needs a pinned refusal"; (b) "a negation strip that leaves the object ('não indexada no Scopus') keeps the evidence it meant to remove"; (c) "a similarity threshold needs a test between the rejected and accepted values, and digits that tell variants apart".

## Requirement traceability update (recommended, not applied)

| Requirement | Previous | New |
| ----------- | -------- | --- |
| TER-01, 02, 05, 08, 09, 10, 11 | Implementing | Verified |
| TER-03 | Implementing | Verified (FT-28 medium, fix task) |
| TER-04 | Implementing | Verified (FT-29 low) |
| TER-06 | Implementing | Verified (FT-30 low) |
| TER-07 | Implementing | Verified (FT-31 low) |

## Summary

Overall: PASS. Gate green (ruff, pytest 3513, lint, build, vitest 183, 211-point test). 11/11 TER requirements match the spec outcome in code and tests; sensor 64/70 backend and 6/6 frontend mutants killed; survivors are boundary pins (FT-32). One medium regression (FT-28, coordination across a line break) and four low gaps. Next: fix task for FT-28, cheap pins for FT-32, correct the "3 deselected" note, then run `validate_state.py inteligencia-documental`.
