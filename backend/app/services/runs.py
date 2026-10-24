from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, col, func, select

from app.core.settings import Settings
from app.db.session import engine
from app.integrations.open_targets import OpenTargetsClient
from app.models import Candidate, Evidence, Run, RunEvent
from app.services.scientific_pipeline import run_pipeline

logger = logging.getLogger(__name__)


def input_hash(disease_id: str, parameters: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps({"disease_id": disease_id, "parameters": parameters}, sort_keys=True).encode()
    ).hexdigest()


def add_event(
    session: Session,
    run: Run,
    stage: str,
    message: str,
    current: int | None = None,
    total: int | None = None,
    level: str = "info",
) -> None:
    sequence = (
        session.exec(select(func.count()).select_from(RunEvent).where(RunEvent.run_id == run.id)).one() + 1
    )
    session.add(
        RunEvent(
            environment=run.environment,
            run_id=run.id,
            sequence=sequence,
            stage=stage,
            level=level,
            message=message,
            progress_current=current,
            progress_total=total,
        )
    )
    run.updated_at = datetime.now(UTC)
    session.add(run)
    session.commit()


def recover_stale_runs(session: Session, environment: str) -> int:
    rows = session.exec(select(Run).where(Run.environment == environment, col(Run.status) == "running")).all()
    for run in rows:
        run.status = "failed"
        run.error_code = "WORKER_INTERRUPTED"
        run.error_message = "The worker restarted before this run completed. Retry the run."
        run.completed_at = datetime.now(UTC)
        run.updated_at = datetime.now(UTC)
        session.add(run)
        add_event(session, run, "recovery", run.error_message, level="error")
    return len(rows)


class RunWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.executor = ThreadPoolExecutor(max_workers=settings.max_active_runs, thread_name_prefix="aso-run")

    def submit(self, run_id: UUID) -> None:
        self.executor.submit(self._execute, run_id)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def _execute(self, run_id: UUID) -> None:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run is None or run.status != "queued":
                return
            run.status = "running"
            run.started_at = datetime.now(UTC)
            session.add(run)
            session.commit()
            add_event(session, run, "start", "Run started")
            try:
                client = OpenTargetsClient(
                    self.settings.open_targets_url,
                    self.settings.http_timeout_seconds,
                    self.settings.http_retry_total,
                )

                active_run = run

                def progress(stage: str, message: str, current: int | None, total: int | None) -> None:
                    add_event(session, active_run, stage, message, current, total)

                rows, metadata, warnings = run_pipeline(
                    client,
                    run.disease_id,
                    run.parameters,
                    progress,
                    self.settings.clinical_trials_url,
                )
                release = metadata.get("open_targets_release")
                for row in rows:
                    allowed = {key: value for key, value in row.items() if key in Candidate.model_fields}
                    candidate = Candidate(environment=run.environment, run_id=run.id, **allowed)
                    session.add(candidate)
                    session.flush()
                    evidence_fields = {
                        key: row.get(key)
                        for key in (
                            "overall_score",
                            "genetic_score",
                            "loeuf",
                            "n_evidence",
                            "n_evidence_returned",
                            "evidence_truncated",
                            "n_lof",
                            "n_splice",
                            "n_splice_extra",
                            "n_missense",
                            "g2p_mech",
                            "inheritance",
                            "clinvar_interpretation",
                            "drug_status",
                            "aso_drug",
                            "aso_names",
                            "aso_trial_n",
                            "aso_trial_ids",
                        )
                    }
                    session.add(
                        Evidence(
                            environment=run.environment,
                            run_id=run.id,
                            candidate_id=candidate.id,
                            source="normalized_scientific_evidence",
                            external_id=candidate.ensembl_id,
                            query_hash=str(
                                row.get("_variant_query_hash")
                                or metadata.get("association_query_hash")
                                or "unknown"
                            ),
                            upstream_release=str(release) if release else None,
                            completeness=candidate.completeness,
                            normalized=evidence_fields,
                        )
                    )
                run.disease_label = run.disease_label or metadata.pop("disease_label", None)
                run.upstream_metadata = metadata
                run.validation = metadata.pop("validation", {})
                run.warnings = [*run.warnings, *warnings]
                run.status = "succeeded"
                run.completed_at = datetime.now(UTC)
                run.updated_at = datetime.now(UTC)
                session.add(run)
                session.commit()
                add_event(session, run, "complete", "Run completed", len(rows), len(rows))
            except Exception:
                logger.exception("Run %s failed", run_id)
                session.rollback()
                run = session.get(Run, run_id)
                if run is None:
                    return
                run.status = "failed"
                run.error_code = "RUN_FAILED"
                run.error_message = "The run could not be completed. Review events and retry."
                run.completed_at = datetime.now(UTC)
                session.add(run)
                session.commit()
                add_event(session, run, "failed", run.error_message, level="error")
