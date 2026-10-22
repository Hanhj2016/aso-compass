from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes import explain_candidate, get_saved_candidate_explanation
from app.core.settings import Settings
from app.models import AIInsight, Candidate, Evidence, Run
from app.schemas.ai import CandidateExplanationOutput
from app.services.ai_explanations import AIExplanationError, OpenAIExplanationProvider, ProviderResult

AI_HEADERS = {"authorization": "Bearer test-ai-access-token"}


class FakeProvider:
    def __init__(self, source_id: str | None = None) -> None:
        self.calls = 0
        self.source_id = source_id

    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
        self.calls += 1
        source_id = self.source_id or str(packet["sources"][1]["source_id"])
        claim = {
            "claim": "The saved classification is based on deterministic evidence.",
            "source_ids": [source_id],
        }
        return ProviderResult(
            output=CandidateExplanationOutput.model_validate(
                {
                    "summary": "This is an educational explanation of the saved result.",
                    "decision_basis": [claim],
                    "supporting_evidence": [claim],
                    "conflicting_evidence": [],
                    "uncertainties": ["Missing evidence remains uncertain."],
                    "manual_review_steps": ["Review the linked primary record."],
                    "what_this_does_not_mean": ["This is not a treatment recommendation."],
                    "glossary": [
                        {"term": "Modifier", "definition": "An association with uncertain direction."}
                    ],
                }
            ),
            response_id="resp_test_123",
        )


def seed_candidate(session: Session) -> tuple[Run, Candidate]:
    run = Run(
        environment="test",
        disease_id="MONDO_0004976",
        disease_label="ALS",
        status="succeeded",
        parameters={"run_mode": "quick"},
        input_hash="d" * 64,
        warnings=["Quick mode is incomplete."],
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    candidate = Candidate(
        environment="test",
        run_id=run.id,
        ensembl_id="ENSG00000142168",
        gene_symbol="SOD1",
        gene_name="superoxide dismutase 1",
        overall_score=0.9,
        genetic_score=0.8,
        clinvar_call="modifier",
        final_call="modifier",
        call_source="assoc only",
        confidence_tier="Association only",
        confidence_reason="Direction is unknown.",
        shortlist_position=1,
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    session.add(
        Evidence(
            environment="test",
            run_id=run.id,
            candidate_id=candidate.id,
            source="normalized_scientific_evidence",
            external_id=candidate.ensembl_id,
            query_hash="e" * 64,
            normalized={"overall_score": 0.9, "genetic_score": 0.8},
        )
    )
    session.commit()
    return run, candidate


def test_candidate_explanation_is_validated_persisted_and_cached(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    provider = FakeProvider()
    request = SimpleNamespace(client=SimpleNamespace(host="test-client"), headers=AI_HEADERS)
    with Session(engine) as session:
        run, candidate = seed_candidate(session)
        first = explain_candidate(run.id, "sod1", request, session, settings, provider)
        second = explain_candidate(run.id, "SOD1", request, session, settings, provider)
        restored = get_saved_candidate_explanation(run.id, "SOD1", request, session, settings)

        assert not first.cached
        assert second.cached
        assert first.insight_id == second.insight_id
        assert restored.cached
        assert restored.insight_id == first.insight_id
        assert provider.calls == 1
        assert first.ai_generated
        assert "Not for clinical decision-making" in first.research_use_disclaimer
        assert first.source_ids == [f"candidate:{candidate.ensembl_id}"]
        stored = session.exec(select(AIInsight)).one()
        assert stored.response_id == "resp_test_123"
        assert stored.cache_key is not None
        unchanged = session.get(Candidate, candidate.id)
        assert unchanged is not None
        assert unchanged.final_call == "modifier"
        assert unchanged.shortlist_position == 1


def test_candidate_explanation_rejects_unverified_source(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(client=SimpleNamespace(host="source-validation-client"), headers=AI_HEADERS)
    with Session(engine) as session:
        run, _ = seed_candidate(session)
        with pytest.raises(HTTPException) as captured:
            explain_candidate(
                run.id,
                "SOD1",
                request,
                session,
                settings,
                FakeProvider(source_id="invented:source"),
            )
        assert captured.value.status_code == 502
        assert captured.value.detail["code"] == "AI_SOURCE_VALIDATION_FAILED"
        assert session.exec(select(AIInsight)).first() is None


def test_candidate_explanation_is_disabled_by_default(api) -> None:
    _, engine = api
    settings = Settings(app_env="test", run_worker_enabled=False)
    request = SimpleNamespace(client=SimpleNamespace(host="disabled-client"), headers=AI_HEADERS)
    with Session(engine) as session:
        run, _ = seed_candidate(session)
        with pytest.raises(HTTPException) as captured:
            explain_candidate(run.id, "SOD1", request, session, settings, FakeProvider())
        assert captured.value.status_code == 503
        assert captured.value.detail["code"] == "AI_DISABLED"


def test_openai_provider_converts_truncated_structured_output(monkeypatch) -> None:
    class TruncatedResponses:
        def parse(self, **_kwargs):  # type: ignore[no-untyped-def]
            return CandidateExplanationOutput.model_validate_json('{"summary":"truncated')

    class TruncatedClient:
        responses = TruncatedResponses()

    monkeypatch.setattr("app.services.ai_explanations.OpenAI", lambda **_kwargs: TruncatedClient())
    settings = Settings(
        app_env="test",
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )

    with pytest.raises(AIExplanationError) as captured:
        OpenAIExplanationProvider().generate({"sources": []}, "f" * 64, settings)

    assert captured.value.code == "AI_RESPONSE_INVALID"


def test_openai_provider_uses_documented_reasoning_and_verbosity_shape(monkeypatch) -> None:
    captured: dict[str, object] = {}
    output = CandidateExplanationOutput.model_validate(
        {
            "summary": "A concise saved-evidence explanation.",
            "decision_basis": [{"claim": "The result is deterministic.", "source_ids": ["candidate:ENSG1"]}],
            "supporting_evidence": [],
            "conflicting_evidence": [],
            "uncertainties": [],
            "manual_review_steps": [],
            "what_this_does_not_mean": [],
            "glossary": [],
        }
    )

    class CapturingResponses:
        def parse(self, **kwargs):  # type: ignore[no-untyped-def]
            captured.update(kwargs)
            return SimpleNamespace(
                status="completed", output_parsed=output, id="resp_test", _request_id="req_test"
            )

    class CapturingClient:
        responses = CapturingResponses()

    monkeypatch.setattr("app.services.ai_explanations.OpenAI", lambda **_kwargs: CapturingClient())
    settings = Settings(
        app_env="test",
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )

    result = OpenAIExplanationProvider().generate({"sources": []}, "f" * 64, settings)

    assert result.response_id == "resp_test"
    assert captured["reasoning"] == {"effort": "none"}
    assert captured["text"] == {"verbosity": "low"}
    assert "verbosity" not in captured
