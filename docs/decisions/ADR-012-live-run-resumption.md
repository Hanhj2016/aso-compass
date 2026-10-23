# ADR-012: Resume persisted live runs without changing the bundled example

## Status

Accepted — 2026-10-23

## Context

Completed analyses and their candidates are persisted by the FastAPI service in PostgreSQL. The frontend also includes a six-candidate, versioned ALS example for offline education. Opening that example replaced the in-memory live result, which made a persisted full run appear to have been reduced to six candidates.

The same frontend is deployed to more than one Hugging Face Space. Browser storage is isolated by origin, so a browser-only pointer cannot identify the same run across both Space hostnames.

## Decision

- PostgreSQL remains the source of truth for runs, events, and candidates.
- The browser stores only the opaque ID of the latest live run in `localStorage`; it does not duplicate scientific records in browser storage.
- Live result URLs include `?run=<run-id>`. Loading such a URL restores the run from the API and makes it the latest run for that Space origin.
- Opening the bundled example removes the live-run query parameter but preserves the latest-live-run pointer.
- Learn and bundled-example views provide an explicit **Return to latest saved analysis** action.
- Starting a new analysis replaces the latest-live-run pointer. Merely opening the new-analysis form does not delete the persisted pointer or backend data.

## Consequences

- Users can inspect the stable six-candidate tutorial and then return to a full live result without rerunning the engine.
- A run URL can be copied between the two Space deployments, provided both use the same API and CORS configuration.
- Each Space still has independent `localStorage`; automatic cross-origin discovery is intentionally not attempted.
- An invalid or unavailable run link is removed from the address bar, and a matching stale browser pointer is discarded.
- No schema migration is required because run persistence already exists in PostgreSQL.
