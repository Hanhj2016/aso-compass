# ASO Compass

Prepared: 2026-10-19

This is a planning and implementation handoff for building **ASO Compass**, based on the enhanced Python ASO Target Finder v4.1 workflow.

> **ASO Compass** — Evidence-guided target exploration for research and education.

Target architecture:

- React + Vite + TypeScript static frontend deployed identically to two Hugging Face Spaces;
- FastAPI backend on Render;
- SQLModel and Alembic with a shared Supabase PostgreSQL project;
- optional OpenAI explanation features, isolated from deterministic scientific scoring;
- the R and Python Colab notebooks retained as reproducible teaching companions.

The repository includes the deterministic baseline, FastAPI/SQLModel backend, React/Vite interface,
versioned offline example, deployment configuration, and automated backend/frontend/end-to-end checks.
No credentials are included.

The frontend follows an academic research-portfolio structure: **Portfolio** presents the research question
and demonstrated capabilities; **Case Studies** contains six reviewed teaching cases; **Research Workspace**
supports live and saved analyses; and **Methods & Glossary** exposes the interpretation method and vocabulary.

Run the backend locally:

```bash
cd backend
python -m pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The default database is local SQLite for setup convenience. Configure the documented Supabase PostgreSQL
URL for shared local/demo persistence; automated tests always use temporary SQLite.

Run the frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The deployment targets remain Render for the API and Hugging Face Static Spaces for the frontend. GitHub is
the only manually maintained source repository: after all CI gates pass on `main`, GitHub Actions builds and
audits the browser bundle and publishes `README.md` plus `dist/` to each Space with a separate short-lived OIDC credential.
See `docs/06_HUGGINGFACE_STATIC_SPACE.md` for setup. After deployment, use
`backend/scripts/deployment_smoke.py` with the final HTTPS origins to verify health, database readiness, CORS,
the public configuration boundary, and frontend reachability.

## Start here

1. Read `AGENTS.md` for non-negotiable implementation rules.
2. Read `CODEX_HANDOFF.md` for the build sequence.
3. Read `docs/01_PRODUCT_AND_SCIENCE.md` and `docs/02_ARCHITECTURE.md`.
4. For an approachable introduction to ASO biology and interface terminology, read
   `docs/17_ASO_GLOSSARY_AND_RATIONALE.md`.
5. Configure the single Supabase project using `docs/04_SUPABASE.md`.
6. Use the templates as examples; copy them to their real locations only when the application scaffold exists.
7. Validate each phase against `ACCEPTANCE_CRITERIA.md` and `docs/09_TESTING_VALIDATION.md`.
8. See `docs/14_IMPLEMENTATION_STATUS.md` for completed work and the remaining external release gates.

## Contents

- `AGENTS.md` — instructions Codex should obey while working in the future repository.
- `CODEX_HANDOFF.md` — phased build plan and recommended first prompt.
- `ACCEPTANCE_CRITERIA.md` — definition of done.
- `docs/` — product, architecture, setup, deployment, safety, testing, operations, and roadmap guides.
- `templates/` — safe environment/configuration examples with placeholders only.
- `reference/engine/` — audited enhanced Python and R engines plus validation notes.
- `reference/notebooks/` — the enhanced v4 Colab notebooks.
- `MANIFEST.sha256` — checksums generated for integrity verification.

## Important boundaries

- This is a hypothesis-generation and teaching tool, not a clinical decision system.
- The web port must preserve the v4.1 deterministic classifications and warnings before changing scientific logic.
- AI text is optional commentary. It must never silently alter scores, tracks, shortlist order, exclusions, or `final_call`.
- Do not enter patient-identifiable or clinical record data.
- A single Supabase project is accepted for Phase 1, but local and deployed records must remain visibly tagged and cleanly separable.
- Render free services can sleep and have ephemeral local storage. PostgreSQL must hold durable state; the local filesystem is cache-only.

## Official documentation checked

Service instructions were checked through 2026-10-21. Pricing, quotas, UI labels, and product behavior can change; verify the linked official pages before deployment.

- Supabase: https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase billing: https://supabase.com/docs/guides/platform/billing-on-supabase
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Render FastAPI: https://render.com/docs/deploy-fastapi
- Render free services: https://render.com/docs/free
- Hugging Face static Spaces: https://huggingface.co/docs/hub/main/spaces-sdks-static
- Hugging Face GitHub Actions: https://huggingface.co/docs/hub/spaces-github-actions
- Hugging Face Trusted Publishers: https://huggingface.co/docs/hub/trusted-publishers
- OpenAI API overview: https://developers.openai.com/api/reference/overview
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
