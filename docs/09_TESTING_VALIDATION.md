# Testing and validation strategy

## Test pyramid

### Pure domain tests

Extract classification, precedence, warnings, confidence explanations, normalization, shortlist filtering, and source-row transformations into pure functions. Test boundary values such as 4 versus 5 records and LoF fractions around 0.25 and 0.60.

### Characterization/golden tests

Before refactoring, capture normalized fixtures from the reference engine and assert stable outputs. Exclude inherently changing fields such as retrieval time and live release counts. Keep expected scientific fields human-readable for review.

### Integration tests

- SQLModel persistence and Alembic migration on PostgreSQL;
- run state transitions and stale-run recovery;
- mocked Open Targets and ClinicalTrials.gov error/retry/truncation behavior;
- export creation and SHA-256 manifest;
- authentication/ownership when enabled;
- optional OpenAI service with recorded synthetic responses, never a real key in routine tests.
- guarded-Q&A preflight with synthetic identifier, patient-specific, clinical-advice, ranking-override, prompt-injection, and safe-but-unsupported cases; no live model or shared database.

### Frontend tests

- disease selector/custom validation;
- Basic/Advanced modes;
- queued/running/succeeded/failed/interrupted states;
- truncation and failure warnings;
- filtering/sorting and gene detail;
- cold-start fallback;
- accessible names, keyboard focus, contrast, responsive layout;
- no secret-like values in production output.

### End-to-end tests

1. open precomputed example without backend;
2. submit a bounded run, poll progress, view results, and export;
3. simulate backend cold start;
4. simulate an upstream timeout and confirm it is not shown as negative evidence;
5. refresh during a run and recover progress;
6. confirm one environment cannot appear in the other's default history view.

## Invariants

- candidate IDs are unique within a run;
- score ranges are valid;
- track sets are pairwise disjoint and their union equals all candidates;
- shortlist entries exist in annotated candidates and obey filters;
- cap/truncation flags agree with returned/available counts;
- succeeded runs contain version, parameters, sources, warnings, and validation result;
- failed runs have a safe code/message and preserved prior events;
- deterministic fields cannot be modified by AI output.

## Live validation

Retain the documented bounded ALS connectivity smoke test as a manual/opt-in check. Because upstream data changes, verify schema, identifiers, invariants, and plausibility rather than pinning exact counts forever. Record date, release, request parameters, and deviations.

## Deployment smoke test

- `/health/live` returns quickly;
- `/health/ready` reports database connectivity and app readiness without leaking secrets;
- frontend production assets load from the Space;
- CORS accepts the exact Space and rejects an unlisted origin;
- one bounded run persists across a frontend refresh;
- export contents and checksums are correct;
- restart recovery is exercised;
- AI-off behavior is clean;
- logs contain request/run IDs but not credentials.

## Scientific review gate

Any change to thresholds, consequence categories, indirect associations, evidence precedence, shortlist sorting, or warning language requires a written rationale, before/after fixture results, and manual scientific review. Treat such a change as a versioned behavior change, not a UI refactor.
