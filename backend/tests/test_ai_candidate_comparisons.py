from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import Session, select

from app.api.routes import compare_candidates
from app.core.settings import Settings
from app.models import AIInsight, Candidate, Evidence, Run
from app.schemas.ai import CandidateComparisonOutput, CandidateComparisonRequest
from app.services.ai_candidate_comparisons import CandidateComparisonProviderResult


class FakeComparisonProvider:
    def __init__(self, source_id: str | None = None, change_gene: bool = False) -> None:
        self.calls = 0
        self.source_id = source_id
        self.change_gene = change_gene

    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
        self.calls += 1
        candidate_sources = [source for source in packet["sources"] if source["kind"] == "deterministic_candidate"]
        summaries = [
            {
                "gene_symbol": source["data"]["gene_symbol"],
                "evidence_summary": "This describes the saved deterministic evidence.",
                "source_ids": [self.source_id or source["source_id"]],
            }
            for source in candidate_sources
        ]
        if self.change_gene:
            summaries[-1]["gene_symbol"] = "GENEC"
        source_ids = [self.source_id or source["source_id"] for source in candidate_sources]
        claim = {"claim": "The candidates have different saved classifications.", "source_ids": source_ids}
        return CandidateComparisonProviderResult(
            output=CandidateComparisonOutput.model_validate(
                {
                    "overview": "This comparison describes differences without selecting a preferred candidate.",
                    "candidate_summaries": summaries,
                    "key_differences": [
                        {
                            "dimension": "Classification",
                            "explanation": "The deterministic calls differ.",
                            "source_ids": source_ids,
                        }
                    ],
                    "shared_features": [claim],
                    "evidence_gaps": [claim],
                    "review_priorities": [claim],
                    "limitations": ["The comparison uses saved evidence only."],
                    "what_this_does_not_mean": ["This does not identify a best target."],
                }
            ),
            response_id="resp_comparison_test",
        )


def seed_comparison(session: Session) -> tuple[Run, list[Candidate]]:
    run = Run(
        environment="test",
        disease_id="MONDO_0004976",
        disease_label="ALS",
        status="succeeded",
        parameters={"run_mode": "quick"},
        input_hash="c" * 64,
        warnings=["Quick mode is incomplete."],
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    rows = [
        Candidate(
            environment="test",
            run_id=run.id,
            ensembl_id="ENSG00000000001",
            gene_symbol="GENEA",
            gene_name="gene A",
            overall_score=0.8,
            genetic_score=0.7,
            clinvar_call="modifier",
            final_call="modifier",
            call_source="assoc only",
            confidence_tier="Association only",
            confidence_reason="Direction is unknown.",
            shortlist_position=1,
        ),
        Candidate(
            environment="test",
            run_id=run.id,
            ensembl_id="ENSG00000000002",
            gene_symbol="GENEB",
            gene_name="gene B",
            overall_score=0.7,
            genetic_score=0.6,
            clinvar_call="insufficient data",
            final_call="insufficient data",
            call_source="ClinVar heuristic",
            confidence_tier="Insufficient evidence",
            confidence_reason="Too few classified records.",
        ),
    ]
    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
        session.add(
            Evidence(
                environment="test",
                run_id=run.id,
                candidate_id=row.id,
                source="normalized_scientific_evidence",
                external_id=row.ensembl_id,
                query_hash=row.ensembl_id[-1] * 64,
                normalized={"gene_symbol": row.gene_symbol, "final_call": row.final_call},
            )
        )
    session.commit()
    return run, rows


def test_candidate_comparison_is_validated_persisted_and_order_independent(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    provider = FakeComparisonProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="comparison-client"))
    with Session(engine) as session:
        run, rows = seed_comparison(session)
        original = [(row.final_call, row.shortlist_position) for row in rows]

        first = compare_candidates(
            run.id,
            CandidateComparisonRequest(gene_symbols=["geneb", "genea"]),
            request,
            session,
            settings,
            provider,
        )
        second = compare_candidates(
            run.id,
            CandidateComparisonRequest(gene_symbols=["GENEA", "GENEB"]),
            request,
            session,
            settings,
            provider,
        )

        assert not first.cached
        assert second.cached
        assert first.insight_id == second.insight_id
        assert first.compared_gene_symbols == ["GENEA", "GENEB"]
        assert provider.calls == 1
        stored = session.exec(select(AIInsight)).one()
        assert stored.insight_type == "candidate_comparison"
        assert stored.candidate_id is None
        unchanged = list(
            session.exec(select(Candidate).where(Candidate.run_id == run.id).order_by(Candidate.gene_symbol)).all()
        )
        assert [(row.final_call, row.shortlist_position) for row in unchanged] == original


def test_candidate_comparison_rejects_unverified_source(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(client=SimpleNamespace(host="invalid-comparison-client"))
    with Session(engine) as session:
        run, _ = seed_comparison(session)
        with pytest.raises(HTTPException) as captured:
            compare_candidates(
                run.id,
                CandidateComparisonRequest(gene_symbols=["GENEA", "GENEB"]),
                request,
                session,
                settings,
                FakeComparisonProvider(source_id="invented:source"),
            )
        assert captured.value.status_code == 502
        assert captured.value.detail["code"] == "AI_SOURCE_VALIDATION_FAILED"


def test_candidate_comparison_rejects_changed_candidate_set(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(client=SimpleNamespace(host="candidate-validation-client"))
    with Session(engine) as session:
        run, _ = seed_comparison(session)
        with pytest.raises(HTTPException) as captured:
            compare_candidates(
                run.id,
                CandidateComparisonRequest(gene_symbols=["GENEA", "GENEB"]),
                request,
                session,
                settings,
                FakeComparisonProvider(change_gene=True),
            )
        assert captured.value.status_code == 502
        assert captured.value.detail["code"] == "AI_CANDIDATE_VALIDATION_FAILED"


def test_candidate_comparison_request_requires_two_or_three_unique_symbols() -> None:
    with pytest.raises(ValidationError):
        CandidateComparisonRequest(gene_symbols=["GENEA"])
    with pytest.raises(ValidationError):
        CandidateComparisonRequest(gene_symbols=["GENEA", "genea"])
    with pytest.raises(ValidationError):
        CandidateComparisonRequest(gene_symbols=["A", "B", "C", "D"])
