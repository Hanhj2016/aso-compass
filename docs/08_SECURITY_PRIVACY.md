# Security, privacy, and research-use safeguards

## Data policy

Design for public disease/gene evidence and application metadata. Do not collect names, medical record numbers, dates of birth, contact details, free-form patient histories, genomic files tied to individuals, or other patient-identifiable data.

Place a clear statement beside every free-text AI field: “Do not enter patient or personally identifiable information.” Add a small server-side heuristic rejection layer and log only a safe rejection code, not the submitted text.

## Secret inventory

Backend-only secrets:

- `DATABASE_URL` and database password;
- `OPENAI_API_KEY`;
- Supabase secret/service-role key, if one is needed;
- signing/encryption secrets;
- private Storage credentials.

Potentially public configuration:

- Render API base URL;
- Supabase project URL and publishable/anonymous key only if browser-side Supabase Auth/Data API is deliberately enabled;
- build/version/source links.

Never rely on a `VITE_` variable to protect a secret; Vite embeds such values in browser assets.

## API controls

- validate every identifier, enum, numeric range, page size, and free-text length;
- apply request body size and run-workload caps;
- use per-IP/session/user rate limits;
- use idempotency keys for run creation;
- restrict CORS to exact origins;
- return safe errors and request IDs, not stack traces;
- set security headers at the API and static host where supported;
- keep dependencies pinned and update them deliberately;
- use parameterized ORM queries only;
- authorize every object lookup, not just route entry;
- use short-lived signed export links if private artifacts are stored.

## Authentication phases

For a public classroom demonstration, anonymous runs can be ephemeral and addressed by an unguessable token stored in the browser. Do not provide a public list of all runs.

When persistent peer histories are needed, add Supabase Auth. Verify bearer tokens in FastAPI, map the subject to `owner_id`, and enforce ownership for reads, writes, retries, exports, and AI calls. Add appropriate grants/RLS before any direct browser database access.

## Shared database risks

One Supabase database for local and demo means:

- local code can corrupt demo data;
- unfinished migrations affect the live app;
- local credentials can access demonstration records;
- cleanup mistakes have a wider blast radius.

Mitigate with environment tagging, least-privilege application roles where practical, migration reviews, backups/exports, test isolation, and guarded cleanup. Splitting the projects remains the recommended future step.

## Scientific safety

- display the non-clinical disclaimer persistently;
- preserve original evidence links and timestamps;
- distinguish “not found” from “not checked” and “check failed”;
- make truncation visually prominent;
- do not display deterministic confidence labels as validated probabilities;
- keep manual overrides attributable and auditable;
- label AI output and never overwrite deterministic evidence.

## Incident basics

If a key is exposed, revoke/rotate it immediately, redeploy, inspect access logs, and invalidate affected sessions. If scientific results are corrupted, disable new runs, preserve logs, identify affected engine/source versions and input hashes, mark affected runs, and regenerate from known inputs after the fix.

