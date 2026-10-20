# Architecture

The application and repository identity is **ASO Compass**. Preserve legacy `ASO_Target_Finder` filenames only within reference materials and compatibility exports.

## Deployment topology

```text
Browser
  |
  | HTTPS
  v
Hugging Face Static Space
React + Vite + TypeScript
  |
  | JSON API, explicit CORS origin
  v
Render Web Service
FastAPI + SQLModel + deterministic ASO engine
  |             |                 |
  | PostgreSQL  | HTTPS           | optional HTTPS
  v             v                 v
Supabase     Open Targets,      OpenAI Responses API
Postgres     ClinicalTrials.gov  (explanations only)
```

For Phase 1, React should not query scientific tables directly. FastAPI owns validation, authorization, state transitions, database writes, upstream calls, exports, and optional OpenAI calls.

## Backend layers

- `api`: HTTP routing and response schemas only.
- `services`: run orchestration, persistence checkpoints, exports, AI explanation service.
- `domain`: pure scientific transformations and classification rules ported from v4.1.
- `integrations`: Open Targets, ClinicalTrials.gov, OpenAI, Supabase Storage.
- `models`: SQLModel table models.
- `schemas`: public request/response and AI Structured Output models.
- `db`: engine/session lifecycle and migrations.
- `core`: settings, logging, security helpers, error mapping.

Do not mix HTTP requests or database commits into pure classification functions.

## Data model outline

### Run

`id`, `environment`, `owner_id`/`anonymous_session_id`, `disease_id`, `disease_label`, `status`, parameter JSON, normalized input hash, engine version, upstream release metadata, started/completed timestamps, warning count, error code/message, created/updated timestamps.

### Candidate

`id`, `run_id`, identifiers, symbols/names, association scores, constraint fields, variant counts/fractions, G2P fields, drug/trial summaries, `final_call`, call source, deterministic confidence label/explanation, safety note, shortlist position, truncation/completeness fields.

### Evidence

Optional normalized or JSON representation of source-specific evidence. Keep source name, stable external identifier, retrieval time, upstream release, query parameters/hash, raw-cache reference, normalized fields, and completeness state.

### RunEvent

`id`, `run_id`, sequence, stage, level, message, progress numerator/denominator, structured details, timestamp. This powers polling and preserves progress across page refresh.

### ExportArtifact

`id`, `run_id`, format, storage location, SHA-256, byte size, created timestamp, schema/version.

### AIInsight

`id`, `run_id`, optional candidate ID, type, model, prompt version, input hash, output schema version, structured output JSON, source IDs, API response/request ID, token/usage metadata when available, status, reviewer fields, timestamps.

## Run execution on a free Render service

Free Render does not provide a separate free background worker. Start with one in-process queue and one active run. A create request writes a `queued` record and returns immediately. A background task claims it, checkpoints after each stage, and records progress events. On startup, mark stale `running` records as interrupted/retryable rather than leaving them indefinitely running.

This is suitable for a demonstration, not high-volume production. A future production deployment should use a durable job queue/worker or managed task service.

## Caching

- Preserve request-level HTTP cache keys and TTLs from the enhanced engine.
- Cache files on Render are opportunistic only because the filesystem is ephemeral.
- For durable reproducibility, store query hashes, source/release metadata, timestamps, truncation information, and normalized evidence in PostgreSQL; optionally place larger raw responses/exports in Supabase Storage.
- Never confuse a cache hit with current upstream evidence.

## Static example fallback

Bundle small versioned examples under the frontend's public assets. The application home page can open them without the backend. Clearly label them precomputed and display engine/source dates. This makes the educational app useful during Render cold starts or upstream outages.

## Future GPU path

The current workflow is network- and tabular-processing-bound; a GPU does not improve it. A future GPU stage should be a separately versioned downstream service that consumes a frozen shortlist for a genuinely GPU-capable task such as sequence design, accessibility, activity, toxicity, or off-target modeling. It must not be introduced as an accelerator for the existing retrieval logic.
