from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.settings import Settings, get_settings
from app.db.session import get_session
from app.domain.classification import DISCLAIMER, ENGINE_VERSION
from app.models import AIInsight, Candidate, Evidence, ExportArtifact, Run, RunEvent
from app.schemas.ai import (
    AIQuestionPublic,
    AIQuestionRequest,
    CandidateComparisonOutput,
    CandidateComparisonPublic,
    CandidateComparisonRequest,
    CandidateExplanationOutput,
    CandidateExplanationPublic,
    QuestionAnswerOutput,
    RunSummaryOutput,
    RunSummaryPublic,
)
from app.schemas.runs import CandidatePublic, EventPublic, RunCreate, RunPublic
from app.services.ai_access import require_ai_access
from app.services.ai_candidate_comparisons import (
    OUTPUT_SCHEMA_VERSION as CANDIDATE_COMPARISON_OUTPUT_SCHEMA_VERSION,
)
from app.services.ai_candidate_comparisons import (
    PROMPT_VERSION as CANDIDATE_COMPARISON_PROMPT_VERSION,
)
from app.services.ai_candidate_comparisons import (
    CandidateComparisonProvider,
    build_candidate_comparison_packet,
    get_candidate_comparison_provider,
    validate_candidate_comparison,
)
from app.services.ai_explanations import (
    OUTPUT_SCHEMA_VERSION,
    PROMPT_VERSION,
    AIExplanationError,
    ExplanationProvider,
    build_evidence_packet,
    get_explanation_provider,
    validate_source_ids,
)
from app.services.ai_question_safety import assess_ai_question
from app.services.ai_questions import (
    OUTPUT_SCHEMA_VERSION as QUESTION_OUTPUT_SCHEMA_VERSION,
)
from app.services.ai_questions import PROMPT_VERSION as QUESTION_PROMPT_VERSION
from app.services.ai_questions import (
    QuestionProvider,
    assess_saved_evidence_support,
    build_authoritative_candidate_facts,
    build_question_packet,
    detect_false_classification_premises,
    get_question_provider,
    validate_question_determinism,
    validate_question_source_ids,
)
from app.services.ai_run_summaries import (
    OUTPUT_SCHEMA_VERSION as RUN_SUMMARY_OUTPUT_SCHEMA_VERSION,
)
from app.services.ai_run_summaries import (
    PROMPT_VERSION as RUN_SUMMARY_PROMPT_VERSION,
)
from app.services.ai_run_summaries import (
    RunSummaryProvider,
    build_run_summary_packet,
    get_run_summary_provider,
    validate_run_summary_source_ids,
)
from app.services.rate_limit import ai_explanation_limiter, create_run_limiter
from app.services.runs import input_hash

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]

PRESETS = [
    {"id": "MONDO_0004976", "label": "Amyotrophic lateral sclerosis (ALS)", "group": "Neurodegenerative"},
    {"id": "MONDO_0004975", "label": "Alzheimer disease", "group": "Neurodegenerative"},
    {"id": "MONDO_0005180", "label": "Parkinson disease", "group": "Neurodegenerative"},
    {"id": "MONDO_0007739", "label": "Huntington disease", "group": "Neurogenetic"},
    {"id": "MONDO_0010679", "label": "Duchenne muscular dystrophy", "group": "Neuromuscular"},
    {"id": "MONDO_0001516", "label": "Spinal muscular atrophy", "group": "Neuromuscular"},
    {"id": "MONDO_0100135", "label": "Dravet syndrome", "group": "Neurogenetic"},
    {"id": "EFO_0700065", "label": "Hereditary ATTR amyloidosis", "group": "Amyloidosis"},
]


def require_run(session: Session, run_id: UUID, settings: Settings) -> Run:
    run = session.get(Run, run_id)
    if run is None or run.environment != settings.app_env:
        raise HTTPException(404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found"})
    return run


@router.get("/health/live")
def live(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


@router.get("/health/ready")
def ready(session: SessionDep) -> dict[str, str]:
    session.exec(select(1)).one()
    return {"status": "ready", "database": "reachable"}


@router.get("/api/v1/config/public")
def public_config(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "ai_enabled": settings.ai_enabled,
        "ai_access_required": settings.ai_enabled,
        "engine_version": ENGINE_VERSION,
        "research_use_disclaimer": DISCLAIMER,
    }


@router.get("/api/v1/diseases/prefilled")
def diseases() -> list[dict[str, str]]:
    return PRESETS


@router.post("/api/v1/runs", response_model=RunPublic, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: RunCreate,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
) -> Run:
    client = getattr(request, "client", None)
    client_key = client.host if client else "unknown"
    if not create_run_limiter.allow(client_key, settings.create_run_rate_limit_per_minute):
        raise HTTPException(
            429,
            detail={"code": "RATE_LIMITED", "message": "Too many run requests; retry in one minute"},
            headers={"Retry-After": "60"},
        )
    parameters = payload.parameters.normalized()
    digest = input_hash(payload.disease_id, parameters)
    if idempotency_key:
        existing = session.exec(
            select(Run).where(Run.environment == settings.app_env, Run.idempotency_key == idempotency_key)
        ).first()
        if existing:
            return existing
    queued = session.exec(
        select(Run).where(Run.environment == settings.app_env, col(Run.status).in_(["queued", "running"]))
    ).all()
    if len(queued) >= settings.max_queued_runs + settings.max_active_runs:
        raise HTTPException(429, detail={"code": "QUEUE_FULL", "message": "The demonstration queue is full"})
    warnings = (
        ["Quick mode caps variant and drug enrichment at 25 genes; results are incomplete."]
        if parameters["run_mode"] == "quick"
        else []
    )
    run = Run(
        environment=settings.app_env,
        disease_id=payload.disease_id,
        disease_label=payload.disease_label,
        parameters=parameters,
        input_hash=digest,
        idempotency_key=idempotency_key,
        warnings=warnings,
    )
    session.add(run)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(Run).where(Run.environment == settings.app_env, Run.idempotency_key == idempotency_key)
        ).first()
        if existing:
            return existing
        raise
    session.refresh(run)
    if settings.run_worker_enabled:
        request.app.state.run_worker.submit(run.id)
    return run


@router.get("/api/v1/runs/{run_id}", response_model=RunPublic)
def get_run(run_id: UUID, session: SessionDep, settings: Annotated[Settings, Depends(get_settings)]) -> Run:
    return require_run(session, run_id, settings)


@router.get("/api/v1/runs/{run_id}/events", response_model=list[EventPublic])
def events(
    run_id: UUID, session: SessionDep, settings: Annotated[Settings, Depends(get_settings)]
) -> list[RunEvent]:
    require_run(session, run_id, settings)
    return list(
        session.exec(select(RunEvent).where(RunEvent.run_id == run_id).order_by(col(RunEvent.sequence))).all()
    )


@router.get("/api/v1/runs/{run_id}/candidates", response_model=list[CandidatePublic])
def candidates(
    run_id: UUID,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    track: str | None = None,
    shortlist_only: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[Candidate]:
    require_run(session, run_id, settings)
    statement = select(Candidate).where(Candidate.run_id == run_id)
    if track:
        statement = statement.where(Candidate.final_call == track)
    if shortlist_only:
        statement = statement.where(col(Candidate.shortlist_position).is_not(None))
    statement = (
        statement.order_by(
            col(Candidate.shortlist_position).asc().nulls_last(), col(Candidate.overall_score).desc()
        )
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


@router.get("/api/v1/runs/{run_id}/candidates/{gene_symbol}", response_model=CandidatePublic)
def candidate(
    run_id: UUID, gene_symbol: str, session: SessionDep, settings: Annotated[Settings, Depends(get_settings)]
) -> Candidate:
    require_run(session, run_id, settings)
    row = session.exec(
        select(Candidate).where(Candidate.run_id == run_id, Candidate.gene_symbol == gene_symbol.upper())
    ).first()
    if row is None:
        raise HTTPException(404, detail={"code": "CANDIDATE_NOT_FOUND", "message": "Candidate not found"})
    return row


def _explanation_response(insight: AIInsight, cached: bool) -> CandidateExplanationPublic:
    return CandidateExplanationPublic(
        insight_id=insight.id,
        cached=cached,
        generated_at=insight.created_at,
        model=insight.model,
        prompt_version=insight.prompt_version,
        output_schema_version=insight.output_schema_version,
        source_ids=insight.source_ids,
        output=CandidateExplanationOutput.model_validate(insight.output),
    )


def _run_summary_response(insight: AIInsight, cached: bool) -> RunSummaryPublic:
    return RunSummaryPublic(
        insight_id=insight.id,
        cached=cached,
        generated_at=insight.created_at,
        model=insight.model,
        prompt_version=insight.prompt_version,
        output_schema_version=insight.output_schema_version,
        source_ids=insight.source_ids,
        output=RunSummaryOutput.model_validate(insight.output),
    )


def _candidate_comparison_response(insight: AIInsight, cached: bool) -> CandidateComparisonPublic:
    output = CandidateComparisonOutput.model_validate(insight.output)
    return CandidateComparisonPublic(
        insight_id=insight.id,
        cached=cached,
        generated_at=insight.created_at,
        model=insight.model,
        prompt_version=insight.prompt_version,
        output_schema_version=insight.output_schema_version,
        compared_gene_symbols=sorted(summary.gene_symbol.upper() for summary in output.candidate_summaries),
        source_ids=insight.source_ids,
        output=output,
    )


def _question_response(
    insight: AIInsight,
    cached: bool,
    selected_candidates: list[Candidate],
    premise_corrections: list[str],
) -> AIQuestionPublic:
    output = QuestionAnswerOutput.model_validate(insight.output)
    insufficient = output.answer_status == "insufficient_saved_evidence"
    return AIQuestionPublic(
        mode="insufficient_saved_evidence" if insufficient else "evidence_answer",
        message=(
            "The model found insufficient support in the supplied saved evidence."
            if insufficient
            else "Answer generated from the supplied saved evidence."
        ),
        selected_gene_symbols=sorted(candidate.gene_symbol for candidate in selected_candidates),
        authoritative_facts=build_authoritative_candidate_facts(selected_candidates),
        premise_corrections=premise_corrections,
        insight_id=insight.id,
        cached=cached,
        generated_at=insight.created_at,
        model=insight.model,
        prompt_version=insight.prompt_version,
        output_schema_version=insight.output_schema_version,
        source_ids=insight.source_ids,
        output=output,
        ai_generated=True,
    )


@router.post("/api/v1/runs/{run_id}/ai-summary", response_model=RunSummaryPublic)
def summarize_run(
    run_id: UUID,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[RunSummaryProvider, Depends(get_run_summary_provider)],
) -> RunSummaryPublic:
    if not settings.ai_enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED", "message": "AI summaries are disabled."})
    if settings.openai_api_key is None:
        raise HTTPException(
            503, detail={"code": "AI_NOT_CONFIGURED", "message": "AI summaries are not configured."}
        )
    require_ai_access(request, settings)
    run = require_run(session, run_id, settings)
    if run.status != "succeeded":
        raise HTTPException(
            409, detail={"code": "RUN_NOT_COMPLETE", "message": "Summaries require a succeeded run."}
        )
    rows = list(session.exec(select(Candidate).where(Candidate.run_id == run_id)).all())
    if not rows:
        raise HTTPException(
            409, detail={"code": "RUN_HAS_NO_CANDIDATES", "message": "The run has no candidates to summarize."}
        )
    packet, packet_hash, allowed_source_ids = build_run_summary_packet(run, rows)
    cached = session.exec(
        select(AIInsight).where(
            AIInsight.run_id == run_id,
            col(AIInsight.candidate_id).is_(None),
            AIInsight.environment == settings.app_env,
            AIInsight.insight_type == "run_summary",
            AIInsight.model == settings.openai_model,
            AIInsight.prompt_version == RUN_SUMMARY_PROMPT_VERSION,
            AIInsight.output_schema_version == RUN_SUMMARY_OUTPUT_SCHEMA_VERSION,
            AIInsight.input_hash == packet_hash,
            AIInsight.status == "generated",
        )
    ).first()
    if cached is not None:
        try:
            validate_run_summary_source_ids(RunSummaryOutput.model_validate(cached.output), allowed_source_ids)
        except AIExplanationError:
            cached = None
    if cached is not None:
        return _run_summary_response(cached, cached=True)

    client = getattr(request, "client", None)
    client_key = f"{client.host if client else 'unknown'}:{run_id}:summary"
    if not ai_explanation_limiter.allow(client_key, settings.ai_rate_limit_per_minute):
        raise HTTPException(
            429,
            detail={"code": "AI_RATE_LIMITED", "message": "Too many summary requests."},
            headers={"Retry-After": "60"},
        )
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_run_summary_source_ids(generated.output, allowed_source_ids)
    except AIExplanationError as exc:
        status_code = 503 if exc.code in {"AI_NOT_CONFIGURED", "AI_UPSTREAM_UNAVAILABLE"} else 502
        if exc.code == "AI_UPSTREAM_RATE_LIMITED":
            status_code = 429
        raise HTTPException(status_code, detail={"code": exc.code, "message": exc.message}) from exc

    insight = AIInsight(
        environment=run.environment,
        run_id=run.id,
        candidate_id=None,
        insight_type="run_summary",
        model=settings.openai_model,
        prompt_version=RUN_SUMMARY_PROMPT_VERSION,
        input_hash=packet_hash,
        output_schema_version=RUN_SUMMARY_OUTPUT_SCHEMA_VERSION,
        output=generated.output.model_dump(mode="json"),
        source_ids=source_ids,
        response_id=generated.response_id,
        status="generated",
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return _run_summary_response(insight, cached=False)


@router.post("/api/v1/runs/{run_id}/ai-compare", response_model=CandidateComparisonPublic)
def compare_candidates(
    run_id: UUID,
    payload: CandidateComparisonRequest,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[CandidateComparisonProvider, Depends(get_candidate_comparison_provider)],
) -> CandidateComparisonPublic:
    if not settings.ai_enabled:
        raise HTTPException(
            503, detail={"code": "AI_DISABLED", "message": "AI comparisons are disabled."}
        )
    if settings.openai_api_key is None:
        raise HTTPException(
            503, detail={"code": "AI_NOT_CONFIGURED", "message": "AI comparisons are not configured."}
        )
    require_ai_access(request, settings)
    run = require_run(session, run_id, settings)
    if run.status != "succeeded":
        raise HTTPException(
            409, detail={"code": "RUN_NOT_COMPLETE", "message": "Comparisons require a succeeded run."}
        )
    expected_symbols = set(payload.gene_symbols)
    rows = list(
        session.exec(
            select(Candidate).where(
                Candidate.run_id == run_id,
                col(Candidate.gene_symbol).in_(sorted(expected_symbols)),
            )
        ).all()
    )
    found_symbols = {row.gene_symbol.upper() for row in rows}
    if found_symbols != expected_symbols:
        missing = sorted(expected_symbols - found_symbols)
        raise HTTPException(
            404,
            detail={
                "code": "CANDIDATE_NOT_FOUND",
                "message": f"Candidate not found: {', '.join(missing)}",
            },
        )
    candidate_ids = [row.id for row in rows]
    evidence_rows = list(
        session.exec(
            select(Evidence).where(
                Evidence.run_id == run_id,
                Evidence.environment == settings.app_env,
                col(Evidence.candidate_id).in_(candidate_ids),
            )
        ).all()
    )
    packet, packet_hash, allowed_source_ids = build_candidate_comparison_packet(
        run, rows, evidence_rows
    )
    cached = session.exec(
        select(AIInsight).where(
            AIInsight.run_id == run_id,
            col(AIInsight.candidate_id).is_(None),
            AIInsight.environment == settings.app_env,
            AIInsight.insight_type == "candidate_comparison",
            AIInsight.model == settings.openai_model,
            AIInsight.prompt_version == CANDIDATE_COMPARISON_PROMPT_VERSION,
            AIInsight.output_schema_version == CANDIDATE_COMPARISON_OUTPUT_SCHEMA_VERSION,
            AIInsight.input_hash == packet_hash,
            AIInsight.status == "generated",
        )
    ).first()
    if cached is not None:
        try:
            validate_candidate_comparison(
                CandidateComparisonOutput.model_validate(cached.output),
                allowed_source_ids,
                expected_symbols,
            )
        except AIExplanationError:
            cached = None
    if cached is not None:
        return _candidate_comparison_response(cached, cached=True)

    client = getattr(request, "client", None)
    client_key = f"{client.host if client else 'unknown'}:{run_id}:comparison"
    if not ai_explanation_limiter.allow(client_key, settings.ai_rate_limit_per_minute):
        raise HTTPException(
            429,
            detail={"code": "AI_RATE_LIMITED", "message": "Too many comparison requests."},
            headers={"Retry-After": "60"},
        )
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_candidate_comparison(
            generated.output, allowed_source_ids, expected_symbols
        )
    except AIExplanationError as exc:
        status_code = 503 if exc.code in {"AI_NOT_CONFIGURED", "AI_UPSTREAM_UNAVAILABLE"} else 502
        if exc.code == "AI_UPSTREAM_RATE_LIMITED":
            status_code = 429
        raise HTTPException(status_code, detail={"code": exc.code, "message": exc.message}) from exc

    insight = AIInsight(
        environment=run.environment,
        run_id=run.id,
        candidate_id=None,
        insight_type="candidate_comparison",
        model=settings.openai_model,
        prompt_version=CANDIDATE_COMPARISON_PROMPT_VERSION,
        input_hash=packet_hash,
        output_schema_version=CANDIDATE_COMPARISON_OUTPUT_SCHEMA_VERSION,
        output=generated.output.model_dump(mode="json"),
        source_ids=source_ids,
        response_id=generated.response_id,
        status="generated",
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return _candidate_comparison_response(insight, cached=False)


@router.post("/api/v1/runs/{run_id}/ai-question", response_model=AIQuestionPublic)
def answer_saved_evidence_question(
    run_id: UUID,
    payload: AIQuestionRequest,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[QuestionProvider, Depends(get_question_provider)],
) -> AIQuestionPublic:
    if not settings.ai_enabled:
        raise HTTPException(
            503,
            detail={"code": "AI_DISABLED", "message": "AI questions are disabled."},
        )
    if settings.openai_api_key is None:
        raise HTTPException(
            503,
            detail={"code": "AI_NOT_CONFIGURED", "message": "AI questions are not configured."},
        )
    require_ai_access(request, settings)
    safety = assess_ai_question(payload.question)
    if not safety.allowed:
        raise HTTPException(
            422,
            detail={"code": safety.code, "message": safety.public_message},
        )
    run = require_run(session, run_id, settings)
    if run.status != "succeeded":
        raise HTTPException(
            409,
            detail={"code": "RUN_NOT_COMPLETE", "message": "Questions require a succeeded run."},
        )

    all_candidates = list(session.exec(select(Candidate).where(Candidate.run_id == run_id)).all())
    expected_symbols = set(payload.gene_symbols)
    selected_candidates = (
        list(
            session.exec(
                select(Candidate).where(
                    Candidate.run_id == run_id,
                    col(Candidate.gene_symbol).in_(payload.gene_symbols),
                )
            ).all()
        )
        if payload.gene_symbols
        else []
    )
    found_symbols = {candidate.gene_symbol.upper() for candidate in selected_candidates}
    if found_symbols != expected_symbols:
        missing = sorted(expected_symbols - found_symbols)
        raise HTTPException(
            404,
            detail={
                "code": "CANDIDATE_NOT_FOUND",
                "message": f"Candidate not found: {', '.join(missing)}",
            },
        )

    authoritative_facts = build_authoritative_candidate_facts(selected_candidates)
    premise_corrections = detect_false_classification_premises(
        payload.question, selected_candidates
    )

    support = assess_saved_evidence_support(payload.question, payload.gene_symbols)
    if not support.supported:
        return AIQuestionPublic(
            mode="unsupported_by_saved_evidence",
            message=support.public_message,
            selected_gene_symbols=payload.gene_symbols,
            authoritative_facts=authoritative_facts,
            premise_corrections=premise_corrections,
        )

    selected_ids = [candidate.id for candidate in selected_candidates]
    evidence_rows = (
        list(
            session.exec(
                select(Evidence).where(
                    Evidence.run_id == run_id,
                    Evidence.environment == settings.app_env,
                    col(Evidence.candidate_id).in_(selected_ids),
                )
            ).all()
        )
        if selected_ids
        else []
    )
    packet, packet_hash, allowed_source_ids = build_question_packet(
        run,
        all_candidates,
        selected_candidates,
        evidence_rows,
        payload.question,
    )
    cached = session.exec(
        select(AIInsight).where(
            AIInsight.run_id == run_id,
            col(AIInsight.candidate_id).is_(None),
            AIInsight.environment == settings.app_env,
            AIInsight.insight_type == "run_question",
            AIInsight.model == settings.openai_model,
            AIInsight.prompt_version == QUESTION_PROMPT_VERSION,
            AIInsight.output_schema_version == QUESTION_OUTPUT_SCHEMA_VERSION,
            AIInsight.input_hash == packet_hash,
            AIInsight.status == "generated",
        )
    ).first()
    if cached is not None:
        try:
            cached_output = QuestionAnswerOutput.model_validate(cached.output)
            validate_question_source_ids(cached_output, allowed_source_ids)
            validate_question_determinism(cached_output, selected_candidates, packet)
        except AIExplanationError:
            cached = None
    if cached is not None:
        return _question_response(
            cached,
            cached=True,
            selected_candidates=selected_candidates,
            premise_corrections=premise_corrections,
        )

    client = getattr(request, "client", None)
    client_key = f"{client.host if client else 'unknown'}:{run_id}:question"
    if not ai_explanation_limiter.allow(client_key, settings.ai_rate_limit_per_minute):
        raise HTTPException(
            429,
            detail={"code": "AI_RATE_LIMITED", "message": "Too many question requests."},
            headers={"Retry-After": "60"},
        )
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_question_source_ids(generated.output, allowed_source_ids)
        validate_question_determinism(generated.output, selected_candidates, packet)
    except AIExplanationError as exc:
        status_code = 503 if exc.code in {"AI_NOT_CONFIGURED", "AI_UPSTREAM_UNAVAILABLE"} else 502
        if exc.code == "AI_UPSTREAM_RATE_LIMITED":
            status_code = 429
        raise HTTPException(status_code, detail={"code": exc.code, "message": exc.message}) from exc

    insight = AIInsight(
        environment=run.environment,
        run_id=run.id,
        candidate_id=None,
        insight_type="run_question",
        model=settings.openai_model,
        prompt_version=QUESTION_PROMPT_VERSION,
        input_hash=packet_hash,
        output_schema_version=QUESTION_OUTPUT_SCHEMA_VERSION,
        output=generated.output.model_dump(mode="json"),
        source_ids=source_ids,
        response_id=generated.response_id,
        status="generated",
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return _question_response(
        insight,
        cached=False,
        selected_candidates=selected_candidates,
        premise_corrections=premise_corrections,
    )


@router.post(
    "/api/v1/runs/{run_id}/candidates/{gene_symbol}/ai-explanation",
    response_model=CandidateExplanationPublic,
)
def explain_candidate(
    run_id: UUID,
    gene_symbol: str,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[ExplanationProvider, Depends(get_explanation_provider)],
) -> CandidateExplanationPublic:
    if not settings.ai_enabled:
        raise HTTPException(
            503,
            detail={"code": "AI_DISABLED", "message": "AI explanations are currently disabled."},
        )
    if settings.openai_api_key is None:
        raise HTTPException(
            503,
            detail={"code": "AI_NOT_CONFIGURED", "message": "AI explanations are not configured."},
        )
    require_ai_access(request, settings)
    run = require_run(session, run_id, settings)
    if run.status != "succeeded":
        raise HTTPException(
            409,
            detail={"code": "RUN_NOT_COMPLETE", "message": "Explanations require a succeeded run."},
        )
    row = session.exec(
        select(Candidate).where(Candidate.run_id == run_id, Candidate.gene_symbol == gene_symbol.upper())
    ).first()
    if row is None:
        raise HTTPException(404, detail={"code": "CANDIDATE_NOT_FOUND", "message": "Candidate not found"})
    evidence_rows = list(
        session.exec(
            select(Evidence).where(
                Evidence.run_id == run_id,
                Evidence.candidate_id == row.id,
                Evidence.environment == settings.app_env,
            )
        ).all()
    )
    packet, packet_hash, allowed_source_ids = build_evidence_packet(run, row, evidence_rows)
    cached = session.exec(
        select(AIInsight).where(
            AIInsight.run_id == run_id,
            AIInsight.candidate_id == row.id,
            AIInsight.environment == settings.app_env,
            AIInsight.insight_type == "candidate_explanation",
            AIInsight.model == settings.openai_model,
            AIInsight.prompt_version == PROMPT_VERSION,
            AIInsight.output_schema_version == OUTPUT_SCHEMA_VERSION,
            AIInsight.input_hash == packet_hash,
            AIInsight.status == "generated",
        )
    ).first()
    if cached is not None:
        try:
            validate_source_ids(CandidateExplanationOutput.model_validate(cached.output), allowed_source_ids)
        except AIExplanationError:
            cached = None
    if cached is not None:
        return _explanation_response(cached, cached=True)

    client = getattr(request, "client", None)
    client_key = f"{client.host if client else 'unknown'}:{run_id}"
    if not ai_explanation_limiter.allow(client_key, settings.ai_rate_limit_per_minute):
        raise HTTPException(
            429,
            detail={"code": "AI_RATE_LIMITED", "message": "Too many explanation requests."},
            headers={"Retry-After": "60"},
        )
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_source_ids(generated.output, allowed_source_ids)
    except AIExplanationError as exc:
        status_code = 503 if exc.code in {"AI_NOT_CONFIGURED", "AI_UPSTREAM_UNAVAILABLE"} else 502
        if exc.code == "AI_UPSTREAM_RATE_LIMITED":
            status_code = 429
        raise HTTPException(status_code, detail={"code": exc.code, "message": exc.message}) from exc

    insight = AIInsight(
        environment=run.environment,
        run_id=run.id,
        candidate_id=row.id,
        insight_type="candidate_explanation",
        model=settings.openai_model,
        prompt_version=PROMPT_VERSION,
        input_hash=packet_hash,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        output=generated.output.model_dump(mode="json"),
        source_ids=source_ids,
        response_id=generated.response_id,
        status="generated",
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return _explanation_response(insight, cached=False)


@router.post("/api/v1/runs/{run_id}/retry", response_model=RunPublic, status_code=202)
def retry(
    run_id: UUID, request: Request, session: SessionDep, settings: Annotated[Settings, Depends(get_settings)]
) -> Run:
    old = require_run(session, run_id, settings)
    if old.status not in {"failed", "cancelled"}:
        raise HTTPException(
            409,
            detail={"code": "RUN_NOT_RETRYABLE", "message": "Only failed or cancelled runs may be retried"},
        )
    run = Run(
        environment=old.environment,
        disease_id=old.disease_id,
        disease_label=old.disease_label,
        parameters=old.parameters,
        input_hash=old.input_hash,
        warnings=list(old.warnings),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    if settings.run_worker_enabled:
        request.app.state.run_worker.submit(run.id)
    return run


@router.get("/api/v1/runs/{run_id}/exports/{format}")
def export(
    run_id: UUID, format: str, session: SessionDep, settings: Annotated[Settings, Depends(get_settings)]
) -> Response:
    run = require_run(session, run_id, settings)
    if run.status != "succeeded":
        raise HTTPException(
            409, detail={"code": "RUN_NOT_COMPLETE", "message": "Exports require a succeeded run"}
        )
    rows = list(
        session.exec(
            select(Candidate).where(Candidate.run_id == run_id).order_by(col(Candidate.overall_score).desc())
        ).all()
    )
    fields = [
        "ensembl_id",
        "gene_symbol",
        "gene_name",
        "overall_score",
        "genetic_score",
        "final_call",
        "call_source",
        "confidence_tier",
        "evidence_truncated",
        "drug_status",
        "approved_drugs",
        "aso_drug",
        "aso_names",
        "aso_trial_n",
        "aso_trial_ids",
        "aso_precedent",
        "shortlist_position",
        "flag",
        "note",
    ]
    if format == "csv":
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=[*fields, "research_use_disclaimer"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {**{field: getattr(row, field) for field in fields}, "research_use_disclaimer": DISCLAIMER}
            )
        body, media = stream.getvalue().encode(), "text/csv"
    elif format == "json":
        body = json.dumps(
            {
                "metadata": {
                    "run_id": str(run.id),
                    "engine_version": run.engine_version,
                    "parameters": run.parameters,
                    "upstream": run.upstream_metadata,
                    "warnings": run.warnings,
                    "research_use_disclaimer": DISCLAIMER,
                },
                "candidates": [{field: getattr(row, field) for field in fields} for row in rows],
            },
            default=str,
            indent=2,
        ).encode()
        media = "application/json"
    else:
        raise HTTPException(404, detail={"code": "EXPORT_FORMAT_UNKNOWN", "message": "Use csv or json"})
    digest = hashlib.sha256(body).hexdigest()
    session.add(
        ExportArtifact(
            environment=run.environment,
            run_id=run.id,
            format=format,
            sha256=digest,
            byte_size=len(body),
            storage_location=None,
        )
    )
    session.commit()
    return Response(
        content=body,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="aso-compass-{run.id}.{format}"',
            "Digest": f"sha-256={digest}",
        },
    )
