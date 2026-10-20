# ADR-004: Ship guarded Q&A backend disabled pending review

Date: 2026-10-20

## Status

Superseded by ADR-005.

## Context

Free-text questions introduce privacy, prompt-injection, unsupported-evidence, and clinical-interpretation risks that are absent from the fixed-input explanation features. General `AI_ENABLED` is already used locally for candidate explanations, summaries, and comparisons, so it cannot also serve as the release approval for Q&A.

## Decision

- Add `POST /api/v1/runs/{run_id}/ai-question`, guarded by both `AI_ENABLED` and a separate `AI_QA_ENABLED` flag that defaults to false.
- Run deterministic safety preflight before database reads or model calls.
- Require zero to three explicit saved-candidate selections; do not infer authorization or selection from free text.
- Route only recognized saved-run and selected-candidate evidence topics. Return `unsupported_by_saved_evidence` without a model call for everything else.
- Send only server-loaded saved evidence to the model and require a strict structured response with allow-listed source IDs.
- Persist the validated answer, provenance, and a SHA-256 cache identity, but never persist the raw question.
- Keep the frontend absent and the Q&A flag false until scientific/safety fixture review and production log verification are complete.

## Consequences

The endpoint can be tested end-to-end without making it available accidentally when other AI features are enabled. The deterministic topic router is intentionally conservative and may decline some answerable questions; expanding it requires new reviewed fixtures. Regex preflight remains defense in depth and does not replace operational privacy review.
