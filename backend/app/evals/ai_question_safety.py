from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.evals.ai_outputs import EvalAnnotation
from app.services.ai_question_safety import QuestionSafetyCode, assess_ai_question
from app.services.ai_questions import assess_saved_evidence_support

DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "evals" / "fixtures" / "ai_question_safety_v1.json"
AnswerMode = Literal["evidence_answer", "unsupported_by_saved_evidence", "refused"]


class QuestionSafetyCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    question: str
    selected_gene_symbols: list[str] = Field(default_factory=list, max_length=3)
    expected_allowed: bool
    expected_code: QuestionSafetyCode
    expected_answer_mode: AnswerMode
    tags: list[str] = Field(min_length=1)
    annotation: EvalAnnotation

    @field_validator("expected_answer_mode")
    @classmethod
    def require_answer_mode_consistency(
        cls, answer_mode: AnswerMode, info: object
    ) -> AnswerMode:
        data = getattr(info, "data", {})
        expected_allowed = data.get("expected_allowed")
        if expected_allowed is True and answer_mode == "refused":
            raise ValueError("Allowed questions cannot expect a refusal")
        if expected_allowed is False and answer_mode != "refused":
            raise ValueError("Rejected questions must expect a refusal")
        return answer_mode


class QuestionSafetyDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_name: str
    schema_version: str
    cases: list[QuestionSafetyCase] = Field(min_length=1)

    @field_validator("cases")
    @classmethod
    def require_unique_cases(cls, cases: list[QuestionSafetyCase]) -> list[QuestionSafetyCase]:
        case_ids = [case.case_id for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Question safety case IDs must be unique")
        return cases


class QuestionSafetyCaseResult(BaseModel):
    case_id: str
    passed: bool
    expected_code: QuestionSafetyCode
    actual_code: QuestionSafetyCode
    expected_answer_mode: AnswerMode
    actual_answer_mode: AnswerMode


class QuestionSafetySuiteResult(BaseModel):
    dataset_name: str
    schema_version: str
    passed: bool
    case_count: int
    passed_count: int
    pending_scientific_review_count: int
    scientific_review_complete: bool
    results: list[QuestionSafetyCaseResult]


def load_question_safety_dataset(path: Path = DEFAULT_DATASET_PATH) -> QuestionSafetyDataset:
    return QuestionSafetyDataset.model_validate_json(path.read_text(encoding="utf-8"))


def run_question_safety_dataset(dataset: QuestionSafetyDataset) -> QuestionSafetySuiteResult:
    results = []
    for case in dataset.cases:
        assessment = assess_ai_question(case.question)
        if not assessment.allowed:
            actual_answer_mode: AnswerMode = "refused"
        else:
            support = assess_saved_evidence_support(case.question, case.selected_gene_symbols)
            actual_answer_mode = (
                "evidence_answer" if support.supported else "unsupported_by_saved_evidence"
            )
        results.append(
            QuestionSafetyCaseResult(
                case_id=case.case_id,
                passed=assessment.allowed == case.expected_allowed
                and assessment.code == case.expected_code
                and actual_answer_mode == case.expected_answer_mode,
                expected_code=case.expected_code,
                actual_code=assessment.code,
                expected_answer_mode=case.expected_answer_mode,
                actual_answer_mode=actual_answer_mode,
            )
        )
    passed_count = sum(result.passed for result in results)
    pending_count = sum(
        case.annotation.status == "scientific_review_pending" for case in dataset.cases
    )
    return QuestionSafetySuiteResult(
        dataset_name=dataset.dataset_name,
        schema_version=dataset.schema_version,
        passed=passed_count == len(results),
        case_count=len(results),
        passed_count=passed_count,
        pending_scientific_review_count=pending_count,
        scientific_review_complete=pending_count == 0,
        results=results,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the guarded Q&A preflight classifier.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--require-scientific-review", action="store_true")
    args = parser.parse_args(argv)
    result = run_question_safety_dataset(load_question_safety_dataset(args.dataset))
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    if not result.passed:
        return 1
    if args.require_scientific_review and not result.scientific_review_complete:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
