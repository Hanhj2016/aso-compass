# ADR-005: Use one activation flag for optional AI features

Date: 2026-10-20

## Status

Accepted.

## Context

The guarded Q&A backend initially had an additional `AI_QA_ENABLED` release switch on top of the existing global `AI_ENABLED` control. Maintaining two switches complicates configuration and can produce an unexpected state where some AI features work while saved-evidence questions do not.

## Decision

- Remove `AI_QA_ENABLED` from settings, environment templates, deployment configuration, and the public configuration response.
- Make guarded Q&A available whenever `AI_ENABLED=true` and the backend OpenAI key is configured.
- Keep `AI_ENABLED=false` as the default and global kill switch for every optional AI feature.
- Preserve all Q&A-specific safety preflight, saved-evidence routing, input bounds, rate limits, source validation, and no-raw-question persistence behavior.
- Show the guarded Q&A panel for completed non-example runs when global AI is enabled; require scientific/safety fixture review before public deployment.

## Consequences

Activation is simpler and consistent across AI features. Enabling AI now also enables the guarded Q&A API and panel, so deployments must treat the global switch as approval for all implemented AI workflows. Scientific/safety review remains a public-deployment and operational-readiness requirement rather than a second runtime flag.
