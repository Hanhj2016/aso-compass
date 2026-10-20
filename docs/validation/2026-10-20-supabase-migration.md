# Supabase migration validation — 2026-10-20

## Scope

The reviewed Alembic revisions were applied once from the verified API image to the Phase 1 shared Supabase PostgreSQL project. Credentials and connection details were supplied only through ignored backend environment storage and were not logged.

## Preflight

- PostgreSQL 16 disposable target: upgrade, full downgrade, and re-upgrade passed.
- SQLite fresh upgrade passed, including the PostgreSQL-only RLS revision as a no-op.
- Backend format, lint, strict typing, and 11 unit tests passed.
- Test bootstrap forces `APP_ENV=test`, temporary SQLite, and a disabled worker before application imports, regardless of a developer `.env`.

## Shared project result

- Alembic revision: `20261020_0003 (head)`.
- Tables: `runs`, `candidates`, `evidence`, `run_events`, `export_artifacts`, and `ai_insights`.
- Row Level Security: enabled on all six tables with no browser policies.
- Initial row counts: zero in all six tables.
- API `/health/live`: passed.
- API `/health/ready`: database reachable.
- Public configuration: `environment=local`, AI disabled, research-use disclaimer present.

No scientific run was submitted during this migration validation.
