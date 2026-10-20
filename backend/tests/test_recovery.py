from sqlmodel import Session, SQLModel, create_engine

from app.models import Run
from app.services.runs import recover_stale_runs


def test_stale_running_jobs_become_retryable_failures(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'recovery.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        run = Run(
            environment="test",
            disease_id="MONDO_0004976",
            status="running",
            parameters={},
            input_hash="d" * 64,
        )
        session.add(run)
        session.commit()
        assert recover_stale_runs(session, "test") == 1
        session.refresh(run)
        assert run.status == "failed"
        assert run.error_code == "WORKER_INTERRUPTED"
