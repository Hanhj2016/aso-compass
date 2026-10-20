# Local development on Linux Mint

## Prerequisites

- Git
- Miniconda/Conda
- Node.js LTS with npm
- access to the chosen Supabase project
- optional OpenAI API key for the later AI phase

Use the repository's eventual pinned Python and Node versions if they differ from the examples below.

## Backend setup

```bash
conda create -n aso-web python=3.12 -y
conda activate aso-web
cd backend
python -m pip install -e '.[dev]'
cp .env.example .env
```

Fill `DATABASE_URL` with the same Supabase project used by the demo, set `APP_ENV=local`, and use local frontend origins. Never commit `.env`.

Run migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify `http://127.0.0.1:8000/health/live` and `/docs`.

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set `VITE_API_BASE_URL=http://127.0.0.1:8000`. Only values prefixed with `VITE_` are embedded into browser code, so no secret may use that prefix.

## Shared database discipline

The local API and Render API intentionally use one Supabase project in Phase 1. They must use different `APP_ENV` values:

- local machine: `APP_ENV=local`
- deployed demonstration: `APP_ENV=demo`
- automated tests: `APP_ENV=test`

Every run and dependent record inherits the run environment. UI history defaults to the active environment. Any cleanup command must require both an explicit environment and an age threshold; it must print a count and require confirmation unless invoked in a disposable test database.

Do not run destructive development seeds, table resets, or broad `DELETE`/`TRUNCATE` operations against the shared project.

## Tests

Unit tests should default to temporary SQLite and mocked upstream HTTP. This is fast and prevents accidental shared-database writes. Add PostgreSQL-specific integration tests separately because SQLite does not reproduce PostgreSQL JSON, enum, concurrency, pooling, or migration behavior.

Suggested commands after the project exists:

```bash
cd backend
ruff check .
mypy app
pytest
alembic upgrade head

cd ../frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Live scientific smoke tests

Live API tests should be opt-in, bounded, cached, and marked separately from unit tests. They must record the date, Open Targets release, parameters, returned row counts, and truncation. Never make exact changing upstream counts a permanent unit-test assertion.

