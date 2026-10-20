# ADR-006: Keep guarded Q&A subordinate to deterministic facts

Date: 2026-10-20

## Status

Accepted.

## Context

A generated answer could cite an allow-listed candidate record while still misstating that candidate's
classification. Citation validation proves provenance identity; it does not prove semantic consistency.
Because classifications, scores, evidence counts, and shortlist positions are deterministic outputs, the
Q&A layer needs an independent enforcement boundary.

## Decision

- Generate selected-candidate fact cards and false-premise corrections in FastAPI, never in the model.
- Include those facts and corrections in the model packet, while visually labeling the fact cards as
  server generated and not AI.
- Require structured candidate fact checks in every model response and compare them exactly with SQLModel
  records before persistence or disclosure.
- Reject prose that directly assigns a conflicting deterministic classification.
- Reject numeric claims whose values do not occur in the supplied saved sources.
- Version the prompt and output schema as `saved-evidence-question-v2`; do not reuse v1 cache entries.
- Retain source allow-list validation and all existing request safety controls.

## Consequences

The interface can correct a user's false classification premise even if generation later fails. A model
response that contradicts protected fields returns a generic upstream-style failure and is not saved.
The checks are deliberately conservative and do not make generated prose authoritative; scientific review
of the Q&A evaluation set remains a release requirement.
