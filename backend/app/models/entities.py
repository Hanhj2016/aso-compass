from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC)


class AuditMixin(SQLModel):
    environment: str = Field(index=True, max_length=8)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Run(AuditMixin, table=True):
    __tablename__ = "runs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    disease_id: str = Field(index=True, max_length=32)
    disease_label: str | None = Field(default=None, max_length=300)
    status: str = Field(default="queued", index=True, max_length=16)
    parameters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    input_hash: str = Field(index=True, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)
    engine_version: str = Field(default="4.1-guided", max_length=32)
    upstream_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    validation: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=500)

    __table_args__ = (
        UniqueConstraint("environment", "idempotency_key", name="uq_run_environment_idempotency"),
        Index("ix_run_environment_hash", "environment", "input_hash"),
    )


class Candidate(AuditMixin, table=True):
    __tablename__ = "candidates"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", ondelete="CASCADE", index=True)
    ensembl_id: str = Field(max_length=32)
    gene_symbol: str = Field(index=True, max_length=64)
    gene_name: str | None = Field(default=None, max_length=500)
    overall_score: float
    genetic_score: float
    loeuf: float | None = None
    n_evidence: int | None = None
    n_evidence_returned: int | None = None
    evidence_truncated: bool | None = None
    n_lof: int | None = None
    n_splice: int | None = None
    n_splice_extra: int | None = None
    n_missense: int | None = None
    frac_lof: float | None = None
    frac_splice_related: float | None = None
    g2p_mech: str | None = Field(default=None, max_length=32)
    inheritance: str | None = Field(default=None, max_length=32)
    clinvar_call: str = Field(max_length=32)
    final_call: str = Field(index=True, max_length=32)
    call_source: str = Field(max_length=32)
    confidence_tier: str = Field(max_length=64)
    confidence_reason: str = Field(max_length=500)
    flag: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=1000)
    drug_status: str = Field(default="not checked", max_length=500)
    has_approved_drug: bool | None = None
    n_drugs: int | None = None
    drug_max_stage: str | None = Field(default=None, max_length=64)
    approved_drugs: str = Field(default="", max_length=1000)
    oligo_drug: str | None = Field(default=None, max_length=64)
    oligo_names: str = Field(default="", max_length=1000)
    aso_drug: str | None = Field(default=None, max_length=64)
    aso_names: str = Field(default="", max_length=1000)
    aso_trial_n: int | None = None
    aso_trial_weak: int | None = None
    aso_trial_best: str | None = Field(default=None, max_length=128)
    aso_trial_ids: str = Field(default="", max_length=500)
    aso_precedent: str = Field(default="", max_length=1000)
    has_aso_precedent: bool = False
    shortlist_position: int | None = None
    completeness: str = Field(default="complete", max_length=32)

    __table_args__ = (UniqueConstraint("run_id", "ensembl_id", name="uq_candidate_run_ensembl"),)


class Evidence(AuditMixin, table=True):
    __tablename__ = "evidence"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", ondelete="CASCADE", index=True)
    candidate_id: UUID | None = Field(default=None, foreign_key="candidates.id", ondelete="CASCADE")
    source: str = Field(max_length=64)
    external_id: str | None = Field(default=None, max_length=255)
    query_hash: str = Field(max_length=64)
    retrieved_at: datetime = Field(default_factory=now)
    upstream_release: str | None = Field(default=None, max_length=64)
    completeness: str = Field(default="complete", max_length=32)
    normalized: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    __table_args__ = (Index("ix_evidence_run_source", "run_id", "source"),)


class RunEvent(AuditMixin, table=True):
    __tablename__ = "run_events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", ondelete="CASCADE", index=True)
    sequence: int
    stage: str = Field(max_length=64)
    level: str = Field(default="info", max_length=16)
    message: str = Field(max_length=1000)
    progress_current: int | None = None
    progress_total: int | None = None
    details: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_event_run_sequence"),)


class ExportArtifact(AuditMixin, table=True):
    __tablename__ = "export_artifacts"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", ondelete="CASCADE", index=True)
    format: str = Field(max_length=16)
    storage_location: str | None = Field(default=None, max_length=1000)
    sha256: str = Field(max_length=64)
    byte_size: int
    schema_version: str = Field(default="1", max_length=16)


class AIInsight(AuditMixin, table=True):
    __tablename__ = "ai_insights"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", ondelete="CASCADE", index=True)
    candidate_id: UUID | None = Field(default=None, foreign_key="candidates.id", ondelete="CASCADE")
    insight_type: str = Field(max_length=32)
    model: str = Field(max_length=128)
    prompt_version: str = Field(max_length=32)
    input_hash: str = Field(max_length=64)
    output_schema_version: str = Field(max_length=32)
    output: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    source_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    response_id: str | None = Field(default=None, max_length=255)
    status: str = Field(default="created", max_length=32)
