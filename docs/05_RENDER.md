# Render deployment — FastAPI backend

Recommended Render service name: `aso-compass-api`.

Checked against official documentation on 2026-10-20:

- FastAPI deployment: https://render.com/docs/deploy-fastapi
- Web services: https://render.com/docs/web-services
- Free services: https://render.com/docs/free
- Environment variables: https://render.com/docs/configure-environment-variables

## Current free-tier caveats

Render currently documents that a free web service:

- spins down after 15 minutes without inbound traffic and can take about a minute to wake;
- has an ephemeral filesystem, so local files and SQLite data are lost on restart/redeploy/spin-down;
- receives 750 free instance hours per workspace per month;
- cannot scale beyond one instance or use a persistent disk;
- can be suspended for unusually high service-initiated traffic.

Free resources are appropriate for a demonstration, not a production or clinically relied-upon service. Recheck these terms before deploying.

## Deployment steps

1. Push the completed repository to a supported Git provider.
2. In Render, create a **Web Service** and connect the repository.
3. Point the root directory to `backend` if using the proposed monorepo.
4. Use the repository's pinned Python version.
5. Example build command:

   ```text
   python -m pip install .
   ```

6. Example start command:

   ```text
   python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

7. Set health check path to `/health/ready` after it is implemented.
8. Choose the free plan for the initial demonstration.
9. Add secrets in the Render dashboard, not in `render.yaml`.
10. Deploy and inspect build/runtime logs.

## Required environment variables

```text
APP_ENV=demo
DATABASE_URL=<Supabase session-pooler or reachable direct URL>
FRONTEND_ORIGINS=https://<assigned-space-host>.static.hf.space
AI_ENABLED=false
OPENAI_API_KEY=<only if AI is enabled later>
OPENAI_MODEL=<configured supported model>
```

Also configure engine/cache/run limits from the backend `.env.example`.

The committed blueprint keeps AI off and defaults the optional model name to `gpt-6-luna`. Add
`OPENAI_API_KEY` and `AI_ACCESS_TOKEN_HASH` as Render secrets only after the AI scientific/safety review is complete, then set `AI_ENABLED=true`. `AI_ACCESS_TOKEN_HASH` is the SHA-256 digest of the separate token entered in the GUI; never enter the OpenAI key, the raw app token, or either value in Hugging Face variables. The model is
appropriate for this cost-sensitive, bounded saved-evidence workflow and supports its `reasoning: none`
configuration; model access still depends on the configured OpenAI project.

## CORS

Use the exact production Space origin reported by the Hugging Face Space API and explicit localhost origins.
Do not infer the hostname from the repository name: directly served Static Spaces can use a
`.static.hf.space` host. Do not combine credentialed requests with a wildcard origin. If the Space URL changes,
update the backend and redeploy.

## Run orchestration

Do not keep an analysis request open until the scientific workflow finishes. Create a queued run, return its ID, execute with bounded concurrency, persist events, and let the frontend poll. Assume Render may restart the process.

With the initial one-process approach:

- allow one active scientific run;
- put additional runs in PostgreSQL as queued;
- use a database claim/lock to prevent duplicate execution;
- checkpoint after every major source;
- mark stale `running` records interrupted/retryable on startup;
- enforce maximum candidates/pages/runtime;
- reject or defer overload politely.

## Cold-start user experience

The frontend should immediately show a message such as “The research API is waking; this can take about a minute on the free demonstration tier,” retry health checks with backoff, and offer a precomputed example. Do not present a cold start as a scientific failure.

## Schema migration release procedure

Because local and demo share one database:

1. back up/export important data;
2. test migration upgrade and downgrade in a disposable PostgreSQL database;
3. ensure old and new code can coexist during deployment;
4. run the migration once from a controlled environment;
5. deploy the backend;
6. run readiness and smoke tests;
7. deploy the frontend if its contract changes.

Do not run unreviewed `alembic upgrade head` from multiple web instances at startup.

Render's pre-deploy command is the preferred migration hook, but it is not available to free web services.
For the Phase 1 free service, run each reviewed migration once from the local backend environment immediately
before deploying:

```bash
cd backend
APP_ENV=demo DATABASE_URL='<Supabase session-pooler URL>' alembic current
APP_ENV=demo DATABASE_URL='<Supabase session-pooler URL>' alembic upgrade head
APP_ENV=demo DATABASE_URL='<Supabase session-pooler URL>' alembic current
```

Enter the URL interactively or load it from an uncommitted backend environment file; do not place it in shell
history or repository files. The application readiness endpoint fails if the database is unreachable, but it
does not replace migration review.

## Post-deploy verification

After the Space URL and Render URL are final, run the read-only smoke script:

```bash
cd backend
python scripts/deployment_smoke.py \
  --api-url https://<service>.onrender.com \
  --frontend-url https://<assigned-space-host>.static.hf.space \
  --allowed-origin https://<assigned-space-host>.static.hf.space
```

It verifies liveness, database readiness, the public configuration boundary, allowed and rejected CORS origins,
and the frontend document without creating a run.
