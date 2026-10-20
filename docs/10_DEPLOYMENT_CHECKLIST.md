# Deployment checklist

## Before accounts and secrets

- [ ] Repository has a license decision, `CITATION.cff`, README, scientific disclaimer, and source acknowledgments.
- [ ] Reference parity and all automated quality gates pass.
- [ ] No secret or real `.env` is in Git history.
- [ ] Production frontend build has been inspected for secret-like strings.
- [ ] `npm run audit:dist` passes after the production frontend build.
- [ ] One precomputed example works offline from the API.

## Supabase

- [ ] Project region and free-plan constraints are acceptable.
- [ ] Database password is stored in a password manager.
- [ ] Correct connection string was copied from **Connect**.
- [ ] TLS and a small application pool are configured.
- [ ] Alembic migration was reviewed and tested on a disposable PostgreSQL database.
- [ ] Migration was applied once and current revision verified.
- [ ] `environment` is required/indexed and set server-side.
- [ ] Exposed tables have reviewed grants/RLS; no secret key is in the browser.
- [ ] Backup/export and retention approach is documented.

## Render

- [ ] Backend root/build/start commands are correct.
- [ ] Reviewed migrations were applied from a controlled environment before the free-plan deploy.
- [ ] `APP_ENV=demo` is set.
- [ ] `DATABASE_URL` is a secret.
- [ ] `FRONTEND_ORIGINS` has the exact Space URL.
- [ ] AI is off unless intentionally configured.
- [ ] `/health/live` and `/health/ready` behave correctly.
- [ ] Persistent state is in Supabase, not local SQLite/files.
- [ ] Single-run concurrency and queue limits are enabled.
- [ ] Cold start, restart recovery, upstream timeout, and overload were tested.

## Hugging Face Static Space

- [ ] README metadata uses `sdk: static`.
- [ ] Build command and `dist/index.html` are correct.
- [ ] Render API URL is configured as public config only.
- [ ] `VITE_API_BASE_URL` is set to the exact HTTPS Render origin.
- [ ] Direct route refresh works or hash routing is used.
- [ ] Space includes description, caveat, sources, citation, and version.
- [ ] Responsive and keyboard-only checks pass.

## End-to-end release

- [ ] Frontend can wake the backend and explains the delay.
- [ ] Disease presets and custom MONDO validation work.
- [ ] A bounded demo run completes with progress and metadata.
- [ ] Five-track invariant passes.
- [ ] Truncation/failure warnings are prominent.
- [ ] Gene detail and visualizations agree with the table.
- [ ] CSV/JSON/HTML/ZIP exports include manifest and disclaimer.
- [ ] No patient data is requested.
- [ ] Deployment URLs and support/issue path are documented.
- [ ] `backend/scripts/deployment_smoke.py` passes against the final URLs.

## Optional AI release

- [ ] Key exists only in Render/local backend secret storage.
- [ ] `AI_ENABLED` kill switch works.
- [ ] Structured schema/refusal/incomplete handling is tested.
- [ ] Deterministic fields remain immutable.
- [ ] Grounding/citation evaluation passed.
- [ ] Rate, token, cache, and budget controls are active.
- [ ] Generated text is labeled and non-clinical disclaimer displayed.
