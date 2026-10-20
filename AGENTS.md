# ASO Compass repository instructions for Codex

## Objective

Build **ASO Compass**, a transparent educational and research-demonstration web interface around `reference/engine/aso_target_finder_enhanced.py`. Preserve deterministic behavior first; improve the interface and operability around it.

## Non-negotiable rules

1. Treat reference files as evidence, not files to edit in place. Port tested behavior into `backend/app/domain/` and document intentional differences.
2. Use FastAPI, SQLModel, Alembic, PostgreSQL, React, Vite, and TypeScript.
3. Use one Supabase project for both local development and the deployed demo during Phase 1. Every mutable top-level record must include an `environment` value of `local`, `demo`, or `test`.
4. Automated tests must not write to the shared Supabase project. Use temporary SQLite for unit tests and an explicitly named disposable PostgreSQL schema/database for integration tests only when configured.
5. Never commit `.env`, API keys, database passwords, Supabase secret/service-role keys, or generated user data.
6. The browser must never receive `DATABASE_URL`, `OPENAI_API_KEY`, the Supabase database password, or a Supabase secret/service-role key.
7. Initially route scientific data access through FastAPI. Do not allow arbitrary browser SQL or user-provided SQL.
8. AI must be optional and off by default. It may explain existing evidence, but may not change `final_call`, deterministic scores, shortlist membership/order, exclusions, or warnings.
9. Keep citations and source identifiers adjacent to scientific claims. Do not let an AI-generated citation become a trusted source without server-side validation.
10. Display the research-use disclaimer in the run form, results page, exports, and AI panels.
11. Do not add patient data fields. Reject likely patient-identifiable free text if an AI question endpoint is enabled.
12. Use migrations for schema changes. Do not instruct users to make undocumented manual production edits.
13. Treat Render local disk as ephemeral. Persistent runs, progress, metadata, and exports belong in Supabase PostgreSQL/Storage.
14. Keep upstream HTTP timeouts, retries, cache provenance, truncation warnings, and run metadata from v4.1.
15. Do not report success until lint, type-checks, unit tests, migrations, a deterministic golden-case test, and a production build pass.

## Expected repository shape

```text
aso-compass/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── domain/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── public/examples/
│   └── package.json
├── notebooks/
├── docs/
├── render.yaml
├── Dockerfile
├── CITATION.cff
├── LICENSE
└── README.md
```

## Working method

- Inspect the reference engine and notebooks before defining API schemas.
- Implement in the phases in `CODEX_HANDOFF.md`; keep the application runnable after each phase.
- Prefer small pure functions around scientific classification logic.
- Add regression fixtures for transformations before refactoring them.
- Record architectural changes in `docs/decisions/`.
- Stop and ask before changing scientific thresholds, evidence precedence, or clinical interpretation.
