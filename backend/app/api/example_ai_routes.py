from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from app.api.routes import (
    _candidate_comparison_response,
    _explanation_response,
    _question_response,
    _run_summary_response,
)
from app.core.settings import Settings, get_settings
from app.db.session import get_session
from app.models import AIInsight, Candidate
from app.schemas.ai import (
    AIQuestionPublic,
    AIQuestionRequest,
    CandidateComparisonPublic,
    CandidateComparisonRequest,
    CandidateExplanationOutput,
    CandidateExplanationPublic,
    RunSummaryOutput,
    RunSummaryPublic,
)
from app.services.ai_access import require_ai_access
from app.services.ai_candidate_comparisons import (
    OUTPUT_SCHEMA_VERSION as COMPARISON_SCHEMA,
)
from app.services.ai_candidate_comparisons import PROMPT_VERSION as COMPARISON_PROMPT
from app.services.ai_candidate_comparisons import (
    CandidateComparisonProvider,
    build_candidate_comparison_packet,
    get_candidate_comparison_provider,
    validate_candidate_comparison,
)
from app.services.ai_explanations import (
    OUTPUT_SCHEMA_VERSION as EXPLANATION_SCHEMA,
)
from app.services.ai_explanations import PROMPT_VERSION as EXPLANATION_PROMPT
from app.services.ai_explanations import (
    AIExplanationError,
    ExplanationProvider,
    build_evidence_packet,
    get_explanation_provider,
    validate_source_ids,
)
from app.services.ai_insight_cache import (
    AIInsightGenerationInProgress,
    abandon_ai_insight,
    build_ai_cache_key,
    complete_ai_insight,
    invalidate_ai_insight,
    reserve_ai_insight,
)
from app.services.ai_question_safety import assess_ai_question
from app.services.ai_questions import OUTPUT_SCHEMA_VERSION as QUESTION_SCHEMA
from app.services.ai_questions import PROMPT_VERSION as QUESTION_PROMPT
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
from app.services.ai_run_summaries import OUTPUT_SCHEMA_VERSION as SUMMARY_SCHEMA
from app.services.ai_run_summaries import PROMPT_VERSION as SUMMARY_PROMPT
from app.services.ai_run_summaries import (
    RunSummaryProvider,
    build_run_summary_packet,
    get_run_summary_provider,
    validate_run_summary_source_ids,
)
from app.services.example_bundles import ExampleBundle, load_example_bundle, published_example_cases
from app.services.rate_limit import ai_explanation_limiter

router = APIRouter(prefix="/api/v1/examples")
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("")
def list_published_examples() -> dict[str, object]:
    """Expose reviewed example metadata without exposing unpublished fixtures."""

    return {
        "schema_version": "educational-case-manifest-v1",
        "cases": [
            {
                "case_id": case.case_id,
                "slug": case.slug,
                "example_id": case.example_id,
                "title": case.title,
                "disease_id": case.disease_id,
                "fixture_version": case.fixture_version,
                "engine_version": case.engine_version,
                "source_releases": case.source_releases,
                "learning_objectives": list(case.learning_objectives),
                "teaching_candidates": list(case.teaching_candidates),
                "debrief": case.debrief,
                "review_status": case.review_status,
                "reviewer": case.reviewer,
            }
            for case in published_example_cases()
        ],
    }


def _require_ai(request: Request, settings: Settings) -> None:
    if not settings.ai_enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED", "message": "AI features are disabled."})
    if settings.openai_api_key is None:
        raise HTTPException(
            503, detail={"code": "AI_NOT_CONFIGURED", "message": "AI features are not configured."}
        )
    require_ai_access(request, settings)


def _require_saved_ai(request: Request, settings: Settings) -> None:
    if not settings.ai_enabled:
        raise HTTPException(503, detail={"code": "AI_DISABLED", "message": "AI features are disabled."})
    require_ai_access(request, settings)


def _bundle(example_id: str, settings: Settings) -> ExampleBundle:
    bundle = load_example_bundle(example_id, settings.app_env)
    if bundle is None:
        raise HTTPException(
            404, detail={"code": "EXAMPLE_NOT_FOUND", "message": "Educational example not found."}
        )
    return bundle


def _candidates(bundle: ExampleBundle, symbols: list[str]) -> list[Candidate]:
    expected = set(symbols)
    rows = [row for row in bundle.candidates if row.gene_symbol.upper() in expected]
    found = {row.gene_symbol.upper() for row in rows}
    if found != expected:
        missing = sorted(expected - found)
        raise HTTPException(
            404,
            detail={"code": "CANDIDATE_NOT_FOUND", "message": f"Candidate not found: {', '.join(missing)}"},
        )
    return rows


def _rate_limit(request: Request, example_id: str, feature: str, settings: Settings) -> None:
    client = getattr(request, "client", None)
    client_key = f"{client.host if client else 'unknown'}:example:{example_id}:{feature}"
    if not ai_explanation_limiter.allow(client_key, settings.ai_rate_limit_per_minute):
        raise HTTPException(
            429,
            detail={"code": "AI_RATE_LIMITED", "message": "Too many AI requests."},
            headers={"Retry-After": "60"},
        )


def _provider_error(exc: AIExplanationError) -> HTTPException:
    status_code = 503 if exc.code in {"AI_NOT_CONFIGURED", "AI_UPSTREAM_UNAVAILABLE"} else 502
    if exc.code == "AI_UPSTREAM_RATE_LIMITED":
        status_code = 429
    return HTTPException(status_code, detail={"code": exc.code, "message": exc.message})


def _insight(
    bundle: ExampleBundle,
    insight_type: str,
    model: str,
    prompt_version: str,
    schema_version: str,
    packet_hash: str,
    output: object | None,
    source_ids: list[str],
    response_id: str,
    cache_key: str | None = None,
    candidate: Candidate | None = None,
) -> AIInsight:
    return AIInsight(
        environment=bundle.run.environment,
        run_id=None,
        example_id=str(bundle.run.parameters["example_id"]),
        candidate_id=None,
        subject_key=candidate.gene_symbol if candidate else None,
        insight_type=insight_type,
        model=model,
        prompt_version=prompt_version,
        input_hash=packet_hash,
        output_schema_version=schema_version,
        output=output.model_dump(mode="json") if output is not None else {},  # type: ignore[attr-defined]
        source_ids=source_ids,
        response_id=response_id,
        status="generated",
        cache_key=cache_key,
    )


@router.post("/{example_id}/ai-summary", response_model=RunSummaryPublic)
def summarize_example(
    example_id: str,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[RunSummaryProvider, Depends(get_run_summary_provider)],
) -> RunSummaryPublic:
    _require_ai(request, settings)
    bundle = _bundle(example_id, settings)
    packet, packet_hash, allowed = build_run_summary_packet(bundle.run, bundle.candidates)
    cache_key = build_ai_cache_key(
        environment=settings.app_env,
        example_id=example_id,
        insight_type="run_summary",
        model=settings.openai_model,
        prompt_version=SUMMARY_PROMPT,
        output_schema_version=SUMMARY_SCHEMA,
        input_hash=packet_hash,
    )
    cached = session.exec(select(AIInsight).where(AIInsight.cache_key == cache_key)).first()
    if cached is not None:
        try:
            validate_run_summary_source_ids(RunSummaryOutput.model_validate(cached.output), allowed)
        except AIExplanationError:
            invalidate_ai_insight(session, cached)
            cached = None
    if cached is not None:
        return _run_summary_response(cached, cached=True)
    _rate_limit(request, example_id, "summary", settings)
    pending = _insight(
        bundle, "run_summary", settings.openai_model, SUMMARY_PROMPT, SUMMARY_SCHEMA,
        packet_hash, None, [], "", cache_key,
    )
    try:
        reservation = reserve_ai_insight(session, pending)
    except AIInsightGenerationInProgress as exc:
        raise HTTPException(
            409,
            detail={"code": "AI_GENERATION_IN_PROGRESS", "message": "This summary is already being generated."},
            headers={"Retry-After": "3"},
        ) from exc
    if not reservation.acquired:
        validate_run_summary_source_ids(
            RunSummaryOutput.model_validate(reservation.insight.output), allowed
        )
        return _run_summary_response(reservation.insight, cached=True)
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_run_summary_source_ids(generated.output, allowed)
    except AIExplanationError as exc:
        abandon_ai_insight(session, reservation.insight)
        raise _provider_error(exc) from exc
    insight = complete_ai_insight(
        session,
        reservation.insight,
        output=generated.output.model_dump(mode="json"),
        source_ids=source_ids,
        response_id=generated.response_id,
    )
    return _run_summary_response(insight, cached=False)


@router.get("/{example_id}/ai-summary", response_model=RunSummaryPublic)
def get_saved_example_summary(
    example_id: str,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RunSummaryPublic | Response:
    _require_saved_ai(request, settings)
    bundle = _bundle(example_id, settings)
    _, packet_hash, allowed = build_run_summary_packet(bundle.run, bundle.candidates)
    cache_key = build_ai_cache_key(
        environment=settings.app_env,
        example_id=example_id,
        insight_type="run_summary",
        model=settings.openai_model,
        prompt_version=SUMMARY_PROMPT,
        output_schema_version=SUMMARY_SCHEMA,
        input_hash=packet_hash,
    )
    cached = session.exec(select(AIInsight).where(AIInsight.cache_key == cache_key)).first()
    if cached is None:
        return Response(status_code=204)
    try:
        validate_run_summary_source_ids(RunSummaryOutput.model_validate(cached.output), allowed)
    except AIExplanationError as exc:
        raise HTTPException(
            404,
            detail={"code": "AI_INSIGHT_INVALID", "message": "The saved AI summary is no longer valid."},
        ) from exc
    return _run_summary_response(cached, cached=True)


@router.post("/{example_id}/ai-compare", response_model=CandidateComparisonPublic)
def compare_example_candidates(
    example_id: str,
    payload: CandidateComparisonRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[CandidateComparisonProvider, Depends(get_candidate_comparison_provider)],
) -> CandidateComparisonPublic:
    _require_ai(request, settings)
    bundle = _bundle(example_id, settings)
    rows = _candidates(bundle, payload.gene_symbols)
    packet, packet_hash, allowed = build_candidate_comparison_packet(bundle.run, rows, [])
    _rate_limit(request, example_id, "comparison", settings)
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_candidate_comparison(generated.output, allowed, set(payload.gene_symbols))
    except AIExplanationError as exc:
        raise _provider_error(exc) from exc
    insight = _insight(
        bundle, "candidate_comparison", settings.openai_model, COMPARISON_PROMPT, COMPARISON_SCHEMA,
        packet_hash, generated.output, source_ids, generated.response_id,
    )
    return _candidate_comparison_response(insight, cached=False)


@router.post("/{example_id}/ai-question", response_model=AIQuestionPublic)
def answer_example_question(
    example_id: str,
    payload: AIQuestionRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[QuestionProvider, Depends(get_question_provider)],
) -> AIQuestionPublic:
    _require_ai(request, settings)
    safety = assess_ai_question(payload.question)
    if not safety.allowed:
        raise HTTPException(422, detail={"code": safety.code, "message": safety.public_message})
    bundle = _bundle(example_id, settings)
    selected = _candidates(bundle, payload.gene_symbols) if payload.gene_symbols else []
    authoritative = build_authoritative_candidate_facts(selected)
    corrections = detect_false_classification_premises(payload.question, selected)
    support = assess_saved_evidence_support(payload.question, payload.gene_symbols)
    if not support.supported:
        return AIQuestionPublic(
            mode="unsupported_by_saved_evidence",
            message=support.public_message,
            selected_gene_symbols=payload.gene_symbols,
            authoritative_facts=authoritative,
            premise_corrections=corrections,
        )
    packet, packet_hash, allowed = build_question_packet(
        bundle.run, bundle.candidates, selected, [], payload.question
    )
    _rate_limit(request, example_id, "question", settings)
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_question_source_ids(generated.output, allowed)
        validate_question_determinism(generated.output, selected, packet)
    except AIExplanationError as exc:
        raise _provider_error(exc) from exc
    insight = _insight(
        bundle, "run_question", settings.openai_model, QUESTION_PROMPT, QUESTION_SCHEMA,
        packet_hash, generated.output, source_ids, generated.response_id,
    )
    return _question_response(insight, False, selected, corrections)


@router.post(
    "/{example_id}/candidates/{gene_symbol}/ai-explanation",
    response_model=CandidateExplanationPublic,
)
def explain_example_candidate(
    example_id: str,
    gene_symbol: str,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[ExplanationProvider, Depends(get_explanation_provider)],
) -> CandidateExplanationPublic:
    _require_ai(request, settings)
    bundle = _bundle(example_id, settings)
    row = _candidates(bundle, [gene_symbol.upper()])[0]
    packet, packet_hash, allowed = build_evidence_packet(bundle.run, row, [])
    cache_key = build_ai_cache_key(
        environment=settings.app_env,
        example_id=example_id,
        subject_key=row.gene_symbol,
        insight_type="candidate_explanation",
        model=settings.openai_model,
        prompt_version=EXPLANATION_PROMPT,
        output_schema_version=EXPLANATION_SCHEMA,
        input_hash=packet_hash,
    )
    cached = session.exec(select(AIInsight).where(AIInsight.cache_key == cache_key)).first()
    if cached is not None:
        try:
            validate_source_ids(CandidateExplanationOutput.model_validate(cached.output), allowed)
        except AIExplanationError:
            invalidate_ai_insight(session, cached)
            cached = None
    if cached is not None:
        return _explanation_response(cached, cached=True)
    _rate_limit(request, example_id, f"explanation:{row.gene_symbol}", settings)
    pending = _insight(
        bundle, "candidate_explanation", settings.openai_model, EXPLANATION_PROMPT,
        EXPLANATION_SCHEMA, packet_hash, None, [], "",
        cache_key, row,
    )
    try:
        reservation = reserve_ai_insight(session, pending)
    except AIInsightGenerationInProgress as exc:
        raise HTTPException(
            409,
            detail={"code": "AI_GENERATION_IN_PROGRESS", "message": "This explanation is already being generated."},
            headers={"Retry-After": "3"},
        ) from exc
    if not reservation.acquired:
        validate_source_ids(
            CandidateExplanationOutput.model_validate(reservation.insight.output), allowed
        )
        return _explanation_response(reservation.insight, cached=True)
    try:
        generated = provider.generate(packet, packet_hash, settings)
        source_ids = validate_source_ids(generated.output, allowed)
    except AIExplanationError as exc:
        abandon_ai_insight(session, reservation.insight)
        raise _provider_error(exc) from exc
    insight = complete_ai_insight(
        session,
        reservation.insight,
        output=generated.output.model_dump(mode="json"),
        source_ids=source_ids,
        response_id=generated.response_id,
    )
    return _explanation_response(insight, cached=False)


@router.get(
    "/{example_id}/candidates/{gene_symbol}/ai-explanation",
    response_model=CandidateExplanationPublic,
)
def get_saved_example_candidate_explanation(
    example_id: str,
    gene_symbol: str,
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CandidateExplanationPublic | Response:
    _require_saved_ai(request, settings)
    bundle = _bundle(example_id, settings)
    row = _candidates(bundle, [gene_symbol.upper()])[0]
    _, packet_hash, allowed = build_evidence_packet(bundle.run, row, [])
    cache_key = build_ai_cache_key(
        environment=settings.app_env,
        example_id=example_id,
        subject_key=row.gene_symbol,
        insight_type="candidate_explanation",
        model=settings.openai_model,
        prompt_version=EXPLANATION_PROMPT,
        output_schema_version=EXPLANATION_SCHEMA,
        input_hash=packet_hash,
    )
    cached = session.exec(select(AIInsight).where(AIInsight.cache_key == cache_key)).first()
    if cached is None:
        return Response(status_code=204)
    try:
        validate_source_ids(CandidateExplanationOutput.model_validate(cached.output), allowed)
    except AIExplanationError as exc:
        raise HTTPException(
            404,
            detail={"code": "AI_INSIGHT_INVALID", "message": "The saved AI explanation is no longer valid."},
        ) from exc
    return _explanation_response(cached, cached=True)
