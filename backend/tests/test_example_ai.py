import json
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session, select

from app.api.example_ai_routes import (
    explain_example_candidate,
    get_saved_example_candidate_explanation,
    get_saved_example_summary,
    summarize_example,
)
from app.core.settings import Settings
from app.models import AIInsight, Run
from app.schemas.ai import CandidateExplanationOutput, RunSummaryOutput
from app.services.ai_explanations import ProviderResult
from app.services.ai_run_summaries import RunSummaryProviderResult
from app.services.example_bundles import load_example_bundle


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
        self.calls += 1
        source_id = packet["sources"][1]["source_id"]
        claim = {"claim": "The saved classification is deterministic.", "source_ids": [source_id]}
        return ProviderResult(
            output=CandidateExplanationOutput.model_validate(
                {
                    "summary": "An explanation of the versioned educational example.",
                    "decision_basis": [claim],
                    "supporting_evidence": [],
                    "conflicting_evidence": [],
                    "uncertainties": ["This is a versioned example."],
                    "manual_review_steps": ["Review the supplied primary record."],
                    "what_this_does_not_mean": ["This is not a treatment recommendation."],
                    "glossary": [],
                }
            ),
            response_id="resp_example_test",
        )


class FakeSummaryProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
        self.calls += 1
        source_id = packet["sources"][1]["source_id"]
        claim = {"claim": "The saved example has deterministic results.", "source_ids": [source_id]}
        return RunSummaryProviderResult(
            output=RunSummaryOutput.model_validate(
                {
                    "overview": "A summary of the versioned educational example.",
                    "key_findings": [claim],
                    "track_breakdown": [],
                    "evidence_gaps": [claim],
                    "review_priorities": [claim],
                    "limitations": ["This is a versioned example."],
                    "what_this_does_not_mean": ["This is not a treatment recommendation."],
                }
            ),
            response_id="resp_example_summary_test",
        )


def test_server_example_matches_frontend_bundle() -> None:
    backend_file = Path(__file__).parents[1] / "app/data/examples/als-v4.1.json"
    frontend_file = Path(__file__).parents[2] / "frontend/public/examples/als-v4.1.json"
    assert json.loads(backend_file.read_text()) == json.loads(frontend_file.read_text())


def test_empty_example_ai_cache_probe_returns_no_content(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(
        client=SimpleNamespace(host="example-cache-probe-client"),
        headers={"authorization": "Bearer test-ai-access-token"},
    )

    with Session(engine) as session:
        summary = get_saved_example_summary(
            "example-als-2026-10", request, session, settings
        )
        explanation = get_saved_example_candidate_explanation(
            "example-als-2026-10", "TARDBP", request, session, settings
        )

    assert summary.status_code == 204
    assert explanation.status_code == 204


def test_example_explanation_uses_allowlisted_bundle_and_persistent_cache(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(
        client=SimpleNamespace(host="example-client"),
        headers={"authorization": "Bearer test-ai-access-token"},
    )

    provider = FakeProvider()
    bundle = load_example_bundle("example-als-2026-10", "test")
    assert bundle is not None
    assert bundle.run.parameters["example_id"] == "example-als-2026-10"
    with Session(engine) as session:
        response = explain_example_candidate(
            "example-als-2026-10", "tardbp", request, session, settings, provider
        )
        repeated = explain_example_candidate(
            "example-als-2026-10", "TARDBP", request, session, settings, provider
        )
        restored = get_saved_example_candidate_explanation(
            "example-als-2026-10", "TARDBP", request, session, settings
        )

        assert response.output.summary.startswith("An explanation")
        assert response.source_ids == ["candidate:ENSG00000120948"]
        assert not response.cached
        assert repeated.cached
        assert restored.cached
        assert response.insight_id == repeated.insight_id == restored.insight_id
        assert provider.calls == 1
        assert session.exec(select(Run)).first() is None
        stored = session.exec(select(AIInsight)).one()
        assert stored.run_id is None
        assert stored.example_id == "example-als-2026-10"
        assert stored.subject_key == "TARDBP"
        assert stored.cache_key is not None


def test_example_summary_is_persisted_and_restored_without_another_model_call(api) -> None:
    _, engine = api
    settings = Settings(
        app_env="test",
        run_worker_enabled=False,
        ai_enabled=True,
        openai_api_key="test-only-not-a-real-key",
        openai_model="test-model",
    )
    request = SimpleNamespace(
        client=SimpleNamespace(host="example-summary-client"),
        headers={"authorization": "Bearer test-ai-access-token"},
    )
    provider = FakeSummaryProvider()
    with Session(engine) as session:
        first = summarize_example("example-als-2026-10", request, session, settings, provider)
        second = summarize_example("example-als-2026-10", request, session, settings, provider)
        restored = get_saved_example_summary(
            "example-als-2026-10", request, session, settings
        )

        assert not first.cached
        assert second.cached and restored.cached
        assert first.insight_id == second.insight_id == restored.insight_id
        assert provider.calls == 1
        stored = session.exec(select(AIInsight)).one()
        assert stored.example_id == "example-als-2026-10"
        assert stored.subject_key is None
