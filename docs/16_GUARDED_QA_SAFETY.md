# Guarded Q&A safety gate

Guarded free-text Q&A has a backend endpoint, deterministic preflight, saved-evidence support classifier, and results-page panel. It follows the global `AI_ENABLED` switch and has no separate activation flag. The fixture annotations still require scientific/safety review before public deployment.

## Layered request flow

The backend endpoint applies these checks in order:

1. normalize the question with Unicode NFKC and enforce the 500-character limit;
2. run `assess_ai_question()` before logging or persistence;
3. refuse likely patient identifiers, patient-specific interpretation, clinical advice, ranking changes, and prompt injection;
4. validate zero to three explicitly selected saved candidates;
5. decide deterministically whether saved run or selected-candidate evidence can support the question topic;
6. return `unsupported_by_saved_evidence` rather than browse, infer, or invent missing facts;
7. compute authoritative candidate facts and explicit false-classification premise corrections on the server;
8. if supported, call the model with a strict schema and validate every returned source ID against the supplied evidence packet;
9. require an exact structured echo of selected-candidate final calls, scores, evidence counts, truncation, and shortlist positions;
10. reject generated prose that contradicts a selected candidate's classification or introduces numeric claims absent from the saved sources.

The preflight and evidence-support decisions are intentionally separate. For example, a question about later literature is safe in wording but unsupported by a frozen saved run. It passes lexical preflight and receives an evidence-bound unsupported response without a model call. Candidate-specific questions require explicit candidate selection rather than extracting gene symbols from arbitrary text.

## Deterministic refusal codes

`backend/app/services/ai_question_safety.py` returns one stable code and a generic public message:

- `EMPTY_QUESTION`
- `QUESTION_TOO_LONG`
- `PATIENT_IDENTIFIABLE`
- `PATIENT_SPECIFIC`
- `CLINICAL_ADVICE`
- `RANKING_OVERRIDE`
- `PROMPT_INJECTION`
- `SAFE`

Rejected question text must not be persisted or included in application logs. Public errors must not echo suspected identifiers. These lexical checks are defense in depth, not a complete privacy or safety system.

## Offline adversarial fixtures

`backend/evals/fixtures/ai_question_safety_v1.json` contains synthetic cases for:

- ordinary saved-evidence explanation questions;
- safe wording that is unsupported or off-topic;
- synthetic names, email addresses, record numbers, birth dates, and phone numbers;
- patient-specific interpretation and clinical advice;
- attempts to override classifications, shortlist membership, and rank;
- instruction override, secret extraction, role-play bypass, and destructive SQL prompts.

No fixture contains real patient information. Run the suite from `backend/`:

```bash
PYTHONPATH=. python -m app.evals.ai_question_safety
pytest -q tests/test_ai_question_safety.py
```

The engineering runner exits zero when deterministic expectations pass. The stricter release command remains non-zero while any annotation needs scientific/safety review:

```bash
PYTHONPATH=. python -m app.evals.ai_question_safety --require-scientific-review
```

Exit status 2 means the engineering checks passed but review is pending.

## Release gate

Do not deploy the Q&A UI publicly until all of the following are complete:

- scientific/safety review of the versioned fixture expectations;
- tests or operational verification that rejected text is absent from production access/application logs;
- rate limits, input bounds, generic errors, and AI-off behavior;
- deployed-browser verification that the research disclaimer and patient-data warning appear before submission.

Already implemented are the conservative support classifier, strict answer schema, server-side source allow-list validation, deterministic fact matching, false-premise correction, unsupported-number rejection, no-model-call refusal/unsupported paths, hashed cache identity, bounded candidate selection, pre-submission disclaimer and patient-data warning, and tests proving raw questions are not stored in `AIInsight`. Prompt and output schema version `saved-evidence-question-v2` intentionally invalidate v1 cached answers.

OpenAI's safety guidance recommends adversarial testing with representative inputs and prompt-injection attempts. The fixture set applies that practice, but ASO Compass's repository rules—especially the prohibition on patient data and AI changes to deterministic science—remain the controlling policy.
