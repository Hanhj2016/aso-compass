# Implementation status

Updated: 2026-10-21

## Completed locally

- Phase 0 repository foundation and characterization fixtures.
- Phase 1 FastAPI API, SQLModel persistence, Alembic migrations, bounded worker, recovery, exports, and environment isolation.
- Deterministic v4.1 track/precedence behavior with drug, trial, constraint, ClinVar/EVA, and G2P enrichment provenance.
- Phase 2 React/Vite/TypeScript workflow, progress recovery, candidate exploration, downloads, responsive layout, and offline ALS example.
- Input-size, queue, and per-client run-admission bounds; explicit CORS and security response headers.
- Deny-by-default PostgreSQL Row Level Security on every application table; no direct browser Data API path.
- Backend format/lint/type/unit checks, fresh SQLite migration, disposable PostgreSQL 16 upgrade/downgrade/re-upgrade rehearsal, frontend type/lint/unit/build checks, desktop/mobile Playwright checks, and production Docker image build.
- A bounded live ALS connectivity check recorded in `docs/validation/2026-10-19-als-live-smoke.md`.
- Supabase migration through `20261020_0003`, six-table RLS verification, empty-state verification, and API database-readiness smoke recorded in `docs/validation/2026-10-20-supabase-migration.md`.
- Phase 4 first increment: backend-only candidate evidence explanations using the OpenAI Responses API, strict Pydantic Structured Outputs, source allow-list validation, input-hash caching, persisted `AIInsight` provenance, rate limiting, and a separately labeled candidate-drawer UI. The feature remains disabled by default and all automated tests use a fake provider.
- Phase 4 second increment: saved-run AI summaries over deterministic aggregates and a bounded set of candidate excerpts, with strict structured output, source allow-list validation, caching, provenance, rate limiting, and a separate results-page panel. The model cannot re-rank candidates or select a best target.
- Phase 4 third increment: constrained comparisons for exactly two or three saved candidates, with canonicalized cache identity, exact candidate-set validation, source allow-list validation, and a table selection workflow. Comparisons explain differences and shared evidence gaps without naming a winner.
- Phase 4 evaluation gate: a six-case offline fixture dataset and deterministic graders for schemas, citation allow-lists, required caveats, unsafe recommendation language, exact track counts, and comparison identity. Engineering checks run in CI; scientific annotation is explicitly pending and blocks guarded Q&A release readiness.
- Guarded-Q&A workflow: a results-page panel accepts a bounded research question and zero-to-three explicit candidate contexts. Deterministic preflight runs before persistence, retrieval, or model requests; a conservative saved-evidence router prevents unsupported questions from calling the provider; model answers use a strict cited schema and source allow-list validation; and raw questions are not persisted. Schema v2 adds server-generated fact cards, false-classification premise correction, exact candidate-fact validation, conflicting-classification rejection, and unsupported-number rejection. The workflow follows the global `AI_ENABLED` switch. Its 29 synthetic cases cover supported wording, unsupported saved-evidence questions, likely patient identifiers, patient-specific interpretation, clinical advice, ranking overrides, and prompt injection.
- Deployment-readiness hardening: Render and Hugging Face configuration was rechecked against current official documentation; container builds exclude environment files and run as a non-root user; PostgreSQL pooling is bounded for the Supabase session pooler; Static Spaces can consume the public API URL through Hugging Face runtime variables; CI scans the production browser bundle for secret markers; and a read-only deployed health/CORS/frontend smoke script is available.
- Automated Static Space publishing: the existing GitHub CI builds the frontend with the public Render API URL, validates and audits the bundle, and publishes only `README.md` plus `dist/` after all backend and frontend gates pass. Hugging Face authentication uses a repository-, branch-, and workflow-scoped Trusted Publisher with short-lived GitHub OIDC credentials, leaving GitHub as the only manually maintained source repository.
- Bilingual guided learning path: the Learn view now provides English and Simplified Chinese explanations of the evidence pipeline, five deterministic tracks, evidence-reading order, AI boundaries, minimum terminology, knowledge checks, and a direct walkthrough into the bundled ALS example.

## Deliberately not enabled

- Optional AI explanations remain off by default. Deterministic results do not depend on AI.
- Guarded free-text Q&A is present when global AI is enabled. Its scientific/safety fixture review remains pending, so it is not yet cleared for a public deployment.
- Authentication/private histories remain out of scope for the public Phase 1 demonstration.

## External release gates

1. Choose and add the repository software license after reviewing reference/data-source terms.
2. Complete the first OIDC GitHub Actions deployment and verify the generated Space payload and assigned host.
3. Run the deployed smoke checklist in `docs/10_DEPLOYMENT_CHECKLIST.md` after each release-affecting configuration change.

Do not place any of those credentials in repository files or frontend build variables.
