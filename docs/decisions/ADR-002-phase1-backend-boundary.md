# ADR-002: Phase 1 deterministic backend boundary

Date: 2026-10-19

## Decision

Port the v4.1 mechanism classifier into pure functions under `backend/app/domain/` and keep upstream
retrieval in `integrations/` and persistence/orchestration in `services/`. Scientific thresholds,
precedence, track names, shortlist tiers, and warning language remain unchanged.

The web pipeline retrieves Open Targets associations, constraint, EVA/ClinVar consequence counts,
Gene2Phenotype evidence, dynamically discovered target drug fields, and ClinicalTrials.gov API v2 records.
Failed sources remain explicitly unknown or failed rather than being represented as negative evidence.
Quick mode caps enriched genes at 25 and is marked incomplete in API metadata and exports.

## Consequences

The deterministic classifier is testable without network access and temporary SQLite tests never touch
Supabase. A single bounded in-process executor persists run events and recovers interrupted jobs. The
executor is appropriate for the Phase 1 demonstration only; durable distributed execution is deferred.

The eight disease preset identifiers and labels were checked directly against the Open Targets GraphQL
API on 2026-10-19. This is time-dependent seed evidence and should be rechecked before deployment.
