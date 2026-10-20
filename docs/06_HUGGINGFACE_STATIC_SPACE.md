# Hugging Face Static Space — React/Vite frontend

Recommended Space name: `aso-compass`, displaying the title **ASO Compass**.

Checked against official documentation on 2026-10-20:

- Static Spaces: https://huggingface.co/docs/hub/main/spaces-sdks-static
- Configuration reference: https://huggingface.co/docs/hub/en/spaces-config-reference

Hugging Face documents Static Spaces as free and served without runtime compute. Static Spaces can run a build command for React/Vite and serve the resulting entry file.

## Prepare the frontend

1. Ensure `npm run build` creates `dist/index.html`.
2. Make the deployed Render URL configurable as `VITE_API_BASE_URL` at build time.
3. Configure Vite's base path only if tests show asset URLs require it; a Space served from its own `hf.space` origin normally behaves like an origin-root application.
4. Ensure client-side routes work on a static host. Prefer hash routing initially, or verify a suitable SPA fallback before using browser-history routing.
5. Include precomputed examples under versioned public assets.

## Create the Space

1. Create a new Space and select the **Static** SDK.
2. Use a public Space if source transparency is desired; remember that public Space files are visible.
3. Place the frontend project at the Space repository root, or use a dedicated deployment branch/repository.
4. Add YAML metadata to the top of the Space `README.md` as shown in `templates/huggingface_space/README.md`.
5. Push `package.json`, the lockfile, source, public assets, and README.
6. Watch the build logs and open the public Space URL.

The key metadata is:

```yaml
sdk: static
app_build_command: npm run build
app_file: dist/index.html
```

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

## Deploy from a monorepo

The simplest reliable approach is a small deployment workflow that copies or mirrors `frontend/` to the Space repository. Keep generated `dist/` out of source control unless the chosen process explicitly requires it. Pin Node dependencies with a lockfile.

## Validation

- refresh each route directly;
- test API health, CORS, and HTTPS mixed-content behavior;
- exercise backend-cold-start messaging;
- verify all assets and example datasets load;
- inspect the built JavaScript for accidental secrets;
- test a narrow mobile layout and keyboard-only use;
- confirm the Space README includes research-use caveats and backend/source links.

Run `npm run build && npm run audit:dist` before publishing. The audit rejects backend environment names,
PostgreSQL URLs, OpenAI-style keys, and JWT-like service credentials in the built browser bundle.
