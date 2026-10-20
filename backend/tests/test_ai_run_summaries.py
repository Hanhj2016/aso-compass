from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes import summarize_run
from app.core.settings import Settings
from app.models import AIInsight, Candidate, Run
from app.schemas.ai import RunSummaryOutput
from app.services.ai_run_summaries import (
    MAX_CANDIDATE_EXCERPTS,
    RunSummaryProviderResult,
    build_run_summary_packet,
)

AI_HEADERS = {"authorization": "Bearer test-ai-access-token"}


class FakeRunSummaryProvider:
    def __init__(self, source_id: str | None = None) -> None:
        self.calls = 0
        self.source_id = source_id

    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
        self.calls += 1
        aggregate_id = self.source_id or str(packet["sources"][1]["source_id"])
        claim = {"claim": "The run contains deterministic candidate results.", "source_ids": [aggregate_id]}
        return RunSummaryProviderResult(
            output=RunSummaryOutput.model_validate(
                {
                    "overview": "This saved run is summarized without changing its deterministic results.",
                    "key_findings": [claim],
                    "track_breakdown": [
                        {
                            "track": "modifier",
                            "count": 1,
                            "interpretation": "Direction remains unresolved in the saved evidence.",
                            "source_ids": [aggregate_id],
                        }
                    ],
                    "evidence_gaps": [claim],
                    "review_priorities": [claim],
                    "limitations": ["Quick mode is incomplete."],
                    "what_this_does_not_mean": ["This is not a target recommendation."],
                }
            ),
            response_id="resp_run_summary_test",
        )


def seed_run(session: Session, candidate_count: int = 2) -> tuple[Run, list[Candidate]]:
    run = Run(
        environment="test",
        disease_id="MONDO_0004976",
        disease_label="ALS",
        status="succeeded",
        parameters={"run_mode": "quick"},
        input_hash="a" * 64,
        warnings=["Quick mode is incomplete."],
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    candidates = []
    for index in range(candidate_count):
        candidate = Candidate(
            environment="test",
            run_id=run.id,
            ensembl_id=f"ENSG{index:011d}",
            gene_symbol=f"GENE{index:03d}",
            gene_name=f"gene {index}",
            overall_score=0.9 - index / 1000,
            genetic_score=0.8,
            clinvar_call="modifier",
            final_call="modifier" if index == 0 else "insufficient data",
            call_source="assoc only",
            confidence_tier="Association only",
            confidence_reason="Direction is unknown.",
            evidence_truncated=index == 1,
            aso_precedent="Phase 2: EXAMPLE" if index == 0 else "",
            shortlist_position=1 if index == 0 else None,
        )
        session.add(candidate)
        candidates.append(candidate)
    session.commit()
    for candidate in candidates:
        session.refresh(candidate)
    return run, candidates


def test_run_summary_is_validated_persisted_and_cached(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    provider = FakeRunSummaryProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="summary-client"), headers=AI_HEADERS)
    with Session(engine) as session:
        run, candidates = seed_run(session)
        original_calls = [(candidate.final_call, candidate.shortlist_position) for candidate in candidates]

        first = summarize_run(run.id, request, session, settings, provider)
        second = summarize_run(run.id, request, session, settings, provider)

        assert not first.cached
        assert second.cached
        assert first.insight_id == second.insight_id
        assert provider.calls == 1
        assert first.ai_generated
        assert "Not for clinical decision-making" in first.research_use_disclaimer
        assert first.source_ids == [f"run-summary:{run.id}"]
        stored = session.exec(select(AIInsight)).one()
        assert stored.candidate_id is None
        assert stored.insight_type == "run_summary"
        assert stored.response_id == "resp_run_summary_test"
        unchanged = list(
            session.exec(select(Candidate).where(Candidate.run_id == run.id).order_by(Candidate.gene_symbol)).all()
        )
        assert [(candidate.final_call, candidate.shortlist_position) for candidate in unchanged] == original_calls


def test_run_summary_rejects_unverified_source(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(client=SimpleNamespace(host="invalid-summary-client"), headers=AI_HEADERS)
    with Session(engine) as session:
        run, _ = seed_run(session)
        with pytest.raises(HTTPException) as captured:
            summarize_run(
                run.id,
                request,
                session,
                settings,
                FakeRunSummaryProvider(source_id="invented:source"),
            )
        assert captured.value.status_code == 502
        assert captured.value.detail["code"] == "AI_SOURCE_VALIDATION_FAILED"
        assert session.exec(select(AIInsight)).first() is None


def test_run_summary_packet_has_aggregate_and_bounded_excerpts(api) -> None:
    _, engine = api
    with Session(engine) as session:
        run, candidates = seed_run(session, candidate_count=MAX_CANDIDATE_EXCERPTS + 4)
        packet, _, allowed = build_run_summary_packet(run, candidates)

    assert packet["sources"][1]["data"]["candidate_count"] == MAX_CANDIDATE_EXCERPTS + 4
    assert packet["sources"][1]["data"]["evidence_truncated_count"] == 1
    assert len(packet["sources"]) == MAX_CANDIDATE_EXCERPTS + 2
    assert len(allowed) == MAX_CANDIDATE_EXCERPTS + 2
    assert packet["candidate_excerpt_policy"]["total"] == MAX_CANDIDATE_EXCERPTS + 4


def test_run_summary_is_disabled_by_default(api) -> None:
    _, engine = api
    settings = Settings(app_env="test", run_worker_enabled=False)
    request = SimpleNamespace(client=SimpleNamespace(host="disabled-summary-client"), headers=AI_HEADERS)
    with Session(engine) as session:
        run, _ = seed_run(session)
        with pytest.raises(HTTPException) as captured:
            summarize_run(run.id, request, session, settings, FakeRunSummaryProvider())
        assert captured.value.status_code == 503
        assert captured.value.detail["code"] == "AI_DISABLED"
