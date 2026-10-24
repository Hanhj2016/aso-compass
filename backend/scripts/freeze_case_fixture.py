"""Freeze an exact, bounded teaching excerpt from a completed ASO Compass run.

This utility is intentionally read-only with respect to the database. It copies
the public run/event/candidate fields without recalculating scores or editing
scientific values. Candidate selection remains a separately reviewed manifest
decision.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, col, select

from app.db.session import engine
from app.models import Candidate, Run, RunEvent
from app.schemas.runs import CandidatePublic, EventPublic, RunPublic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--example-id", required=True)
    parser.add_argument("--candidate", action="append", dest="candidates", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mirror-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with Session(engine) as session:
        run = session.get(Run, args.run_id)
        if run is None or run.status != "succeeded":
            raise SystemExit("The source run must exist and have succeeded")
        rows = list(
            session.exec(
                select(Candidate)
                .where(Candidate.run_id == run.id, col(Candidate.gene_symbol).in_(args.candidates))
                .order_by(col(Candidate.overall_score).desc())
            ).all()
        )
        by_symbol = {row.gene_symbol: row for row in rows}
        missing = [symbol for symbol in args.candidates if symbol not in by_symbol]
        if missing:
            raise SystemExit(f"Source run is missing requested candidates: {', '.join(missing)}")
        events = list(
            session.exec(
                select(RunEvent).where(RunEvent.run_id == run.id).order_by(col(RunEvent.sequence))
            ).all()
        )

        run_payload = RunPublic.model_validate(run).model_dump(mode="json")
        run_payload["id"] = args.example_id
        fixture = {
            "fixture_provenance": {
                "source_run_id": str(run.id),
                "scope": "reviewed teaching-candidate excerpt",
                "candidate_values": "copied unchanged from the completed source run",
            },
            "run": run_payload,
            "events": [EventPublic.model_validate(event).model_dump(mode="json") for event in events],
            "candidates": [
                CandidatePublic.model_validate(by_symbol[symbol]).model_dump(mode="json")
                for symbol in args.candidates
            ],
        }
    rendered = json.dumps(fixture, indent=2) + "\n"
    for output in (args.output, args.mirror_output):
        if output is None:
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
