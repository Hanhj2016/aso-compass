import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes import answer_saved_evidence_question
from app.core.settings import Settings
from app.models import AIInsight, Candidate, Evidence, Run
from app.schemas.ai import AIQuestionRequest, QuestionAnswerOutput
from app.services.ai_questions import (
    OUTPUT_SCHEMA_VERSION,
    PROMPT_VERSION,
    QuestionProviderResult,
    build_question_packet,
)


class FakeQuestionProvider:
    def __init__(
        self,
        source_id: str | None = None,
        insufficient: bool = False,
        conflict: str | None = None,
    ) -> None:
        self.calls = 0
        self.source_id = source_id
        self.insufficient = insufficient
        self.conflict = conflict

    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
        self.calls += 1
        candidate_sources = [
            source for source in packet["sources"] if source["kind"] == "deterministic_candidate"
        ]
        source_id = self.source_id or str(
            candidate_sources[0]["source_id"]
            if candidate_sources
            else packet["sources"][1]["source_id"]
        )
        fact_checks = [
            {
                "gene_symbol": source["data"]["gene_symbol"],
                "final_call": source["data"]["final_call"],
                "overall_score": source["data"]["overall_score"],
                "genetic_score": source["data"]["genetic_score"],
                "n_evidence": source["data"]["n_evidence"],
                "n_evidence_returned": source["data"]["n_evidence_returned"],
                "evidence_truncated": source["data"]["evidence_truncated"],
                "shortlist_position": source["data"]["shortlist_position"],
                "source_ids": [source["source_id"]],
            }
            for source in candidate_sources
        ]
        answer = (
            "The supplied saved evidence does not contain that detail."
            if self.insufficient
            else "The saved deterministic classification is modifier because direction is unresolved."
        )
        if self.conflict == "prose_final_call":
            answer = 'GENEA is classified as "insufficient data."'
        elif self.conflict == "invented_number":
            answer = "GENEA has 999 evidence records."
        elif self.conflict == "fact_final_call" and fact_checks:
            fact_checks[0]["final_call"] = "insufficient data"
        return QuestionProviderResult(
            output=QuestionAnswerOutput.model_validate(
                {
                    "answer_status": (
                        "insufficient_saved_evidence" if self.insufficient else "answered"
                    ),
                    "answer": answer,
                    "candidate_fact_checks": fact_checks,
                    "cited_claims": (
                        []
                        if self.insufficient
                        else [
                            {
                                "claim": "The saved classification is modifier.",
                                "source_ids": [source_id],
                            }
                        ]
                    ),
                    "uncertainties": ["Only the saved run evidence was considered."],
                    "manual_review_steps": ["Review the cited saved record."],
                    "what_this_does_not_mean": ["This is not a treatment recommendation."],
                }
            ),
            response_id="resp_question_test",
        )


def seed_question_run(session: Session) -> tuple[Run, list[Candidate], list[Evidence]]:
    run = Run(
        environment="test",
        disease_id="MONDO_0004976",
        disease_label="ALS",
        status="succeeded",
        parameters={"run_mode": "quick"},
        input_hash="q" * 64,
        warnings=["Quick mode is incomplete."],
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    candidates = [
        Candidate(
            environment="test",
            run_id=run.id,
            ensembl_id="ENSG00000000011",
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
            ensembl_id="ENSG00000000012",
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
    session.add_all(candidates)
    session.commit()
    evidence_rows = []
    for index, candidate in enumerate(candidates):
        session.refresh(candidate)
        evidence = Evidence(
            environment="test",
            run_id=run.id,
            candidate_id=candidate.id,
            source="normalized_scientific_evidence",
            external_id=candidate.ensembl_id,
            query_hash=str(index) * 64,
            normalized={"gene_symbol": candidate.gene_symbol, "final_call": candidate.final_call},
        )
        session.add(evidence)
        evidence_rows.append(evidence)
    session.commit()
    for evidence in evidence_rows:
        session.refresh(evidence)
    return run, candidates, evidence_rows


def enabled_settings() -> Settings:
    return Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )


def test_saved_evidence_question_is_validated_persisted_and_cached_without_raw_question(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="question-client"))
    private_question = "Why is GENEA classified as modifier?"
    payload = AIQuestionRequest(question=private_question, gene_symbols=["genea"])
    with Session(engine) as session:
        run, candidates, _ = seed_question_run(session)
        original = [(candidate.final_call, candidate.shortlist_position) for candidate in candidates]

        first = answer_saved_evidence_question(
            run.id, payload, request, session, enabled_settings(), provider
        )
        second = answer_saved_evidence_question(
            run.id, payload, request, session, enabled_settings(), provider
        )

        assert first.mode == "evidence_answer"
        assert not first.cached
        assert second.cached
        assert first.insight_id == second.insight_id
        assert provider.calls == 1
        assert first.authoritative_facts[0].final_call == "modifier"
        assert first.prompt_version == "saved-evidence-question-v2"
        stored = session.exec(select(AIInsight)).one()
        assert stored.insight_type == "run_question"
        assert private_question not in json.dumps(stored.output)
        assert private_question not in stored.input_hash
        unchanged = list(
            session.exec(
                select(Candidate).where(Candidate.run_id == run.id).order_by(Candidate.gene_symbol)
            ).all()
        )
        assert [(candidate.final_call, candidate.shortlist_position) for candidate in unchanged] == original


def test_rejected_patient_identifier_never_calls_provider_or_persists(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="pii-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        with pytest.raises(HTTPException) as captured:
            answer_saved_evidence_question(
                run.id,
                AIQuestionRequest(
                    question="Patient name is Jane Example; explain GENEA.",
                    gene_symbols=["GENEA"],
                ),
                request,
                session,
                enabled_settings(),
                provider,
            )
        assert captured.value.status_code == 422
        assert captured.value.detail["code"] == "PATIENT_IDENTIFIABLE"
        assert "Jane Example" not in captured.value.detail["message"]
        assert provider.calls == 0
        assert session.exec(select(AIInsight)).first() is None


def test_unsupported_question_returns_without_provider_or_persistence(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="unsupported-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        result = answer_saved_evidence_question(
            run.id,
            AIQuestionRequest(question="What is the weather near the laboratory?"),
            request,
            session,
            enabled_settings(),
            provider,
        )
        assert result.mode == "unsupported_by_saved_evidence"
        assert not result.ai_generated
        assert result.output is None
        assert provider.calls == 0
        assert session.exec(select(AIInsight)).first() is None


def test_candidate_question_requires_an_explicit_saved_candidate_selection(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="selection-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        result = answer_saved_evidence_question(
            run.id,
            AIQuestionRequest(question="Why is GENEA classified as modifier?"),
            request,
            session,
            enabled_settings(),
            provider,
        )
        assert result.mode == "unsupported_by_saved_evidence"
        assert "Select up to three" in result.message
        assert provider.calls == 0


def test_unverified_answer_source_is_rejected_and_not_persisted(api) -> None:
    _, engine = api
    request = SimpleNamespace(client=SimpleNamespace(host="source-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        with pytest.raises(HTTPException) as captured:
            answer_saved_evidence_question(
                run.id,
                AIQuestionRequest(
                    question="Why is GENEA classified as modifier?", gene_symbols=["GENEA"]
                ),
                request,
                session,
                enabled_settings(),
                FakeQuestionProvider(source_id="invented:source"),
            )
        assert captured.value.status_code == 502
        assert captured.value.detail["code"] == "AI_SOURCE_VALIDATION_FAILED"
        assert session.exec(select(AIInsight)).first() is None


def test_insufficient_model_answer_can_return_without_inventing_a_citation(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider(insufficient=True)
    request = SimpleNamespace(client=SimpleNamespace(host="insufficient-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        result = answer_saved_evidence_question(
            run.id,
            AIQuestionRequest(
                question="What saved evidence gaps affect GENEA?", gene_symbols=["GENEA"]
            ),
            request,
            session,
            enabled_settings(),
            provider,
        )
        assert result.mode == "insufficient_saved_evidence"
        assert result.source_ids == []
        assert result.output is not None
        assert result.output.answer_status == "insufficient_saved_evidence"


def test_question_packet_contains_only_selected_candidate_evidence(api) -> None:
    _, engine = api
    with Session(engine) as session:
        run, candidates, evidence_rows = seed_question_run(session)
        packet, _, allowed = build_question_packet(
            run,
            candidates,
            [candidates[0]],
            evidence_rows,
            "Why is GENEA classified as modifier?",
        )

    assert packet["selected_gene_symbols"] == ["GENEA"]
    assert f"candidate:{candidates[0].ensembl_id}" in allowed
    assert f"candidate:{candidates[1].ensembl_id}" not in allowed
    assert f"evidence:{evidence_rows[0].id}" in allowed
    assert f"evidence:{evidence_rows[1].id}" not in allowed
    assert packet["authoritative_candidate_facts"][0]["final_call"] == "modifier"
    assert packet["premise_corrections"] == []


def test_false_classification_premise_is_corrected_by_the_server(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="premise-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        result = answer_saved_evidence_question(
            run.id,
            AIQuestionRequest(
                question="Why is GENEA classified as insufficient data?",
                gene_symbols=["GENEA"],
            ),
            request,
            session,
            enabled_settings(),
            provider,
        )

    assert result.premise_corrections == [
        "GENEA is not classified as insufficient data in this saved run. "
        "Its deterministic final call is modifier."
    ]
    assert result.authoritative_facts[0].final_call == "modifier"


@pytest.mark.parametrize("conflict", ["fact_final_call", "prose_final_call", "invented_number"])
def test_deterministic_conflicts_are_rejected_and_not_persisted(api, conflict: str) -> None:
    _, engine = api
    request = SimpleNamespace(client=SimpleNamespace(host=f"conflict-{conflict}"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        with pytest.raises(HTTPException) as captured:
            answer_saved_evidence_question(
                run.id,
                AIQuestionRequest(
                    question="Why is GENEA classified as modifier?", gene_symbols=["GENEA"]
                ),
                request,
                session,
                enabled_settings(),
                FakeQuestionProvider(conflict=conflict),
            )

        assert captured.value.status_code == 502
        assert captured.value.detail["code"] == "AI_DETERMINISTIC_CONFLICT"
        assert session.exec(select(AIInsight)).first() is None


def test_question_contract_uses_v2_cache_boundary() -> None:
    assert PROMPT_VERSION == "saved-evidence-question-v2"
    assert OUTPUT_SCHEMA_VERSION == "saved-evidence-question-v2"


def test_question_endpoint_follows_the_global_ai_disabled_gate(api) -> None:
    _, engine = api
    provider = FakeQuestionProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="disabled-question-client"))
    with Session(engine) as session:
        run, _, _ = seed_question_run(session)
        with pytest.raises(HTTPException) as captured:
            answer_saved_evidence_question(
                run.id,
                AIQuestionRequest(
                    question="Why is GENEA classified as modifier?", gene_symbols=["GENEA"]
                ),
                request,
                session,
                Settings(app_env="test", run_worker_enabled=False, ai_enabled=False),
                provider,
            )
        assert captured.value.status_code == 503
        assert captured.value.detail["code"] == "AI_DISABLED"
        assert provider.calls == 0
