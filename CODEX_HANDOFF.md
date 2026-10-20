# ASO Compass implementation handoff

## Outcome

Create **ASO Compass**, a shareable web application with a rich, approachable interface for life-science students and researchers. The web app should reproduce the enhanced Python ASO Target Finder v4.1 workflow, preserve provenance, explain limitations, and tolerate free-tier hosting constraints.

Product identity:

- Name: **ASO Compass**
- Tagline: **Evidence-guided target exploration for research and education**
- Repository: `aso-compass`
- Frontend: `aso-compass-web`
- Backend/API: `aso-compass-api`
- Python package namespace: `aso_compass`
- Research-use statement: **For hypothesis generation and education only. Not for clinical decision-making.**

## Recommended build sequence

### Phase 0 — establish the baseline

- Run/import the reference Python engine locally.
- Freeze at least one small deterministic fixture and the documented ALS smoke-test expectations.
- Write characterization tests for the five mutually exclusive tracks, metadata, truncation flags, and export manifest.
- Record any live API drift separately from transformation regressions.

### Phase 1 — backend foundation

- Scaffold FastAPI settings, logging, health endpoints, CORS, SQLModel, Alembic, and tests.
- Add `Run`, `Candidate`, `Evidence`, `RunEvent`, `ExportArtifact`, and optional `AIInsight` models.
- Add `environment` and audit timestamps to mutable records.
- Build `POST /api/v1/runs`, run retrieval, event/progress retrieval, candidate listing, and export endpoints.
- Execute runs with a bounded in-process worker suitable for one Render instance. Persist state after every stage and recover abandoned `running` jobs on startup.

### Phase 2 — frontend

- Build a guided run form with a searchable disease dropdown plus custom MONDO input.
- Add Basic and Advanced modes, parameter explanations, estimated workload, and explicit Full/Quick caveats.
- Show run progress by polling persisted events; do not require a long open request.
- Add sortable/filterable candidate table, track summary, score plot, mechanism distribution, evidence completeness/truncation indicators, gene detail drawer, export panel, and educational glossary.
- Bundle precomputed example runs so the static frontend remains useful while Render wakes.

### Phase 3 — deployment

- Configure the single Supabase project and run Alembic migrations.
- Deploy FastAPI to Render and set secrets in the dashboard.
- Deploy the built frontend to a Hugging Face Static Space.
- Restrict CORS to the exact Space URL and localhost origins.
- Run the smoke-test checklist from both localhost and the Space.

### Phase 4 — optional AI explanation layer

- Add only after deterministic results are stable.
- Use the OpenAI Responses API server-side and Structured Outputs validated with Pydantic.
- Implement `Explain this gene`, `Summarize this run`, and constrained Q&A over saved evidence.
- Store model, prompt version, input hash, response/request identifier, output JSON, sources, and review state.
- Cache identical inputs, cap tokens and request frequency, and provide a global kill switch.

### Phase 5 — authentication and collaboration

- Add Supabase Auth if peer-specific private histories are required.
- Verify access tokens in FastAPI and enforce ownership on every query.
- Add Row Level Security/grants if the frontend later accesses Supabase Data APIs directly.
- Do not expose a database secret to gain convenience.

## Initial API contract

```text
GET    /health/live
GET    /health/ready
GET    /api/v1/config/public
GET    /api/v1/diseases/prefilled
POST   /api/v1/runs
GET    /api/v1/runs/{run_id}
GET    /api/v1/runs/{run_id}/events
GET    /api/v1/runs/{run_id}/candidates
GET    /api/v1/runs/{run_id}/candidates/{gene_symbol}
POST   /api/v1/runs/{run_id}/retry
GET    /api/v1/runs/{run_id}/exports/{format}
POST   /api/v1/runs/{run_id}/ai-summary
POST   /api/v1/runs/{run_id}/candidates/{gene_symbol}/ai-explanation
POST   /api/v1/runs/{run_id}/ai-question
```

Use `202 Accepted` when run creation only queues work. Run states should be `queued`, `running`, `succeeded`, `failed`, or `cancelled`. Return a stable public error code, a safe message, and a request ID; keep traces server-side.

## Preferred prefilled diseases

- ALS — `MONDO_0004976`
- Alzheimer disease
- Parkinson disease
- Huntington disease
- Duchenne muscular dystrophy
- spinal muscular atrophy
- Dravet syndrome
- hereditary transthyretin amyloidosis

Verify every identifier and display label against the current Open Targets ontology before seeding it. The custom input must accept `MONDO:nnnnnnn` and normalize to `MONDO_nnnnnnn`.

## Suggested first Codex prompt

> Read `AGENTS.md`, `CODEX_HANDOFF.md`, `ACCEPTANCE_CRITERIA.md`, and the files under `reference/engine/` in full. Implement Phase 0 and Phase 1 only. Preserve the reference algorithm and add characterization tests before refactoring. Use temporary SQLite for tests and keep the production SQLModel schema PostgreSQL-compatible. Do not use real secrets or the shared Supabase database during automated tests. Run validation and report deviations from the reference behavior.

## Decisions already made

- SQLModel rather than raw SQLAlchemy models.
- Supabase PostgreSQL rather than SQLite for deployed persistence.
- One Supabase project shared by local development and demo for now.
- Hugging Face Static Space for the public science-facing frontend.
- Render for FastAPI.
- React/Vite/TypeScript for the interface.
- Colab notebooks remain available as transparent educational companions.
- Optional OpenAI explanations belong in the backend and do not participate in ranking.
