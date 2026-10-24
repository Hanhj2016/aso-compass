from types import SimpleNamespace

from fastapi import HTTPException
from sqlmodel import Session

from app.api.routes import candidates, create_run, export, get_run, live
from app.core.settings import Settings
from app.models import Candidate, Run
from app.schemas.runs import RunCreate


def test_health_and_create_idempotent_run(api) -> None:
    _, engine = api
    settings = Settings(app_env="test", run_worker_enabled=False)
    assert live(settings)["status"] == "ok"
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    payload = RunCreate.model_validate({"disease_id": "MONDO:0004976", "parameters": {"run_mode": "quick"}})
    with Session(engine) as session:
        first = create_run(payload, request, session, settings, "same-request")
        second = create_run(payload, request, session, settings, "same-request")
        assert second.id == first.id
        assert first.disease_id == "MONDO_0004976"
        assert first.warnings[0] == (
            "Quick mode caps variant and drug enrichment at 25 genes; results are incomplete."
        )


def test_candidates_are_environment_scoped(api) -> None:
    _, engine = api
    settings = Settings(app_env="test", run_worker_enabled=False)
    with Session(engine) as session:
        run = Run(
            environment="test",
            disease_id="MONDO_0004976",
            status="succeeded",
            parameters={},
            input_hash="a" * 64,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        session.add(
            Candidate(
                environment="test",
                run_id=run.id,
                ensembl_id="ENSG1",
                gene_symbol="SOD1",
                overall_score=0.9,
                genetic_score=0.8,
                clinvar_call="knockdown",
                final_call="knockdown",
                call_source="ClinVar",
                confidence_tier="Strong heuristic evidence",
                confidence_reason="fixture",
                shortlist_position=1,
            )
        )
        hidden = Run(environment="demo", disease_id="MONDO_0004976", parameters={}, input_hash="b" * 64)
        session.add(hidden)
        session.commit()
        rows = candidates(run.id, session, settings, None, False, 0, 100)
        assert rows[0].gene_symbol == "SOD1"
        try:
            get_run(hidden.id, session, settings)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("Cross-environment run was exposed")


def test_export_has_disclaimer_and_digest_manifest(api) -> None:
    _, engine = api
    settings = Settings(app_env="test", run_worker_enabled=False)
    with Session(engine) as session:
        run = Run(
            environment="test",
            disease_id="MONDO_0004976",
            status="succeeded",
            parameters={},
            input_hash="c" * 64,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        session.add(
            Candidate(
                environment="test",
                run_id=run.id,
                ensembl_id="ENSG1",
                gene_symbol="GENE1",
                overall_score=0.8,
                genetic_score=0.7,
                clinvar_call="knockdown",
                final_call="knockdown",
                call_source="ClinVar",
                confidence_tier="fixture",
                confidence_reason="fixture",
                clinvar_interpretation={
                    "schema_version": "clinvar-interpretation-v1",
                    "metadata_status": "available",
                    "records_returned": 2,
                    "records_with_review_status": 2,
                    "conflict_records": 0,
                },
            )
        )
        session.commit()
        response = export(run.id, "json", session, settings)

        body = response.body.decode()
        assert "Not for clinical decision-making" in body
        assert "clinvar-interpretation-v1" in body
        assert response.headers["digest"].startswith("sha-256=")

        csv_response = export(run.id, "csv", session, settings)
        csv_body = csv_response.body.decode()
        assert "clinvar_review_status_coverage" in csv_body
        assert "2/2" in csv_body
