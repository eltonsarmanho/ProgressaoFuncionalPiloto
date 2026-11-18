# Verification: documents outside the interstice (FORA-01..09)

**Date**: 2026-11-18
**Spec**: `.specs/features/inteligencia-documental/spec.md` (story "Documentos fora do interstício", lines 433-452)
**Tasks**: Phase 18, T141-T145
**Diff range**: `be7c11b~1..7a8e4f5` (commits `be7c11b`, `df59346`, `0c6fbff`, `a1b651c`, `7a8e4f5`), HEAD `7a8e4f5`
**Verifier**: independent (author != verifier), tlc-spec-driven, evidence-or-zero
**Isolation**: mutants and probes ran in `git archive` copies under the session scratchpad; the repo tree was never mutated (porcelain before and after: `requeriment.txt`, `test/` only). No `Documentos/` or `Modelos/` access, no MariTalk call, no push or deploy. All probes use synthetic text.

## Verdict

**FORA-01, 02, 04, 05, 06, 07, 08, 09: Verified. FORA-03: Partial** (holds for a document that is processed outside; does not hold when an edited or validated activity already existed before the document became outside). No Blocker. One Medium defect (D1), the rest Low or informational. 43 of 50 mutants killed; 3 survivors are equivalent; 4 are real test gaps (low).

## Gate

| Check | Result |
| ----- | ------ |
| Backend `ruff check .` | clean |
| Backend `pytest -q` (full, pristine copy of HEAD) | 4613 passed, 6 deselected (`maritalk_live` and live markers), 0 failed |
| Frontend `tsc --noEmit`, `eslint src` | clean |
| Frontend `vitest run` | 245 passed, 1 skipped (the dist-dependent test, `REQUIRE_DIST` unset in the scratch copy), 26 files |
| `validate_spec.py`, `validate_state.py` | 0 errors |
| `validate_tasks.py` | 0 errors, 6 warnings (`Tests: none`, unchanged) |
| New FORA tests collected | `test_document_period.py` 10, `test_document_analyzer_outside_interstice.py` 10, `test_process_outside_interstice.py` 4, `test_documents_outside_interstice_api.py` 8, `DocumentList.test.tsx` 9, plus 1 CSS case in `styles.test.ts`; the diff deletes no test (the six rewritten analyzer tests keep their assertions, see I1) |

## Spec-anchored acceptance criteria

| Criterion | Spec-defined outcome | Evidence (`file:line`, assertion) | Result |
| --------- | -------------------- | --------------------------------- | ------ |
| FORA-01 all dated activities `FORA` | alert `DOCUMENTO_FORA_DO_INTERSTICIO`, no activity | Rule `backend/app/domain/rules/document_period.py:15-17`; applied at `document_analyzer.py:251`, activities cleared at `:269`. Tests `test_document_analyzer_outside_interstice.py:51-57` (`result.activities == ()`, `status_code == OUTSIDE.value`), `test_document_period.py:12-14`, `test_process_outside_interstice.py:38-56` (no activity, no evidence). Probe: day boundary 22/11/2024 outside, 23/11/2024 inside; 23/11/2026 inside, 24/11/2026 outside | Verified |
| FORA-02 banner text and dates | exact text; latest date; `mm/aaaa` for month precision; interstice dates | Text built at `frontend/src/labels.ts:148-157`; `DocumentList.test.tsx:364-371` asserts the exact string `"Data do documento 10/03/2022, fora do interstício (23/11/2024 a 23/11/2026): não será processado nas próximas etapas"`; `:373-378` asserts `03/2022`. Latest date `test_document_analyzer_outside_interstice.py:72-81` (`== "2023-05-02"`); API `test_documents_outside_interstice_api.py:86-97`. Alert colour `styles.test.ts` (FORA-02 case) | Verified (test gap: date taken from start or end of a period is not asserted, B14; probe confirms a 2020-01-10 to 2021-01-09 period gives `document_date 2021-01-09`) |
| FORA-03 excluded from Etapas 3, 4, 5 | no activity, score row, table row, report entry or comprovante page from it | Fresh outside document: `test_documents_outside_interstice_api.py:125-135` (activities list, evidences and scoring JSON do not mention the document) and `:151-162` (link is 409). Etapas 3 to 5 read only activities and evidences (`process_verification.py` and `scoring_verification.py` do not read documents; final-document assemblers take activity evidences), so absence of activities means absence everywhere | Partial: see D1 (reprocess after the document became outside) and D2 (Etapa 3 link list) |
| FORA-04 buttons and refusal | Visualizar, Baixar, Reprocessar, Excluir; no Classificar, no Criar atividade | UI `DocumentList.test.tsx:386-390` (`toEqual(["Visualizar","Baixar","Excluir","Reprocessar"])`, none of Criar atividade, Classificar, Substituir); code `DocumentList.tsx:390,423,434`. API 409 with `code == "DOCUMENTO_FORA_DO_INTERSTICIO"` for classify (`test_documents_outside_interstice_api.py:138-148`, guard `documents.py:720`) and for link (`:151-162`, guard `evidences.py:112`); download, reprocess and delete still work (`:165-170`) | Verified (the API refuses the link, not a "create activity" call; see I3) |
| FORA-05 one `DENTRO` or `PARCIAL` keeps the document | processed normally, outside activity stays `FORA_DO_INTERSTICIO` | `test_document_analyzer_outside_interstice.py:101-113` (`reasons == [(FORA_DO_INTERSTICIO,), ()]`), `:116-125` (`FORA` next to a month crossing the limit: 2 activities, no alert); `test_document_period.py:17-24` | Verified |
| FORA-06 no usable date | rule not applied | `test_document_analyzer_outside_interstice.py:128-142,145-151` (undated, date not proven by the page, no interstice); `test_document_period.py:27-40`. Probe: inverted interstice (`NAO_VERIFICAVEL`) leaves the document processed | Verified |
| FORA-07 reprocess re-evaluates | widen: alert gone, activity created; narrow: alert applied | `test_process_outside_interstice.py:69-83` (`status_code is None`, one new activity) and `:86-96` (`status_code == OUTSIDE`, old draft `REJEITADA`) | Verified |
| FORA-08 count in the summary | "N fora do interstício" | `DocumentList.test.tsx:408-419` (`toHaveTextContent("2 fora do interstício")`, `"1 pendente de revisão"`) and `:421-424` (`0 fora do interstício`); code `DocumentList.tsx:83-94` | Verified |
| FORA-09 not pending, not an error | status `PROCESSADO`, no `REQUER_REVISAO` | `test_document_analyzer_outside_interstice.py:56` (`status is PROCESSADO`), `test_process_outside_interstice.py:44-46`, `DocumentList.test.tsx:401-406`; nothing in the frontend gates the step on document status (grep of `REQUER_REVISAO` and `status_code` in `frontend/src`) | Verified |

CLAUDE.md rule 4 matches the spec text and the behavior, except for the D1 exception (rule 4 says the document "não aparece nas Etapas 3, 4 e 5") and the missing sentence that with month precision the banner shows `mm/aaaa` (the author already notes this).

## Discrimination sensor

Mutants ran in a scratch copy, one at a time, against the targeted tests (11 backend files, `DocumentList.test.tsx`, `styles.test.ts`). A survivor of that set was not re-run against the full suite; the survivors are code that no FORA or changed test reaches, and the 3 equivalent ones are equivalent by reading.

**Backend, 29 mutants: 26 killed, 3 survived**

| # | Mutation (file) | Result |
| - | --------------- | ------ |
| B1 | `all` to `any` in the rule (`document_period.py:17`) | killed |
| B2 | drop `bool(dated)` (empty list becomes outside) | killed |
| B3 | `PARCIAL` counted as `FORA` | killed |
| B4 | `SEM_DATA` no longer ignored | killed |
| B5 | `None` no longer ignored | killed |
| B6 | rule never applied in the analyzer (`:251`) | killed |
| B7 | no `activities.clear()` (`:269`) | killed |
| B8 | status `REQUER_REVISAO` instead of `PROCESSADO` | killed |
| B9 | `min` instead of `max` for the document date | killed |
| B10 | precision forced to `DAY` in the detail | killed |
| B11 | `interstice_end` written as the start | killed |
| B12 | period state recorded after the no-item return (undated by item) | killed |
| B13 | `yearly` flag dropped from the period state (open-ended yearly) | killed |
| **B14** | `_latest_date` reads only `event_date` (`:402-405`) | **survived** |
| B15 | month precision ignored for the period state | killed |
| B16 | outside document gets category `SEM_ITEM_DE_PONTUACAO` (`document_processing.py:259`) | killed |
| B17 | alert `detail` not stored (`_alert_dict`) | killed |
| B18 | classification not refused (`documents.py:720`) | killed |
| B19 | `refuse_outside_interstice` is a no-op | killed |
| B20 | refusal with the wrong code | killed |
| B21 | link not refused (`evidences.py:112`) | killed |
| B22 | list never reads the outside data | killed |
| B23 | list reads the alert for every document | survived, equivalent (a document without the alert has no such alert; it is only the "no extra query" optimisation) |
| B24 | `outside_interstice` property inverted | killed |
| B25 | schema flag always false | killed |
| B26 | precision not sent | killed |
| B27 | interstice start and end swapped in the schema | killed |
| B28 | alert `detail` not exposed in the detail schema | killed |
| B29 | `_outside_of` ignores the alert code | survived, equivalent (only the outside alert carries `detail`) |

**Frontend, 21 mutants: 17 killed, 4 survived**

| # | Mutation | Result |
| - | -------- | ------ |
| F1, F2, F3 | Criar atividade, Classificar or Substituir shown on the outside row | killed |
| F4, F5 | banner not rendered; row not highlighted | killed |
| F6, F7 | month precision ignored; month shown as `aaaa/mm` | killed |
| **F8** | pending count includes outside documents | survived, equivalent: an outside document is always `PROCESSADO`, so the filter cannot differ for API data |
| F9, F10 | outside count off by one; count omitted | killed |
| F11 | Reprocessar disabled on the outside row | killed |
| **F12** | Excluir disabled on the outside row | **survived** (`DocumentList.test.tsx:386-390` lists button labels, which includes disabled buttons; no test clicks Excluir or Visualizar on an outside row) |
| F13 | Baixar hidden | killed |
| F14, F15, F16 | banner interstice dates swapped; wording changed; document date replaced by the interstice start | killed |
| **F17** | fallback banner text removed when the API sends no dates (`DocumentList.tsx:78`) | **survived** (the fallback label has no test) |
| F18 | banner colour lost in the CSS | killed |
| F19 | outside flag read as `!== false` | killed |
| F20 | justification field added to the banner | killed |
| **F21** | Visualizar disabled on the outside row | **survived** (same cause as F12) |

Total 50 mutants: 43 killed, 7 survived (3 equivalent: B23, B29, F8; 4 real gaps: B14, F12, F17, F21, all Low). Scratch copies were discarded; the repo porcelain is unchanged.

## Edge cases probed (executed in the scratch copy, synthetic text)

Interstice 23/11/2024 to 23/11/2026 unless noted.

| Case | Observed |
| ---- | -------- |
| Month `outubro de 2024` (whole month before) | outside, `date_precision MONTH`, document date 2024-10-01 |
| Month `novembro de 2024` and `novembro de 2026` (cross a limit) | not outside, 1 activity, `DATA_PARCIAL` (matches DATA-10) |
| Month `dezembro de 2026` (whole month after) | outside, MONTH |
| Period ending 22/11/2024 | outside |
| Period ending 23/11/2024 (boundary day, `PARCIAL`) | processed, 1 activity |
| Open-ended yearly function starting 2020 | processed (runs to the end of the interstice, `DATA_FIM_AUSENTE`) |
| Open-ended yearly function starting 10/12/2026 | outside |
| Closed period 2020-2021 | outside, `document_date 2021-01-09` |
| Banca outside plus open-ended yearly function from 2020 (two groups) | both created, no alert |
| Banca outside plus function starting after the interstice (two groups) | outside, no activity |
| Dated outside plus a distinct undated activity | outside, **no activity at all** (the undated one is dropped with the document, as FORA-01 says; see I2) |
| Dated inside plus undated | both created |
| Other professor, wholly outside | `PROCESSADO`, alerts: only `DOCUMENTO_FORA_DO_INTERSTICIO` (**no `DOCENTE_DIVERGENTE`**, see D3) |
| Other professor, inside | `REQUER_REVISAO` with `DOCENTE_DIVERGENTE` (unchanged) |
| Inverted interstice | rule not applied |

Reprocess scenarios (API level, simulated MariTalk):

| Scenario | Observed |
| -------- | -------- |
| Untouched draft, interstice narrowed, reprocess | document outside, `activity_count 0`, the old draft becomes `REJEITADA` and stays as a zero-point row (documented and tested) |
| Activity **validated**, interstice narrowed, reprocess | document outside; activity stays `VALIDADA` (version 2) with its evidence to the document; it stays in the Etapa 3 list; scoring row `NAO_PONTUADA 0.00` (the engine itself marks it outside the interstice, total drops from 2.00 to 0.00); the document list shows `outside_interstice true` and `activity_count 1` |
| Activity **edited** (still `AGUARDANDO_REVISAO`), narrowed, reprocess | the edited draft stays linked, `activity_count 1`, outside banner shown |
| Same, then widened back and reprocessed | document no longer outside, `activity_count 2`: the edited draft stays and a new v1 draft is created from the same page (PIPE-09 behavior, not new, but the outside flip makes it easy to reach) |

## Defects and observations

| ID | Severity | Finding | Evidence | Recommendation |
| -- | -------- | ------- | -------- | -------------- |
| D1 | Medium | After a reprocess that turns a document outside, an activity the user edited or validated stays linked to it. FORA-03 ("nenhuma atividade, linha de pontuação ... vem dele") and the banner ("não será processado nas próximas etapas") are then false for that document: it still has activities in Etapa 3, a scoring row in Etapa 4 (0 points, because the engine rejects the out-of-period date), and an evidence that would carry its pages into the Comprovante. The Etapa 2 row shows `activity_count 1` next to the banner. Not exploitable without a prior edit or validation. | probe above; `documents.py:523-541` (`_reject_untouched_drafts` only touches version-1 drafts of the retired run) | Do not auto-reject validated or edited work (silent loss of user decisions, against the "agem na hora" spirit of rule 5 and against rule 1 where the user validates). Instead: (1) amend FORA-03 and CLAUDE.md rule 4 to "nenhuma atividade criada por ele; as já editadas ou validadas permanecem", and (2) make the state visible: add a second line to the banner ("N atividade(s) já editadas ou validadas continuam ligadas a este documento; revise na Etapa 3") from a count the list already has (`activity_count`), and (3) keep them out of the final documents by the existing `FORA_DO_INTERSTICIO` row status. The lead should decide between this and a stricter exclusion; a fix task for the banner line and tests is small. |
| D2 | Low | The Etapa 3 "Vincular documento" dropdown lists documents outside the interstice. Choosing one ends in the 409 message. FORA-03 says the document does not take part in Etapa 3. | `frontend/src/components/ActivityReviewList.tsx:66` (`documents.map` with no filter); `ProcessActivities.tsx:69` passes the full list | Filter `!d.outside_interstice` in the options; add one test. |
| D3 | Low (documentation, behavior acceptable) | `validation.md` line 483 says a wholly outside document of another professor ends `PROCESSADO` with the outside alert and "`DOCENTE_DIVERGENTE` is still stored". It is not: the analyzer returns at `document_analyzer.py:251` before `_same_professor` (`:257`). Probe: alerts contain only the outside alert. The document is not pending either way (FORA-09), so the user loses only the divergence hint on a document that will not be processed. | probe `DIVERGENT+FORA` | Correct the sentence (or move the professor check before the rule if the hint is wanted). |
| D4 | Low (test gaps) | B14, F12, F21, F17 survived: no test for the document date taken from a period, none that Excluir and Visualizar are usable on an outside row, none for the fallback banner without dates. | mutants above | Add four small assertions: a period activity gives its end date; click Excluir and Visualizar on the outside row; render with `outside_interstice true` and no dates and expect the label of the code. |
| I1 | Info | SUG-09 (spec line 167) still says the outside activity is always kept; FORA-01 and FORA-05 narrow it. Author already flagged it. Six old analyzer tests were rewritten to add a second inside activity: the asserted outcomes are unchanged, so this is an adaptation to the new rule, not a weakening. | `git diff be7c11b~1 HEAD -- backend/tests/unit/application/test_document_analyzer_*` | Add "(see FORA-05)" to SUG-09. |
| I2 | Info | A wholly outside document drops its undated activities too, and the outside row offers no Criar atividade, so an undated activity that was in fact inside the period must be created by hand in Etapa 3 without a link to the document (the link is 409). Spec-consistent (FORA-01, FORA-04). | probe `FORA+UNDATED` | Accept; mention in the user guide. |
| I3 | Info | The 409 for "Criar atividade" exists only on the link call (`evidences.py:112`); the plain activity creation cannot know the document. The UI hides the button, so only a direct API client could leave an unlinked activity behind. | `ProcessDocuments.tsx` (`ActivityFromDocument` creates, then links) | Accept. |
| I4 | Info | The banner shows the interstice that was current when the document was processed (stored in the alert `detail`). After an Etapa 1 change the banner keeps the old dates until Reprocessar. This is the accepted assumption in the spec decision row (line 44). | `documents.py:361-394` | Accept. |

## Answer to the author's open point (edited or validated activity after reprocess)

Exact behavior: Reprocess retires the active run and, for the activities of the retired run, rejects only those still `AGUARDANDO_REVISAO` at version 1 (`documents.py:523-541`). An activity that was validated, or edited (version above 1), is kept with its link and its evidence. If the new reading puts the document outside the interstice, no activity is created, the document gets the outside alert, and the kept activity remains visible in Etapa 3 and as a scoring row in Etapa 4 (probe: `VALIDADA`, `NAO_PONTUADA`, 0.00). If the interstice is widened again and the document reprocessed, the kept edited draft stays next to a new v1 draft of the same page (duplicate review rows, pre-existing PIPE-09 behavior).

Risk: (a) the screen contradicts itself (banner says not processed, row says 1 activity); (b) a validated activity that the engine now scores 0 is a silent drop of points the user had accepted, with no message on Etapa 2; (c) its evidence still points to a document the user was told is out of the process. The risk is bounded: the scoring engine already refuses to score an out-of-period date, so no wrong points reach the total, and this only happens after the user edited or validated before narrowing the interstice.

Recommendation: keep the current non-destructive behavior, record it in the spec (FORA-03 wording) and make it visible (D1), and filter the dropdown (D2). Do not auto-reject validated or edited activities.

## Requirement traceability update

| Requirement | Previous | New |
| ----------- | -------- | --- |
| FORA-01, 02, 04, 05, 06, 07, 08, 09 | Implementing | Verified |
| FORA-03 | Implementing | Partial (D1, D2) |

## Summary

**Overall**: conditional PASS. The core rule, the API guards, the banner and the summary are correct, with a discriminating test set (43 of 50 mutants killed, the 3 survivors in the implementation are equivalent). Before closing the feature: decide D1 (wording plus a banner line), fix D2, correct D3, and add the four assertions of D4. These are fix tasks of one commit each at most; no re-run of the whole feature is needed.
