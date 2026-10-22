from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any
from uuid import UUID, uuid5

from app.models import Candidate, Evidence, Run

EXAMPLE_NAMESPACE = UUID("7ce235d5-caa6-4e42-9fbe-8e615a46cc37")
EXAMPLE_FILES = {"example-als-2026-10": "als-v4.1.json"}


@dataclass(frozen=True)
class ExampleBundle:
    run: Run
    candidates: list[Candidate]
    evidence: list[Evidence]


def load_example_bundle(example_id: str, environment: str) -> ExampleBundle | None:
    """Load one allow-listed, versioned example as read-only in-memory models."""

    filename = EXAMPLE_FILES.get(example_id)
    if filename is None:
        return None
    resource = files("app.data.examples").joinpath(filename)
    raw = resource.read_text(encoding="utf-8")
    payload: dict[str, Any] = json.loads(raw)
    run_data = payload["run"]
    run_id = uuid5(EXAMPLE_NAMESPACE, example_id)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    run = Run(
        id=run_id,
        environment=environment,
        disease_id=run_data["disease_id"],
        disease_label=run_data.get("disease_label"),
        status="succeeded",
        parameters={**run_data.get("parameters", {}), "example_id": example_id},
        input_hash=digest,
        engine_version=run_data["engine_version"],
        upstream_metadata={**run_data.get("upstream_metadata", {}), "example_id": example_id},
        warnings=run_data.get("warnings", []),
        validation=run_data.get("validation", {}),
        started_at=run_data.get("started_at"),
        completed_at=run_data.get("completed_at"),
    )
    candidates: list[Candidate] = []
    for item in payload["candidates"]:
        candidate_data = dict(item)
        candidate_data["has_aso_precedent"] = bool(candidate_data.get("aso_precedent"))
        candidates.append(
            Candidate(
                id=uuid5(run_id, candidate_data["ensembl_id"]),
                run_id=run_id,
                environment=environment,
                **candidate_data,
            )
        )
    return ExampleBundle(run=run, candidates=candidates, evidence=[])
