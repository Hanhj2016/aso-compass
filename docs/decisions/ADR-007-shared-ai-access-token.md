# ADR-007: Gate optional AI routes with a shared application token

Date: 2026-10-20

## Status

Accepted for the Phase 1 demonstration.

## Context

The public static frontend needs a lightweight way to restrict cost-bearing AI requests. Sending the OpenAI API key to the browser would expose a privileged provider credential. Full user accounts and per-user quotas are not yet required, and the current demo group may share one identity.

## Decision

- Keep `OPENAI_API_KEY` exclusively in the FastAPI deployment.
- Require a separate bearer token on every AI endpoint while leaving deterministic endpoints public.
- Store only the token's SHA-256 digest in `AI_ACCESS_TOKEN_HASH` and compare digests in constant time.
- Fail closed when the digest is absent, even if `AI_ENABLED=true`.
- Let the React UI retain the raw token in tab-scoped `sessionStorage`; never compile it into the frontend or place it in Hugging Face variables.
- Keep `AI_ENABLED` as the global kill switch and the existing rate limiter as an independent abuse/cost control.

## Consequences

The OpenAI credential never reaches the browser, and possession of the lower-privilege app token is required for AI spending. The shared token provides one application identity, not user authentication, revocation by user, or reliable per-user quotas. A later public or multi-user release should replace it with Supabase Auth, short-lived sessions, and user-specific quotas while retaining the server-side OpenAI boundary.
