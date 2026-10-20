# ADR-003: Guarded evidence explanations and run summaries

Date: 2026-10-20

## Status

Accepted and implemented behind a disabled-by-default feature flag.

## Context

ASO Compass has stable deterministic classifications and saved provenance. An optional language model can make this evidence easier to understand, but it must not become part of the scientific decision path, invent sources, receive secrets in the browser, or accept patient-identifiable free text.

## Decision

The initial AI features are a candidate evidence explainer, a saved-run summary, and a constrained candidate comparison—not an open chatbot.

- React sends only a run ID and gene symbol to a narrow FastAPI endpoint.
- FastAPI retrieves the saved run, candidate, and normalized evidence in the active environment.
- The OpenAI API key is backend-only, and the global `AI_ENABLED` flag defaults to false.
- The Responses API returns a strict Pydantic Structured Output.
- Scientific claims cite source IDs supplied by the server. Unknown source IDs reject the entire output before persistence.
- The explanation is stored separately in `AIInsight`; no `Run`, `Candidate`, or `Evidence` scientific field is updated.
- Cache identity includes the evidence packet hash, model, prompt version, and output schema version.
- The UI labels the result as generated, keeps it visually separate from deterministic evidence, and repeats the research-use disclaimer.
- Automated tests inject a fake provider and remove any API key from the test process.
- The run summary uses a server-computed aggregate plus no more than 25 deterministic candidate excerpts. It may describe track distribution, gaps, warnings, and review priorities, but it cannot choose a best target.
- Candidate comparison accepts only two or three saved gene symbols. It validates that the output preserves the exact selected set and may explain differences without naming a winner or producing a new rank.

## Consequences

The features are auditable and inexpensive to disable, and repeated inputs avoid new API calls. They cannot answer arbitrary questions or search literature. Guarded Q&A requires separate review, patient-information rejection controls, and new evaluation fixtures before implementation.
