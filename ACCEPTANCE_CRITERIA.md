# Acceptance criteria

## Scientific parity

- A fixed input fixture yields the same track assignment, precedence, warnings, shortlist rules, and core output columns as the reference Python v4.1 engine.
- Exactly five disjoint candidate tracks cover all annotated candidates: knockdown, splice/upregulation, ambiguous, modifier, and insufficient data.
- Manual override, G2P, ClinVar heuristic, and modifier precedence is unchanged unless a separately approved change is documented.
- Quick/capped work is conspicuously marked incomplete in the UI, API, metadata, and exports.
- Failed upstream lookups remain unknown/failed—not silently converted to negative evidence.

## Usability

- A first-time student can run a prefilled disease without editing code.
- Disease input offers searchable presets plus a validated custom identifier.
- Basic mode exposes essential controls; Advanced mode explains expert controls.
- Progress survives page refresh and shows the current stage.
- Results provide overview cards, filters, sortable table, visual summaries, gene-level evidence, caveats, and downloads without requiring console output.
- At least one precomputed example remains viewable if the backend is asleep or unavailable.
- Keyboard navigation, visible focus, labeled controls, non-color-only status, and responsive layout are checked.

## Reliability and operations

- API requests use bounded timeouts, retries with backoff, and logged request IDs.
- Run stages checkpoint to PostgreSQL; a process restart does not leave a run permanently ambiguous.
- Duplicate submission protection is implemented with an idempotency key or deterministic input hash.
- Local disk is not the only copy of durable results or exports.
- Health endpoints distinguish process liveness from database/upstream readiness.
- Render cold-start behavior has a friendly frontend message and retry.

## Security and privacy

- Repository and built frontend contain no secret values.
- `DATABASE_URL`, OpenAI key, database password, and Supabase secret/service-role key are backend-only.
- CORS uses explicit origins, not `*`, for authenticated or credentialed requests.
- API input sizes and rate limits are bounded.
- Logs exclude credentials, full authorization headers, and sensitive free text.
- The app states that it is not for patient-identifiable data or clinical decisions.
- Ownership checks exist before private multi-user history is enabled.

## AI, when enabled

- AI is disabled cleanly when `AI_ENABLED=false` or no key is configured.
- Responses conform to a versioned schema and refusals/incomplete responses are handled.
- Every panel is labeled AI-generated and cites only evidence supplied or independently validated by the server.
- AI output never changes deterministic database fields or ordering.
- Model, prompt version, input hash, timestamps, source IDs, and response/request ID are auditable.
- Identical requests can be cached; per-user/run limits and output-token caps exist.

## Quality gates

- Backend formatting/lint, typing, unit tests, migration upgrade, and API integration tests pass.
- Frontend formatting/lint, TypeScript checks, unit/component tests, accessibility checks, and production build pass.
- One end-to-end happy path and one upstream-failure path pass.
- A clean clone can be configured using committed examples and documentation only.
- `CITATION.cff`, license decision, data/source acknowledgments, scientific disclaimer, and deployment version are visible.

