from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.classification import DISCLAIMER


class RunParameters(BaseModel):
    min_score: float = Field(default=0.20, ge=0, le=1)
    min_genetic: float = Field(default=0.10, ge=0, le=1)
    use_variants: bool = True
    use_g2p: bool = True
    check_drugs: bool = True
    check_trials: bool = True
    include_modifiers: bool = True
    exclude_approved: bool = False
    exclude_aso_precedent: bool = False
    run_mode: Literal["quick", "full"] = "quick"
    max_genes_for_variants: int = Field(default=300, ge=1, le=300)
    max_genes_for_drugs: int = Field(default=300, ge=1, le=300)
    page_size: int = Field(default=100, ge=10, le=500)

    def normalized(self) -> dict[str, object]:
        values = self.model_dump()
        if self.run_mode == "quick":
            values["max_genes_for_variants"] = min(self.max_genes_for_variants, 25)
            values["max_genes_for_drugs"] = min(self.max_genes_for_drugs, 25)
        return values


class RunCreate(BaseModel):
    disease_id: str = Field(min_length=7, max_length=32)
    disease_label: str | None = Field(default=None, max_length=300)
    parameters: RunParameters = Field(default_factory=RunParameters)

    @field_validator("disease_id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        normalized = value.strip().upper().replace(":", "_")
        prefix, separator, number = normalized.partition("_")
        if separator != "_" or prefix not in {"MONDO", "EFO"} or not number.isdigit():
            raise ValueError("Use a MONDO:nnnnnnn or MONDO_nnnnnnn identifier (verified presets may use EFO)")
        return normalized


class RunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    environment: str
    disease_id: str
    disease_label: str | None
    status: str
    parameters: dict[str, object]
    engine_version: str
    upstream_metadata: dict[str, object]
    warnings: list[str]
    validation: dict[str, object]
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    research_use_disclaimer: str = DISCLAIMER


class EventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sequence: int
    stage: str
    level: str
    message: str
    progress_current: int | None
    progress_total: int | None
    details: dict[str, object]
    created_at: datetime


class CandidatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ensembl_id: str
    gene_symbol: str
    gene_name: str | None
    overall_score: float
    genetic_score: float
    loeuf: float | None
    n_evidence: int | None
    n_evidence_returned: int | None
    evidence_truncated: bool | None
    n_lof: int | None
    n_splice: int | None
    n_splice_extra: int | None
    n_missense: int | None
    frac_lof: float | None
    frac_splice_related: float | None
    g2p_mech: str | None
    inheritance: str | None
    clinvar_call: str
    final_call: str
    call_source: str
    confidence_tier: str
    confidence_reason: str
    flag: str
    note: str
    drug_status: str
    has_approved_drug: bool | None
    n_drugs: int | None
    drug_max_stage: str | None
    approved_drugs: str
    oligo_drug: str | None
    oligo_names: str
    aso_drug: str | None
    aso_names: str
    aso_trial_n: int | None
    aso_trial_weak: int | None
    aso_trial_best: str | None
    aso_trial_ids: str
    aso_precedent: str
    shortlist_position: int | None
    completeness: str
    clinvar_interpretation: dict[str, object]
