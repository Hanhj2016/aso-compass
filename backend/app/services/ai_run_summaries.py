from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any, Protocol

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, OpenAIError, RateLimitError
from pydantic import ValidationError

from app.core.settings import Settings
from app.models import Candidate, Run
from app.schemas.ai import RunSummaryOutput
from app.services.ai_explanations import AIExplanationError

PROMPT_VERSION = "run-summary-v1"
OUTPUT_SCHEMA_VERSION = "run-summary-v1"
MAX_CANDIDATE_EXCERPTS = 25
logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """You summarize one saved deterministic ASO Compass run for research and education.
Use only the supplied evidence packet. Do not add outside facts or citations. Preserve every source_id
exactly and cite each scientific claim with supplied source_ids. Counts, tracks, scores, shortlist positions,
warnings, and exclusions are fixed inputs: explain them but never revise them, re-rank candidates, select a
best target, or recommend treatment. Distinguish missing, not checked, failed, and negative evidence. Make
caps, truncation, and quick-mode limitations prominent. Candidate excerpts are illustrative and may not
include every candidate; run-wide claims must use the deterministic aggregate source. Keep the overview
under 140 words, each claim under 45 words, and each track interpretation under 35 words. Do not provide
clinical, dosing, treatment, or patient-specific advice."""


@dataclass(frozen=True)
class RunSummaryProviderResult:
    output: RunSummaryOutput
    response_id: str


class RunSummaryProvider(Protocol):
    def generate(
        self, packet: dict[str, Any], packet_hash: str, settings: Settings
    ) -> RunSummaryProviderResult: ...


class OpenAIRunSummaryProvider:
    def generate(
        self, packet: dict[str, Any], packet_hash: str, settings: Settings
    ) -> RunSummaryProviderResult:
        if settings.openai_api_key is None:
            raise AIExplanationError("AI_NOT_CONFIGURED", "AI summaries are not configured.")
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
                text_format=RunSummaryOutput,
                text={"verbosity": "low"},
                max_output_tokens=settings.ai_max_output_tokens,
                reasoning={"effort": "none"},
                prompt_cache_key=packet_hash,
                metadata={"feature": "run_summary", "environment": settings.app_env},
                store=False,
            )
        except ValidationError as exc:
            logger.warning("OpenAI run summary was invalid or truncated")
            raise AIExplanationError("AI_RESPONSE_INVALID", "The summary was incomplete; please retry.") from exc
        except RateLimitError as exc:
            logger.warning("OpenAI rate limit request_id=%s", getattr(exc, "request_id", None))
            raise AIExplanationError(
                "AI_UPSTREAM_RATE_LIMITED", "The summary service is busy; please retry later."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning("OpenAI connection failure type=%s", type(exc).__name__)
            raise AIExplanationError(
                "AI_UPSTREAM_UNAVAILABLE", "The summary service is temporarily unavailable."
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
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The summary could not be generated.") from exc
        except OpenAIError as exc:
            logger.warning("OpenAI SDK error type=%s", type(exc).__name__)
            raise AIExplanationError("AI_UPSTREAM_ERROR", "The summary could not be generated.") from exc

        if response.status != "completed" or response.output_parsed is None:
            raise AIExplanationError("AI_RESPONSE_INCOMPLETE", "The summary was refused or incomplete.")
        try:
            output = RunSummaryOutput.model_validate(response.output_parsed)
        except (ValidationError, TypeError, ValueError) as exc:
            raise AIExplanationError("AI_RESPONSE_INVALID", "The summary did not match the required schema.") from exc
        logger.info(
            "OpenAI run summary completed response_id=%s request_id=%s",
            response.id,
            getattr(response, "_request_id", None),
        )
        return RunSummaryProviderResult(output=output, response_id=response.id)


def get_run_summary_provider() -> RunSummaryProvider:
    return OpenAIRunSummaryProvider()


def _candidate_excerpt(candidate: Candidate) -> dict[str, Any]:
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
            "final_call",
            "call_source",
            "confidence_tier",
            "confidence_reason",
            "flag",
            "drug_status",
            "aso_precedent",
            "shortlist_position",
            "completeness",
        )
    }


def build_run_summary_packet(
    run: Run, candidates: list[Candidate]
) -> tuple[dict[str, Any], str, set[str]]:
    run_source_id = f"run:{run.id}"
    aggregate_source_id = f"run-summary:{run.id}"
    track_counts = Counter(candidate.final_call for candidate in candidates)
    completeness_counts = Counter(candidate.completeness for candidate in candidates)
    aggregate = {
        "candidate_count": len(candidates),
        "track_counts": dict(sorted(track_counts.items())),
        "shortlist_count": sum(candidate.shortlist_position is not None for candidate in candidates),
        "evidence_truncated_count": sum(bool(candidate.evidence_truncated) for candidate in candidates),
        "aso_precedent_count": sum(bool(candidate.aso_precedent) for candidate in candidates),
        "flagged_candidate_count": sum(bool(candidate.flag) for candidate in candidates),
        "completeness_counts": dict(sorted(completeness_counts.items())),
    }
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            candidate.shortlist_position is None,
            candidate.shortlist_position if candidate.shortlist_position is not None else 10**9,
            -candidate.overall_score,
            candidate.gene_symbol,
        ),
    )
    selected = ordered[:MAX_CANDIDATE_EXCERPTS]
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
                "validation": run.validation,
                "upstream_metadata": run.upstream_metadata,
            },
        },
        {"source_id": aggregate_source_id, "kind": "deterministic_run_aggregate", "data": aggregate},
    ]
    sources.extend(
        {
            "source_id": f"candidate:{candidate.ensembl_id}",
            "kind": "deterministic_candidate_excerpt",
            "data": _candidate_excerpt(candidate),
        }
        for candidate in selected
    )
    packet = {
        "task": "Summarize the saved deterministic run without changing or extending its results.",
        "candidate_excerpt_policy": {
            "included": len(selected),
            "total": len(candidates),
            "selection": "shortlist position, then overall score; maximum 25",
        },
        "sources": sources,
    }
    serialized = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
    packet_hash = hashlib.sha256(serialized.encode()).hexdigest()
    return packet, packet_hash, {str(source["source_id"]) for source in sources}


def validate_run_summary_source_ids(
    output: RunSummaryOutput, allowed_source_ids: set[str]
) -> list[str]:
    cited: set[str] = set()
    claims = [*output.key_findings, *output.evidence_gaps, *output.review_priorities]
    source_groups = [claim.source_ids for claim in claims]
    source_groups.extend(track.source_ids for track in output.track_breakdown)
    for source_ids in source_groups:
        unknown = set(source_ids) - allowed_source_ids
        if unknown:
            raise AIExplanationError(
                "AI_SOURCE_VALIDATION_FAILED",
                "The generated summary referenced an unverified source.",
            )
        cited.update(source_ids)
    if not cited:
        raise AIExplanationError(
            "AI_SOURCE_VALIDATION_FAILED", "The generated summary did not cite supplied evidence."
        )
    return sorted(cited)
