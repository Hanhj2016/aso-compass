from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    LengthFinishReasonError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.settings import Settings
from app.models import Candidate, Evidence, Run
from app.schemas.ai import AuthoritativeCandidateFact, QuestionAnswerOutput
from app.services.ai_explanations import AIExplanationError

PROMPT_VERSION = "saved-evidence-question-v2"
OUTPUT_SCHEMA_VERSION = "saved-evidence-question-v2"
logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """Answer one question about a saved deterministic ASO Compass run for research
and education. Use only the supplied sources; do not use outside knowledge, browse, or add citations.
Preserve source_id values exactly and attach them to every scientific claim. Copy
candidate_fact_checks_required into candidate_fact_checks exactly as supplied. Deterministic classifications, scores, rankings,
shortlist membership, warnings, and exclusions are fixed: explain but never revise them. If the packet contains
premise_corrections, acknowledge the correction before answering and do not repeat the false premise as fact.
If the supplied sources do not support the requested fact, set answer_status to
insufficient_saved_evidence and state that limitation plainly. Distinguish missing, not checked, failed,
truncated, and negative evidence. Never provide clinical, treatment, dosing, prognosis, patient-specific,
or target-selection advice. Keep the answer under 140 words, use at most 4 cited claims, and be concise."""

_TRACKS = ("knockdown", "splice / upregulation", "ambiguous", "modifier", "insufficient data")
_NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])")

SupportCode = Literal[
    "SUPPORTED_RUN_EVIDENCE",
    "SUPPORTED_CANDIDATE_EVIDENCE",
    "UNSUPPORTED_SELECTION_REQUIRED",
    "UNSUPPORTED_BY_SAVED_EVIDENCE",
]


class EvidenceSupportAssessment(BaseModel):
    supported: bool
    code: SupportCode
    public_message: str


_RUN_TOPIC_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bquick[- ]mode\b",
        r"\b(?:run|analysis)\s+(?:warning|warnings|limitation|limitations|summary)\b",
        r"\b(?:how many|number of)\s+(?:candidates|genes|shortlisted candidates|shortlist entries)\b",
        r"\b(?:track|classification)\s+(?:count|counts|breakdown|distribution)\b",
        r"\b(?:evidence|variant)\s+(?:cap|caps|capped|truncation|truncated)\b",
    )
)

_CANDIDATE_TOPIC_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:classif(?:y|ied|ication)|final[_ ]?call|call source|confidence|track|direction)\b",
        r"\b(?:modifier|knockdown|splice|upregulation|ambiguous|insufficient data)\b",
        r"\b(?:overall|genetic|association)\s+score\b",
        r"\b(?:score|scores|loeuf|constraint)\b",
        r"\b(?:saved )?(?:evidence|source|sources|record|records|clinvar|variant|variants)\b",
        r"\b(?:mechanism|g2p|inheritance|loss[- ]of[- ]function|lof|missense)\b",
        r"\b(?:drug|therapeutic|aso|trial|precedent|approved)\b",
        r"\b(?:warning|warnings|gap|gaps|missing|truncated|completeness)\b",
    )
)


def _matches_any(question: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(question) is not None for pattern in patterns)


def assess_saved_evidence_support(
    question: str, selected_gene_symbols: list[str]
) -> EvidenceSupportAssessment:
    """Conservatively route a safe question without calling a model."""

    normalized = unicodedata.normalize("NFKC", question).strip()
    if _matches_any(normalized, _RUN_TOPIC_PATTERNS):
        return EvidenceSupportAssessment(
            supported=True,
            code="SUPPORTED_RUN_EVIDENCE",
            public_message="The question can be checked against saved run evidence.",
        )
    if _matches_any(normalized, _CANDIDATE_TOPIC_PATTERNS):
        if selected_gene_symbols:
            return EvidenceSupportAssessment(
                supported=True,
                code="SUPPORTED_CANDIDATE_EVIDENCE",
                public_message="The question can be checked against the selected saved candidates.",
            )
        return EvidenceSupportAssessment(
            supported=False,
            code="UNSUPPORTED_SELECTION_REQUIRED",
            public_message="Select up to three saved candidates for this evidence question.",
        )
    return EvidenceSupportAssessment(
        supported=False,
        code="UNSUPPORTED_BY_SAVED_EVIDENCE",
        public_message="This question is not supported by the saved run evidence.",
    )


@dataclass(frozen=True)
class QuestionProviderResult:
    output: QuestionAnswerOutput
    response_id: str


class QuestionProvider(Protocol):
    def generate(
        self, packet: dict[str, Any], packet_hash: str, settings: Settings
    ) -> QuestionProviderResult: ...


class OpenAIQuestionProvider:
    def generate(
        self, packet: dict[str, Any], packet_hash: str, settings: Settings
    ) -> QuestionProviderResult:
        if settings.openai_api_key is None:
            raise AIExplanationError("AI_NOT_CONFIGURED", "AI questions are not configured.")
        client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.ai_timeout_seconds,
            max_retries=2,
        )
        try:
            response = client.responses.parse(
                model=settings.openai_model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str),
                text_format=QuestionAnswerOutput,
                text={"verbosity": "low"},
                max_output_tokens=settings.ai_max_output_tokens,
                reasoning={"effort": "none"},
                prompt_cache_key=packet_hash,
                metadata={"feature": "saved_evidence_question", "environment": settings.app_env},
                store=False,
            )
        except ValidationError as exc:
            logger.warning("OpenAI saved-evidence answer was invalid or truncated")
            raise AIExplanationError(
                "AI_RESPONSE_INVALID", "The answer was incomplete; please retry."
            ) from exc
        except RateLimitError as exc:
            logger.warning("OpenAI rate limit request_id=%s", getattr(exc, "request_id", None))
            raise AIExplanationError(
                "AI_UPSTREAM_RATE_LIMITED", "The question service is busy; please retry later."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("OpenAI connection failure type=%s", type(exc).__name__)
            raise AIExplanationError(
                "AI_UPSTREAM_UNAVAILABLE", "The question service is temporarily unavailable."
            ) from exc
        except LengthFinishReasonError as exc:
            logger.warning("OpenAI saved-evidence answer reached the output-token limit")
            raise AIExplanationError(
                "AI_RESPONSE_INCOMPLETE", "The answer exceeded its output limit; please retry."
            ) from exc
        except APIError as exc:
            logger.warning(
                "OpenAI API error status=%s code=%s param=%s type=%s request_id=%s",
                getattr(exc, "status_code", None),
                exc.code,
                exc.param,
                exc.type,
                getattr(exc, "request_id", None),
            )
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The answer could not be generated.") from exc
        except OpenAIError as exc:
            logger.warning("OpenAI SDK error type=%s", type(exc).__name__)
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The answer could not be generated.") from exc

        if response.status != "completed" or response.output_parsed is None:
            raise AIExplanationError("AI_RESPONSE_INCOMPLETE", "The answer was refused or incomplete.")
        try:
            output = QuestionAnswerOutput.model_validate(response.output_parsed)
        except (ValidationError, TypeError, ValueError) as exc:
            raise AIExplanationError(
                "AI_RESPONSE_INVALID", "The answer did not match the required schema."
            ) from exc
        logger.info(
            "OpenAI saved-evidence answer completed response_id=%s request_id=%s",
            response.id,
            getattr(response, "_request_id", None),
        )
        return QuestionProviderResult(output=output, response_id=response.id)


def get_question_provider() -> QuestionProvider:
    return OpenAIQuestionProvider()


def _candidate_data(candidate: Candidate) -> dict[str, Any]:
    return {
        key: getattr(candidate, key)
        for key in (
            "ensembl_id",
            "gene_symbol",
            "gene_name",
            "overall_score",
            "genetic_score",
            "loeuf",
            "n_evidence",
            "n_evidence_returned",
            "evidence_truncated",
            "n_lof",
            "n_splice",
            "n_splice_extra",
            "n_missense",
            "frac_lof",
            "frac_splice_related",
            "g2p_mech",
            "inheritance",
            "clinvar_call",
            "final_call",
            "call_source",
            "confidence_tier",
            "confidence_reason",
            "flag",
            "note",
            "drug_status",
            "approved_drugs",
            "aso_names",
            "aso_trial_n",
            "aso_trial_ids",
            "aso_precedent",
            "shortlist_position",
            "completeness",
        )
    }


def build_authoritative_candidate_facts(
    candidates: list[Candidate],
) -> list[AuthoritativeCandidateFact]:
    return [
        AuthoritativeCandidateFact(
            gene_symbol=candidate.gene_symbol,
            final_call=candidate.final_call,
            confidence_tier=candidate.confidence_tier,
            overall_score=candidate.overall_score,
            genetic_score=candidate.genetic_score,
            n_evidence=candidate.n_evidence,
            n_evidence_returned=candidate.n_evidence_returned,
            evidence_truncated=candidate.evidence_truncated,
            shortlist_position=candidate.shortlist_position,
            completeness=candidate.completeness,
            source_id=f"candidate:{candidate.ensembl_id}",
        )
        for candidate in sorted(candidates, key=lambda item: item.gene_symbol)
    ]


def detect_false_classification_premises(
    question: str, candidates: list[Candidate]
) -> list[str]:
    """Detect only explicit, safely correctable classification assertions."""

    normalized = unicodedata.normalize("NFKC", question).lower().replace("_", " ")
    corrections: list[str] = []
    for candidate in sorted(candidates, key=lambda item: item.gene_symbol):
        symbol = re.escape(candidate.gene_symbol.lower())
        subjects = [symbol]
        if len(candidates) == 1:
            subjects.extend((r"it", r"this candidate", r"the candidate"))
        assumed: str | None = None
        for track in _TRACKS:
            escaped_track = re.escape(track).replace(r"\ ", r"\s+")
            for subject in subjects:
                patterns = (
                    rf"\b{subject}\b\s+(?:is|was)\s+(?:classified\s+as\s+)?[\"'“”]?{escaped_track}\b",
                    rf"\bwhy\s+(?:is|was)\s+\b{subject}\b\s+(?:classified\s+as\s+)?[\"'“”]?{escaped_track}\b",
                )
                if any(re.search(pattern, normalized) for pattern in patterns):
                    assumed = track
                    break
            if assumed is not None:
                break
        if assumed is not None and assumed != candidate.final_call.lower():
            corrections.append(
                f"{candidate.gene_symbol} is not classified as {assumed} in this saved run. "
                f"Its deterministic final call is {candidate.final_call}."
            )
    return corrections


def build_question_packet(
    run: Run,
    all_candidates: list[Candidate],
    selected_candidates: list[Candidate],
    evidence_rows: list[Evidence],
    question: str,
) -> tuple[dict[str, Any], str, set[str]]:
    normalized_question = unicodedata.normalize("NFKC", question).strip()
    track_counts = Counter(candidate.final_call for candidate in all_candidates)
    sources: list[dict[str, Any]] = [
        {
            "source_id": f"run:{run.id}",
            "kind": "run_context",
            "data": {
                "disease_id": run.disease_id,
                "disease_label": run.disease_label,
                "engine_version": run.engine_version,
                "parameters": run.parameters,
                "warnings": run.warnings,
                "validation": run.validation,
                "upstream_metadata": run.upstream_metadata,
            },
        },
        {
            "source_id": f"run-summary:{run.id}",
            "kind": "deterministic_run_aggregate",
            "data": {
                "candidate_count": len(all_candidates),
                "track_counts": dict(sorted(track_counts.items())),
                "shortlist_count": sum(
                    candidate.shortlist_position is not None for candidate in all_candidates
                ),
                "evidence_truncated_count": sum(
                    bool(candidate.evidence_truncated) for candidate in all_candidates
                ),
                "aso_precedent_count": sum(bool(candidate.aso_precedent) for candidate in all_candidates),
            },
        },
    ]
    for candidate in sorted(selected_candidates, key=lambda item: item.gene_symbol):
        sources.append(
            {
                "source_id": f"candidate:{candidate.ensembl_id}",
                "kind": "deterministic_candidate",
                "data": _candidate_data(candidate),
            }
        )
    selected_ids = {candidate.id for candidate in selected_candidates}
    for row in sorted(evidence_rows, key=lambda item: str(item.id)):
        if row.candidate_id not in selected_ids:
            continue
        sources.append(
            {
                "source_id": f"evidence:{row.id}",
                "kind": row.source,
                "candidate_id": str(row.candidate_id),
                "external_id": row.external_id,
                "retrieved_at": row.retrieved_at,
                "upstream_release": row.upstream_release,
                "completeness": row.completeness,
                "data": row.normalized,
            }
        )
    authoritative_facts = build_authoritative_candidate_facts(selected_candidates)
    premise_corrections = detect_false_classification_premises(
        normalized_question, selected_candidates
    )
    packet = {
        "task": "Answer the question using only this saved deterministic evidence.",
        "question": normalized_question,
        "selected_gene_symbols": [
            candidate.gene_symbol
            for candidate in sorted(selected_candidates, key=lambda item: item.gene_symbol)
        ],
        "authoritative_candidate_facts": [
            fact.model_dump(mode="json") for fact in authoritative_facts
        ],
        "candidate_fact_checks_required": [
            {
                "gene_symbol": candidate.gene_symbol,
                "final_call": candidate.final_call,
                "overall_score": candidate.overall_score,
                "genetic_score": candidate.genetic_score,
                "n_evidence": candidate.n_evidence,
                "n_evidence_returned": candidate.n_evidence_returned,
                "evidence_truncated": candidate.evidence_truncated,
                "shortlist_position": candidate.shortlist_position,
                "source_ids": [f"candidate:{candidate.ensembl_id}"],
            }
            for candidate in sorted(selected_candidates, key=lambda item: item.gene_symbol)
        ],
        "premise_corrections": premise_corrections,
        "sources": sources,
    }
    serialized = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    packet_hash = hashlib.sha256(serialized.encode()).hexdigest()
    return packet, packet_hash, {str(source["source_id"]) for source in sources}


def validate_question_source_ids(
    output: QuestionAnswerOutput, allowed_source_ids: set[str]
) -> list[str]:
    cited: set[str] = set()
    for claim in output.cited_claims:
        unknown = set(claim.source_ids) - allowed_source_ids
        if unknown:
            raise AIExplanationError(
                "AI_SOURCE_VALIDATION_FAILED",
                "The generated answer referenced an unverified source.",
            )
        cited.update(claim.source_ids)
    if output.answer_status == "answered" and not cited:
        raise AIExplanationError(
            "AI_SOURCE_VALIDATION_FAILED",
            "The generated answer did not cite supplied evidence.",
        )
    return sorted(cited)


def _human_output_text(output: QuestionAnswerOutput) -> str:
    parts = [output.answer]
    parts.extend(claim.claim for claim in output.cited_claims)
    parts.extend(output.uncertainties)
    parts.extend(output.manual_review_steps)
    parts.extend(output.what_this_does_not_mean)
    return "\n".join(parts)


def _numeric_values(value: Any) -> set[Decimal]:
    serialized = json.dumps(value, sort_keys=True, default=str)
    values: set[Decimal] = set()
    for match in _NUMBER_PATTERN.findall(serialized):
        try:
            values.add(Decimal(match.replace(",", "")))
        except InvalidOperation:
            continue
    return values


def validate_question_determinism(
    output: QuestionAnswerOutput,
    selected_candidates: list[Candidate],
    packet: dict[str, Any],
) -> None:
    """Reject structured or prose claims that conflict with fixed saved fields."""

    expected = {candidate.gene_symbol.upper(): candidate for candidate in selected_candidates}
    checks = {check.gene_symbol.upper(): check for check in output.candidate_fact_checks}
    if set(checks) != set(expected) or len(checks) != len(output.candidate_fact_checks):
        raise AIExplanationError(
            "AI_DETERMINISTIC_CONFLICT",
            "The generated answer did not preserve the selected candidate facts.",
        )
    for symbol, candidate in expected.items():
        check = checks[symbol]
        expected_source = f"candidate:{candidate.ensembl_id}"
        if (
            check.final_call != candidate.final_call
            or check.overall_score != candidate.overall_score
            or check.genetic_score != candidate.genetic_score
            or check.n_evidence != candidate.n_evidence
            or check.n_evidence_returned != candidate.n_evidence_returned
            or check.evidence_truncated != candidate.evidence_truncated
            or check.shortlist_position != candidate.shortlist_position
            or check.source_ids != [expected_source]
        ):
            raise AIExplanationError(
                "AI_DETERMINISTIC_CONFLICT",
                "The generated answer conflicted with the saved deterministic result.",
            )

    text = unicodedata.normalize("NFKC", _human_output_text(output)).lower()
    for candidate in selected_candidates:
        subjects = [re.escape(candidate.gene_symbol.lower())]
        if len(selected_candidates) == 1:
            subjects.extend((r"the candidate", r"it"))
        for track in _TRACKS:
            if track == candidate.final_call.lower():
                continue
            escaped_track = re.escape(track).replace(r"\ ", r"\s+")
            patterns: list[str] = []
            for subject in subjects:
                patterns.extend(
                    (
                        rf"\b{subject}\b\s+(?:is|was|has been)\s+(?!not\b)(?:classified\s+as|categorized\s+as|called)\s+[\"'“”]?{escaped_track}\b",
                        rf"\b{subject}\b[^.\n]{{0,80}}\b(?:final|deterministic)\s+(?:classification|call)\s+(?:is|was)\s+[\"'“”]?{escaped_track}\b",
                    )
                )
            if any(re.search(pattern, text) for pattern in patterns):
                raise AIExplanationError(
                    "AI_DETERMINISTIC_CONFLICT",
                    "The generated answer conflicted with the saved deterministic result.",
                )

    allowed_numbers = _numeric_values(packet["sources"])
    claimed_numbers = _numeric_values(_human_output_text(output))
    if claimed_numbers - allowed_numbers:
        raise AIExplanationError(
            "AI_DETERMINISTIC_CONFLICT",
            "The generated answer included a number not found in the saved evidence.",
        )
