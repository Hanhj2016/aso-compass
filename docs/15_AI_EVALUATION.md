# AI output evaluation

ASO Compass evaluates optional AI text separately from the deterministic scientific engine. Routine evaluation is offline: it does not read Supabase, use `OPENAI_API_KEY`, or call OpenAI.

The initial dataset is `backend/evals/fixtures/ai_outputs_v1.json`. It contains six synthetic, review-ready cases spanning:

- candidate explanations for modifier and insufficient-data calls;
- all five deterministic tracks;
- quick-mode caps and truncated evidence;
- upstream lookup failure versus negative evidence;
- therapeutic precedent caveats;
- two- and three-candidate comparisons;
- preservation of exact candidate identity and no-winner language.

## Run the suite

From `backend/`:

```bash
PYTHONPATH=. python -m app.evals.ai_outputs
pytest -q tests/test_ai_evals.py
```

The runner accepts another recorded dataset:

```bash
PYTHONPATH=. python -m app.evals.ai_outputs --dataset evals/fixtures/candidate_outputs.json
```

No API key is required. CI runs the same graders through the backend test suite.

## Deterministic graders

Every case is checked for:

1. strict Pydantic schema validity;
2. allow-listed source identifiers adjacent to claim-bearing fields;
3. required reviewed caveats;
4. prohibited recommendation, dosing, winner, and clinical-advice language;
5. exact run track counts where applicable;
6. exact two- or three-candidate identity for comparisons.

Guarded Q&A schema v2 adds request-level regression checks for exact candidate fact echoes,
classification contradictions in generated prose, unsupported numeric claims, and server-generated
false-premise corrections. These checks run before an `AIInsight` is persisted or returned.

Negative-control tests deliberately inject an invented citation, recommendation language, changed track count, and changed candidate identity. Each must fail.

## Scientific annotation gate

All v1 cases are initially marked `scientific_review_pending`. Passing automated graders means the engineering constraints work; it does **not** mean a domain expert approved the scientific wording.

A scientific reviewer should examine the expected output and annotation rationale, edit any inaccurate expectation, and then change that case to `scientific_reviewed`. Record the review in the normal repository review history. The strict release gate is:

```bash
PYTHONPATH=. python -m app.evals.ai_outputs --require-scientific-review
```

That command exits with status 2 while any case remains pending. Guarded free-text Q&A should not be enabled until the relevant cases are scientifically reviewed and additional patient-information rejection cases have been added.

## Updating prompts or schemas

For every prompt, model, or output-schema change:

1. preserve the old fixture file as a versioned baseline;
2. add cases for newly discovered failures;
3. run automated graders against recorded candidate outputs;
4. compare failures and reviewer critiques;
5. obtain scientific review for changed expectations;
6. never overwrite deterministic fields with an AI result.

This follows OpenAI's evaluation guidance: annotations provide human ground truth, while automated graders make repeatable checks scalable.

## Guarded-Q&A preflight suite

Free-text safety is evaluated separately from generated-output quality. The 29-case dataset at `backend/evals/fixtures/ai_question_safety_v1.json` tests supported wording, safe-but-unsupported requests, likely patient information, patient-specific interpretation, clinical advice, deterministic ranking overrides, and adversarial prompt injection.

```bash
PYTHONPATH=. python -m app.evals.ai_question_safety
PYTHONPATH=. python -m app.evals.ai_question_safety --require-scientific-review
```

The first command is an engineering regression gate and checks both safety classification and deterministic saved-evidence routing. The strict command exits with status 2 until the scientific/safety annotations are reviewed. See `docs/16_GUARDED_QA_SAFETY.md` for the layered request flow and the additional gates required before the disabled endpoint can be enabled.
