from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal
from uuid import UUID, uuid5

from app.models import Candidate, Evidence, Run

EXAMPLE_NAMESPACE = UUID("7ce235d5-caa6-4e42-9fbe-8e615a46cc37")


@dataclass(frozen=True)
class ExampleCase:
    case_id: str
    slug: str
    example_id: str | None
    title: str
    disease_id: str
    status: Literal["published", "planned"]
    fixture_file: str | None
    fixture_version: str | None
    engine_version: str | None
    source_releases: dict[str, str]
    learning_objectives: tuple[str, ...]
    teaching_candidates: tuple[str, ...]
    candidate_lessons: tuple[dict[str, str], ...]
    debrief: str
    debrief_points: tuple[str, ...]
    references: tuple[dict[str, str], ...]
    source_run_id: str | None
    fixture_sha256: str | None
    candidate_count_exception: str | None
    review_status: Literal["published", "pending"]
    reviewer: str | None


@lru_cache(maxsize=1)
def load_example_cases() -> tuple[ExampleCase, ...]:
    """Load and validate the review-gated educational case manifest."""

    resource = files("app.data.examples").joinpath("manifest.json")
    payload: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "educational-case-manifest-v1":
        raise ValueError("Unsupported educational case manifest schema")
    cases = tuple(
        ExampleCase(
            case_id=item["case_id"],
            slug=item["slug"],
            example_id=item.get("example_id"),
            title=item["title"],
            disease_id=item["disease_id"],
            status=item["status"],
            fixture_file=item.get("fixture_file"),
            fixture_version=item.get("fixture_version"),
            engine_version=item.get("engine_version"),
            source_releases=dict(item.get("source_releases", {})),
            learning_objectives=tuple(item.get("learning_objectives", [])),
            teaching_candidates=tuple(item.get("teaching_candidates", [])),
            candidate_lessons=tuple(item.get("candidate_lessons", [])),
            debrief=item["debrief"],
            debrief_points=tuple(item.get("debrief_points", [])),
            references=tuple(item.get("references", [])),
            source_run_id=item.get("source_run_id"),
            fixture_sha256=item.get("fixture_sha256"),
            candidate_count_exception=item.get("candidate_count_exception"),
            review_status=item["review_status"],
            reviewer=item.get("reviewer"),
        )
        for item in payload["cases"]
    )
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    for case in cases:
        if case.case_id in seen_ids or case.slug in seen_slugs:
            raise ValueError("Educational case IDs and slugs must be unique")
        seen_ids.add(case.case_id)
        seen_slugs.add(case.slug)
        if case.status == "published":
            if (
                not case.example_id
                or not case.fixture_file
                or not case.fixture_version
                or not case.engine_version
                or not case.source_releases
                or not case.reviewer
                or not case.source_run_id
                or not case.fixture_sha256
                or case.review_status != "published"
            ):
                raise ValueError(
                    "Published educational cases require a reviewed, versioned fixture and provenance"
                )
            ordinary_count = 3 <= len(case.teaching_candidates) <= 5
            reviewed_sparse_exception = (
                len(case.teaching_candidates) == 2 and bool(case.candidate_count_exception)
            )
            if not ordinary_count and not reviewed_sparse_exception:
                raise ValueError(
                    "Published cases require three to five candidates or a reviewed two-candidate exception"
                )
            lesson_symbols = {lesson.get("gene_symbol") for lesson in case.candidate_lessons}
            if (
                any(symbol not in lesson_symbols for symbol in case.teaching_candidates)
                or not case.debrief_points
                or not case.references
            ):
                raise ValueError("Published cases require reviewed lessons, debrief points, and references")
        elif (
            case.example_id is not None
            or case.fixture_file is not None
            or case.teaching_candidates
            or case.candidate_lessons
            or case.debrief_points
            or case.references
            or case.source_run_id is not None
            or case.fixture_sha256 is not None
            or case.candidate_count_exception is not None
            or case.review_status != "pending"
            or case.reviewer is not None
        ):
            raise ValueError("Planned educational cases cannot expose unreviewed fixture data")
    return cases


def published_example_cases() -> tuple[ExampleCase, ...]:
    return tuple(case for case in load_example_cases() if case.status == "published")


@dataclass(frozen=True)
class ExampleBundle:
    run: Run
    candidates: list[Candidate]
    evidence: list[Evidence]


def load_example_bundle(example_id: str, environment: str) -> ExampleBundle | None:
    """Load one allow-listed, versioned example as read-only in-memory models."""

    case = next((item for item in published_example_cases() if item.example_id == example_id), None)
    if case is None or case.fixture_file is None:
        return None
    resource = files("app.data.examples").joinpath(case.fixture_file)
    raw = resource.read_text(encoding="utf-8")
    digest = hashlib.sha256(raw.encode()).hexdigest()
    if digest != case.fixture_sha256:
        raise ValueError("Educational fixture digest does not match its reviewed manifest")
    payload: dict[str, Any] = json.loads(raw)
    run_data = payload["run"]
    if run_data["disease_id"] != case.disease_id or run_data["engine_version"] != case.engine_version:
        raise ValueError("Educational fixture provenance does not match its reviewed manifest")
    fixture_symbols = {str(item["gene_symbol"]) for item in payload["candidates"]}
    missing_teaching_candidates = set(case.teaching_candidates) - fixture_symbols
    if missing_teaching_candidates:
        missing = ", ".join(sorted(missing_teaching_candidates))
        raise ValueError(f"Educational fixture is missing reviewed teaching candidates: {missing}")
    run_id = uuid5(EXAMPLE_NAMESPACE, example_id)
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
