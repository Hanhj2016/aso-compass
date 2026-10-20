from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.classification import DISCLAIMER


class CitedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1, max_length=600)
    source_ids: list[str] = Field(min_length=1, max_length=5)


class GlossaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str = Field(min_length=1, max_length=80)
    definition: str = Field(min_length=1, max_length=400)


class CandidateExplanationOutput(BaseModel):
    """Strict model-generated portion of a candidate explanation."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    decision_basis: list[CitedClaim] = Field(max_length=6)
    supporting_evidence: list[CitedClaim] = Field(max_length=8)
    conflicting_evidence: list[CitedClaim] = Field(max_length=6)
    uncertainties: list[str] = Field(max_length=8)
    manual_review_steps: list[str] = Field(max_length=6)
    what_this_does_not_mean: list[str] = Field(max_length=5)
    glossary: list[GlossaryEntry] = Field(max_length=8)


class CandidateExplanationPublic(BaseModel):
    insight_id: UUID
    cached: bool
    generated_at: datetime
    model: str
    prompt_version: str
    output_schema_version: str
    source_ids: list[str]
    output: CandidateExplanationOutput
    ai_generated: bool = True
    research_use_disclaimer: str = DISCLAIMER


class RunTrackSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track: str = Field(min_length=1, max_length=80)
    count: int = Field(ge=0)
    interpretation: str = Field(min_length=1, max_length=500)
    source_ids: list[str] = Field(min_length=1, max_length=5)


class RunSummaryOutput(BaseModel):
    """Strict model-generated portion of a saved-run summary."""

    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=1, max_length=1400)
    key_findings: list[CitedClaim] = Field(max_length=6)
    track_breakdown: list[RunTrackSummary] = Field(max_length=5)
    evidence_gaps: list[CitedClaim] = Field(max_length=6)
    review_priorities: list[CitedClaim] = Field(max_length=6)
    limitations: list[str] = Field(max_length=6)
    what_this_does_not_mean: list[str] = Field(max_length=5)


class RunSummaryPublic(BaseModel):
    insight_id: UUID
    cached: bool
    generated_at: datetime
    model: str
    prompt_version: str
    output_schema_version: str
    source_ids: list[str]
    output: RunSummaryOutput
    ai_generated: bool = True
    research_use_disclaimer: str = DISCLAIMER


class CandidateComparisonRequest(BaseModel):
    gene_symbols: list[str] = Field(min_length=2, max_length=3)

    @field_validator("gene_symbols")
    @classmethod
    def normalize_gene_symbols(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values]
        if any(not value or len(value) > 64 for value in normalized):
            raise ValueError("Gene symbols must contain between 1 and 64 characters")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Gene symbols must be unique")
        return normalized


class CandidateComparisonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gene_symbol: str = Field(min_length=1, max_length=64)
    evidence_summary: str = Field(min_length=1, max_length=420)
    source_ids: list[str] = Field(min_length=1, max_length=6)


class CandidateDifference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=450)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class CandidateComparisonOutput(BaseModel):
    """Strict model-generated comparison of two or three saved candidates."""

    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=1, max_length=800)
    candidate_summaries: list[CandidateComparisonSummary] = Field(min_length=2, max_length=3)
    key_differences: list[CandidateDifference] = Field(max_length=4)
    shared_features: list[CitedClaim] = Field(max_length=2)
    evidence_gaps: list[CitedClaim] = Field(max_length=3)
    review_priorities: list[CitedClaim] = Field(max_length=3)
    limitations: list[str] = Field(max_length=3)
    what_this_does_not_mean: list[str] = Field(max_length=3)


class CandidateComparisonPublic(BaseModel):
    insight_id: UUID
    cached: bool
    generated_at: datetime
    model: str
    prompt_version: str
    output_schema_version: str
    compared_gene_symbols: list[str]
    source_ids: list[str]
    output: CandidateComparisonOutput
    ai_generated: bool = True
    research_use_disclaimer: str = DISCLAIMER


class AIQuestionRequest(BaseModel):
    question: str = Field(max_length=2048)
    gene_symbols: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("gene_symbols")
    @classmethod
    def normalize_question_gene_symbols(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values]
        if any(not value or len(value) > 64 for value in normalized):
            raise ValueError("Gene symbols must contain between 1 and 64 characters")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Gene symbols must be unique")
        return sorted(normalized)


class QuestionCandidateFactCheck(BaseModel):
    """Model echo of fixed fields, checked against the database before disclosure."""

    model_config = ConfigDict(extra="forbid")

    gene_symbol: str = Field(min_length=1, max_length=64)
    final_call: str = Field(min_length=1, max_length=32)
    overall_score: float
    genetic_score: float
    n_evidence: int | None
    n_evidence_returned: int | None
    evidence_truncated: bool | None
    shortlist_position: int | None
    source_ids: list[str] = Field(min_length=1, max_length=2)


class QuestionAnswerOutput(BaseModel):
    """Strict model-generated answer grounded in one saved run."""

    model_config = ConfigDict(extra="forbid")

    answer_status: Literal["answered", "insufficient_saved_evidence"]
    answer: str = Field(min_length=1, max_length=1600)
    candidate_fact_checks: list[QuestionCandidateFactCheck] = Field(max_length=3)
    cited_claims: list[CitedClaim] = Field(max_length=6)
    uncertainties: list[str] = Field(max_length=5)
    manual_review_steps: list[str] = Field(max_length=4)
    what_this_does_not_mean: list[str] = Field(max_length=3)


class AuthoritativeCandidateFact(BaseModel):
    """Server-generated deterministic fields shown separately from AI prose."""

    gene_symbol: str
    final_call: str
    confidence_tier: str
    overall_score: float
    genetic_score: float
    n_evidence: int | None
    n_evidence_returned: int | None
    evidence_truncated: bool | None
    shortlist_position: int | None
    completeness: str
    source_id: str


class AIQuestionPublic(BaseModel):
    mode: Literal[
        "evidence_answer", "insufficient_saved_evidence", "unsupported_by_saved_evidence"
    ]
    message: str
    selected_gene_symbols: list[str]
    authoritative_facts: list[AuthoritativeCandidateFact] = Field(default_factory=list)
    premise_corrections: list[str] = Field(default_factory=list)
    insight_id: UUID | None = None
    cached: bool = False
    generated_at: datetime | None = None
    model: str | None = None
    prompt_version: str | None = None
    output_schema_version: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    output: QuestionAnswerOutput | None = None
    ai_generated: bool = False
    research_use_disclaimer: str = DISCLAIMER
