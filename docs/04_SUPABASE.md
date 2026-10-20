# Supabase setup — one shared project for Phase 1

Checked against official documentation on 2026-10-19.

Supabase provides PostgreSQL, not SQLite. The Free plan currently allows two active free projects and documents a 500 MB database quota per project, 1 GB Storage, 5 GB egress, and 50,000 monthly active users. These allowances can change. See:

- https://supabase.com/docs/guides/platform/billing-on-supabase
- https://supabase.com/docs/guides/platform/database-size

## 1. Create the project

1. Sign in to Supabase and create a project in a nearby region.
2. Generate and save a strong database password in a password manager.
3. Record the project reference and project URL.
4. Open **Connect** in the project dashboard to obtain connection strings; do not construct a pooler hostname from memory.

## 2. Choose the backend connection

FastAPI on Render is a persistent backend, but network IPv4 support matters. Supabase currently recommends:

- direct connection for persistent backends that can reach the project's IPv6 endpoint;
- shared pooler in session mode as the persistent-backend alternative on IPv4-only networks;
- transaction mode primarily for serverless/edge workloads.

For Render, begin with the **Session pooler** string from the Connect dialog if the direct IPv6 address is not reachable. Use TLS and a small SQLAlchemy pool. Keep the exact database URL in backend secrets only.

Official connection guide: https://supabase.com/docs/guides/database/connecting-to-postgres

For SQLModel/SQLAlchemy with Psycopg 3, the runtime URL commonly needs the dialect form `postgresql+psycopg://...`; adapt the copied Supabase URL without changing its host, username, password, port, or database. Percent-encode reserved password characters.

## 3. Configure local and demo use

Use the same database URL in:

- local `backend/.env`, with `APP_ENV=local`;
- Render secret settings, with `APP_ENV=demo`.

Do not place `DATABASE_URL` in the frontend. Do not commit it. The application must derive each new record's `environment` from trusted backend settings, not from a user-editable request field.

## 4. Apply schema migrations

Use SQLModel for models and Alembic for migrations. Generate a migration, inspect it, test it against a fresh temporary database, and then run:

```bash
alembic upgrade head
```

Run this from a controlled local admin session for the first deployment. Later, add a reviewed release migration step. Avoid automatically generating migrations during application startup.

## 5. Recommended data separation

- `runs.environment` is required and indexed.
- Child tables reference `run_id`; their environment should either be materialized consistently or derived by joining the run.
- All history/export/admin queries filter by environment unless deliberately cross-environment.
- Seed/example records use an explicit owner/source marker.
- Cleanup requires an exact environment plus a cutoff date and should use a transaction.
- Automated tests never use this database by default.

One project means local migrations immediately affect the demo. Use backward-compatible migrations: add nullable/defaulted structures first, deploy compatible code, backfill, and only then tighten constraints.

## 6. Browser access, Auth, and RLS

In the first version, the browser talks to FastAPI rather than directly to Supabase tables. If Supabase Auth is added, React may receive the project URL and a publishable/anonymous key, but database secrets remain server-only.

Migration `20261020_0003` enables Row Level Security on every application table without adding browser policies. This makes direct Data API access deny-by-default while the trusted FastAPI database-owner connection remains the only Phase 1 data path. Add reviewed policies in a later migration before granting browser access.

If tables are exposed through the Supabase Data API, enable Row Level Security and configure both grants and policies. Supabase warns that secret/service-role access can bypass RLS and must never be used in the browser. See:

https://supabase.com/docs/guides/database/postgres/row-level-security

Using a privileged PostgreSQL connection in FastAPI also means FastAPI must enforce ownership on every protected query. RLS is not a substitute for understanding which database role the backend actually uses.

## 7. Storage

Start by generating exports on request from PostgreSQL. If ZIP/report artifacts become large or expensive to regenerate, place them in a private Supabase Storage bucket with short-lived signed download URLs and retain SHA-256, size, format, and schema version in `export_artifacts`.

## 8. Backups and limits

- Monitor database size, egress, Storage, and active-user quotas.
- Export schema and important demonstration data periodically.
- Do not assume free-tier retention or recovery equals a production backup plan.
- Add a simple retention policy for local runs before the shared project fills.

## 9. Later split

The design must permit a future second Supabase project by changing `DATABASE_URL` and applying the same migrations. Avoid hard-coded project references. Export/import only the intended environment's records and verify row counts/checksums.
