# Optional OpenAI explanation layer

Checked against official OpenAI documentation on 2026-10-19:

- API authentication and Responses API: https://developers.openai.com/api/reference/overview
- Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs

## Role in the application

OpenAI should be an optional explanation layer beside the deterministic engine. Good first features are:

- **Explain this gene** — translate saved evidence and warnings into beginner or advanced language;
- **Summarize this run** — describe major tracks, evidence gaps, truncation, and review priorities;
- **Ask about this saved result** — answer only from a constrained server-provided evidence context.

A later literature assistant may retrieve records from PubMed/Europe PMC/ClinicalTrials.gov using deterministic tools and then summarize them. Every citation must be validated against the retrieved record before display.

## Implemented increments

The candidate evidence explainer is implemented behind `AI_ENABLED=false` by default:

```text
POST /api/v1/runs/{run_id}/candidates/{gene}/ai-explanation
```

It accepts no user-supplied text. FastAPI loads the succeeded run, candidate, and normalized evidence; creates a canonical evidence packet; and calls the Responses API with a strict Pydantic schema. Returned source IDs must be a subset of the packet source IDs before an `AIInsight` is persisted or displayed. Identical candidate evidence, model, prompt version, and output schema reuse the saved result.

The run summary is also implemented:

```text
POST /api/v1/runs/{run_id}/ai-summary
```

It accepts no user-supplied text. The server computes a deterministic run aggregate covering candidate and track counts, shortlist membership, evidence caps, flags, completeness, and ASO precedent. The model receives that aggregate, saved run warnings and metadata, and at most 25 deterministic candidate excerpts selected by shortlist position and then overall score. Run-wide claims must cite the aggregate source. The output cannot choose a best target or alter any saved result.

Saved summaries and candidate explanations can be restored without invoking the model:

```text
GET /api/v1/runs/{run_id}/ai-summary
GET /api/v1/runs/{run_id}/candidates/{gene}/ai-explanation
GET /api/v1/examples/{example_id}/ai-summary
GET /api/v1/examples/{example_id}/candidates/{gene}/ai-explanation
```

These routes require the same shared AI access token as generation routes. They rebuild the canonical
evidence packet, require an exact environment/model/prompt/schema/input-hash match, and revalidate saved
structured output and source identifiers before disclosure. A cache miss returns `404` and never calls
OpenAI. The frontend checks these routes after AI access is unlocked and restores available output.

Versioned educational examples remain separate from user runs, but their validated AI interpretations
are persisted as example-scoped `AIInsight` records. Changing the bundled evidence, model, prompt, or
output schema changes the cache identity and forces an explicit new generation. Deterministic example
records themselves are not inserted into PostgreSQL.

The constrained candidate comparison is implemented:

```text
POST /api/v1/runs/{run_id}/ai-compare
{"gene_symbols": ["GENE1", "GENE2"]}
```

The request must contain exactly two or three unique saved gene symbols and no free-text question. FastAPI loads their deterministic candidate and normalized evidence records. It canonicalizes selection order for cache reuse, validates every returned source identifier, and verifies that the structured output contains exactly the requested candidates. The comparison describes differences and shared gaps; it cannot name a winner or create a new rank.

Comparison schema v2 uses compact section and word limits so its structured JSON completes within the default 1,800-output-token budget. Validation failures log only error types and schema locations, never evidence packet contents.

Local opt-in, after adding the key privately to `backend/.env`:

```dotenv
AI_ENABLED=true
# SHA-256 of a separate shared GUI token; never the OpenAI API key.
AI_ACCESS_TOKEN_HASH=<64-character SHA-256 hex digest>
OPENAI_API_KEY=<private backend-only key>
OPENAI_MODEL=gpt-6-luna
AI_MAX_OUTPUT_TOKENS=1800
AI_TIMEOUT_SECONDS=45
AI_RATE_LIMIT_PER_MINUTE=6
```

Restart FastAPI after changing these values. Never add this key to a `VITE_` variable, source file, screenshot, log, or chat message.

Every AI endpoint also requires `Authorization: Bearer <ASO Compass access token>`. The browser asks for this separate shared token and keeps it in `sessionStorage`, so it is cleared when the tab is closed. Only its SHA-256 digest belongs in Render. The token, digest, and OpenAI key must not be placed in Hugging Face variables or the frontend bundle.

Generate a high-entropy token and its digest from a private terminal without putting the token in shell history:

```bash
read -rsp "AI access token: " ASO_AI_TOKEN
printf %s "$ASO_AI_TOKEN" | sha256sum
unset ASO_AI_TOKEN
```

Put only the printed digest in `AI_ACCESS_TOKEN_HASH`. Share the original token out of band with intended demo users. This shared identity is a Phase 1 control, not per-user authentication; Supabase Auth plus user-specific quotas is the recommended later replacement.

## Hard boundaries

The model must not:

- change deterministic scores, classifications, exclusions, warnings, or shortlist order;
- provide patient-specific treatment or dosing advice;
- accept patient-identifiable notes or records;
- invent citations or imply literature was searched when it was not;
- turn generated text directly into a curated override;
- execute arbitrary SQL or receive an unrestricted database tool.

## Backend-only architecture

`OPENAI_API_KEY` belongs only in local backend `.env` and Render secrets. Official OpenAI documentation states that API keys are secrets and must not be exposed in browser/client code. The React app calls narrow FastAPI endpoints with the separate app token; FastAPI validates its digest, retrieves only the authorized saved evidence, and calls the Responses API.

Recommended endpoints:

```text
POST /api/v1/runs/{run_id}/ai-summary
POST /api/v1/runs/{run_id}/ai-compare
POST /api/v1/runs/{run_id}/candidates/{gene}/ai-explanation
POST /api/v1/runs/{run_id}/ai-question
GET  /api/v1/runs/{run_id}/ai-summary
GET  /api/v1/runs/{run_id}/candidates/{gene}/ai-explanation
```

The candidate explanation, run summary, their exact-match saved-result retrieval routes, constrained candidate comparison, and guarded saved-evidence Q&A endpoints are implemented. They all follow the global `AI_ENABLED` switch; there is no separate Q&A activation flag. The results page includes a guarded Q&A panel with explicit zero-to-three candidate context, a 500-character limit, patient-information warning, refusal/error states, and separately labeled cited output. Q&A schema v2 also displays server-generated deterministic candidate facts separately from AI prose, corrects explicit false classification premises, and rejects outputs that conflict with selected-candidate fields or introduce numeric claims absent from the supplied sources. See `docs/16_GUARDED_QA_SAFETY.md`.

## Structured response schema

Use Pydantic plus Structured Outputs. A candidate explanation can contain:

```text
summary
decision_basis[]
supporting_evidence[]
conflicting_evidence[]
uncertainties[]
manual_review_steps[]
glossary[]
disclaimer
```

Validate refusals and incomplete outputs explicitly. Store the output schema version. Function calling is appropriate only for narrow read-only functions such as `get_run_summary`, `get_candidate_evidence`, and `list_run_warnings`; never expose a general SQL function.

## Prompt and provenance

System/developer instructions should state:

- use only supplied evidence;
- distinguish retrieved facts from interpretation;
- preserve source IDs exactly;
- mention missing, failed, cached, or truncated sources;
- avoid therapeutic recommendations;
- use calibrated language;
- return the specified schema.

Record `model`, `prompt_version`, `input_hash`, `output_schema_version`, API response/request ID, source IDs, timestamps, and review status in `AIInsight`. Cache identical inputs.

## Cost and abuse controls

- `AI_ENABLED=false` by default;
- fail-closed shared-token authorization for every AI route;
- configurable model rather than hard-coding one in many files;
- maximum context and output tokens;
- per-user/session and per-run rate limits;
- one cached explanation per input hash/prompt/model combination;
- project budgets/alerts and a backend kill switch;
- no anonymous bulk literature summarization.

An API key does not imply free or unlimited usage. Check current model availability and pricing in official OpenAI documentation/dashboard before enabling the feature.

## Evaluation

Create a small reviewed set spanning agreement, conflict, insufficient evidence, truncation, upstream failure, modifier, and manual override. Evaluate schema validity, factual grounding, citation correctness, uncertainty coverage, unsafe advice, readability, and deterministic-field immutability.

The first offline engineering suite is implemented in `backend/evals/fixtures/ai_outputs_v1.json` with deterministic graders in `app/evals/ai_outputs.py`. It covers all three implemented AI features and deliberately failing controls. A separate versioned suite exercises guarded-Q&A preflight, including patient-information, clinical-advice, ranking-override, and prompt-injection rejection. Scientific/safety annotations remain pending; see `docs/15_AI_EVALUATION.md` and `docs/16_GUARDED_QA_SAFETY.md`.

AI text should always be labeled as generated and remain visually separate from the deterministic call or aggregate.
