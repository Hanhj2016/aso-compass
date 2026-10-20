# Operations and troubleshooting

## Frontend loads but API is unavailable

Likely causes: Render cold start, failed deployment, wrong API base URL, or CORS mismatch.

1. Open `/health/live` on the Render URL and allow approximately a minute for a free service to wake.
2. Check Render deployment/runtime logs.
3. Confirm the frontend's built API URL.
4. Confirm `FRONTEND_ORIGINS` exactly matches the browser origin, including scheme and without an accidental path.
5. Use a bundled precomputed example while the service recovers.

## Database connection fails

1. Recopy the appropriate connection string from Supabase **Connect**.
2. Confirm reserved password characters are percent-encoded.
3. Try the shared session pooler when direct IPv6 connectivity is unavailable.
4. Require TLS and verify the Psycopg/SQLAlchemy URL dialect.
5. Keep the application pool small and inspect Supabase connection metrics.
6. Never print the connection URL in logs.

## Migration differs between local and demo

Because both use one project, this normally means the code and database revision are out of sync. Check `alembic current` and application release version. Do not delete the migration history or reset the database. Deploy compatible code or apply the reviewed missing migration.

## Run is stuck in `running`

1. Inspect the last persisted `RunEvent` and heartbeat/update time.
2. Confirm whether Render restarted or slept.
3. Recovery should mark a stale run interrupted/retryable.
4. Retry from the last safe stage only if the stage is idempotent; otherwise start a new run linked to the prior one.
5. Prevent two workers from claiming the same run with a database lock/atomic state transition.

## Upstream API schema or request fails

- keep the failure attached to the relevant source/stage;
- show partial results only with an explicit incomplete warning;
- preserve request ID/query hash, safe error category, and timestamp;
- compare with the reference client's schema discovery behavior;
- add/update a fixture before changing parsing logic;
- never translate a failed lookup to “none found.”

## Free quota pressure

- cap workload, candidates, pages, run frequency, and AI calls;
- expire old `local` runs first with guarded cleanup;
- regenerate exports instead of storing duplicates where practical;
- monitor Supabase database/storage/egress and Render hours/bandwidth/build minutes;
- pause optional AI or live trials checks under pressure;
- upgrade or split services before research records become important.

## Suspected secret exposure

1. Revoke/rotate the credential at the provider.
2. update local and Render secrets;
3. redeploy;
4. inspect Git history, build artifacts, frontend JavaScript, and logs;
5. invalidate sessions or signed links as applicable;
6. document the incident without reproducing the secret.

## AI explanation is unsupported or misleading

Disable AI immediately with `AI_ENABLED=false`, preserve the insight/input hash for review, and keep deterministic results available. Expand the reviewed evaluation set before re-enabling. Do not patch scientific fields from the generated output.

