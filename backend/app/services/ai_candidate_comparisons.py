from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    LengthFinishReasonError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.settings import Settings
from app.models import Candidate, Evidence, Run
from app.schemas.ai import CandidateComparisonOutput
from app.services.ai_explanations import AIExplanationError

PROMPT_VERSION = "candidate-comparison-v2"
OUTPUT_SCHEMA_VERSION = "candidate-comparison-v2"
logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """Compare exactly the supplied deterministic ASO Compass candidates for research
and education. Use only the supplied evidence packet; do not add outside facts or citations. Preserve each
source_id exactly and cite every scientific claim. Explain differences in saved classification, association
scores, mechanism evidence, constraint, evidence completeness, warnings, and therapeutic precedent. Do not
name a winner, choose a best target, create a new rank, revise any deterministic field, or imply that a score
is a treatment recommendation. Distinguish missing, not checked, failed, and negative evidence, and mention
caps or truncation. Return one candidate summary for every supplied gene symbol and no others. Keep the
overview under 120 words and individual explanations under 45 words. Do not provide clinical, dosing,
treatment, or patient-specific advice. Stay within this compact budget: overview at most 90 words; each
candidate summary at most 35 words; at most 4 key differences with at most 30 words each; at most 2 shared
features; at most 3 evidence gaps; at most 3 review priorities; at most 3 limitations; and at most 3
"what this does not mean" items. Prefer fewer items when evidence is sparse."""


@dataclass(frozen=True)
class CandidateComparisonProviderResult:
    output: CandidateComparisonOutput
    response_id: str


class CandidateComparisonProvider(Protocol):
    def generate(
        self, packet: dict[str, Any], packet_hash: str, settings: Settings
    ) -> CandidateComparisonProviderResult: ...


class OpenAICandidateComparisonProvider:
    def generate(
        self, packet: dict[str, Any], packet_hash: str, settings: Settings
    ) -> CandidateComparisonProviderResult:
        if settings.openai_api_key is None:
            raise AIExplanationError("AI_NOT_CONFIGURED", "AI comparisons are not configured.")
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
                text_format=CandidateComparisonOutput,
                text={"verbosity": "low"},
                max_output_tokens=settings.ai_max_output_tokens,
                reasoning={"effort": "none"},
                prompt_cache_key=packet_hash,
                metadata={"feature": "candidate_comparison", "environment": settings.app_env},
                store=False,
            )
        except ValidationError as exc:
            validation_details = [
                {"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
                for error in exc.errors(include_url=False, include_input=False)[:3]
            ]
            logger.warning(
                "OpenAI candidate comparison was invalid or truncated validation=%s",
                validation_details,
            )
            raise AIExplanationError(
                "AI_RESPONSE_INVALID", "The comparison was incomplete; please retry."
            ) from exc
        except RateLimitError as exc:
            logger.warning("OpenAI rate limit request_id=%s", getattr(exc, "request_id", None))
            raise AIExplanationError(
                "AI_UPSTREAM_RATE_LIMITED", "The comparison service is busy; please retry later."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("OpenAI connection failure type=%s", type(exc).__name__)
            raise AIExplanationError(
                "AI_UPSTREAM_UNAVAILABLE", "The comparison service is temporarily unavailable."
            ) from exc
        except LengthFinishReasonError as exc:
            logger.warning("OpenAI candidate comparison reached the output-token limit")
            raise AIExplanationError(
                "AI_RESPONSE_INCOMPLETE", "The comparison exceeded its output limit; please retry."
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
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The comparison could not be generated.") from exc
        except OpenAIError as exc:
            logger.warning("OpenAI SDK error type=%s", type(exc).__name__)
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The comparison could not be generated.") from exc

        if response.status != "completed" or response.output_parsed is None:
            raise AIExplanationError("AI_RESPONSE_INCOMPLETE", "The comparison was refused or incomplete.")
        try:
            output = CandidateComparisonOutput.model_validate(response.output_parsed)
        except (ValidationError, TypeError, ValueError) as exc:
            raise AIExplanationError(
                "AI_RESPONSE_INVALID", "The comparison did not match the required schema."
            ) from exc
        logger.info(
            "OpenAI candidate comparison completed response_id=%s request_id=%s",
            response.id,
            getattr(response, "_request_id", None),
        )
        return CandidateComparisonProviderResult(output=output, response_id=response.id)


def get_candidate_comparison_provider() -> CandidateComparisonProvider:
    return OpenAICandidateComparisonProvider()


def build_candidate_comparison_packet(
    run: Run, candidates: list[Candidate], evidence_rows: list[Evidence]
) -> tuple[dict[str, Any], str, set[str]]:
    ordered_candidates = sorted(candidates, key=lambda candidate: candidate.gene_symbol)
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
                "upstream_metadata": run.upstream_metadata,
            },
        }
    ]
    for candidate in ordered_candidates:
        sources.append(
            {
                "source_id": f"candidate:{candidate.ensembl_id}",
                "kind": "deterministic_candidate",
                "data": {
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
                },
            }
        )
    for row in sorted(evidence_rows, key=lambda item: str(item.id)):
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
    packet = {
        "task": "Compare these saved candidates without ranking or changing them.",
        "compared_gene_symbols": [candidate.gene_symbol for candidate in ordered_candidates],
        "sources": sources,
    }
    serialized = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    packet_hash = hashlib.sha256(serialized.encode()).hexdigest()
    return packet, packet_hash, {str(source["source_id"]) for source in sources}


def validate_candidate_comparison(
    output: CandidateComparisonOutput,
    allowed_source_ids: set[str],
    expected_gene_symbols: set[str],
) -> list[str]:
    returned_symbols = {summary.gene_symbol.upper() for summary in output.candidate_summaries}
    if returned_symbols != expected_gene_symbols or len(returned_symbols) != len(output.candidate_summaries):
        raise AIExplanationError(
            "AI_CANDIDATE_VALIDATION_FAILED",
            "The generated comparison did not preserve the selected candidates.",
        )
    source_groups = [summary.source_ids for summary in output.candidate_summaries]
    source_groups.extend(difference.source_ids for difference in output.key_differences)
    claims = [*output.shared_features, *output.evidence_gaps, *output.review_priorities]
    source_groups.extend(claim.source_ids for claim in claims)
    cited: set[str] = set()
    for source_ids in source_groups:
        unknown = set(source_ids) - allowed_source_ids
        if unknown:
            raise AIExplanationError(
                "AI_SOURCE_VALIDATION_FAILED",
                "The generated comparison referenced an unverified source.",
            )
        cited.update(source_ids)
    if not cited:
        raise AIExplanationError(
            "AI_SOURCE_VALIDATION_FAILED", "The generated comparison did not cite supplied evidence."
        )
    return sorted(cited)
