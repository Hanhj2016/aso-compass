import { useState, type ReactNode } from "react";
import type { Candidate } from "./types";

const FULL_GLOSSARY_URL = "https://github.com/Hanhj2016/aso-compass/blob/main/docs/17_ASO_GLOSSARY_AND_RATIONALE.md";

type TermDefinition = {
  label: string;
  plain: string;
  biology: string;
  app: string;
  mistake: string;
};

const TERMS = {
  loeuf: {
    label: "LOEUF",
    plain: "A population-based estimate of how tolerant a gene is to loss-of-function variants; lower values indicate less tolerance.",
    biology: "Genes depleted of loss-of-function variants in population data may be dosage-sensitive or important for normal function.",
    app: "ASO Compass uses LOEUF as safety context and a review flag. It does not choose the mechanism track.",
    mistake: "A low LOEUF does not prove that a target is undruggable, and a high LOEUF does not prove that knockdown is safe.",
  },
  gof: {
    label: "GoF",
    plain: "Gain of function: a variant gives a gene product increased, new, or abnormally active function.",
    biology: "Disease can arise from harmful activity rather than from too little normal function.",
    app: "A curated G2P GoF annotation can support a knockdown direction, subject to safety and manual review.",
    mistake: "GoF does not mean that every variant in the gene acts the same way or that full knockdown is safe.",
  },
  dn: {
    label: "DN",
    plain: "Dominant negative: an altered gene product interferes with the normal product.",
    biology: "One altered copy can disrupt the function of the product made by the unaffected copy.",
    app: "A curated G2P DN annotation can support a knockdown direction, but allele specificity and residual normal function still matter.",
    mistake: "DN is not simply another name for dominant inheritance, and it does not automatically justify non-selective knockdown.",
  },
  haploinsufficiency: {
    label: "haploinsufficiency",
    plain: "One working copy of a gene does not produce enough normal function.",
    biology: "Reducing functional dosage to roughly one copy can contribute to disease.",
    app: "ASO Compass treats dominant loss-of-function evidence as a warning against indiscriminate knockdown and as support for restoration-oriented review.",
    mistake: "It does not prove that upregulation or splice correction is feasible, effective, or safe.",
  },
  capped: {
    label: "evidence capped",
    plain: "The source contained more records than the run was configured to retrieve.",
    biology: "The observed evidence mixture may not represent the complete set of known records.",
    app: "ASO Compass marks the candidate for manual review and warns that calculated consequence fractions may be incomplete.",
    mistake: "Capped does not mean negative, low quality, or absent evidence; it means the retrieval was truncated.",
  },
  reviewStatus: {
    label: "review status",
    plain: "ClinVar's indication of the review and consensus supporting a submitted or aggregate classification.",
    biology: "Expert-panel review, multiple agreeing submitters, a single submitter, and conflicting submissions carry different evidentiary context.",
    app: "New ASO Compass runs retain the review-status text returned through Open Targets EVA and summarize its coverage. Older bundled examples may not contain it.",
    mistake: "A pathogenic label without its review status, condition, submitter evidence, and date should not be treated as equally certain in every context.",
  },
  lof: {
    label: "LoF",
    plain: "Loss of function: a variant is expected to reduce or remove normal gene-product function.",
    biology: "Loss of normal function may contribute to disease, but the effect depends on gene, allele, inheritance, transcript, and condition.",
    app: "ASO Compass uses categorized consequence counts and curated G2P mechanism evidence to infer a research direction.",
    mistake: "A predicted LoF consequence is not automatically a pathogenic classification or proof of haploinsufficiency.",
  },
} satisfies Record<string, TermDefinition>;

export type TermKey = keyof typeof TERMS;

export function TermHelp({ term, children }: { term: TermKey; children?: ReactNode }) {
  const entry = TERMS[term];
  const [open, setOpen] = useState(false);
  return <span className={`term-help${open ? " term-help-open" : ""}`}>
    <button type="button" aria-label={`Explain ${entry.label}`} aria-expanded={open} onClick={() => setOpen(current => !current)}>{children ?? entry.label}<span aria-hidden="true">?</span></button>
    <span className="term-popover" role="note">
      <b className="term-popover-title">{entry.label}</b>
      <span className="term-popover-entry"><b>Plain language</b><span>{entry.plain}</span></span>
      <span className="term-popover-entry"><b>Biological meaning</b><span>{entry.biology}</span></span>
      <span className="term-popover-entry"><b>Inside ASO Compass</b><span>{entry.app}</span></span>
      <span className="term-popover-entry"><b>Common mistake</b><span>{entry.mistake}</span></span>
      <a href={FULL_GLOSSARY_URL} target="_blank" rel="noreferrer">Open the full glossary ↗</a>
    </span>
  </span>;
}

function sourceAvailability(candidate: Candidate) {
  return {
    openTargets: `Association scores available: overall ${candidate.overall_score.toFixed(3)}, genetic ${candidate.genetic_score.toFixed(3)}.`,
    g2p: candidate.g2p_mech || candidate.inheritance
      ? `Returned mechanism: ${candidate.g2p_mech ?? "not returned"}; inheritance: ${candidate.inheritance ?? "not returned"}.`
      : "No mechanism or inheritance annotation was returned for this candidate.",
    clinvar: candidate.n_evidence === null
      ? "Variant enrichment was not checked."
      : `${candidate.n_evidence_returned ?? 0} of ${candidate.n_evidence} evidence records were returned${candidate.evidence_truncated ? "; retrieval was capped" : ""}.`,
    gnomad: candidate.loeuf === null ? "LOEUF was not returned." : `LOEUF ${candidate.loeuf.toFixed(3)} was returned as population-constraint context.`,
    precedent: candidate.aso_precedent || candidate.drug_status || "No therapeutic-precedent summary was returned.",
  };
}

export function EvidenceSourceMap({ candidate }: { candidate: Candidate }) {
  const available = sourceAvailability(candidate);
  const sources = [
    ["Open Targets", "Association", available.openTargets, "Supports a retrieved gene–disease association and its source scores.", "Does not prove causation, intervention direction, safety, or therapeutic success."],
    ["Gene2Phenotype", "Mechanism + inheritance", available.g2p, "Can support curated disease mechanism and inheritance context.", "Does not establish that an ASO modality is feasible or safe for this candidate."],
    ["ClinVar / EVA", "Submitted variant evidence", available.clinvar, "Supports the returned variant-consequence inventory and, for new runs, bounded review-status and variant–condition context.", "It does not establish causality, retain every source record, or expose a reliable submitter count through this query."],
    ["gnomAD", "Population constraint", available.gnomad, "Supports population constraint context through LOEUF.", "Does not determine the disease mechanism or prove that knockdown is safe or unsafe."],
    ["Drug / trials", "Therapeutic precedent", available.precedent, "Supports that a target-linked drug or trial record was found by the configured checks.", "Does not establish efficacy for this disease, approval for this indication, or a treatment recommendation."],
  ];
  return <section className="source-map" aria-labelledby="source-map-title">
    <p className="eyebrow">Evidence-source map</p>
    <h3 id="source-map-title">How the saved evidence reaches this track</h3>
    <p>Open a source to see what claim it can support—and what it cannot support.</p>
    <div className="source-map-list">
      {sources.map(([name, role, status, supports, limitation]) => <details key={name}>
        <summary><span><b>{name}</b><small>{role}</small></span><span aria-hidden="true">+</span></summary>
        <div><p className="source-map-status">{status}</p><dl><div><dt>Can support</dt><dd>{supports}</dd></div><div><dt>Cannot support</dt><dd>{limitation}</dd></div></dl></div>
      </details>)}
    </div>
    <div className="source-map-result"><span aria-hidden="true">↓</span><small>Deterministic output</small><b>{candidate.final_call}</b><p>Selected by the saved rule engine; not by the source map or AI.</p></div>
  </section>;
}

export function MechanismHelp({ value }: { value: string | null }) {
  if (!value) return <>Not returned</>;
  if (value === "GoF/DN") return <><TermHelp term="gof"/> / <TermHelp term="dn"/></>;
  if (value === "GoF") return <TermHelp term="gof"/>;
  if (value === "DN") return <TermHelp term="dn"/>;
  if (value === "LoF") return <TermHelp term="lof"/>;
  return <>{value}</>;
}

export function ClinVarLearningCheckpoint({ candidate }: { candidate: Candidate }) {
  const returned = candidate.n_evidence_returned ?? 0;
  const interpretation = candidate.clinvar_interpretation;
  const available = interpretation?.metadata_status === "available" || interpretation?.metadata_status === "partial";
  const reviewCounts = Object.entries(interpretation?.review_status_counts ?? {});
  const representatives = interpretation?.representative_records ?? [];
  return <section className="clinvar-checkpoint" aria-labelledby="clinvar-checkpoint-title">
    <p className="eyebrow">Interpretation checkpoint</p>
    <h3 id="clinvar-checkpoint-title">A ClinVar classification is more than a label</h3>
    <div className="clinvar-retained">
      <div><span>Returned / reported</span><b>{candidate.n_evidence === null ? "Not checked" : `${returned} / ${candidate.n_evidence}`}</b></div>
      <div><span>Completeness</span><b>{candidate.evidence_truncated ? <TermHelp term="capped"/> : candidate.completeness}</b></div>
      <div><span>Heuristic result</span><b>{candidate.clinvar_call}</b></div>
    </div>
    {available ? <>
      <div className="clinvar-metadata-grid">
        <div><span><TermHelp term="reviewStatus"/> coverage</span><b>{interpretation?.records_with_review_status ?? 0} / {returned}</b></div>
        <div><span>Conflict-marked records</span><b>{interpretation?.conflict_records ?? 0}</b></div>
        <div><span>Latest evidence date</span><b>{interpretation?.latest_evidence_date ?? "Not returned"}</b></div>
        <div><span>Submitter count</span><b>{interpretation?.submitter_count ?? "Not exposed"}</b></div>
      </div>
      {reviewCounts.length > 0 && <div className="review-status-list" aria-label="Review status distribution">{reviewCounts.map(([status, count]) => <span key={status}><b>{count}</b>{status}</span>)}</div>}
      {(interpretation?.conditions?.length ?? 0) > 0 && <details className="learning-question"><summary>Variant–condition relationships returned</summary><ul>{interpretation?.conditions?.map(condition => <li key={`${condition.id}-${condition.label}`}>{condition.label ?? condition.id ?? "Unlabelled condition"} <small>({condition.record_count} records)</small></li>)}</ul></details>}
      {representatives.length > 0 && <details className="learning-question representative-records"><summary>Inspect representative variant records ({representatives.length})</summary><div>{representatives.map((record, index) => <article key={record.source_record_id ?? `${record.rs_id}-${index}`}>
        <div><b>{record.rs_id ?? "Variant ID not returned"}</b><span>{record.review_stars === null ? "Stars not returned" : `${"★".repeat(record.review_stars)}${"☆".repeat(4 - record.review_stars)} (${record.review_stars})`}</span></div>
        <p>{record.clinical_significances.join(", ") || "Clinical significance not returned"} · {record.consequence_label?.replaceAll("_", " ") ?? "consequence not returned"}</p>
        <p>{record.review_status ?? "Review status not returned"}</p>
        <small>{record.condition_label ?? record.condition_id ?? "Condition not returned"} · evidence {record.evidence_date ?? "date not returned"}</small>
        {record.rs_id && <a href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(record.rs_id)}`} target="_blank" rel="noreferrer">Review in ClinVar ↗</a>}
      </article>)}</div></details>}
      <p><b>Still not available here:</b> reliable submitter count and the full submission-level evidence. This is a bounded learning view; inspect the primary ClinVar record before variant-level interpretation.</p>
    </> : <p><b>Interpretation metadata unavailable:</b> this saved candidate does not retain review status, submitter count, agreement/conflict, assertion date/version, or per-variant condition context. This is expected for older bundled examples. Inspect the primary record before variant-level interpretation.</p>}
    <details className="learning-question"><summary>Question: if zero qualifying records were returned, does that mean “benign”?</summary><p><b>No.</b> It means this workflow returned no qualifying evidence records. Source scope, query rules, missingness, and unmodeled mechanisms remain possible explanations.</p></details>
    <details className="learning-question"><summary>Question: can these aggregate counts establish a variant's clinical significance?</summary><p><b>No.</b> They support the application’s gene-level heuristic only. Variant-level interpretation requires the specific variant–condition record, review status, submissions, criteria, dates, and supporting evidence.</p></details>
  </section>;
}
