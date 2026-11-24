# Documentos Gerados - Verification B (report, deletion, screens, FORA-03)

**Date**: 2026-11-18
**Spec**: `.specs/features/documentos-gerados/spec.md` (REL-01..15, DEL-01..15, ORD-01..02, UIG-01..09) and `.specs/features/inteligencia-documental/spec.md` (FORA-03, FORA-07, as amended by AD-019 / T146)
**Code under test**: HEAD `4628f08` on `feat/inteligencia-documental` (T146 = `4e2727d`); the working tree was never changed (porcelain identical before and after; `requeriment.txt`, `test/` and the uncommitted `Dashboard*`, `types.ts`, `ProcessDialogs.tsx` were not touched)
**Verifier**: independent sub-agent (author != verifier). Scope A (TAB, CMP, ARR, VER) is not covered here.

## Verdict

**PASS, with 3 Medium findings and 7 test-gap fix tasks recommended before delivery.** No Blocker or High defect.
Every acceptance criterion of the scope has a passing, executed assertion and was also exercised in a real run (real PostgreSQL, real backend, built-from-source frontend driven by headless Chrome, synthetic data only). Two criteria carry caveats: REL-12 (PARTIAL: the deterministic check has two known bypasses) and ORD-01 (PASS with a spec-precision gap about where the list is shown).

| Item | Result |
|---|---|
| Requirements in scope | 41 (REL 15, DEL 15, ORD 2, UIG 9) + FORA-03 and FORA-07 = 43: 42 PASS (DEL-04, DEL-12 and ORD-01 with a test gap or a spec-precision gap noted), 1 PARTIAL (REL-12), 0 FAIL |
| Discrimination sensor | 173 mutants (116 backend, 57 frontend); 165 killed, 8 survived (1 equivalent, 7 test gaps) |
| Targeted gate (backend) | 392 unit (report, wording, conclusion, config, MariTalk) + 185 integration (wording, draft, conclusion, purge, worker, dossier) passed; whole `tests/unit` (3588 tests, minus `test_process_corpus.py` that needs the real corpus dir) passed; `ruff check .` clean |
| Targeted gate (frontend) | `vitest run`: 34 files, 366 tests passed (the tree contains another author's uncommitted Dashboard work); the 10 Etapa 5 files: 136 passed |
| Full backend `pytest -q` | Started and stopped by me after ~6 min (integration suite is slow on this machine); not claimed. Scope A or the orchestrator gate covers it |
| `npm run lint` / `npm run build` | Not run by me |
| Real run | Done: API + Chrome (Playwright over `google-chrome`, desktop 1280 px and 360 px) |

## Spec-anchored acceptance criteria

Evidence format: `file:line` of the assertion actually opened and read, plus the real-run observation (RR). "M:" lists mutant IDs that kill the behaviour (table below).

### REL (Relatório de Atividades)

| ID | Spec-defined outcome | Evidence (test assertion; real run) | Result |
|---|---|---|---|
| REL-01 | First open creates sections 1.1, 1.2, 1.3, 2..6 with activities distributed by the group map; read does not save | `backend/tests/integration/doc_usecases/test_report_draft_read.py:44` `assert (view.saved, view.draft.version) == (False, 0)`, `:45` `entries_by_section(...) == {...}`, `:49` `stored_draft(world) is None`, `:50` section keys == `ALL_SECTIONS`; `tests/unit/domain/test_report_draft_proposal.py:43` (each group to its section). RR: draft opened with the 8 sections, group III and VII entries in section 6. M: D01, D04, R13 | PASS |
| REL-02 | 1.1/1.2 by academic period; 1.3 by modality, ended before ongoing | `test_report_draft_proposal.py:137` `keys_of(draft, "1.1") == [first_year, early_a, early_b, late]`, `:163` `keys_of(draft, "1.3") == [ended_a, ongoing_a, ended_b, ongoing_b]`. Note (design, not a defect): the course appears only when it is in the title or description | PASS |
| REL-03 | Request answers 202 with GERANDO, MariTalk called in background with only the activity fields | `test_report_wording_request.py:44` `(job.section_key, job.state) == ("1.3", GERANDO)`, `:46` `started_at, finished_at, error_code == (None, None, None)`, `:48` `stored_draft(world).version == 1`; `test_generated_report_acceptance.py:131`. RR: POST `.../wording` answered 202 at once; the UI showed "Gerando a redação…" and the PRONTO state 3-4 s later. M: R05, U06 | PASS |
| REL-04 | Number/date/name not in the fields: text replaced by the template text with `REDACAO_REJEITADA` | `test_report_wording_run.py:62` `(good.text, good.source) == (FAITHFUL, IA)`, `:63-64` bad entry is `MODELO`, `"40 horas" not in bad.text`, `:66` warning code/message, `:71` job warning `[REDACAO_REJEITADA]`; `tests/unit/domain/test_report_grounding_numbers.py`, `test_report_grounding_vocabulary.py`, `test_report_wording_apply.py:88`. RR (fake provider, mode `invent`: "999 participantes ... resultado excelente"): entry stayed template text, section warning "A redação da IA trazia dado que não está na atividade e foi recusada ... (número que não está na atividade, palavra proibida)"; mode `faithful`: entry became "Redigido pela IA". Probe of `check_wording` with 16 hand-made wordings: invented number, percentage, spelled number ("cem alunos"), ordinal, wrong date, capitalized place, other person, "objetivo", praise: all refused with the right reason; faithful and "trinta horas" accepted. M: G01-G16, W04, W05 (G10b survived, see D6) | PASS |
| REL-05 | MariTalk unavailable / error / over 60 s: template text, `REDACAO_INDISPONIVEL`, job PRONTO | `test_generated_report_acceptance.py:153-161` (job PRONTO, warning `REDACAO_INDISPONIVEL`, every entry `MODELO`, draft GET still 200); `test_report_wording_run.py:108-109`; `tests/unit/infrastructure/test_report_writer.py::test_the_call_gives_up_at_the_deadline_of_60_seconds`, `::test_a_provider_error_is_redacao_indisponivel_with_no_repetition`. RR: (a) key unset, (b) provider HTTP 500, (c) provider silent past the deadline (`WORDING_TIMEOUT_SECONDS=8`): all three ended PRONTO with the template text and the warning "A IA não respondeu a tempo: ficou o texto-modelo"; no 5xx on the draft. M: A01-A06, U01, W02, W03 | PASS |
| REL-06 | Never send page text or personal data | `test_report_wording_run.py:209-211` `"123.456.789-09" not in text`, `"Anotação interna" not in text`, professor name/SIAPE not in text; `test_report_wording_items.py::test_the_payload_never_carries_the_evidence_note_the_author_or_the_process`. RR: the fake provider logged the real request bodies: only `id, tipo, titulo, datas, carga_horaria, quantidade, descricao`. M: W06-W09, W07 | PASS |
| REL-07 | Edited text is final; AI never rewrites it | `test_report_wording_run.py:129` `stored.version == 2  # the edit moved it once; the wording did not`, `:130-134`; `test_generated_report_acceptance.py:185` only the non-edited activity was sent in the second call, `:180`. RR: user-edited entries kept "Editado" through three wording runs. M: W01, W06, U02, U03, U10, D01, D02 | PASS |
| REL-08 | Move activity to another section and keep it | `test_report_draft_move.py:38` `entries_by_section(stored_draft) == {"1.3": [stays], "5": [moved]}`, `:40`, `:46` generation uses it; `ReportDraftEditor.test.tsx:147`. RR: not walked in the browser (API/component only). M: D02, R12 | PASS |
| REL-09 | DOCX and PDF with institutional header, identification, all sections, stored text | `test_generated_report_acceptance.py:220-223` edited text and template text present, invented text absent, in both extensions. RR: downloaded v1 DOCX and PDF: header "Serviço Público Federal / Universidade Federal do Pará / Faculdade ...", name, "Professor C, nível 4", interstice, "ATIVIDADES DESENVOLVIDAS", sections with the stored texts | PASS |
| REL-10 | Validated activity without description and without title: refuse with `ATIVIDADE_SEM_DESCRICAO` naming it | `test_request_refusals.py:59` `error.code == ATIVIDADE_SEM_DESCRICAO`, `:60` `str(blank.id) in error.message`; `:63` title alone or description alone is enough. M: R07 | PASS |
| REL-11 | Empty section omitted from the document and listed as empty | `test_report_draft_proposal.py:114` `empty_sections(draft) == ("1.2","1.3","3","4","5","6")`, `:115` `document_sections == ["1.1","2"]`; `test_report_draft_read.py:59`. RR: UI "Seção vazia: não aparece no documento."; the PDF has no 1.1, 1.2, 5. M: D03 | PASS |
| REL-12 | Never add objectives, results, methodology or any fact not in the fields or the user's text | `test_report_grounding_vocabulary.py` (forbidden words, vocabulary limit, length); template text built only from `activity_fields` (`backend/app/domain/rules/report_draft.py:116-132`). **Two bypasses of the check found by probe** (`check_wording` on a synthetic activity): a lowercase invented institution is accepted ("... na universidade federal do amazonas": accepted, no reason), and an inverted statement is accepted ("Não ministrou o curso ... em formato remoto"). Both use only words already in the fields or at most 3 new content words (`max_new_words = 3`). The design records this limit ("uma afirmação qualitativa feita só de palavras já permitidas passaria", design.md, Risks) and relies on human review and the "IA" badge | PARTIAL (known design limit, see D3) |
| REL-13 | Second request for a GERANDO section: 409 `REDACAO_EM_ANDAMENTO`, other sections editable | `test_report_wording_request.py:74` `error.value.code == REDACAO_EM_ANDAMENTO`, `:76-77`; `test_generated_report_acceptance.py:201` `(second.status_code, second.json()["code"]) == (409, "REDACAO_EM_ANDAMENTO")`, `:202`. RR: API 202, then 409 with that code, other section 202; in the UI the running section's button is disabled and the others stay enabled. M: R04, R05 | PASS |
| REL-14 | Restart with a GERANDO job: FALHOU `INTERROMPIDA`, draft unchanged | `test_recover_generations.py:66-80` started wording job to `(FALHOU, INTERROMPIDA)`, waiting one stays GERANDO and is claimable; `test_wording_job_repository.py:182-185`. RR: SIGKILL of the backend with a section-4 job running; after restart `GET .../wording` showed `('4','FALHOU','INTERROMPIDA')` and the log `recovered_wordings=1`. M: R01, R02, R03 | PASS |
| REL-15 | Internal error: FALHOU `ERRO_INTERNO`, texts unchanged, new request allowed | `test_report_wording_run.py:149` `(done.state, done.error_code) == (FALHOU, ERRO_INTERNO)`, `:150` `stored_draft == before`, `:156,158,159` no text in audit/logs; `test_report_wording_request.py:80` section can be asked again. M: U05, R11 | PASS |

### DEL (conclusion and deletion of the input documents)

| ID | Spec-defined outcome | Evidence | Result |
|---|---|---|---|
| DEL-01 | Missing PRONTO version: 422 `ARTEFATOS_PENDENTES` listing the kinds, nothing deleted | `test_conclusion_api.py:111-116` 422, code, `"RELATORIO"` and `"COMPROVANTE"` in the message and `"TABELA"` not, one file still stored; `tests/unit/domain/test_conclusion_check.py:31-32` code and order TABELA, RELATORIO, COMPROVANTE; `test_conclude_process.py:123` (a FALHOU version does not count). M: C02, C04, C17 | PASS |
| DEL-02 | Generation, wording or document processing in progress: 409 `OPERACAO_EM_ANDAMENTO`, nothing deleted | `test_conclude_process.py:158-159` (parametrized over the three operations, line 152); `test_conclusion_api.py:119`. RR: not reproduced in the browser (the process was RASCUNHO, so the transition check answered first). M: C01, C05, P12, P13, P14 | PASS |
| DEL-03 | Preview: files, bytes, and which kinds are PRONTO | `test_conclusion_api.py:68-73`; `test_conclusion_acceptance.py:104-105` `(preview["files"], preview["bytes"]) == (3, size_before)`; RR: dialog "3 arquivos, 6 KB serão excluídos de forma irreversível" and DB sizes 1576 + 2570 + 2137 = 6283 B. M: C11, C12, C18 | PASS |
| DEL-04 | No explicit confirmation: 422 `CONFIRMACAO_OBRIGATORIA`, nothing deleted | `test_conclusion_api.py:97-101` (field `geracao`, code, one file still stored, status not CONCLUIDO); `test_conclude_process.py:93-95`. RR: the button is off until the checkbox is ticked. **Gap**: no test posts a body without `confirmar` (mutant R09: schema default `False` -> `True` survived, see D2) | PASS (test gap) |
| DEL-05 | Delete original files, extracted page texts and evidence excerpts of every document | `test_conclude_process.py:206` `(after.file_exists, after.pages, after.links) == (False, [], [(1, "")])`; `test_conclusion_acceptance.py:117` no file left under `uploads`. RR (DB after conclusion): `uploads/{process}` empty, `document_pages` 0 rows, `activity_evidences` 8 rows with 0 non-empty excerpts. M: P01-P05, P09, P10 | PASS |
| DEL-06 | Keep metadata (marked), links, activities, all generated versions | `test_conclude_process.py:207` `file_deleted_at is not None`, `:209-212` generated file bytes identical and 6 PRONTO versions; `test_conclusion_acceptance.py:118,138-140`. RR: documents kept name, `page_count`, `size_bytes`, `sha256` with `file_deleted_at` set; the 5 generated files untouched and every version's SHA-256 still equals the stored one | PASS |
| DEL-07 | Status CONCLUIDO only after all files are gone, rechecked in the same transaction | `test_conclude_process.py:203` `(process.status, process.version) == (CONCLUIDO, EM_ANDAMENTO_VERSION + 1)`, `:335-340` a document uploaded during the conclusion stops the transition (`EXCLUSAO_PARCIAL`) and the repeat closes it. M: C08, C09, C10 (C14 equivalent) | PASS |
| DEL-08 | A removal fails: stays EM_ANDAMENTO, `EXCLUSAO_PARCIAL` with counts, repeatable | `test_conclude_process.py:283-292`; `test_conclusion_acceptance.py:183-193` (`EM_ANDAMENTO`, removed/pending, second try CONCLUIDO, bytes add up). RR: made one stored file undeletable (a directory in its place): dialog "Nem todos os arquivos foram excluídos: tente de novo", "2 arquivos excluídos, 1 arquivo ainda por excluir", button "Tentar de novo"; process stayed EM_ANDAMENTO; after clearing the blocker the retry concluded. M: C09, C10, P02, P06 | PASS |
| DEL-09 | Repeat: missing file counts as removed, only what is left is done, CONCLUIDO answers 200 and changes nothing | `test_conclude_process.py:308-310`, `:319-321` (`== ConclusionResult(CONCLUIDO, 0, 0, 0)`, process and audit count unchanged); `test_conclusion_api.py:166`. RR: repeat on the concluded process: 200 `{arquivos_removidos:0, ..., bytes_liberados:0, alertas:[]}`. M: C06, P07 | PASS |
| DEL-10 | Audit with counts and bytes, no file name, on success and on partial | `test_conclude_process.py:226` (`operation PURGE`, `files_removed`, `files_pending`, `bytes_removed`, `bytes_pending`), `:233-238` status event, `not any(name in dumped ...)`. RR: `audit_logs` rows `{files_removed 2, files_pending 1, bytes_removed 4146, bytes_pending 2137}` then `{1, 0, 2137, 0}`. M: C13, C15, C16 | PASS |
| DEL-11 | Comprovante refused with 422 `ORIGINAIS_EXCLUIDOS` while a document is marked deleted | `test_conclusion_acceptance.py:129-131` `(detail["field"], detail["code"]) == ("geracao", "ORIGINAIS_EXCLUIDOS")`; `tests/unit/domain/test_comprovante_plan_limits.py::test_a_deleted_file_refuses_even_when_the_plan_does_not_use_that_document`. RR: 422 with that body; UI button off with "Os documentos de entrada foram excluídos: o Comprovante não pode mais ser gerado." M: S06 | PASS |
| DEL-12 | File or page of a deleted document: 410 `ARQUIVO_EXCLUIDO` | `test_documents_deleted_api.py:67-70` (410, field `arquivo`, code, message), `:111-112` replace/reprocess/link are 410; `test_conclusion_acceptance.py:134-136`. RR: `GET /file`, `GET /file?inline=true` and `POST /reprocess` of the 3 purged documents: 410 with the code. Spec-precision gap: there is no standalone page route; the page text is reached only through `GET /documents/{id}` (200 with `pages: []`) and the evidence link (410) | PASS (spec-precision gap) |
| DEL-13 | CONCLUIDO: Tabela and Relatório generate again, every version downloads | `test_conclusion_acceptance.py:154-157` v2 of both, `downloaded(client, versions) == before` byte for byte. RR: after the conclusion `POST generated-documents` TABELA and RELATORIO answered 202 and reached PRONTO v2; the SHA-256 of every earlier version equalled the stored hash and size | PASS |
| DEL-14 | Generic status route with CONCLUIDO: 409 `CONCLUSAO_EXIGE_EXCLUSAO` | `test_process_updates_api.py:176-177` (409 and code; process stays `EM_ANDAMENTO` v2), `test_process_status_change.py:39`. RR: 409 with the code. M: S05 | PASS |
| DEL-15 | Role, 404 outside access, 409 stale `expected_version`, only EM_ANDAMENTO | `test_conclusion_api.py:142` 409 `VERSAO_DESATUALIZADA`, `:220,226` 404 on both routes, `:245` RASCUNHO is 409; `test_conclude_process.py:171` (stale version is `StaleVersion`), `:179` (RASCUNHO and ARQUIVADO are refused); `:267` owner docente and unit secretaria may conclude. M: C07, C18, R09 | PASS |

### ORD (dossier order)

| ID | Spec-defined outcome | Evidence | Result |
|---|---|---|---|
| ORD-01 | List ordered from the model, with the generated documents marked, shown in the "Documentos" step | `test_dossier_order_api.py:15,21-23` first three titles, `[RELATORIO, TABELA, COMPROVANTE]` marked, item keys `{order,title,generated_by}`; `DossierOrder.test.tsx:45`. RR: 7 items in the file order with the three "Gerado pelo sistema" badges. Spec-precision gap: the list is on the Etapa 5 page ("Documentos gerados"), while the story says "na etapa Documentos", which is the name of Etapa 2 (the design places it in Etapa 5). Could not compare with the model PDF (`Modelos/` is off limits). M: O01, O03, F50, F51 | PASS (spec-precision gap, D8) |
| ORD-02 | List read from a versioned config file, never typed in the screen | `test_dossier_order_api.py:32,47` route re-reads the file at every call (second content served after the file changed); `backend/app/infrastructure/documents/config/dossier_order.json`; `DossierOrder.tsx` renders only API data (`DossierOrder.test.tsx:35`). M: O02 (killed by `test_report_config_loader.py`) | PASS |

### UIG (Etapa 5 screens)

| ID | Spec-defined outcome | Evidence | Result |
|---|---|---|---|
| UIG-01 | Three blocks with Gerar, state and history with download per format | `ProcessGenerated.test.tsx:65-75` (3 blocks, dossier), `GeneratedBlock.test.tsx:50-70` (links `/api/generated-documents/g1/files/docx`, `DOCX (40 KB)`). RR: all three generated from the UI; histories "Versão 1 · 18/11/2026 · DOCX (38 KB) · PDF (46 KB)"; downloads 200 with correct content type and `attachment; filename*=UTF-8''Tabela_de_Pontuacao_2022-2024_v1.pdf`. M: F15-F18, F23, F24 | PASS |
| UIG-02 | Report block: sections, editable text, section warnings, request-wording button | `ReportDraftEditor.test.tsx:45,63,75,198`. RR: edit, save, reload persisted. **Defect D1**: clicking the per-entry "Salvar" button sends two PUTs and shows a false conflict alert (below) | PASS (D1 open) |
| UIG-03 | Comprovante block: arrangement with add/remove/reorder pages and repeat with justification | `ComprovanteLayoutEditor.test.tsx:109,209,298`. RR: removed a page, moved an activity down, added a page of another document (page 9 rejected with "A página indicada não existe no documento."), repeated a page (empty justification refused, then accepted), saved, reloaded: all persisted and the numbering changed (p. 7, 9, 11) | PASS |
| UIG-04 | While generating, show the state and poll every 3 s until PRONTO/FALHOU | `GeneratedBlock.test.tsx:50-70` (`lists()` 1 -> 2 after 3000 ms, stays 2 after 9000 ms more), `usePolling.test.ts:9-47`. RR: after the three generations reached PRONTO there were 0 further list requests in 7 s. M: F12-F16 | PASS |
| UIG-05 | Alerts of a finished generation listed in Portuguese | `GeneratedBlock.test.tsx:110` and `:94` (FALHOU reason). RR: "Página repetida com justificativa", "Atividade sem comprovante anexado", "Há atividades que ficaram fora do documento: ..." and "A numeração do Comprovante mudou ..." shown. Cosmetic duplication of the label in the text (D5) | PASS |
| UIG-06 | Warning before the Generate button with how many activities stay out | `ProcessGenerated.test.tsx:77` (pending and unclassified count, rejected does not), `GeneratedBlock.test.tsx:144`. RR: "1 atividade fica de fora" on the 3 blocks (the activity without group/item). M: F19, F28 (F29 survived, D6) | PASS |
| UIG-07 | No page horizontal scroll at 360 px | `frontend/src/styles.test.ts:90-135` is a static CSS test only (known debt). RR (real browser, 360 x 740): `scrollWidth == clientWidth == 360` with the draft and the arrangement open, in Etapa 5 and in Etapa 2; no element extends past the viewport | PASS |
| UIG-08 | Section GERANDO: show state, poll every 3 s, other sections editable, reload the section text when done | `ReportDraftEditor.test.tsx:214-248` (poll count 1 -> 2 on 3 s, text replaced on PRONTO, polling stops after, other section's unsaved typing kept), `:250` other sections enabled. RR: at +3 s the section showed the new text and badge; 0 further wording requests afterwards. M: F36, F39-F41, F44 | PASS |
| UIG-09 | Conclusion confirmation: irreversible notice, files and space, missing documents, send only after explicit confirmation | `ConcludeDialog.test.tsx:28,46,64-77` (button off until the checkbox, body `{expected_version: 5, confirmar: true}`), `:92` partial. RR: dialog text, no justification field (`inputs: [checkbox:conclude-confirm]`), button disabled before the checkbox. M: F01-F11 | PASS |

### FORA (inteligencia-documental, T146)

| ID | Spec-defined outcome | Evidence | Result |
|---|---|---|---|
| FORA-03 | Reprocessing that puts a document outside the interstice rejects, with audit, the activities linked only to it (also edited or validated); one with evidence from another document stays, without the outside evidence; none enters Etapas 3-5 | `backend/tests/integration/doc_usecases/test_process_outside_interstice.py:148` validated -> `REJEITADA`, `:153-155` audit `STATUS VALIDADA->REJEITADA`, justification `DOCUMENTO_FORA_DO_INTERSTICIO`, `user_id is None`; `:158` edited one rejected too; `:178` other documents' and manual activities untouched; `:209-215` shared activity stays `VALIDADA`, outside evidence removed, kept evidence intact, unlink audited; `:263-266` score 0, `NAO_PONTUADA`, `REJEITADA`; `:282-284` generation inputs empty, `excluded == {"rejeitadas": 1}`; `tests/integration/api/test_documents_outside_interstice_api.py:201`. RR: activity X (user-edited, v2, only on the 2019 document) -> REJEITADA; activity Y (same document + another) stayed VALIDADA with a single evidence (the other document); `audit_logs`: `activity STATUS` and `activity_evidence UPDATE UNLINK`, both with `DOCUMENTO_FORA_DO_INTERSTICIO` and no user; Etapa 2 shows the banner "Data do documento 12/03/2019, fora do interstício (23/11/2022 a 23/11/2024): não será processado nas próximas etapas" and "1 fora do interstício" in the summary; the purge counted the outside document too. M: T01-T11 all killed | PASS (propose `Verified`) |
| FORA-07 | Reprocessing re-evaluates the rule with the process interstice | `test_process_outside_interstice.py:76-91` (widen: alert goes, activity created), `:232-237` second reprocess with a wider interstice creates the activity and keeps the rejected one (no duplicate); `:93` narrowing. RR: reprocess of the 2019 document returned `PROCESSADO`, `status_code DOCUMENTO_FORA_DO_INTERSTICIO`. M: T02 | PASS |

## Discrimination sensor

Method: isolated copies of `git archive HEAD` in the scratchpad (4 backend copies, 2 frontend copies, each against its own PostgreSQL database or `vitest`); one mutation at a time applied by exact string replacement (each `old` text had to occur once), targeted tests run with `-x`, file restored from the base copy. Result code 1 = killed, 0 = survived. The real tree was never mutated. Each mutant was run first with a targeted test group; survivors were re-run against a wider group (full `tests/unit`, full frontend `src`, or the missed test files), which reclassified five of them as killed (S06, U04, C13, O02, F55) and showed that two of my groups were too narrow.

**Result: 165 / 173 killed (95.4 %), 8 survived.** Sensor depth: P0-full (data integrity: irreversible deletion, grounding of AI text, optimistic locking), more than 5 mutants per branch.

Survivors (all fixes are test additions; no production code is wrong):

| Mutant | What survived | Classification | Fix task |
|---|---|---|---|
| R09 `confirmar: bool = False` -> `True` (`backend/app/presentation/schemas/generated.py:540`) | Body without `confirmar` would delete irreversibly | **Test gap, Medium** (DEL-04) | Add an API test: `POST /conclusion` with only `expected_version` -> 422 `CONFIRMACAO_OBRIGATORIA`, nothing removed |
| C14 `uow.processes.update(concluded, current.version)` (`conclusion.py:95`) | Same value as `expected_version` at that point | **Equivalent** (`check_status_change` right before compares them) | none |
| F18 history list without the `PRONTO` filter (`GeneratedBlock.tsx:66`) | FALHOU/GERANDO rows would show as "Versão null" | Test gap, Low | Test: a FALHOU row beside a PRONTO one does not appear in "Versões geradas" |
| F29 left-out count `group null || item null` -> `group null` (`ProcessGenerated.tsx:36`) | Item-less validated activity not counted | Test gap, Low (UIG-06) | Add the case |
| F34 free-text textarea not read-only in a concluded process (`ReportDraftEditor.tsx:290`) | Section free text editable in read-only mode (server would answer 409) | Test gap, Low (DEL-13 UI) | Assert `readonly` on `Texto livre da seção` |
| F57 "Subir" of an activity never disabled (`ComprovanteLayoutEditor.tsx:360`) | First activity could be "moved up" (no-op) | Test gap, Low | Assert disabled at the ends for activities |
| G10b `CONTENT_WORD_LETTERS = 5` -> `7` (`report_grounding.py:76`) | 5-6 letter words stop counting as new words, weakening the vocabulary check | Test gap, Low (REL-04/12) | Boundary test with a 5-letter and a 6-letter new word |
| W09b extra field `course` -> `curso` sent to the AI (`report_wording.py:28`) | Payload could carry the derived course | Near-equivalent (value comes from title/description already sent), Low | Exact-keys test with an activity whose title names a course |

Isolation check: `git status --porcelain` of the real tree equals the baseline taken before any sensor work.

### All mutants

| ID | Mutation (area) | File:line | Result | Killed by |
|---|---|---|---|---|
| A01 | ai-retries-on | `infrastructure/ai/report_writer.py:117` | KILLED | unit/infrastructure/test_report_writer.py::test_a_provider_error_is_redacao_indisponivel_with_no_repetition[ou |
| A02 | ai-deadline-ignored | `infrastructure/ai/report_writer.py:116` | KILLED | unit/infrastructure/test_report_writer.py::test_the_call_gives_up_at_the_deadline_of_60_seconds |
| A03 | ai-error-not-mapped | `infrastructure/ai/report_writer.py:119` | KILLED | unit/infrastructure/test_report_writer.py::test_a_provider_error_is_redacao_indisponivel_with_no_repetition[ou |
| A04 | client-retries-flag | `infrastructure/ai/maritalk.py:115` | KILLED | unit/infrastructure/test_report_writer.py::test_a_provider_error_is_redacao_indisponivel_with_no_repetition[ou |
| A05 | client-invalid-no-retries | `infrastructure/ai/maritalk.py:144` | KILLED | unit/infrastructure/test_report_writer.py::test_an_answer_that_is_not_json_or_was_cut_short_is_not_repeated |
| A06 | ai-empty-items-calls | `infrastructure/ai/report_writer.py:101` | KILLED | unit/infrastructure/test_report_writer.py::test_a_section_with_no_item_to_word_makes_no_call |
| C01 | concl-active-ops | `domain/rules/conclusion_rules.py:34` | KILLED | unit/domain/test_conclusion_check.py::test_an_operation_in_progress_refuses_with_operacao_em_andamento[1] |
| C02 | concl-missing-comprovante | `domain/rules/conclusion_rules.py:19` | KILLED | unit/domain/test_conclusion_check.py::test_without_a_ready_comprovante_it_refuses_listing_only_the_comprovante |
| C03 | concl-no-confirm | `application/use_cases/conclusion.py:119` | KILLED | integration/api/test_conclusion_api.py::test_without_the_confirmation_it_is_422_and_nothing_is_removed |
| C04 | concl-no-pending-check | `application/use_cases/conclusion.py:126` | KILLED | integration/api/test_conclusion_api.py::test_a_missing_generated_document_is_422_with_the_kinds_that_are_missi |
| C05 | concl-no-busy-check | `application/use_cases/conclusion.py:131` | KILLED | integration/api/test_conclusion_api.py::test_an_operation_in_progress_is_409_with_the_code |
| C06 | concl-idempotent-removed | `application/use_cases/conclusion.py:116` | KILLED | integration/api/test_conclusion_api.py::test_repeating_the_conclusion_of_a_concluded_process_changes_nothing |
| C07 | concl-no-role-check | `application/use_cases/conclusion.py:118` | KILLED | integration/api/test_conclusion_api.py::test_a_process_that_is_still_a_draft_cannot_be_concluded_and_nothing_i |
| C08 | concl-left-ignored | `application/use_cases/conclusion.py:73` | KILLED | integration/api/test_conclusion_api.py::test_a_file_that_cannot_be_removed_leaves_the_process_open_with_the_pa |
| C09 | concl-outcome-threshold | `domain/rules/conclusion_rules.py:64` | KILLED | unit/domain/test_conclusion_purge.py::test_an_outcome_with_one_pending_file_keeps_the_process_in_progress_with |
| C10 | concl-partial-alert-removed | `domain/rules/conclusion_rules.py:70` | KILLED | unit/domain/test_conclusion_purge.py::test_an_outcome_with_one_pending_file_keeps_the_process_in_progress_with |
| C11 | preview-counts-deleted | `domain/rules/conclusion_rules.py:51` | KILLED | unit/domain/test_conclusion_purge.py::test_the_preview_counts_only_documents_that_still_have_a_file_and_sums_t |
| C12 | preview-bytes | `domain/rules/conclusion_rules.py:55` | KILLED | unit/domain/test_conclusion_purge.py::test_the_preview_counts_only_documents_that_still_have_a_file_and_sums_t |
| C13 | concl-audit-removed | `application/use_cases/conclusion.py:86` | KILLED | integration/doc_usecases/test_conclude_process.py::test_the_events_carry_counts_and_no_file_names |
| C14 | concl-transition-version | `application/use_cases/conclusion.py:95` | SURVIVED | - |
| C15 | audit-files-pending | `application/use_cases/conclusion.py:87` | KILLED | integration/doc_usecases/test_conclude_process.py::test_a_removal_that_fails_keeps_the_process_em_andamento_wi |
| C16 | audit-bytes-removed | `application/use_cases/conclusion.py:88` | KILLED | integration/doc_usecases/test_conclude_process.py::test_the_events_carry_counts_and_no_file_names |
| C17 | kind-order | `domain/rules/conclusion_rules.py:19` | KILLED | unit/domain/test_conclusion_check.py::test_without_any_ready_kind_it_lists_the_three_in_table_report_comprovan |
| C18 | preview-no-access-check | `application/use_cases/conclusion.py:31` | KILLED | integration/doc_usecases/test_conclusion_preview.py::test_outside_the_access_the_process_is_not_found[other_do |
| D01 | draft-reconcile-overwrite-ai | `domain/rules/report_draft.py:263` | KILLED | unit/domain/test_report_draft_reconcile.py::test_the_entry_from_the_template_follows_the_activity_but_the_one_ |
| D02 | draft-move-user-text-lost | `domain/rules/report_draft.py:296` | KILLED | unit/domain/test_report_draft_reconcile.py::test_moving_keeps_the_text_the_user_typed |
| D03 | draft-empty-section | `domain/rules/report_draft.py:216` | KILLED | unit/domain/test_report_draft_proposal.py::test_a_section_with_only_typed_text_is_not_empty |
| D04 | draft-stale-warning | `domain/rules/report_draft.py:268` | KILLED | unit/domain/test_report_draft_reconcile.py::test_a_removed_activity_leaves_the_draft_and_makes_its_section_sta |
| D05 | draft-reconcile-keeps-gone | `domain/rules/report_draft.py:261` | KILLED | unit/domain/test_report_draft_reconcile.py::test_the_text_typed_by_the_user_stays_identical_when_other_activit |
| F01 | concl-confirm-not-required | `components/ConcludeDialog.tsx:137` | KILLED | components/ConcludeDialog.test.tsx > DEL-04: só envia confirmar: true depois de marcar a confirmação > o botão |
| F02 | concl-missing-not-blocking | `components/ConcludeDialog.tsx:137` | KILLED | components/ConcludeDialog.test.tsx > DEL-01: só conclui com os três documentos gerados > com um tipo sem versã |
| F03 | concl-confirmar-false | `components/ConcludeDialog.tsx:61` | KILLED | components/ConcludeDialog.test.tsx > DEL-04: só envia confirmar: true depois de marcar a confirmação > o botão |
| F04 | concl-expected-version | `components/ConcludeDialog.tsx:60` | KILLED | components/ConcludeDialog.test.tsx > DEL-04: só envia confirmar: true depois de marcar a confirmação > o botão |
| F05 | concl-no-reload-on-success | `components/ConcludeDialog.tsx:64` | KILLED | components/ConcludeDialog.test.tsx > DEL-04: só envia confirmar: true depois de marcar a confirmação > o suces |
| F06 | concl-no-irreversible-text | `components/ConcludeDialog.tsx:105` | KILLED | components/ConcludeDialog.test.tsx > DEL-03, UIG-09: a confirmação de ação irreversível > diz quantos arquivos |
| F07 | concl-no-reload-on-409 | `components/ConcludeDialog.tsx:68` | KILLED | components/ConcludeDialog.test.tsx > DEL-02, DEL-15: recusas do servidor em português > 409 VERSAO_DESATUALIZA |
| F08 | concl-retry-label | `components/ConcludeDialog.tsx:140` | KILLED | components/ConcludeDialog.test.tsx > DEL-08: exclusão parcial > mostra quantos arquivos faltam e permite repet |
| F09 | concl-missing-list-hidden | `components/ConcludeDialog.tsx:119` | KILLED | components/ConcludeDialog.test.tsx > DEL-01: só conclui com os três documentos gerados > com um tipo sem versã |
| F10 | concl-concluded-any-result | `components/ConcludeDialog.tsx:52` | KILLED | components/ConcludeDialog.test.tsx > DEL-08: exclusão parcial > mostra quantos arquivos faltam e permite repet |
| F11 | concl-partial-alert-hidden | `components/ConcludeDialog.tsx:108` | KILLED | components/ConcludeDialog.test.tsx > DEL-08: exclusão parcial > mostra quantos arquivos faltam e permite repet |
| F12 | poll-never-stops | `hooks/usePolling.ts:13` | KILLED | hooks/usePolling.test.ts > UIG-04, UIG-08: hook usePolling > não consulta quando a condição nasce inativa |
| F13 | poll-interval | `hooks/usePolling.ts:4` | KILLED | hooks/usePolling.test.ts > UIG-04, UIG-08: hook usePolling > consulta a cada 3 s enquanto a condição está ativ |
| F14 | poll-no-cleanup | `hooks/usePolling.ts:15` | KILLED | hooks/usePolling.test.ts > UIG-04, UIG-08: hook usePolling > para quando a condição de parada vira verdadeira  |
| F15 | gb-running-wrong-state | `components/GeneratedBlock.tsx:50` | KILLED | components/GeneratedBlock.test.tsx > UIG-01: um bloco por tipo, com botão, estado e histórico > gerar pede o t |
| F16 | gb-button-not-off-while-running | `components/GeneratedBlock.tsx:83` | KILLED | components/GeneratedBlock.test.tsx > UIG-01: um bloco por tipo, com botão, estado e histórico > gerar pede o t |
| F17 | gb-disabled-reason-ignored | `components/GeneratedBlock.tsx:83` | KILLED | components/GeneratedBlock.test.tsx > DEL-11: geração que o processo não aceita > com um motivo para desligar,  |
| F18 | gb-history-all-states | `components/GeneratedBlock.tsx:66` | SURVIVED | - |
| F19 | gb-leftout-threshold | `components/GeneratedBlock.tsx:72` | KILLED | components/GeneratedBlock.test.tsx > UIG-06: aviso das atividades que ficam de fora > uma atividade fica no si |
| F20 | gb-alerts-hidden | `components/GeneratedBlock.tsx:101` | KILLED | components/GeneratedBlock.test.tsx > UIG-05: falha e alertas em português > lista os alertas da última versão  |
| F21 | gb-409-no-reload | `components/GeneratedBlock.tsx:59` | KILLED | components/GeneratedBlock.test.tsx > UIG-05: falha e alertas em português > 409 GERACAO_EM_ANDAMENTO mostra a  |
| F22 | gb-failed-hidden | `components/GeneratedBlock.tsx:91` | KILLED | components/GeneratedBlock.test.tsx > UIG-05: falha e alertas em português > FALHOU mostra o motivo em portuguê |
| F23 | gb-download-href | `components/GeneratedBlock.tsx:122` | KILLED | components/GeneratedBlock.test.tsx > UIG-01: um bloco por tipo, com botão, estado e histórico > consulta a cad |
| F24 | gb-size-hidden | `components/GeneratedBlock.tsx:125` | KILLED | components/GeneratedBlock.test.tsx > UIG-01: um bloco por tipo, com botão, estado e histórico > consulta a cad |
| F25 | pg-concluded-not-readonly | `pages/ProcessGenerated.tsx:82` | KILLED | pages/ProcessGenerated.test.tsx > DEL-13: processo CONCLUIDO > o rascunho e o arranjo ficam somente leitura |
| F26 | pg-comprovante-not-disabled | `pages/ProcessGenerated.tsx:113` | KILLED | pages/ProcessGenerated.test.tsx > UIG-09: Concluir e excluir documentos de entrada > ao concluir, a página rec |
| F27 | pg-conclude-always-shown | `pages/ProcessGenerated.tsx:120` | KILLED | pages/ProcessGenerated.test.tsx > UIG-09: Concluir e excluir documentos de entrada > o processo RASCUNHO não o |
| F28 | pg-leftout-pending | `pages/ProcessGenerated.tsx:35` | KILLED | pages/ProcessGenerated.test.tsx > UIG-01: a página da Etapa 5 > UIG-06: cada bloco avisa quantas atividades fi |
| F29 | pg-leftout-no-item | `pages/ProcessGenerated.tsx:36` | SURVIVED | - |
| F30 | pg-onchanged-noop | `pages/ProcessGenerated.tsx:138` | KILLED | pages/ProcessGenerated.test.tsx > UIG-09: Concluir e excluir documentos de entrada > ao concluir, a página rec |
| F31 | pg-draft-editable-when-readonly | `pages/ProcessGenerated.tsx:106` | KILLED | pages/ProcessGenerated.test.tsx > DEL-13: processo CONCLUIDO > o rascunho e o arranjo ficam somente leitura |
| F32 | pg-layout-editable-when-readonly | `pages/ProcessGenerated.tsx:116` | KILLED | pages/ProcessGenerated.test.tsx > DEL-13: processo CONCLUIDO > o rascunho e o arranjo ficam somente leitura |
| F33 | rde-entry-textarea-editable | `components/ReportDraftEditor.tsx:241` | KILLED | pages/ProcessGenerated.test.tsx > DEL-13: processo CONCLUIDO > o rascunho e o arranjo ficam somente leitura |
| F34 | rde-free-textarea-editable | `components/ReportDraftEditor.tsx:290` | SURVIVED | - |
| F35 | rde-wording-button-in-readonly | `components/ReportDraftEditor.tsx:188` | KILLED | pages/ProcessGenerated.test.tsx > DEL-13: processo CONCLUIDO > o rascunho e o arranjo ficam somente leitura |
| F36 | rde-wording-not-disabled-while-generating | `components/ReportDraftEditor.tsx:195` | KILLED | components/ReportDraftEditor.test.tsx > UIG-08, REL-03: redação por seção em segundo plano > pedir a redação m |
| F37 | rde-entry-version | `components/ReportDraftEditor.tsx:140` | KILLED | components/ReportDraftEditor.test.tsx > REL-07: editar e sair do campo grava a entrada > grava com a versão li |
| F38 | rde-409-no-reload | `components/ReportDraftEditor.tsx:115` | KILLED | components/ReportDraftEditor.test.tsx > REL-07: editar e sair do campo grava a entrada > 409 recarrega o rascu |
| F39 | rde-no-reload-when-wording-ends | `components/ReportDraftEditor.tsx:60` | KILLED | components/ReportDraftEditor.test.tsx > UIG-08, REL-03: redação por seção em segundo plano > consulta a cada 3 |
| F40 | rde-poll-always | `components/ReportDraftEditor.tsx:87` | KILLED | components/ReportDraftEditor.test.tsx > UIG-08, REL-03: redação por seção em segundo plano > consulta a cada 3 |
| F41 | rde-poll-never | `components/ReportDraftEditor.tsx:87` | KILLED | components/ReportDraftEditor.test.tsx > UIG-08, REL-03: redação por seção em segundo plano > consulta a cada 3 |
| F42 | rde-over-limit-saved | `components/ReportDraftEditor.tsx:138` | KILLED | components/ReportDraftEditor.test.tsx > REL-07: o contador bloqueia acima de 20 000 > mostra o contador e não  |
| F43 | rde-max-length | `components/ReportDraftEditor.tsx:9` | KILLED | components/ReportDraftEditor.test.tsx > REL-07: o contador bloqueia acima de 20 000 > mostra o contador e não  |
| F44 | rde-other-sections-typed-lost | `components/ReportDraftEditor.tsx:66` | KILLED | components/ReportDraftEditor.test.tsx > UIG-08, REL-03: redação por seção em segundo plano > ao terminar, o qu |
| F45 | rde-warnings-hidden | `components/ReportDraftEditor.tsx:202` | KILLED | components/ReportDraftEditor.test.tsx > UIG-02: uma seção por cartão > os avisos da seção saem em português, c |
| F46 | dl-deleted-badge | `components/DocumentList.tsx:360` | KILLED | components/DocumentList.test.tsx > DEL-12: documento com o arquivo excluído na conclusão > mostra nome, tipo e |
| F47 | dl-view-download-when-deleted | `components/DocumentList.tsx:377` | KILLED | components/DocumentList.test.tsx > DEL-12: documento com o arquivo excluído na conclusão > não oferece visuali |
| F48 | dl-reprocess-when-deleted | `components/DocumentList.tsx:422` | KILLED | components/DocumentList.test.tsx > DEL-12: documento com o arquivo excluído na conclusão > não oferece visuali |
| F49 | dv-deleted-message | `components/DocumentViewer.tsx:47` | KILLED | components/DocumentViewer.test.tsx > DEL-12: documento com o arquivo excluído na conclusão > mostra Arquivo ex |
| F50 | do-generated-marker | `components/DossierOrder.tsx:42` | KILLED | components/DossierOrder.test.tsx > ORD-01: lembrete da ordem do dossiê > marca Tabela, Relatório e Comprovante |
| F51 | do-order-reversed | `components/DossierOrder.tsx:39` | KILLED | components/DossierOrder.test.tsx > ORD-01: lembrete da ordem do dossiê > mostra a lista na ordem recebida da A |
| F52 | cle-version | `components/ComprovanteLayoutEditor.tsx:260` | KILLED | components/ComprovanteLayoutEditor.test.tsx > ARR-04: reordenar e ARR-03: remover páginas > subir a segunda pá |
| F53 | cle-409-no-reload | `components/ComprovanteLayoutEditor.tsx:276` | KILLED | components/ComprovanteLayoutEditor.test.tsx > ARR-07: 409 recarrega e avisa > recarrega o arranjo do servidor, |
| F54 | cle-save-in-readonly | `components/ComprovanteLayoutEditor.tsx:300` | KILLED | components/ComprovanteLayoutEditor.test.tsx > DEL-13: somente leitura > em processo concluído mostra o arranjo |
| F55 | cle-add-in-readonly | `components/ComprovanteLayoutEditor.tsx:464` | KILLED | pages/ProcessGenerated.test.tsx > DEL-13: processo CONCLUIDO > o rascunho e o arranjo ficam somente leitura |
| F56 | cle-save-justification | `components/ComprovanteLayoutEditor.tsx:503` | KILLED | components/ComprovanteLayoutEditor.test.tsx > CMP-06: repetir a página com justificativa > com a justificativa |
| F57 | cle-move-up-disabled | `components/ComprovanteLayoutEditor.tsx:360` | SURVIVED | - |
| G01 | grounding-date | `domain/rules/report_grounding.py:166` | KILLED | unit/domain/test_report_grounding_numbers.py::test_an_invented_date_is_refused_with_the_reason_date |
| G02 | grounding-number | `domain/rules/report_grounding.py:169` | KILLED | unit/domain/test_report_grounding_numbers.py::test_an_invented_number_of_hours_is_refused_with_the_reason_numb |
| G03 | grounding-name-acronym | `domain/rules/report_grounding.py:198` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_an_acronym_at_the_start_of_a_sentence_is_also_checked |
| G04 | grounding-name-sentence-start | `domain/rules/report_grounding.py:197` | KILLED | unit/domain/test_report_grounding_numbers.py::test_the_academic_period_of_the_field_is_accepted_in_its_variati |
| G05 | grounding-vocab-limit | `domain/rules/report_grounding.py:222` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_exactly_the_limit_of_new_content_words_is_accepted |
| G06 | grounding-length | `domain/rules/report_grounding.py:77` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_a_wording_longer_than_twice_the_template_plus_120_charac |
| G07 | grounding-length-slack | `domain/rules/report_grounding.py:78` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_a_wording_longer_than_twice_the_template_plus_120_charac |
| G08 | grounding-forbidden | `domain/rules/report_grounding.py:227` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_each_forbidden_word_is_refused_with_the_reason_forbidden |
| G09 | grounding-forbidden-minus-facts | `domain/rules/report_grounding.py:226` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_a_forbidden_word_the_fields_already_have_is_not_somethin |
| G10b | grounding-content-letters-allunit | `domain/rules/report_grounding.py:76` | SURVIVED | - |
| G11 | grounding-return-text | `domain/rules/report_grounding.py:246` | KILLED | unit/domain/test_report_grounding_numbers.py::test_a_refused_wording_returns_the_template_text |
| G12 | grounding-accepted | `domain/rules/report_grounding.py:246` | KILLED | unit/domain/test_report_grounding_numbers.py::test_an_invented_number_of_hours_is_refused_with_the_reason_numb |
| G13 | grounding-facts-only-first | `domain/rules/report_grounding.py:242` | KILLED | unit/domain/test_report_grounding_numbers.py::test_the_hours_of_the_field_are_accepted_in_their_variations[Cur |
| G14 | grounding-allowed-terms | `domain/rules/report_grounding.py:218` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_names_and_acronyms_of_the_fields_or_of_the_allowed_terms |
| G15 | grounding-date-month | `domain/rules/report_grounding.py:143` | KILLED | unit/domain/test_report_grounding_numbers.py::test_a_month_of_another_year_than_the_field_is_refused |
| G16 | grounding-new-words-all | `domain/rules/report_grounding.py:207` | KILLED | unit/domain/test_report_grounding_vocabulary.py::test_a_name_that_is_not_in_the_fields_is_refused_with_the_rea |
| O01 | dossier-generated-by-dropped | `infrastructure/documents/config_loader.py:348` | KILLED | integration/api/test_dossier_order_api.py::test_the_list_follows_the_file_with_the_three_generated_documents_m |
| O02 | dossier-order-not-checked | `infrastructure/documents/config_loader.py:336` | KILLED | unit/infrastructure/test_report_config_loader.py::test_a_dossier_item_with_a_bad_title_marker_or_order_names_t |
| O03 | dossier-title-dropped | `infrastructure/documents/config_loader.py:340` | KILLED | integration/api/test_dossier_order_api.py::test_the_list_follows_the_file_with_the_three_generated_documents_m |
| P01 | purge-no-delete-file | `application/services/purge_inputs.py:56` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P02 | purge-no-exists-check | `application/services/purge_inputs.py:57` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_a_file_that_is_still_there_after_the_removal_is_pending |
| P03 | purge-no-delete-pages | `application/services/purge_inputs.py:60` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P04 | purge-no-clear-excerpts | `application/services/purge_inputs.py:61` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P05 | purge-no-mark | `application/services/purge_inputs.py:62` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P06 | purge-bare-except | `application/services/purge_inputs.py:64` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_a_removal_that_fails_leaves_that_document_pending_and_the_ |
| P07 | purge-resumes-deleted | `application/services/purge_inputs.py:43` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_repeating_removes_what_is_missing_and_a_third_run_finds_no |
| P08 | purge-bytes-freed | `application/services/purge_inputs.py:49` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P09 | purge-repo-excerpt | `infrastructure/database/repositories.py:1270` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P10 | purge-repo-pages-scope | `infrastructure/database/repositories.py:1059` | KILLED | integration/doc_usecases/test_conclude_process.py::test_with_everything_ready_the_files_go_and_the_generated_o |
| P11 | purge-repo-mark-overwrite | `infrastructure/database/repositories.py:983` | KILLED | integration/doc_usecases/test_purge_inputs.py::test_three_documents_lose_file_pages_and_excerpts_and_keep_the_ |
| P12 | busy-no-wording | `infrastructure/database/repositories.py:2050` | KILLED | integration/documents/test_process_purge_repository.py::test_a_wording_in_progress_makes_the_process_busy |
| P13 | busy-no-generation | `infrastructure/database/repositories.py:2041` | KILLED | integration/documents/test_process_purge_repository.py::test_a_generation_in_progress_makes_the_process_busy |
| P14 | busy-no-processing-job | `infrastructure/database/repositories.py:2033` | KILLED | integration/api/test_conclusion_api.py::test_an_operation_in_progress_is_409_with_the_code |
| R01 | recover-wording-unstarted | `infrastructure/database/repositories.py:1660` | KILLED | integration/documents/test_wording_job_repository.py::test_recovery_fails_only_the_jobs_that_had_started |
| R02 | recover-wording-code | `infrastructure/database/repositories.py:1665` | KILLED | integration/documents/test_wording_job_repository.py::test_recovery_fails_only_the_jobs_that_had_started |
| R03 | recover-wording-skipped | `application/use_cases/generated_documents.py:721` | KILLED | integration/doc_usecases/test_worker.py::test_a_database_error_while_claiming_does_not_kill_the_thread |
| R04 | wording-409-code | `infrastructure/database/repositories.py:1605` | KILLED | integration/documents/test_wording_job_repository.py::test_a_second_generating_job_of_the_same_section_conflic |
| R05 | wording-claim-restarted | `infrastructure/database/repositories.py:1617` | KILLED | integration/documents/test_wording_job_repository.py::test_claim_next_takes_the_oldest_job_not_started_and_mar |
| R06 | wording-latest-order | `infrastructure/database/repositories.py:1675` | KILLED | integration/documents/test_wording_job_repository.py::test_latest_by_section_gives_the_newest_job_of_each_sect |
| R07 | no-description-and-no-title | `application/use_cases/generated_documents.py:193` | KILLED | integration/doc_usecases/test_run_generation_report.py::test_the_document_uses_the_text_the_user_edited_and_le |
| R08 | gone-as-404 | `presentation/errors.py:63` | KILLED | integration/api/test_generation_error_mapping.py::test_a_gone_error_is_410_with_field_code_and_message |
| R09 | confirmar-default-true | `presentation/schemas/generated.py:539` | SURVIVED | - |
| R10 | wording-in-readonly-process | `application/use_cases/report_draft.py:315` | KILLED | integration/doc_usecases/test_report_wording_request.py::test_a_concluded_or_archived_process_refuses_the_requ |
| R11 | wording-finish-guard | `infrastructure/database/repositories.py:1641` | KILLED | integration/documents/test_wording_job_repository.py::test_a_finished_job_cannot_be_finished_again_and_an_unkn |
| R12 | move-section-validation | `application/use_cases/report_draft.py:289` | KILLED | integration/doc_usecases/test_report_draft_move.py::test_a_section_that_does_not_exist_is_a_422_and_nothing_is |
| R13 | no-title-not-validated-on-draft-sort | `domain/rules/report_draft.py:74` | KILLED | unit/domain/test_report_draft_proposal.py::test_an_activity_without_academic_period_comes_after_the_dated_peri |
| S01 | gone-never | `application/use_cases/documents.py:142` | KILLED | integration/api/test_documents_deleted_api.py::test_the_file_of_a_purged_document_is_410_with_field_code_and_m |
| S02 | download-no-410 | `application/use_cases/documents.py:478` | KILLED | integration/api/test_documents_deleted_api.py::test_the_file_of_a_purged_document_is_410_with_field_code_and_m |
| S03 | evidence-no-410 | `application/use_cases/evidences.py:114` | KILLED | integration/api/test_documents_deleted_api.py::test_replacing_reprocessing_and_linking_a_purged_document_are_4 |
| S04 | reprocess-no-410 | `application/use_cases/documents.py:521` | KILLED | integration/api/test_documents_deleted_api.py::test_replacing_reprocessing_and_linking_a_purged_document_are_4 |
| S05 | status-route-concludes | `application/use_cases/processes.py:224` | KILLED | integration/doc_usecases/test_process_status_change.py::test_the_generic_change_refuses_concluido_and_the_proc |
| S06 | comprovante-deleted-allowed | `domain/rules/comprovante_plan.py:263` | KILLED | unit/domain/test_comprovante_plan_limits.py::test_a_deleted_file_refuses_even_when_the_plan_does_not_use_that_ |
| S07 | get-document-shows-pages-after-purge | `application/use_cases/documents.py:367` | KILLED | integration/doc_usecases/test_deleted_documents.py::test_the_page_text_is_not_returned_even_if_it_is_still_sto |
| S08 | evidence-view-excerpt-after-purge | `application/use_cases/evidences.py:193` | KILLED | integration/doc_usecases/test_evidences_deleted.py::test_an_excerpt_left_behind_is_not_listed_once_the_documen |
| T01 | t146-all-to-any | `application/use_cases/document_processing.py:269` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_an_activity_with_evidence_from_another_docum |
| T02 | t146-not-called | `application/use_cases/document_processing.py:247` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| T03 | t146-keeps-validated | `application/use_cases/document_processing.py:267` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| T04 | t146-keeps-edited | `application/use_cases/document_processing.py:267` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| T05 | t146-no-activity-audit | `application/use_cases/document_processing.py:272` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| T06 | t146-no-unlink | `application/use_cases/document_processing.py:284` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_an_activity_with_evidence_from_another_docum |
| T07 | t146-no-unlink-audit | `application/use_cases/document_processing.py:285` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_an_activity_with_evidence_from_another_docum |
| T08 | t146-status-kept | `application/use_cases/document_processing.py:270` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| T09 | t146-audit-reason | `application/use_cases/document_processing.py:278` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| T10 | t146-unlink-removes-other | `application/use_cases/document_processing.py:283` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_an_activity_with_evidence_from_another_docum |
| T11 | t146-actor-user | `application/use_cases/document_processing.py:273` | KILLED | integration/doc_usecases/test_process_outside_interstice.py::test_a_validated_activity_linked_only_to_the_docu |
| U01 | wording-ai-error-no-fallback | `application/use_cases/report_draft.py:434` | KILLED | integration/doc_usecases/test_report_wording_run.py::test_when_the_ai_is_unavailable_the_template_text_stays_w |
| U02 | wording-apply-overwrites-user | `infrastructure/database/repositories.py:1890` | KILLED | integration/doc_usecases/test_report_wording_run.py::test_an_edit_made_while_the_job_runs_stays_and_the_versio |
| U03 | wording-bumps-version | `infrastructure/database/repositories.py:1895` | KILLED | integration/doc_usecases/test_report_wording_run.py::test_an_edit_made_while_the_job_runs_stays_and_the_versio |
| U04 | wording-apply-no-lock | `infrastructure/database/repositories.py:1880` | KILLED | integration/documents/test_report_draft_repository.py::test_apply_wording_locks_the_row_until_the_transaction_ |
| U05 | wording-fail-state | `application/use_cases/report_draft.py:470` | KILLED | integration/doc_usecases/test_report_wording_run.py::test_an_unexpected_error_fails_the_job_and_leaves_the_dra |
| U06 | wording-request-no-draft-save | `application/use_cases/report_draft.py:319` | KILLED | integration/doc_usecases/test_report_wording_request.py::test_the_request_answers_at_once_with_a_generating_jo |
| U07 | lock-version-check | `infrastructure/database/repositories.py:1799` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_an_outdated_version_is_a_409_with_its_code_and_the_st |
| U08 | lock-version-no-bump | `infrastructure/database/repositories.py:1802` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_a_second_edit_uses_the_version_the_user_saw_and_raise |
| U09 | lock-create-version | `infrastructure/database/repositories.py:1753` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_a_first_save_with_a_version_other_than_0_is_stale_and |
| U10 | entry-source-model | `application/use_cases/report_draft.py:231` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_the_first_save_expects_version_0_creates_the_draft_an |
| U11 | entry-max-length | `application/use_cases/report_draft.py:58` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_more_than_20000_characters_is_a_422_and_exactly_20000 |
| U12 | entry-max-length-boundary | `application/use_cases/report_draft.py:211` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_more_than_20000_characters_is_a_422_and_exactly_20000 |
| U13 | draft-editable-check | `application/use_cases/report_draft.py:174` | KILLED | integration/doc_usecases/test_report_draft_save.py::test_a_concluded_or_archived_process_refuses_the_save_and_ |
| W01 | fallback-user-text | `domain/rules/report_wording.py:121` | KILLED | unit/domain/test_report_wording_apply.py::test_the_text_edited_by_the_user_stays_identical_even_when_the_answe |
| W02 | fallback-ai-unavailable-text | `domain/rules/report_wording.py:125` | KILLED | unit/domain/test_report_wording_apply.py::test_without_an_answer_every_entry_not_typed_gets_the_template_text_ |
| W03 | fallback-unavailable-warning | `domain/rules/report_wording.py:140` | KILLED | unit/domain/test_report_wording_apply.py::test_without_an_answer_every_entry_not_typed_gets_the_template_text_ |
| W04 | fallback-accept-all | `domain/rules/report_wording.py:130` | KILLED | unit/domain/test_report_wording_apply.py::test_an_answer_with_an_invented_number_becomes_the_template_text_wit |
| W05 | fallback-rejected-warning | `domain/rules/report_wording.py:143` | KILLED | unit/domain/test_report_wording_apply.py::test_an_answer_with_an_invented_number_becomes_the_template_text_wit |
| W06 | send-user-text-to-ai | `domain/rules/report_wording.py:88` | KILLED | unit/domain/test_report_wording_apply.py::test_the_activities_to_word_leave_out_the_entries_the_user_edited |
| W07 | no-masking | `domain/rules/report_wording.py:61` | KILLED | unit/domain/test_report_wording_items.py::test_the_description_is_sent_after_masking_cpf_email_and_phone |
| W08 | masked-only-title | `domain/rules/report_wording.py:30` | KILLED | unit/domain/test_report_wording_items.py::test_the_description_is_sent_after_masking_cpf_email_and_phone |
| W09b | send-extra-fields-allunit | `domain/rules/report_wording.py:28` | SURVIVED | - |


## Real run (notes)

**Setup.** Throwaway `postgres:16-alpine` (docker), the committed backend (`git archive HEAD`) served by uvicorn on 127.0.0.1:8010 with `alembic upgrade head` and the seed, the committed frontend served by `vite` (dev server, proxy changed to 8010 in the scratch copy), storage in the scratchpad. No VM, no push, no deploy. Synthetic data only: three PDFs generated in code with PyMuPDF (a declaration text with a fictitious professor "Maria Docente da Silva", SIAPE 1234567); nothing from `Documentos/` or `Modelos/` was opened. The real `.env` (it holds a MariTalk key) was never loaded: `Settings` has no `env_file`, and the key was either unset or pointed at a local fake. Phase A ran with `MARITALK_*` unset. Phase B pointed `MARITALK_API_BASE` at a local fake OpenAI-compatible server I wrote (modes `faithful`, `invent`, `error500`, `slow`) with `WORDING_TIMEOUT_SECONDS=8`; no external call was made.

**Browser.** A browser could be driven: Playwright (`playwright-core` installed in the scratchpad) over `/usr/bin/google-chrome`, headless, at 1280 x 900 and 360 x 740. Screenshots are in `/tmp/claude-1000/-home-nees-Documents-VSCodigo-ProgressaoFuncionalPiloto/118aba81-5621-4e3f-847f-fa68c56fc9d9/scratchpad/vb/shots/` (`a1-etapa5-desktop.png`, `a3-save-click-409.png`, `a4-wording-*.png`, `b1-layout-open.png`, `b2-layout-*.png`, `c1-generated.png`, `d1-360-*.png`, `d2-360-*.png`, `e1-faithful.png`, `f1-dialog-1280.png`, `f1-partial-1280.png`, `f1-concluded-1280.png`, `g1-etapa5-concluded-*.png`, `g1-etapa2-*.png`). I looked at the desktop Etapa 5, the 360 px entry and arrangement views, the conclusion dialogs and Etapa 2.

**Walkthrough, in order.**
1. Login, process with interstice 23/11/2022 to 23/11/2024, official table chosen, 3 PDFs uploaded (key unset: documents `EXTRAIDO_SEM_IA`, text of every page stored), 8 manual activities (7 validated with group and item, 1 without) with page links, one page shared by two activities.
2. Etapa 5 at 1280 px: three blocks, "1 atividade fica de fora", dossier order with three badges, no horizontal scroll.
3. Report draft: 8 sections; typed text saved ("Editado"); a second user saved through the API, then the first user's stale save returned 409: alert "Os dados mudaram desde que você abriu a tela. A versão atual foi recarregada.", the other user's text loaded, the typed text kept and savable. **Defect D1 found here.**
4. Wording with the key unset: 202, "Gerando a redação…", button of that section disabled, other sections enabled, ended after one 3 s poll with the template text and the warning. Phase B: `faithful` accepted ("Redigido pela IA"), `invent` rejected with the reasons, `error500` and `slow` (deadline) fell back, user-edited entries untouched in all runs. API: second request 409 `REDACAO_EM_ANDAMENTO`, other section 202. Backend SIGKILL during a job: after restart FALHOU `INTERROMPIDA`.
5. Layout editor: remove page, move activity, add page (invalid page refused), repeat with justification (empty refused), save, reload: all persisted; numbering updated.
6. Generation of the three documents from the UI; polling stopped at PRONTO; downloads 200; the report DOCX/PDF text checked (headers, identification, stored texts, empty sections omitted).
7. T146: with the fake provider, two validated activities were linked to the 2019 document (one only to it and edited by the user, one also to another document); reprocessing it made it outside the interstice: first rejected (audited), second kept with one evidence; Etapa 2 banner; Etapa 5 no longer counts the rejected activity.
8. Conclusion in the UI: dialog, checkbox, deliberate partial failure (a directory in place of one stored file), "Tentar de novo" concluded it; DB and disk inspected (see DEL-05, DEL-06, DEL-10); 410 on file, inline and reprocess; Comprovante refused; Tabela and Relatório regenerated as v2; older versions byte-identical; read-only draft and arrangement; Etapa 2 shows "Arquivo excluído" on the three documents plus the outside banner, no Visualizar, Baixar, Substituir or Reprocessar.
9. 360 px: no horizontal overflow on Etapa 5 (everything open) and Etapa 2.

**Visual / usability findings.** Etapa 5 is long when both editors are open (about 10 000 px at 360 px) but readable; buttons are reachable. In the Etapa 2 table at 1280 px the headers "Tamanho" and "Confiança" break mid-word ("Taman/ho", "Confianç/a"). The conclusion dialog repeats a "Fechar" button next to the title in the success state (two "Fechar" buttons).

**Not exercised in the real run:** DEL-02 in the browser (covered by tests), the "Mover para" select (covered by tests), a generation that ends FALHOU (scope A), `IMAGEM_GRANDE_DEMAIS` and the other Comprovante refusals (scope A).

## Defects and findings

| # | Severity | Finding | Evidence | Proposed fix |
|---|---|---|---|---|
| D1 | **Medium** | Clicking the per-entry **Salvar** button of the report draft shows a false conflict alert although the text was saved. The click first blurs the textarea (`onBlur` -> `saveEntry`, `ReportDraftEditor.tsx:244`), which saves with version N; the click handler (`:257`) then runs `saveEntry` again with the same stale `view.version` (the first write has not reloaded yet) and the second PUT answers 409, so the user sees "Os dados mudaram desde que você abriu a tela" and the draft reloads. Reproduced twice in Chrome (network: `200 PUT ...` then `409 PUT ...` for the same entry; blur-only gave a single 200 and no alert). The component tests save with `user.tab()` and never click the button after typing, so they do not see it | `shots/a3-save-click-409.png`; `ReportDraftEditor.tsx:134-143,244,257` | Ignore the second save while one is in flight, or drop `onClick` since blur already saves; add a test that types and clicks "Salvar" (jsdom with user-event fires the blur) |
| D2 | **Medium** (test gap on an irreversible action) | No test sends the conclusion body without `confirmar`. Mutant R09 (`confirmar` default `True`) survives, so a regression would delete the files of a request that omitted the confirmation | `backend/app/presentation/schemas/generated.py:540`; `tests/integration/api/test_conclusion_api.py:90-101` always sends the field | Add the API test (DEL-04) |
| D3 | **Medium** (documented design limit, REL-12 PARTIAL) | The deterministic check does not catch an invented lowercase proper noun with 3 or fewer new content words, nor an inverted statement. Probe: "na universidade federal do amazonas" accepted; "Não ministrou o curso ... em formato remoto" accepted. The spec says the AI "nunca" adds facts (REL-12) and the design admits the limit | `backend/app/domain/rules/report_grounding.py:190-200` (`_name_is_new` only looks at capitalized words and acronyms), `:222` (`max_new_words`) | Decide with the user: lower `max_new_words`, treat negations ("não", "sem") as new vocabulary, compare lowercase words that the facts do not contain when the sentence is short; keep the human review and the "Redigido pela IA" badge |
| D4 | Low | In a concluded process, Etapa 2 still offers **Excluir** and **Classificar** on the purged documents; the server then refuses (checked for Excluir: 409 "Processo concluído ou arquivado não pode ser alterado"; Classificar not exercised). Reprocessar, Visualizar, Baixar and Substituir are correctly hidden | `frontend/src/components/DocumentList.tsx:419-455` (`!deleted` is not applied to Excluir and Classificar) | Hide or disable them when the process is read-only |
| D5 | Low | Texts: (a) several alerts repeat the label inside the message ("Há atividades que ficaram fora do documento: Atividades fora do documento: 1 sem enquadramento..."); (b) `REDACAO_REJEITADA` appears twice per rejected entry (section line and entry line); (c) `REDACAO_INDISPONIVEL` always reads "A IA não respondeu a tempo", even when the key is unset or the provider answered 500 | `frontend/src/labels.ts:295-331`, `GeneratedBlock.tsx` alert list | Show the message only when it adds information; word (c) neutrally |
| D6 | Low | Test gaps from surviving mutants F18, F29, F34, F57, G10b, W09b (table above) | see the sensor table | Add the listed assertions |
| D7 | Low | After a partial conclusion and its retry, the success text reports only the last attempt ("1 arquivo excluído, 2 KB liberados") although 3 files and 6 KB were removed in total | `ConcludeDialog.tsx:85` shows `result.*` of the last response | Say "nesta tentativa" or add the previous count |
| D8 | Low (spec ambiguity) | ORD-01 says "na etapa Documentos"; the list is on Etapa 5 ("Documentos gerados"). Etapa 2 is titled "Documentos". Needs the user's answer | `ProcessGenerated.tsx:119`; spec.md ORD story | Confirm the place, or show it in both |
| D9 | Low | `extraction_runs.raw_json` keeps the extracted professor name and titles after the purge (spec assumption "O que fica", `Confirmed = n`, AD-015). Seen in the real run: 1 of 4 runs had the professor name in `raw_json` after the conclusion | DB query after conclusion; `alembic/versions/0003_documents.py` immutability trigger | User decision pending, as recorded in the spec |
| D10 | Low (code reading, not reproduced) | `MariTalkClient._post` bounds each httpx operation by `min(time_left, ai_timeout)`, so the 60 s deadline is checked before the call, not over a slowly dripping response | `backend/app/infrastructure/ai/maritalk.py:184-192` | Use an overall deadline (for example `httpx.Timeout(time_left)` per read plus a monotonic check) if this matters |
| D11 | Low (code reading, not reproduced) | `ProcessDocument._store` calls `uow.activities.update(rejected, activity.version)` inside the unit that stores the reading: if the user saves the same activity at that moment the update raises `StaleVersion` and the whole reprocessing ends as FALHOU, instead of retrying the rejection | `backend/app/application/use_cases/document_processing.py:246-251,264` | Re-read and retry the rejection once, or reject by id with a status-only update |
| D12 | Low | Commit `4e2727d` message says "AD-018" while the specs record AD-019 (renumbered in `4628f08`, docs only) | `git log` | none (history), mention in the next commit |
| D13 | Info | The report text of an edited entry carries only the user's text, without the title; that is by design (REL-07) but the user may expect the title line to stay | `Relatorio_*` PDF, entry "Edição com versão velha." | none |

No Blocker or High finding. D1 to D3 are the ones worth fixing before delivery.

## Spec-precision gaps flagged

- DEL-12 says "o arquivo ou uma página"; there is no page route, only `GET /documents/{id}` (pages empty after the purge) and the evidence link (410). The implementation is consistent with the design; the AC wording should say so.
- ORD-01 location (D8).
- Spec assumption "a tela avisa quando a versão mais recente de um tipo está desatualizada" (assumptions table, DEL): the blocks show `NUMERACAO_DIVERGENTE` and `RASCUNHO_DESATUALIZADO` alerts and the dialog shows nothing about staleness; there is no AC for it, so it is not graded.
- FORA-03 now has three clauses (create nothing, reject linked-only activities, keep shared ones); the tests map to each one.

## Code quality notes

Matches the project patterns (use cases take `uow_factory`, access through `_readable/_editable`, audit with identifiers only, `Gone` and `GenerationRefused` mapped in `presentation/errors.py`). Domain rules are pure (`conclusion_rules.py`, `report_grounding.py`). The purge does the file first and the rows in a unit of its own, and the final transition re-reads the documents under the process row lock (`conclusion.py:68-107`), as designed. Documented guidelines followed: `CLAUDE.md` (no justification field in the conclusion dialog; synthetic data only; key only in the backend). Spot check of the Etapa 5 tests: each maps to a UIG/DEL/REL criterion.

## Requirement traceability update (proposal)

| Requirement | Previous status | Proposed status |
|---|---|---|
| REL-01..11, REL-13..15 | Implementing | Verified |
| REL-12 | Implementing | Implementing (PARTIAL: D3, user decision) |
| DEL-01..03, DEL-05..15 | Implementing | Verified |
| DEL-04 | Implementing | Verified after the D2 test |
| ORD-02 | Implementing | Verified |
| ORD-01 | Implementing | Verified after the D8 answer |
| UIG-01, 03..09 | Implementing / In Tasks | Verified |
| UIG-02 | Implementing | Verified after D1 |
| FORA-03, FORA-07 (`inteligencia-documental`) | Implementing / Verified | Verified |

## Recommendation

**PASS.** The behaviour in scope is implemented and well covered; the real run confirmed every deletion, fallback, locking and read-only rule against a real database and a real browser. Fix tasks, in order: D1 (false 409 on "Salvar"), D2 (`confirmar` omitted), D3 (decide on the grounding limit with the user), then the Low test gaps (D6) and D4/D5/D7. Re-verify D1 and D2 after the fix (loop bound: 3).

Not touched: any code, any other spec, `requeriment.txt`, `test/`, `frontend/src/api/types.ts`, `frontend/src/pages/Dashboard*`, `frontend/src/components/ProcessDialogs.tsx`.
