import json
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session, select

from app.api.example_ai_routes import explain_example_candidate
from app.core.settings import Settings
from app.models import AIInsight, Run
from app.schemas.ai import CandidateExplanationOutput
from app.services.ai_explanations import ProviderResult
from app.services.example_bundles import load_example_bundle


class FakeProvider:
    def generate(self, packet, packet_hash, settings):  # type: ignore[no-untyped-def]
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


def test_server_example_matches_frontend_bundle() -> None:
    backend_file = Path(__file__).parents[1] / "app/data/examples/als-v4.1.json"
    frontend_file = Path(__file__).parents[2] / "frontend/public/examples/als-v4.1.json"
    assert json.loads(backend_file.read_text()) == json.loads(frontend_file.read_text())


def test_example_explanation_uses_allowlisted_bundle_without_database_writes(api) -> None:
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

    response = explain_example_candidate(
        "example-als-2026-10", "tardbp", request, settings, FakeProvider()
    )

    assert response.output.summary.startswith("An explanation")
    assert response.source_ids == ["candidate:ENSG00000120948"]
    assert not response.cached
    bundle = load_example_bundle("example-als-2026-10", "test")
    assert bundle is not None
    assert bundle.run.parameters["example_id"] == "example-als-2026-10"
    with Session(engine) as session:
        assert session.exec(select(Run)).first() is None
        assert session.exec(select(AIInsight)).first() is None
