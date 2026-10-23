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
- [ ] Every destination Space has a GitHub Actions Trusted Publisher restricted to `Hanhj2016/aso-compass`, `main`, and `ci.yml`.
- [ ] GitHub Actions repository variable `VITE_API_BASE_URL` is the exact HTTPS Render origin.
- [ ] CI built and audited `dist/index.html`, and the Space metadata configures it as `app_file`.
- [ ] Each `deploy-huggingface` matrix entry ran only after the backend and frontend CI jobs passed.
- [ ] Each Space repository contains only the generated deployment payload (`README.md` and `dist/`).
- [ ] `app_build_command` is omitted for accounts without Hugging Face build credits.
- [ ] Render API URL is configured as public config only.
- [ ] No permanent `HF_TOKEN` is stored when Trusted Publisher/OIDC is used.
- [ ] Direct route refresh works or hash routing is used.
- [ ] Space includes description, caveat, sources, citation, and version.
- [ ] Responsive and keyboard-only checks pass.
- [ ] Render `FRONTEND_ORIGINS` contains both exact `.static.hf.space` origins and rejects unlisted origins.

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
- [ ] `AI_ACCESS_TOKEN_HASH` is configured in Render and every AI endpoint rejects missing/invalid bearer tokens.
- [ ] The raw shared access token is distributed out of band and is absent from Hugging Face variables and built assets.
- [ ] `AI_ENABLED` kill switch works.
- [ ] Structured schema/refusal/incomplete handling is tested.
- [ ] Deterministic fields remain immutable.
- [ ] Grounding/citation evaluation passed.
- [ ] Rate, token, cache, and budget controls are active.
- [ ] Generated text is labeled and non-clinical disclaimer displayed.
