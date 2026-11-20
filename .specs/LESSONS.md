# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - When an alert lists offending fields, assert each field individually triggers it with its label in the message
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `domain-rules` · harmful: 0
- features: fundacao
- evidence: validation.md M14/M15; backend/tests/unit/domain/test_process_verification.py:249 (domain-rules)
- last seen: 2026-11-17T01:57:02Z

### L-002 - For versioned reference data with immutability and no-overlap rules, test adding a successor version after the current open-ended version is in use
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `career-versions` · harmful: 0
- features: fundacao
- evidence: CARR-08; backend/tests/integration/api/test_career_api.py:156-177 (career-versions)
- last seen: 2026-11-17T01:57:02Z

### L-003 - When one validation makes another check meaningless, state in the spec whether the dependent check is suppressed and pin it with a test
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `domain-rules` · harmful: 0
- features: fundacao
- evidence: PROC-09; validation.md M20 (domain-rules)
- last seen: 2026-11-17T01:57:02Z

### L-004 - Define day-count convention inclusive or exclusive in the spec whenever a duration in days is displayed
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `domain-rules` · harmful: 0
- features: fundacao
- evidence: PROC-02; backend/app/domain/rules/interstice.py:29 (domain-rules)
- last seen: 2026-11-17T01:57:02Z

### L-005 - When every alert must cite a norm, specify the reference for alerts that have no normative basis
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `domain-rules` · harmful: 0
- features: fundacao
- evidence: PROC-04; backend/app/domain/rules/process_verification.py:20 (domain-rules)
- last seen: 2026-11-17T01:57:02Z

### L-006 - Enforce append-only tables with a database trigger, because REVOKE does not restrict the owning role the app connects as
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `database` · harmful: 0
- features: fundacao
- evidence: SPEC_DEVIATION backend/alembic/versions/0001_initial_schema.py:245 (database)
- last seen: 2026-11-17T01:57:02Z

### L-007 - Test date-range guards on the exact boundary day the spec names, such as on-or-after versus after
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `career-versions` · harmful: 0
- features: fundacao
- evidence: N4 backend/app/application/use_cases/career.py:125 (CARR-10) (career-versions) (+1 more)
- last seen: 2026-11-17T02:17:06Z

### L-008 - Test interval overlap checks with ranges that share exactly one endpoint day on each side
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `career-versions` · harmful: 0
- features: fundacao
- evidence: K1/K2 backend/app/application/use_cases/career.py:77,80 (CARR-08 overlap) (career-versions)
- last seen: 2026-11-17T02:32:56Z

### L-009 - For each date guard test the last allowed day as well as the first rejected day
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `career-versions` · harmful: 0
- features: fundacao
- evidence: K3 backend/app/application/use_cases/career.py:125 (CARR-09/CARR-10) (career-versions)
- last seen: 2026-11-17T02:32:56Z

### L-010 - When a derived flag requires two conditions together, assert a case where only one holds and the flag stays false
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `career-versions` · harmful: 0
- features: fundacao
- evidence: X6 backend/app/application/use_cases/career.py:89 (CARR-08) (career-versions)
- last seen: 2026-11-17T03:07:40Z

### L-011 - Test a date-driven selection with data where the start date and the end date select different candidates, so the date actually used is observable.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `scoring` · harmful: 0
- features: pontuacao
- evidence: M31 backend/app/application/use_cases/scoring.py:112 (scoring)
- last seen: 2026-11-17T14:54:33Z

### L-012 - When a rule says latest version, test it with at least two versions so the latest and the first differ.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `scoring-admin` · harmful: 0
- features: pontuacao
- evidence: M56 backend/app/application/use_cases/scoring_admin.py:136 (scoring-admin)
- last seen: 2026-11-17T14:54:33Z

### L-013 - When a selection rule can match several candidates, the spec must define the tie-break and a test must assert it.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `scoring` · harmful: 0
- features: pontuacao
- evidence: SEL-02 M32 backend/app/application/use_cases/scoring.py:114 (scoring)
- last seen: 2026-11-17T14:54:33Z

### L-014 - Bound the rendered pixel size of user-supplied vector files at upload, not only the megapixels of raster images
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `upload-validation` · harmful: 0
- features: inteligencia-documental
- evidence: DOC-04; validation.md G1; backend/app/infrastructure/files/inspector.py:45 (upload-validation)
- last seen: 2026-11-18T00:46:05Z

### L-015 - A retry counter that is stored but never read is not a retry limit: test that a job past the limit ends failed and is never requeued
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `worker` · harmful: 0
- features: inteligencia-documental
- evidence: PIPE-03; validation.md G2; backend/app/infrastructure/database/repositories.py:1093 (worker)
- last seen: 2026-11-18T00:46:05Z

### L-016 - Test settings wiring from the environment to the limits in use, not only the limits object with its defaults
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `config-wiring` · harmful: 0
- features: inteligencia-documental
- evidence: M111, M112; backend/app/presentation/dependencies.py:184 (config-wiring)
- last seen: 2026-11-18T00:46:05Z

### L-017 - Test a function that counts what a document leaves out with a not valid item in every status it can have, not only the rejected one.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `generation` · harmful: 0
- features: revisao-simplificada
- evidence: B27 backend/app/application/services/generation_inputs.py:89 (generation)
- last seen: 2026-11-20T00:35:51Z

### L-018 - Exercise each flag a rule hands to a shared predicate on every call path that sets it, such as an open-ended period on the manual edit and not only on the classification.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `scoring` · harmful: 0
- features: revisao-simplificada
- evidence: B43 backend/app/application/use_cases/scoring.py:422 (scoring)
- last seen: 2026-11-20T00:35:51Z

### L-019 - Assert a count shown in a filtered list while a filter is active, not only with the default filters.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: revisao-simplificada
- evidence: F3b frontend/src/components/ValidActivitiesSection.tsx:73 (frontend)
- last seen: 2026-11-20T00:35:51Z

### L-020 - Test an exclusion flag at every output layer (list, score, generated documents), not only where the flag is set.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `generation` · harmful: 0
- features: revisao-simplificada
- evidence: DUP-03 SEG-02 backend/tests/integration/api/test_generated_validity_acceptance.py:58-95 (generation)
- last seen: 2026-11-20T00:35:51Z

### L-021 - A no-horizontal-scroll requirement at a given width needs a rendered browser check, because a jsdom regex over the CSS does not prove it.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: revisao-simplificada
- evidence: SEC-12 frontend/src/components/ActivityWorkspace.test.tsx:173-179 (frontend)
- last seen: 2026-11-20T00:35:51Z

### L-022 - Map a refusal code in the failure table of the background worker too when a use case shared with the request path can raise it.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `generation` · harmful: 0
- features: revisao-simplificada
- evidence: SEG-05 backend/app/application/use_cases/generated_documents.py:307-318 (generation)
- last seen: 2026-11-20T00:35:51Z

### L-023 - State the precedence order in the spec when several rejection reasons can apply to the same item.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: revisao-simplificada
- evidence: SP1 backend/tests/unit/domain/test_activity_validity.py:290-312 (spec)
- last seen: 2026-11-20T00:35:51Z

### L-024 - List every value of a user-facing reason enum in the spec with its text, including the values the implementation adds.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: revisao-simplificada
- evidence: SP2 frontend/src/labels.test.ts:129-130 (spec)
- last seen: 2026-11-20T00:35:51Z

### L-025 - Say in the spec whether a field the user did not change is validated again on edit.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: revisao-simplificada
- evidence: SP5 backend/tests/integration/api/test_activity_edit_rules_api.py:179-198 (spec)
- last seen: 2026-11-20T00:35:51Z

### L-026 - Write the placement of a new UI control as a testable condition (container, landmark or sibling element), because a vague position phrase leaves no assertion that can fail.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `frontend` · harmful: 0
- features: correcoes-auditoria
- evidence: CAINI-01 ProcessStep1.tsx:189-196 (frontend)
- last seen: 2026-11-20T04:37:32Z

### L-027 - When a requirement fixes the exact names of constants or fixtures, pin them with an assertion or a recorded grep, because renaming a constant breaks no behavior test.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `tests` · harmful: 0
- features: correcoes-auditoria
- evidence: CAREF-04 scoring_variants.py:15-18 (tests)
- last seen: 2026-11-20T04:37:32Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
