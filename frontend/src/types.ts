export type RunStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface RunRecord {
  id: string;
  environment: string;
  disease_id: string;
  disease_label: string | null;
  status: RunStatus;
  parameters: Record<string, unknown>;
  engine_version: string;
  upstream_metadata: Record<string, unknown>;
  warnings: string[];
  validation: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  research_use_disclaimer: string;
}

export interface RunEvent {
  sequence: number;
  stage: string;
  level: string;
  message: string;
  progress_current: number | null;
  progress_total: number | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Candidate {
  ensembl_id: string;
  gene_symbol: string;
  gene_name: string | null;
  overall_score: number;
  genetic_score: number;
  loeuf: number | null;
  n_evidence: number | null;
  n_evidence_returned: number | null;
  evidence_truncated: boolean | null;
  n_lof: number | null;
  n_splice: number | null;
  n_splice_extra: number | null;
  n_missense: number | null;
  frac_lof: number | null;
  frac_splice_related: number | null;
  g2p_mech: string | null;
  inheritance: string | null;
  clinvar_call: string;
  final_call: string;
  call_source: string;
  confidence_tier: string;
  confidence_reason: string;
  flag: string;
  note: string;
  drug_status: string;
  has_approved_drug: boolean | null;
  n_drugs: number | null;
  drug_max_stage: string | null;
  approved_drugs: string;
  oligo_drug: string | null;
  oligo_names: string;
  aso_drug: string | null;
  aso_names: string;
  aso_trial_n: number | null;
  aso_trial_weak: number | null;
  aso_trial_best: string | null;
  aso_trial_ids: string;
  aso_precedent: string;
  shortlist_position: number | null;
  completeness: string;
  clinvar_interpretation?: ClinVarInterpretation;
}

export interface ClinVarRepresentativeRecord {
  source_record_id: string | null;
  rs_id: string | null;
  clinical_report_id: string | null;
  clinical_significances: string[];
  review_status: string | null;
  review_stars: number | null;
  evidence_date: string | null;
  release_date: string | null;
  release_version: string | null;
  condition_id: string | null;
  condition_label: string | null;
  consequence_id: string | null;
  consequence_label: string | null;
}

export interface ClinVarInterpretation {
  schema_version?: string;
  source?: string;
  metadata_status?: "available" | "partial" | "not_checked" | "not_returned";
  records_reported?: number;
  records_returned?: number;
  records_with_review_status?: number;
  records_with_variant_id?: number;
  records_with_condition?: number;
  review_status_counts?: Record<string, number>;
  review_star_counts?: Record<string, number>;
  conflict_records?: number;
  submitter_count?: number | null;
  latest_evidence_date?: string | null;
  latest_release_date?: string | null;
  release_versions?: string[];
  conditions?: Array<{ id: string | null; label: string | null; record_count: number }>;
  representative_records?: ClinVarRepresentativeRecord[];
  representative_limit?: number;
  limitations?: string[];
}

export interface PublicConfig {
  app_name: string;
  version: string;
  environment: string;
  ai_enabled: boolean;
  ai_access_required: boolean;
  engine_version: string;
  research_use_disclaimer: string;
}

export interface CitedClaim {
  claim: string;
  source_ids: string[];
}

export interface CandidateExplanation {
  insight_id: string;
  cached: boolean;
  generated_at: string;
  model: string;
  prompt_version: string;
  output_schema_version: string;
  source_ids: string[];
  output: {
    summary: string;
    decision_basis: CitedClaim[];
    supporting_evidence: CitedClaim[];
    conflicting_evidence: CitedClaim[];
    uncertainties: string[];
    manual_review_steps: string[];
    what_this_does_not_mean: string[];
    glossary: { term: string; definition: string }[];
  };
  ai_generated: boolean;
  research_use_disclaimer: string;
}

export interface RunSummary {
  insight_id: string;
  cached: boolean;
  generated_at: string;
  model: string;
  prompt_version: string;
  output_schema_version: string;
  source_ids: string[];
  output: {
    overview: string;
    key_findings: CitedClaim[];
    track_breakdown: {
      track: string;
      count: number;
      interpretation: string;
      source_ids: string[];
    }[];
    evidence_gaps: CitedClaim[];
    review_priorities: CitedClaim[];
    limitations: string[];
    what_this_does_not_mean: string[];
  };
  ai_generated: boolean;
  research_use_disclaimer: string;
}

export interface CandidateComparison {
  insight_id: string;
  cached: boolean;
  generated_at: string;
  model: string;
  prompt_version: string;
  output_schema_version: string;
  compared_gene_symbols: string[];
  source_ids: string[];
  output: {
    overview: string;
    candidate_summaries: {
      gene_symbol: string;
      evidence_summary: string;
      source_ids: string[];
    }[];
    key_differences: {
      dimension: string;
      explanation: string;
      source_ids: string[];
    }[];
    shared_features: CitedClaim[];
    evidence_gaps: CitedClaim[];
    review_priorities: CitedClaim[];
    limitations: string[];
    what_this_does_not_mean: string[];
  };
  ai_generated: boolean;
  research_use_disclaimer: string;
}

export interface AIQuestionAnswer {
  mode: "evidence_answer" | "insufficient_saved_evidence" | "unsupported_by_saved_evidence";
  message: string;
  selected_gene_symbols: string[];
  authoritative_facts?: {
    gene_symbol: string;
    final_call: string;
    confidence_tier: string;
    overall_score: number;
    genetic_score: number;
    n_evidence: number | null;
    n_evidence_returned: number | null;
    evidence_truncated: boolean | null;
    shortlist_position: number | null;
    completeness: string;
    source_id: string;
  }[];
  premise_corrections?: string[];
  insight_id: string | null;
  cached: boolean;
  generated_at: string | null;
  model: string | null;
  prompt_version: string | null;
  output_schema_version: string | null;
  source_ids: string[];
  output: {
    answer_status: "answered" | "insufficient_saved_evidence";
    answer: string;
    candidate_fact_checks?: {
      gene_symbol: string;
      final_call: string;
      overall_score: number;
      genetic_score: number;
      n_evidence: number | null;
      n_evidence_returned: number | null;
      evidence_truncated: boolean | null;
      shortlist_position: number | null;
      source_ids: string[];
    }[];
    cited_claims: CitedClaim[];
    uncertainties: string[];
    manual_review_steps: string[];
    what_this_does_not_mean: string[];
  } | null;
  ai_generated: boolean;
  research_use_disclaimer: string;
}

export interface ExampleBundle { run: RunRecord; candidates: Candidate[]; events: RunEvent[] }

export interface EducationalCase {
  case_id: string;
  slug: string;
  example_id: string | null;
  title: string;
  disease_id: string;
  status: "published" | "planned";
  fixture_file: string | null;
  fixture_version: string | null;
  engine_version: string | null;
  source_releases: Record<string, string>;
  learning_objectives: string[];
  teaching_candidates: string[];
  debrief: string;
  review_status: "published" | "pending";
  reviewer: string | null;
}

export interface EducationalCaseManifest {
  schema_version: "educational-case-manifest-v1";
  cases: EducationalCase[];
}
