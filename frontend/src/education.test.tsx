import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ClinVarLearningCheckpoint, EvidenceSourceMap, MechanismHelp, TermHelp } from "./education";
import type { Candidate } from "./types";

const candidate: Candidate = {
  ensembl_id: "ENSG00000120948", gene_symbol: "TARDBP", gene_name: "TAR DNA binding protein",
  overall_score: .81, genetic_score: .79, loeuf: .239, n_evidence: 46, n_evidence_returned: 46,
  evidence_truncated: false, n_lof: 7, n_splice: 1, n_splice_extra: 2, n_missense: 31,
  frac_lof: .184, frac_splice_related: .333, g2p_mech: "GoF/DN", inheritance: "dominant",
  clinvar_call: "knockdown", final_call: "knockdown", call_source: "G2P",
  confidence_tier: "Convergent G2P + ClinVar", confidence_reason: "Independent sources agree.",
  flag: "LoF-intolerant: full knockdown risky", note: "Manual review required.", drug_status: "None found",
  has_approved_drug: false, n_drugs: 0, drug_max_stage: null, approved_drugs: "", oligo_drug: null,
  oligo_names: "", aso_drug: null, aso_names: "", aso_trial_n: null, aso_trial_weak: null,
  aso_trial_best: null, aso_trial_ids: "", aso_precedent: "", shortlist_position: 1, completeness: "complete",
  clinvar_interpretation: {
    schema_version: "clinvar-interpretation-v1", source: "Open Targets EVA", metadata_status: "available",
    records_reported: 46, records_returned: 46, records_with_review_status: 45, records_with_variant_id: 44,
    records_with_condition: 46, review_status_counts: { "criteria provided, multiple submitters, no conflicts": 40 },
    review_star_counts: { "2": 40 }, conflict_records: 1, submitter_count: null,
    latest_evidence_date: "2025-02-01", latest_release_date: "2025-03-01", release_versions: [],
    conditions: [{ id: "C0002736", label: "Amyotrophic lateral sclerosis", record_count: 46 }],
    representative_records: [{ source_record_id: "eva-1", rs_id: "rs123", clinical_report_id: null,
      clinical_significances: ["pathogenic"], review_status: "criteria provided, multiple submitters, no conflicts",
      review_stars: 2, evidence_date: "2025-02-01", release_date: "2025-03-01", release_version: null,
      condition_id: "C0002736", condition_label: "Amyotrophic lateral sclerosis", consequence_id: "SO:0001583",
      consequence_label: "missense_variant" }], representative_limit: 12, limitations: [],
  },
};

describe("contextual education", () => {
  it("provides all four terminology explanation layers and a glossary link", () => {
    render(<TermHelp term="loeuf"/>);
    expect(screen.getByText("Plain language")).toBeInTheDocument();
    expect(screen.getByText("Biological meaning")).toBeInTheDocument();
    expect(screen.getByText("Inside ASO Compass")).toBeInTheDocument();
    expect(screen.getByText("Common mistake")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /full glossary/i })).toHaveAttribute("href", expect.stringContaining("17_ASO_GLOSSARY"));
  });

  it("separates support from limitations for every candidate source", () => {
    render(<EvidenceSourceMap candidate={candidate}/>);
    expect(screen.getAllByText("Can support")).toHaveLength(5);
    expect(screen.getAllByText("Cannot support")).toHaveLength(5);
    expect(screen.getByText("Open Targets")).toBeInTheDocument();
    expect(screen.getByText("Gene2Phenotype")).toBeInTheDocument();
    expect(screen.getByText("ClinVar / EVA")).toBeInTheDocument();
    expect(screen.getByText("gnomAD")).toBeInTheDocument();
  });

  it("teaches that aggregate evidence is not a benign or variant-level conclusion", () => {
    render(<ClinVarLearningCheckpoint candidate={candidate}/>);
    expect(screen.getByText(/does that mean “benign”/i)).toBeInTheDocument();
    expect(screen.getByText(/aggregate counts establish a variant's clinical significance/i)).toBeInTheDocument();
    expect(screen.getByText(/still not available here/i)).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText(/rs123/i)).toBeInTheDocument();
  });

  it("expands compound G2P shorthand into contextual terms", () => {
    render(<MechanismHelp value="GoF/DN"/>);
    expect(screen.getByLabelText("Explain GoF")).toBeInTheDocument();
    expect(screen.getByLabelText("Explain DN")).toBeInTheDocument();
  });
});
