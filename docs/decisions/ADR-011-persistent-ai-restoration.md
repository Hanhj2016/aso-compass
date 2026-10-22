# ADR-011: Persist and restore exact-match AI interpretations

## Status

Accepted.

## Context

Live-run summaries and candidate explanations were stored in `AIInsight`, but the frontend did not restore
them after a reload. Versioned educational examples generated a fresh interpretation on every request.
Both behaviors could create avoidable OpenAI usage.

AI prose is valid only for the evidence packet and generation contract that produced it. Reusing text by
disease or gene name alone could present stale or incorrectly sourced claims.

## Decision

1. Use `AIInsight` for both run-scoped and example-scoped generated interpretations. Exactly one owner is
   required; example insights never pretend to be user runs.
2. Identify new cached output with a unique SHA-256 key over environment, owner, optional candidate
   subject, insight type, model, prompt version, output-schema version, and canonical evidence input hash.
   Reserve that key before calling the model. Concurrent identical requests reuse a completed winner or
   receive a short retry response instead of making another OpenAI call; abandoned reservations expire.
3. Add authenticated GET routes for run summaries and candidate explanations. A GET cache miss never calls
   OpenAI.
4. Rebuild the current canonical packet and revalidate the saved structured output and all source IDs before
   returning it.
5. Let the frontend restore saved output after AI access is unlocked. POST remains generate-on-miss and
   returns an exact saved match when one exists.
6. Keep generated output separate from deterministic `Run`, `Candidate`, and `Evidence` fields. Persistence
   cannot change classifications, scores, shortlist membership/order, exclusions, or warnings.

## Consequences

- Refreshing the page or reopening candidate evidence does not require another model call when an exact
  valid interpretation exists.
- Changing evidence, model, prompt, schema, environment, run, example, or candidate identity invalidates
  reuse by construction.
- The shared access token remains required to read generated text.
- Versioned examples can reuse generated interpretations without inserting their deterministic bundle into
  the run tables.
- Existing rows receive collision-free legacy cache keys during migration; newly generated rows receive
  deterministic keys.
