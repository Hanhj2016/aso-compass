# Hugging Face Static Space — React/Vite frontend

Recommended Space name: `aso-compass`, displaying the title **ASO Compass**.

Checked against official documentation on 2026-10-20:

- Static Spaces: https://huggingface.co/docs/hub/main/spaces-sdks-static
- Configuration reference: https://huggingface.co/docs/hub/en/spaces-config-reference

Hugging Face documents Static Spaces as free and served without runtime compute. Its optional server-side
`app_build_command` runs as a Job and can require account credits. The free deployment path used here builds in
GitHub Actions, uploads the generated `dist/` directory to the Space repository, and serves it directly. GitHub
is the only manually maintained source repository.

## Prepare the frontend

1. Ensure `npm run build` creates `dist/index.html`.
2. Make the deployed Render URL configurable as `VITE_API_BASE_URL` at build time.
3. Configure Vite's base path only if tests show asset URLs require it; a Space served from its assigned
   `hf.space` origin normally behaves like an origin-root application.
4. Ensure client-side routes work on a static host. Prefer hash routing initially, or verify a suitable SPA fallback before using browser-history routing.
5. Include precomputed examples under versioned public assets.

## Create the Space

1. Create a new Space and select the **Static** SDK.
2. Use a public Space if source transparency is desired; remember that public Space files are visible.
3. Add YAML metadata to `frontend/README.md`; CI copies this file to the Space repository root.
4. In GitHub, create the public repository variable
   `VITE_API_BASE_URL=https://aso-compass-api.onrender.com`.
5. In the Space settings, add a GitHub Actions Trusted Publisher restricted to repository
   `Hanhj2016/aso-compass`, branch `main`, and workflow `ci.yml`.
6. Push to `main`. The `deploy-huggingface` CI job runs only after backend and frontend validation pass, then
   uploads `README.md` and `dist/` with a short-lived OIDC credential.
7. Open the Space URL after Hugging Face publishes the new commit.

Read the authoritative deployed host from the `host` field returned by:

```text
https://huggingface.co/api/spaces/<account>/<space-name>
```

Do not assume the repository slug is also the browser origin. Prebuilt Static Spaces can be assigned a
`.static.hf.space` host; use that exact origin for Render CORS and deployment smoke tests.

The key metadata is:

```yaml
sdk: static
app_file: dist/index.html
```

Do not set `app_build_command` for this no-credit path. The Space repository is a generated deployment target;
do not edit it manually or treat it as a second source repository.

## API URL configuration

The backend base URL is public, not secret. The frontend supports both:

- a `VITE_API_BASE_URL` value present while Vite builds; and
- a Static Space variable named `VITE_API_BASE_URL`, read at runtime from
  `window.huggingface.variables.VITE_API_BASE_URL`.

Set the Space variable to the Render origin, with no path or trailing slash:

```text
VITE_API_BASE_URL=https://<service>.onrender.com
```

Do not place database passwords, Supabase secret/service-role keys, or OpenAI keys in Space variables consumed by static JavaScript. Everything delivered to the browser is public in practice.

## Deploy from the GitHub monorepo

`.github/workflows/ci.yml` builds the Vite application with the GitHub repository variable
`VITE_API_BASE_URL`, audits the browser bundle, and stores `frontend/dist` as a temporary Actions artifact.
After both backend and frontend jobs pass, `deploy-huggingface` assembles this payload:

```text
README.md
dist/
```

The job publishes the payload with the Hugging Face CLI and deletes obsolete files in the Space repository so
stale hashed assets cannot accumulate. Hugging Face retains repository history for rollback. The main GitHub
repository continues to ignore `frontend/dist/`.

The publishing credential is obtained through the Space's Trusted Publisher registration and GitHub OIDC. Do
not create an `HF_TOKEN` secret when OIDC is configured. This deployment credential is unrelated to the OpenAI
key and the shared ASO Compass AI access token; both remain server-side Render configuration.

For a first deployment, verify the workflow's requested identity exactly matches the Trusted Publisher:

```text
repository: Hanhj2016/aso-compass
branch: main
workflow: ci.yml
resource: spaces/scotthan2021/aso-compass
```

## Validation

- refresh each route directly;
- test API health, CORS, and HTTPS mixed-content behavior;
- exercise backend-cold-start messaging;
- verify all assets and example datasets load;
- inspect the built JavaScript for accidental secrets;
- test a narrow mobile layout and keyboard-only use;
- confirm the Space README includes research-use caveats and backend/source links.

CI runs `npm run build`, `npm run audit:dist`, and the frontend test suite before publishing. The audit rejects
backend environment names, PostgreSQL URLs, OpenAI-style keys, and JWT-like service credentials in the built
browser bundle.
