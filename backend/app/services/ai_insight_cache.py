from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import AIInsight

GENERATION_LEASE = timedelta(minutes=5)


@dataclass(frozen=True)
class CacheReservation:
    insight: AIInsight
    acquired: bool


class AIInsightGenerationInProgress(RuntimeError):
    pass


def build_ai_cache_key(
    *,
    environment: str,
    insight_type: str,
    model: str,
    prompt_version: str,
    output_schema_version: str,
    input_hash: str,
    run_id: UUID | None = None,
    example_id: str | None = None,
    subject_key: str | None = None,
) -> str:
    """Return a stable identity for one validated AI output.

    Exactly one owner is required. The evidence input hash remains part of the
    identity, so changed evidence, prompts, schemas, or models cannot reuse a
    stale generated result.
    """

    if (run_id is None) == (example_id is None):
        raise ValueError("Exactly one of run_id or example_id is required")
    payload = {
        "environment": environment,
        "example_id": example_id,
        "input_hash": input_hash,
        "insight_type": insight_type,
        "model": model,
        "output_schema_version": output_schema_version,
        "prompt_version": prompt_version,
        "run_id": str(run_id) if run_id else None,
        "subject_key": subject_key,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def reserve_ai_insight(session: Session, pending: AIInsight) -> CacheReservation:
    """Atomically reserve an exact cache identity before incurring model cost."""

    if pending.cache_key is None:
        raise ValueError("A cache key is required for reservation")
    pending.status = "generating"
    session.add(pending)
    try:
        session.commit()
        session.refresh(pending)
        return CacheReservation(pending, acquired=True)
    except IntegrityError:
        session.rollback()

    existing = session.exec(select(AIInsight).where(AIInsight.cache_key == pending.cache_key)).first()
    if existing is None:
        # The conflicting transaction may have rolled back between the unique
        # violation and this read. One bounded retry is safe.
        session.add(pending)
        session.commit()
        session.refresh(pending)
        return CacheReservation(pending, acquired=True)
    if existing.status == "generated":
        return CacheReservation(existing, acquired=False)
    created_at = existing.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if existing.status == "generating" and created_at < datetime.now(UTC) - GENERATION_LEASE:
        session.delete(existing)
        session.commit()
        session.add(pending)
        session.commit()
        session.refresh(pending)
        return CacheReservation(pending, acquired=True)
    raise AIInsightGenerationInProgress("An identical AI interpretation is already being generated")


def complete_ai_insight(
    session: Session,
    insight: AIInsight,
    *,
    output: dict[str, object],
    source_ids: list[str],
    response_id: str,
) -> AIInsight:
    insight.output = output
    insight.source_ids = source_ids
    insight.response_id = response_id
    insight.status = "generated"
    insight.updated_at = datetime.now(UTC)
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return insight


def abandon_ai_insight(session: Session, insight: AIInsight) -> None:
    session.delete(insight)
    session.commit()


def invalidate_ai_insight(session: Session, insight: AIInsight) -> None:
    """Retain invalid provenance while releasing its deterministic cache key."""

    insight.status = "invalid"
    insight.cache_key = hashlib.sha256(f"invalid:{insight.id}".encode()).hexdigest()
    insight.updated_at = datetime.now(UTC)
    session.add(insight)
    session.commit()
