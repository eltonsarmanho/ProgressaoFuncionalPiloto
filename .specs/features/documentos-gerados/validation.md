# Documentos Gerados Validation

**Date**: 2026-11-18
**Spec**: `.specs/features/documentos-gerados/spec.md` (79 requirements: TAB 8, CMP 13, ARR 8, REL 15, VER 9, UIG 9, DEL 15, ORD 2), `design.md`, `tasks.md` (T1-T125); plus FORA-03 and FORA-07 of `.specs/features/inteligencia-documental/spec.md` (T146, AD-019)
**Diff range**: feature `be345ac^..4628f08` (verified code, HEAD of the two verifications; 186 commits on `feat/inteligencia-documental`); correction round `2c18cf0..969273e` (T112-T125, 14 commits); final HEAD `969273e`
**Verifier**: two independent sub-agents (author != verifier), scope A (TAB, CMP, ARR, VER) and scope B (REL, DEL, ORD, UIG, FORA-03, FORA-07). The reports are `verification-a.md` and `verification-b.md` and are final; this file consolidates them with the fix commits and does not re-judge code.

---

## Validation: Documentos Gerados - PASS

**Result**: PASS. Verifier A: PASS (36 PASS, 2 PARTIAL, 0 failed in 38 requirements; 0 Blocker, 0 High, 3 Medium, 8 Low). Verifier B: PASS (42 PASS, 1 PARTIAL, 0 failed in 43 requirements; 0 Blocker, 0 High, 3 Medium). After the correction round (T112-T125) every Medium finding is closed and the two Verifiers' PARTIAL items are resolved except two: REL-12 (grounding limit, user decision pending) and CMP-01 (item title cut in the table of contents, accepted limitation, spec text not aligned). Final traceability: 77 of 79 requirements `Verified`, 2 `Implementing` (CMP-01, REL-12). FORA-03 and FORA-07 of `inteligencia-documental` are `Verified`.

| Item | Result |
| --- | --- |
| Spec-anchored check | 79 of 79 requirements have a `file:line` assertion read by a Verifier; 2 criteria differ in part from the spec text (CMP-01, REL-12); 5 spec-precision gaps flagged and listed in "Spec-precision gaps" |
| Gate at final HEAD `969273e` | Backend `ruff check .` clean and full `pytest -q` 5048 passed (clean copy of HEAD); frontend 34 files, 374 tests passed with `REQUIRE_DIST=1`, `npm run lint` clean and `npm run build` ok (clean copy of HEAD, re-run at closure) |
| Sensor | 308 mutants injected (A 135, B 173), 281 killed, 27 survived: 8 equivalent, 19 real test gaps, all 19 closed by tests in T113, T115-T119 and re-killed (see "Discrimination sensor") |
| Real runs | Two end-to-end runs with synthetic data (real uvicorn, worker and PostgreSQL 16); a browser run in Chrome at 1280 px and 360 px; no `Documentos/` or `Modelos/` file opened by any agent |
| Not done | T110 (deferred, needs the user's authorization to read the real corpus); DOCX not opened in Word; one real-user walkthrough (UAT) not performed |

---

## Method

1. **Two independent Verifiers** with fresh context, each on its own scope, in isolated copies under the scratchpad (the real tree was never mutated; `git status --porcelain` identical before and after in both runs, with the other session's uncommitted `Dashboard*`, `types.ts`, `ProcessDialogs.tsx`, plus `requeriment.txt` and `test/` untouched).
2. **Spec-anchored check**: each acceptance criterion traced to a test `file:line` and assertion, plus the observed behavior in the real run or an independent calculation (A section 4, for example the 20-page numbering of the E2E Comprovante derived from the spec before reading the PDF).
3. **Mutants** (P0 depth, data integrity, irreversible deletion, grounding of AI text, optimistic locking): A injected 135 (116 killed), B injected 173 (116 backend and 57 frontend; 165 killed). One mutation at a time in an isolated copy, targeted tests first, wider suites for survivors.
4. **Real end-to-end runs** (synthetic data only, MariTalk absent or replaced by a local fake provider): A generated Tabela, Relatório and Comprovante, downloaded them, compared original pages by pixel, tested the limits (401 pages, 400 pages, PNG above 12 MP), the forced restart with `GERANDO` rows and the database triggers through `psql`. B drove the built frontend with Playwright over Chrome at 1280 x 900 and 360 x 740: draft editing, wording (faithful, invented, provider error, deadline), arrangement editor, generation, conclusion with a deliberate partial failure and retry, 410 and read-only states, FORA-03 reprocessing, and a SIGKILL of the backend during a wording job.
5. **Correction round** T112-T125: each fix has its test and its re-kill of the original mutant in an isolated copy, recorded in the commit body.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1-T109 | Done | All Done-when boxes ticked in `tasks.md` except T110 (0 open boxes outside T110 and T111 before this report); T109 is the deployment note `d946e24` |
| T110 | Deferred | "adiada, aguarda autorização do usuário": it reads the real corpus (`Documentos/`), which no agent may open without the user's explicit authorization; its Done-when boxes stay unticked |
| T111 | Done | This report |
| T112-T125 | Done (14/14) | Correction round, Phase 22, commits `f98d4a5` to `969273e` |

---

## Spec-Anchored Acceptance Criteria

Evidence pointers: `A s2` and `B s` mean the section of `verification-a.md` (section 2, family table) or `verification-b.md` (family table "Spec-anchored acceptance criteria"); the `file:line` is the main assertion cited there (paths relative to `backend/` except where `frontend/` is shown). Each row cites more assertions in the report. "Closed by" names the fix commit when a Verifier finding touched the requirement.

### TAB (Verifier A, `verification-a.md` section 2)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| TAB-01 | Verified | `tests/integration/api/test_generated_table_acceptance.py:37-39` (200 and `Pontuação geral: 211,00` in DOCX and PDF); E2E v1 211,00 and v2 221,00 | T124 `e4fb09fb` (title cap, A-D9) |
| TAB-02 | Verified | `tests/unit/infrastructure/test_table_pdf.py:64-75`; `test_table_docx.py:132` | none |
| TAB-03 | Verified | `tests/unit/infrastructure/test_table_pdf.py:50-56`; `tests/unit/domain/test_table_document_rows.py:88-117`; first page of a multi-page activity pinned (spec silent) | T117 `def97fa` (M96), T124 `e4fb09fb` |
| TAB-04 | Verified | `tests/unit/domain/test_table_document_totals.py:47-52`, `:54-69`; `test_table_document_rows.py:44-50` | T117 `def97fa` (M50, M64, A-D2) |
| TAB-05 | Verified | `tests/unit/domain/test_table_document_totals.py:72-79`; `tests/integration/api/test_generated_table_acceptance.py:43` | none (A-D11 DOCX split, accepted limitation) |
| TAB-06 | Verified | `tests/unit/domain/test_table_document_totals.py:122-130`, `:162-180`; `test_table_pdf.py:112` | none |
| TAB-07 | Verified | `tests/integration/doc_usecases/test_request_generation.py:44-50`; `tests/integration/api/test_generated_documents_api.py:49-59` | none |
| TAB-08 | Verified | `tests/integration/doc_usecases/test_request_generation.py:53-60`; `test_generated_table_acceptance.py:82-89` | none |

### CMP (Verifier A)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| CMP-01 | PARTIAL, stays `Implementing` | `tests/integration/api/test_generated_comprovante_acceptance.py:136-137`; `tests/unit/infrastructure/test_front_matter.py:107-114`, `:143-151`. The item title appears only in the table of contents and is cut with an ellipsis at about 85 characters (A-D4) | not changed: accepted limitation in design Risks (T125 `969273e`); spec text not aligned, see "Decisions pending" |
| CMP-02 | Verified | `tests/unit/infrastructure/test_front_matter.py:117-128` | T118 `f061f13` (M43) |
| CMP-03 | Verified | `tests/unit/infrastructure/test_source_pages.py:26`, `:29-47`; `test_source_pages_rotation.py:28-41`, `:44-55`; E2E maxdiff 0 | none |
| CMP-04 | Verified | `tests/unit/domain/test_comprovante_plan_pages.py:94-99`; `tests/unit/infrastructure/test_comprovante_assembler.py:103-106` | T118 `f061f13` (M41) |
| CMP-05 | Verified | `tests/unit/domain/test_comprovante_plan_sharing.py:51-65`; `test_generated_comprovante_acceptance.py:154` | none |
| CMP-06 | Verified | `tests/unit/domain/test_comprovante_plan_sharing.py:139-158`; `tests/integration/api/test_comprovante_layout_api.py:102-112` | none |
| CMP-07 | Verified | `tests/integration/api/test_generated_comprovante_acceptance.py:155-156`; `test_comprovante_plan_sharing.py:194-212` | none |
| CMP-08 | Verified | `tests/unit/infrastructure/test_source_images.py:35-71`, `:89-100`; `tests/integration/doc_usecases/test_request_refusals.py:131-137` | T123 `ade7afd` (EXIF orientation, A-D1) |
| CMP-09 | Verified | `tests/integration/doc_usecases/test_request_refusals.py:77-94`; `tests/unit/infrastructure/test_comprovante_assembler.py:195-208`; no request-time size estimate (A-D6, see "Decisions pending") | T119 `c0ce4f0` (wiring of the three limits) |
| CMP-10 | Verified | `tests/integration/doc_usecases/test_request_refusals.py:97-107`; `test_run_generation_failure.py:42-57` | T119 `c0ce4f0` (encrypted original, B41) |
| CMP-11 | Verified | `tests/integration/documents/test_comprovante_memory.py:58-62` (`peak_mb < 320`); measured 82 MB for 400 pages | none |
| CMP-12 | Verified | `tests/unit/infrastructure/test_source_images.py:120-133`, `:136-148` | T118 `f061f13` (M28, M29) |
| CMP-13 | Verified | `tests/integration/doc_usecases/test_request_refusals.py:110-137`; `test_source_images.py:74-86` | T119 `c0ce4f0` (B06) |

### ARR (Verifier A)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| ARR-01 | Verified | `tests/unit/domain/test_comprovante_layout_derivation.py:18-26`; `tests/integration/doc_usecases/test_comprovante_layout_read.py:34-52` | none |
| ARR-02 | Verified | `tests/integration/doc_usecases/test_comprovante_layout_save.py:64-79` | none |
| ARR-03 | Verified | `test_comprovante_layout_save.py:82-93`; `test_generated_comprovante_acceptance.py:179-188` | none |
| ARR-04 | Verified | `test_comprovante_layout_save.py:96-111`; `test_generated_comprovante_acceptance.py:200-201` | none |
| ARR-05 | Verified | `tests/unit/domain/test_comprovante_layout_validation.py:104-125`; `test_comprovante_layout_save.py:191-202` | none |
| ARR-06 | Verified | `tests/unit/domain/test_comprovante_layout_validation.py:45-51`; `tests/integration/api/test_comprovante_layout_api.py:135-144` (422 `PAGINA_FORA_DO_DOCUMENTO`), `:169-181` (404). The PARTIAL of A was a text mismatch (spec said 404 for a page outside the document; code and design say 422), not a functional failure | T122 `9470a83` aligned the spec text to the code and the design (A-D5) |
| ARR-07 | Verified | `tests/integration/api/test_comprovante_layout_api.py:115-132`; `test_comprovante_layout_save.py:204-226` | none |
| ARR-08 | Verified | `tests/unit/domain/test_comprovante_staleness.py:37-100`, `:131-170`; `test_comprovante_layout_api.py:185-198` | none |

### REL (Verifier B, `verification-b.md` "REL")

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| REL-01 | Verified | `tests/integration/doc_usecases/test_report_draft_read.py:44`, `:49` | none |
| REL-02 | Verified | `tests/unit/domain/test_report_draft_proposal.py:137`, `:163` | none |
| REL-03 | Verified | `tests/integration/doc_usecases/test_report_wording_request.py:44-48`; `test_generated_report_acceptance.py:131` | none |
| REL-04 | Verified | `tests/integration/doc_usecases/test_report_wording_run.py:62-71`; `tests/unit/domain/test_report_wording_apply.py:88` | T116 `834cfe1` (G10b, content word length) |
| REL-05 | Verified | `test_generated_report_acceptance.py:153-161`; `tests/unit/infrastructure/test_report_writer.py::test_the_call_gives_up_at_the_deadline_of_60_seconds` | T121 `846e5b6` (neutral `REDACAO_INDISPONIVEL` text, B-D5) |
| REL-06 | Verified | `test_report_wording_run.py:209-211`; `tests/unit/domain/test_report_wording_items.py::test_the_payload_never_carries_the_evidence_note_the_author_or_the_process` | T116 `834cfe1` (W09b, exact payload keys) |
| REL-07 | Verified | `test_report_wording_run.py:129-134`; `test_generated_report_acceptance.py:180-185` | T112 `f98d4a5` (B-D1, false 409 on Salvar) |
| REL-08 | Verified | `tests/integration/doc_usecases/test_report_draft_move.py:38-46`; `frontend/src/components/ReportDraftEditor.test.tsx:147` | none |
| REL-09 | Verified | `test_generated_report_acceptance.py:220-223` | none |
| REL-10 | Verified | `tests/integration/doc_usecases/test_request_refusals.py:59-63` | none |
| REL-11 | Verified | `tests/unit/domain/test_report_draft_proposal.py:114-115`; `test_report_draft_read.py:59` | none |
| REL-12 | PARTIAL, stays `Implementing` | `tests/unit/domain/test_report_grounding_vocabulary.py` (forbidden words, vocabulary limit, length); `backend/app/domain/rules/report_draft.py:116-132` (template text from the fields only). Probe: a lowercase invented institution and an inverted statement ("Não ministrou...") pass `check_wording` (B-D3) | none: the grounding limit is a documented design limit (AD-014, design Risks); user decision pending, no code changes until then |
| REL-13 | Verified | `test_report_wording_request.py:74-77`; `test_generated_report_acceptance.py:201-202` | none |
| REL-14 | Verified | `tests/integration/doc_usecases/test_recover_generations.py:66-80`; `tests/integration/documents/test_wording_job_repository.py:182-185`; real SIGKILL run | none |
| REL-15 | Verified | `test_report_wording_run.py:149-159`; `test_report_wording_request.py:80` | none |

### VER (Verifier A)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| VER-01 | Verified | `tests/integration/documents/test_generated_schema.py:202-248`, `:251-281`; `tests/integration/api/test_generated_versions_acceptance.py:98-118`; `psql` refused the 5 direct statements | none |
| VER-02 | Verified | `tests/unit/domain/test_generation_snapshot.py:44-90`, `:129-153` | none |
| VER-03 | Verified | `test_generated_versions_acceptance.py:82-95`; `tests/integration/doc_usecases/test_generated_versions.py:105-116` | none |
| VER-04 | Verified | `tests/integration/api/test_generated_documents_api.py:62-70`; `test_generated_schema.py:100-105` | none |
| VER-05 | Verified | `tests/integration/doc_usecases/test_run_generation_failure.py:74-84`, `:101-126` | T119 `c0ce4f0` (M37, checkpoint failure leaves no target) |
| VER-06 | Verified | `test_generated_documents_api.py:172-181`; `test_generated_versions.py:166-178` | none |
| VER-07 | Verified | `tests/integration/doc_usecases/test_request_generation.py:139-154`; `test_run_generation_table.py:110-127` | none |
| VER-08 | Verified | `tests/integration/doc_usecases/test_recover_generations.py:58-81`, `:84-98`, `:106-127`; real SIGKILL run | none |
| VER-09 | Verified | `test_generated_versions_acceptance.py:121-130`; `test_generated_versions.py:189` | none |

### UIG (Verifier B)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| UIG-01 | Verified | `frontend/src/pages/ProcessGenerated.test.tsx:65-75`; `frontend/src/components/GeneratedBlock.test.tsx:50-70` | T115 `a051f1c` (F18, history shows PRONTO only) |
| UIG-02 | Verified | `frontend/src/components/ReportDraftEditor.test.tsx:45`, `:63`, `:75`, `:198` | T112 `f98d4a5` (B-D1: click on Salvar saved twice and showed a false conflict) |
| UIG-03 | Verified | `frontend/src/components/ComprovanteLayoutEditor.test.tsx:109`, `:209`, `:298` | T115 `a051f1c` (F57) |
| UIG-04 | Verified | `frontend/src/components/GeneratedBlock.test.tsx:50-70`; `frontend/src/hooks/usePolling.test.ts:9-47` | none |
| UIG-05 | Verified | `frontend/src/components/GeneratedBlock.test.tsx:94`, `:110` | T121 `846e5b6` (alert wording, B-D5) |
| UIG-06 | Verified | `frontend/src/pages/ProcessGenerated.test.tsx:77`; `GeneratedBlock.test.tsx:144` | T115 `a051f1c` (F29) |
| UIG-07 | Verified | Real browser at 360 x 740: `scrollWidth == clientWidth == 360` in Etapa 5 (everything open) and Etapa 2 (`verification-b.md` real run, step 9); `frontend/src/styles.test.ts:90-135` is a static CSS test only (known debt in `STATE.md`) | none |
| UIG-08 | Verified | `frontend/src/components/ReportDraftEditor.test.tsx:214-248`, `:250` | none |
| UIG-09 | Verified | `frontend/src/components/ConcludeDialog.test.tsx:28`, `:46`, `:64-77`, `:92` | T120 `f6dd1f0` (success text sums the attempts, B-D7) |

### DEL (Verifier B)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| DEL-01 | Verified | `tests/integration/api/test_conclusion_api.py:111-116`; `tests/unit/domain/test_conclusion_check.py:31-32` | none |
| DEL-02 | Verified | `tests/integration/doc_usecases/test_conclude_process.py:152-159`; `test_conclusion_api.py:119` | none |
| DEL-03 | Verified | `test_conclusion_api.py:68-73`; `tests/integration/api/test_conclusion_acceptance.py:104-105` | none |
| DEL-04 | Verified | `test_conclusion_api.py:97-101`; `test_conclude_process.py:93-95`; test of the body without `confirmar` added | T113 `5e3374b` (R09, 422 `CONFIRMACAO_OBRIGATORIA`) |
| DEL-05 | Verified | `test_conclude_process.py:206`; `test_conclusion_acceptance.py:117` | none (B-D9, `raw_json` kept: decision pending) |
| DEL-06 | Verified | `test_conclude_process.py:207-212`; `test_conclusion_acceptance.py:118`, `:138-140` | none |
| DEL-07 | Verified | `test_conclude_process.py:203`, `:335-340` | none |
| DEL-08 | Verified | `test_conclude_process.py:283-292`; `test_conclusion_acceptance.py:183-193` | T120 `f6dd1f0` |
| DEL-09 | Verified | `test_conclude_process.py:308-310`, `:319-321`; `test_conclusion_api.py:166` | none |
| DEL-10 | Verified | `test_conclude_process.py:226`, `:233-238` | none |
| DEL-11 | Verified | `test_conclusion_acceptance.py:129-131`; `tests/unit/domain/test_comprovante_plan_limits.py::test_a_deleted_file_refuses_even_when_the_plan_does_not_use_that_document` | none |
| DEL-12 | Verified, spec-precision gap | `tests/integration/api/test_documents_deleted_api.py:67-70`, `:111-112`; `test_conclusion_acceptance.py:134-136`. The AC says "o arquivo ou uma página" but there is no page route, only `GET /documents/{id}` (pages empty) and the evidence link (410); wording decision pending | T114 `792193d` (Etapa 2 hides Excluir and Classificar on a document whose file was removed, B-D4) |
| DEL-13 | Verified | `test_conclusion_acceptance.py:154-157` | T115 `a051f1c` (F34, free text read-only) |
| DEL-14 | Verified | `tests/integration/api/test_process_updates_api.py:176-177`; `tests/integration/doc_usecases/test_process_status_change.py:39` | none |
| DEL-15 | Verified | `test_conclusion_api.py:142`, `:220`, `:226`, `:245`; `test_conclude_process.py:171`, `:179`, `:267` | none |

### ORD (Verifier B)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| ORD-01 | Verified, spec-precision gap closed in the text | `tests/integration/api/test_dossier_order_api.py:15`, `:21-23`; `frontend/src/components/DossierOrder.test.tsx:45`. B asked for the location of the list (Etapa 5 "Documentos gerados" in the design; the AC said "etapa Documentos", the name of Etapa 2) | T122 `9470a83` aligned the AC to Etapa 5; there was no new answer from the user (see "Inconsistencies found") |
| ORD-02 | Verified | `tests/integration/api/test_dossier_order_api.py:32`, `:47`; `frontend/src/components/DossierOrder.test.tsx:35` | none |

### FORA of `inteligencia-documental` (Verifier B)

| ID | Verdict | Evidence | Closed by |
| --- | --- | --- | --- |
| FORA-03 | Verified | `backend/tests/integration/doc_usecases/test_process_outside_interstice.py:148`, `:153-155`, `:158`, `:178`, `:209-215`, `:263-266`, `:282-284`; `tests/integration/api/test_documents_outside_interstice_api.py:201`; real run (edited activity rejected with audit, shared activity kept with one evidence) | none; T11 mutants T01-T11 all killed |
| FORA-07 | Verified | `test_process_outside_interstice.py:76-91`, `:93`, `:232-237`; real run (`PROCESSADO`, `DOCUMENTO_FORA_DO_INTERSTICIO`) | none; mutant T02 killed |

---

## Discrimination sensor

**Depth**: P0 full (data integrity, irreversible deletion, grounding of AI text, optimistic locking), more than 5 mutants per branch, manual injection in isolated copies. **Result**: 281 of 308 killed (91.2%); the 27 survivors are 8 equivalent and 19 real test gaps; the 19 gaps are closed. PASS.

| Verifier | Injected | Killed | Survived | Equivalent | Test gaps |
| --- | --- | --- | --- | --- | --- |
| A (backend: TAB 16/20, CMP 45/58, ARR 14/14, VER 41/43 killed) | 135 | 116 | 19 | 7 | 12 |
| B (backend 116, frontend 57) | 173 | 165 | 8 | 1 | 7 |
| Total | 308 | 281 | 27 | 8 | 19 |

Equivalent survivors, by the Verifiers' classification: A M10, M36, M39, M54, B29, M130, M131; B C14. Details in `verification-a.md` section 7 ("Sobreviventes classificados") and `verification-b.md` "Survivors".

Real gaps and their closure (every fix commit re-killed its mutant in an isolated copy of the tree, recorded in the commit body):

| Survivor | Requirement | Closed by | Re-kill |
| --- | --- | --- | --- |
| M50 total re-summed from the rows | TAB-04 | T117 `def97fa` | killed |
| M64 counter of vouchers | TAB-04 | T117 `def97fa` | killed (M64, M64b) |
| M96 last page quoted instead of the first | TAB-03 | T117 `def97fa` | killed |
| M28 raster JPEG quality, M29 one-axis crop | CMP-12 | T118 `f061f13` | killed (M28, M28b, M29, M29b, M29c) |
| M41 `p. N a N`, M43 origin page | CMP-04, CMP-02 | T118 `f061f13` | killed |
| B04, B05, B06 wiring of the three limits | CMP-09, CMP-13 | T119 `c0ce4f0` | killed (B04, B04b, B05, B06) |
| M37 target left after a checkpoint failure, B41 encrypted original | VER-05, CMP-10 | T119 `c0ce4f0` | killed |
| R09 `confirmar` default `True` | DEL-04 | T113 `5e3374b` | killed |
| F18, F29, F34, F57 | UIG-01, UIG-06, DEL-13, UIG-03 | T115 `a051f1c` | killed (F18, F29, F29b, F34, F57, F57b) |
| G10b content word length, W09b payload keys | REL-04, REL-06 | T116 `834cfe1` | killed (G10b, G10c, G10d, W09b) |

New behavior of the correction round also re-killed its own mutants: T123 (EXIF, 10 of 10), T124 (title cap, 5 of 5), T121 (alert wording, 5 of 5).

---

## Gate Check

- **Gate command**: `cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q && cd ../frontend && npm run lint && npm run build && REQUIRE_DIST=1 npm test -- --run`
- **Backend**: `ruff check .` clean; full `pytest -q` at the end of the correction round, clean copy of HEAD: 5048 passed (Verifier A before the round: 5013 passed at `4628f08`, 3 `maritalk_live` deselected, 17 min 54 s). Closure re-ran `ruff check .` on the working tree: clean.
- **Frontend** (clean copy of `969273e` in the scratchpad, `node_modules` linked, `scripts/` included): `npm run lint` clean; `npm run build` ok; `REQUIRE_DIST=1 npm test -- --run` 34 files, 374 tests passed (Verifier B had 366 on a tree that carried another session's uncommitted work; the round added the T112, T114, T115, T120, T121 tests).
- **Test count**: no test file deleted in the feature range (`git diff --diff-filter=D` over `backend/tests` and `frontend/src`: none); the baseline in `STATE.md` Handoff (3783 backend, 236 frontend) predates round 8 and this feature, so a delta per feature is not computed here.
- **Skipped**: 3 `maritalk_live` (need the real key, never run in the suite).
- **Failures**: none.

---

## Real runs (summary)

- **A**: Tabela, Relatório and Comprovante generated and downloaded; Tabela DOCX and PDF with 211,00 and the 7 subtotals read back; Comprovante of 20 pages with numbering equal to the independent calculation; original pages equal by pixel (maxdiff 0), including a rotated page and a JPEG with identical bytes; limits (401 pages = 422, 400 pages = PRONTO at 46 MB, PNG 4000x3100 = 422, output above 60 MB ended FALHOU without a file); memory peak 82 MB for 400 pages; versions 1 to 5 contiguous and byte-identical after changes; `psql` refused UPDATE and DELETE on finished versions; SIGKILL with `GERANDO` rows recovered as `INTERROMPIDA` with two orphan files removed.
- **B**: Etapa 5 at 1280 px and 360 px (no horizontal scroll); report draft with a real 409 conflict; wording against a local fake provider in four modes; arrangement editor; conclusion with a forced partial failure, retry, 410, read-only draft and arrangement, Tabela and Relatório regenerated as v2 with the older versions byte-identical; FORA-03 reprocessing with audit; SIGKILL of the backend during a wording job recovered as `INTERROMPIDA`.

---

## Defects found and resolution

Severity scale of the reports. No Blocker or High in either report.

| ID | Sev. | Finding | Resolution |
| --- | --- | --- | --- |
| A-D1 | Medium | EXIF orientation of a JPEG ignored (phone photo entered lying down) | Fixed: T123 `ade7afd` (orientation 3, 6, 8 turned in the page, bytes untouched; mirrored values stay as stored) |
| A-D2 | Medium | Table total not pinned against a limited subtotal (M50) | Fixed: T117 `def97fa` (test) |
| A-D3 | Medium | Cited page of a multi-page activity not pinned (M96); spec silent | Fixed: T117 `def97fa` pins the first page; recorded in design Risks |
| A-D4 | Low | Item title cut with an ellipsis in the Comprovante table of contents | Accepted limitation, design Risks (T125 `969273e`); CMP-01 stays `Implementing` |
| A-D5 | Low | Page outside the document answers 422, spec said 404 | Fixed in the spec: T122 `9470a83` (ARR-06) |
| A-D6 | Low | No request-time estimate of the 60 MB limit; the dossier of 400 pages of 224 KB (88 to 92 MB) is refused only at the end of the assembly | **Pending user decision**: implement the estimate or accept and align the design; not in T125, no code changed |
| A-D7 | Low | An activity can start on one contents page and end on the next | Accepted limitation, design Risks (`969273e`) |
| A-D8 | Low | Glyphs the font lacks (CJK, emoji) come out empty | Accepted limitation, design Risks (`969273e`) |
| A-D9 | Low | Title of about 5 000 characters broke the Tabela PDF (`LayoutError`, FALHOU `ERRO_INTERNO`) | Fixed: T124 `e4fb09fb` (deterministic cap of 400 characters in PDF, DOCX and alerts) |
| A-D10 | Low | `Com comprovante: 38` counts the engine note while 30 rows say "sem comprovante" | Accepted limitation (TAB-04 asks for the engine counts), design Risks (`969273e`) |
| A-D11 | Low | PIT hours table splits across pages in the DOCX | Accepted limitation, design Risks (`969273e`) |
| B-D1 | Medium | Clicking Salvar saved twice and showed a false 409 | Fixed: T112 `f98d4a5` |
| B-D2 | Medium | No test of a conclusion request without `confirmar` (R09) | Fixed: T113 `5e3374b` |
| B-D3 | Medium | Grounding check passes a lowercase invented proper noun with up to 3 new words and an inverted statement (REL-12) | **Pending user decision**: REL-12 stays `Implementing` (PARTIAL); design Risks row records the options (lower `max_new_words`, treat negations as new vocabulary, or keep human review and the "Redigido pela IA" badge); no code until decided |
| B-D4 | Low | Etapa 2 offered Excluir and Classificar on purged documents | Fixed: T114 `792193d` |
| B-D5 | Low | Repeated and misleading alert texts | Fixed: T121 `846e5b6` |
| B-D6 | Low | Test gaps F18, F29, F34, F57, G10b, W09b | Fixed: T115 `a051f1c`, T116 `834cfe1` |
| B-D7 | Low | Conclusion success text counted only the last attempt | Fixed: T120 `f6dd1f0` |
| B-D8 | Low | ORD-01 location wording | Fixed in the spec: T122 `9470a83` |
| B-D9 | Low | `extraction_runs.raw_json` keeps the extracted professor name and titles after the purge | **Pending user decision** (AD-015, spec assumption `Confirmed = n`); design Risks row; DEL-05 stays `Verified` on its AC (original files, page texts and excerpts) |
| B-D10 | Low | The 60 s deadline is checked per operation, not over a slowly dripping response | Accepted limitation, design Risks (`969273e`) |
| B-D11 | Low | A concurrent save of the same activity can end a reprocessing as FALHOU (`StaleVersion`) | Accepted limitation, design Risks (`969273e`); repeating the reprocessing resolves it |
| B-D12 | Low | Commit `4e2727d` says AD-018, the decision is AD-019 | No change (history is not rewritten); design Risks (`969273e`) |
| B-D13 | Info | The report text of an edited entry carries only the user's text, no title | By design (REL-07), no action |

Findings the correction round did not take: B reported cosmetic items in the real run, the Etapa 2 table headers "Tamanho" and "Confiança" breaking mid-word at 1280 px and two "Fechar" buttons in the success state of the conclusion dialog; neither has a task. A's observations: the worker thread makes a generation wait behind an OCR in progress (about 25 s once; already a design risk), and `can_transition` of `domain/entities/generated.py` is unused by production code (the rule holds through `WHERE state = 'GERANDO'` and the trigger).

---

## Spec-precision gaps

| Gap | Where | Status |
| --- | --- | --- |
| DEL-12 says "o arquivo ou uma página"; there is no page route | `verification-b.md` | Open: wording decision pending |
| ORD-01 location ("etapa Documentos" is Etapa 2) | B-D8 | Closed in the text (T122) |
| ARR-06 404 versus 422 for a page outside the document | A-D5 | Closed in the text (T122) |
| TAB-03 does not say which page a multi-page activity quotes | A-D3 | Pinned as the first page (T117), spec text unchanged |
| CMP-01 "título do item com a nomenclatura da tabela" versus the cut title in the contents | A-D4 | Open: accepted limitation, spec text not aligned |
| CMP-08 silent on EXIF orientation | A-D1 | Behavior now defined by T123 and the design Risks; spec AC unchanged |
| Assumption "a tela avisa quando a versão mais recente de um tipo está desatualizada" has no AC | B | Not graded; the blocks show `NUMERACAO_DIVERGENTE` and `RASCUNHO_DESATUALIZADO` alerts |

---

## Residual risks

- **DOCX not opened in Word**: opened only with python-docx (XML checks: `tblHeader`, `tblGrid`, `tblLayout fixed`) and LibreOffice (headless, to render); AD-011 already accepts it.
- **T110 not run**: "adiada, aguarda autorização do usuário". It counts, with a local script outside the repository, the pages of the real corpus that have rotation and a CropBox smaller than the MediaBox, to decide whether the rasterized fallback (`PAGINA_RASTERIZADA`, CMP-12) is rare enough. It needs the user's explicit authorization to read `Documentos/`; until then the effect of the fallback on real documents is unmeasured and the Comprovante was verified on synthetic documents only.
- **REL-12**: a plausible but false qualitative sentence made of words already allowed passes the grounding check; the human review and the "Redigido pela IA" badge are the only barrier (AD-014).
- **Irreversible deletion without backup in the VM**: the conclusion dialog warns; `raw_json` keeps the extracted structured data after the purge (B-D9).
- **Memory margin**: 82 MB peak measured for 400 pages in the E2E; the 60 MB output limit can refuse a heavy scanned dossier only at the end of the assembly (A-D6).
- **No real-user walkthrough**: the screens were driven by a script in Chrome; no person has used them.
- **Not deployed**: nothing of this feature runs on the VM (still `b58e276`).

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code, surgical changes, no scope creep | Verifier B: matches project patterns (use cases take `uow_factory`, access through `_readable/_editable`, audit with identifiers only, `Gone` and `GenerationRefused` mapped in `presentation/errors.py`); domain rules pure |
| Spec-anchored outcome check (asserted values match spec) | Yes, with the gaps listed above |
| Per-layer coverage expectation | Domain 1:1 to ACs; routes with happy, edge and error paths; the weak spots found by the sensor are closed |
| Every test maps to a spec requirement | Yes (B spot check of the Etapa 5 tests) |
| Documented guidelines followed | `CLAUDE.md`: no justification field in the conclusion dialog, synthetic data only, key only in the backend |
| Weakened assertions | One, authorized by the round's brief: T121 changed the assertion of the old `REDACAO_INDISPONIVEL` text in `ReportDraftEditor.test.tsx` because it pinned the misleading sentence |

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| TAB-01..08 | Implementing | Verified |
| CMP-01 | Implementing | Implementing (PARTIAL, A-D4 accepted, spec text pending) |
| CMP-02..13 | Implementing | Verified |
| ARR-01..08 | Implementing | Verified (ARR-06 after T122) |
| REL-01..11, REL-13..15 | Implementing | Verified |
| REL-12 | Implementing | Implementing (PARTIAL, B-D3, user decision pending) |
| VER-01..09 | Implementing | Verified |
| UIG-01..09 | Implementing / In Tasks | Verified |
| DEL-01..15 | Implementing | Verified |
| ORD-01, ORD-02 | Implementing | Verified |
| FORA-03 (`inteligencia-documental`) | Implementing | Verified |
| FORA-07 (`inteligencia-documental`) | Verified | Verified (evidence added) |

---

## Summary

**Overall**: PASS. Ready for the user's decisions and, after the user's go-ahead, deployment.

**Spec-anchored check**: 77 of 79 requirements match the spec outcome; 2 differ in part (CMP-01 wording, REL-12 grounding limit).
**Sensor**: 281 of 308 killed; 8 equivalent; 19 gaps closed.
**Gate**: backend `ruff` clean and 5048 passed; frontend lint clean, build ok, 374 passed.

**What works**: the three documents are generated from the engine result with versions that are immutable, downloadable byte for byte and audited; the Comprovante keeps original pages intact with a shared numbering plan and the stated limits; the report draft, wording in the background with the template fallback, conclusion with irreversible deletion, 410 states, read-only states and the Etapa 5 screens behave as specified in a real database and a real browser.

**Issues open**: REL-12 grounding limit; CMP-01 contents title; raw_json retention; no request-time estimate of the 60 MB limit; DEL-12 wording.

**Next steps**: the user decides the points in `STATE.md` Handoff; T110 runs only with the user's authorization; deployment of `feat/inteligencia-documental` needs the user's explicit go-ahead (migrations `0006` then `0007`, see `docs/deploy/vm.md`).
