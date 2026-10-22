# ADR-010: Guarded AI for versioned educational examples

## Status

Accepted.

## Context

The frontend includes a versioned ALS result that remains available when live scientific sources or the API are unavailable. AI interpretation was previously disabled because the example is not a persisted run and the existing AI endpoints accept only database-backed run UUIDs.

Sending an evidence bundle supplied by the browser would weaken provenance and allow arbitrary evidence to enter the prompt. Persisting the example as a user run would also blur the distinction between immutable educational material and newly generated analyses.

## Decision

The API owns an allow-list of versioned example bundles and exposes separate `/api/v1/examples/{example_id}/...` AI endpoints. These endpoints:

- load only server-packaged example data;
- construct the same evidence packets used for persisted runs;
- enforce the same shared access token, question-safety rules, rate limits, structured outputs, deterministic-field checks, and source-ID validation;
- do not insert the example, candidates, or evidence into PostgreSQL;
- persist only validated generated interpretations as example-scoped `AIInsight` records; and
- reuse an insight only when environment, example, subject, evidence hash, model, prompt version, and
  output-schema version all match.

The frontend continues to load the deterministic example locally. It explicitly states that optional AI interpretation requires the API and an unlocked access token.

## Consequences

The deterministic example stays offline-ready and immutable, while AI features still require network
access. The first exact request may consume OpenAI API usage; subsequent requests restore the validated
saved interpretation. A changed evidence bundle, model, prompt, or schema deliberately invalidates reuse.
The server and frontend copies of the example are checked for exact JSON parity in automated tests.
