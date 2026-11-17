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

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
