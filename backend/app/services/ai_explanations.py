from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, OpenAIError, RateLimitError
from pydantic import ValidationError

from app.core.settings import Settings
from app.models import Candidate, Evidence, Run
from app.schemas.ai import CandidateExplanationOutput

PROMPT_VERSION = "candidate-explanation-v1"
OUTPUT_SCHEMA_VERSION = "candidate-explanation-v1"
logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """You explain a deterministic ASO target-finding result for research and education.
Use only the supplied evidence packet. Do not add outside facts or citations. Preserve every source_id
exactly and cite each scientific claim with one or more supplied source_ids. The deterministic final_call,
scores, shortlist position, warnings, and exclusions are fixed inputs: explain them but never revise, rank,
or recommend a target. Distinguish missing, not checked, lookup failed, and negative evidence. Mention caps
or truncation. Do not provide treatment, dosing, clinical, or patient-specific advice. Use calibrated,
plain language and make uncertainty prominent. Be concise: use no more than 3 decision-basis claims,
4 supporting claims, 2 conflicting claims, 4 uncertainties, 3 review steps, and 3 limitations. Keep the
summary under 120 words and each claim under 40 words."""


class AIExplanationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProviderResult:
    output: CandidateExplanationOutput
    response_id: str


class ExplanationProvider(Protocol):
    def generate(self, packet: dict[str, Any], packet_hash: str, settings: Settings) -> ProviderResult: ...


class OpenAIExplanationProvider:
    def generate(self, packet: dict[str, Any], packet_hash: str, settings: Settings) -> ProviderResult:
        if settings.openai_api_key is None:
            raise AIExplanationError("AI_NOT_CONFIGURED", "AI explanations are not configured.")
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
                text_format=CandidateExplanationOutput,
                text={"verbosity": "low"},
                max_output_tokens=settings.ai_max_output_tokens,
                reasoning={"effort": "none"},
                prompt_cache_key=packet_hash,
                metadata={"feature": "candidate_explanation", "environment": settings.app_env},
                store=False,
            )
        except ValidationError as exc:
            logger.warning("OpenAI structured response was invalid or truncated")
            raise AIExplanationError(
                "AI_RESPONSE_INVALID", "The explanation was incomplete; please retry."
            ) from exc
        except RateLimitError as exc:
            logger.warning("OpenAI rate limit request_id=%s", getattr(exc, "request_id", None))
            raise AIExplanationError(
                "AI_UPSTREAM_RATE_LIMITED", "The explanation service is busy; please retry later."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("OpenAI connection failure type=%s", type(exc).__name__)
            raise AIExplanationError(
                "AI_UPSTREAM_UNAVAILABLE", "The explanation service is temporarily unavailable."
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
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The explanation could not be generated.") from exc
        except OpenAIError as exc:
            logger.warning("OpenAI SDK error type=%s", type(exc).__name__)
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The explanation could not be generated.") from exc

        if response.status != "completed" or response.output_parsed is None:
            raise AIExplanationError("AI_RESPONSE_INCOMPLETE", "The explanation was refused or incomplete.")
        try:
            output = CandidateExplanationOutput.model_validate(response.output_parsed)
        except (ValidationError, TypeError, ValueError) as exc:
            raise AIExplanationError(
                "AI_RESPONSE_INVALID", "The explanation did not match the required schema."
            ) from exc
        logger.info(
            "OpenAI explanation completed response_id=%s request_id=%s",
            response.id,
            getattr(response, "_request_id", None),
        )
        return ProviderResult(output=output, response_id=response.id)


def get_explanation_provider() -> ExplanationProvider:
    return OpenAIExplanationProvider()


def build_evidence_packet(
    run: Run, candidate: Candidate, evidence_rows: list[Evidence]
) -> tuple[dict[str, Any], str, set[str]]:
    run_source_id = f"run:{run.id}"
    candidate_source_id = f"candidate:{candidate.ensembl_id}"
    sources: list[dict[str, Any]] = [
        {
            "source_id": run_source_id,
            "kind": "run_context",
            "data": {
                "disease_id": run.disease_id,
                "disease_label": run.disease_label,
                "engine_version": run.engine_version,
                "parameters": run.parameters,
                "warnings": run.warnings,
                "upstream_metadata": run.upstream_metadata,
            },
        },
        {
            "source_id": candidate_source_id,
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
        },
    ]
    for row in sorted(evidence_rows, key=lambda item: str(item.id)):
        sources.append(
            {
                "source_id": f"evidence:{row.id}",
                "kind": row.source,
                "external_id": row.external_id,
                "retrieved_at": row.retrieved_at,
                "upstream_release": row.upstream_release,
                "completeness": row.completeness,
                "data": row.normalized,
            }
        )
    packet = {
        "task": "Explain the saved deterministic candidate classification without changing it.",
        "sources": sources,
    }
    serialized = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    packet_hash = hashlib.sha256(serialized.encode()).hexdigest()
    return packet, packet_hash, {str(source["source_id"]) for source in sources}


def validate_source_ids(output: CandidateExplanationOutput, allowed_source_ids: set[str]) -> list[str]:
    cited: set[str] = set()
    groups = (output.decision_basis, output.supporting_evidence, output.conflicting_evidence)
    for claim in (claim for group in groups for claim in group):
        unknown = set(claim.source_ids) - allowed_source_ids
        if unknown:
            raise AIExplanationError(
                "AI_SOURCE_VALIDATION_FAILED",
                "The generated explanation referenced an unverified source.",
            )
        cited.update(claim.source_ids)
    if not cited:
        raise AIExplanationError(
            "AI_SOURCE_VALIDATION_FAILED", "The generated explanation did not cite supplied evidence."
        )
    return sorted(cited)
