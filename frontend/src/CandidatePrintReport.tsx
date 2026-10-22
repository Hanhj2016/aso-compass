import type { Candidate, RunRecord } from "./types";

const TRACK_LABEL: Record<string, string> = {
  knockdown: "Knockdown",
  "splice/upregulation": "Splice / upregulation",
  ambiguous: "Ambiguous",
  modifier: "Modifier",
  "insufficient data": "Insufficient data",
};

function valueOrUnknown(value: string | number | null | undefined) {
  return value === null || value === undefined || value === "" ? "Not returned" : String(value);
}

function fraction(value: number | null) {
  return value === null ? "Not returned" : value.toFixed(3);
}

function trialIds(row: Candidate) {
  return row.aso_trial_ids.split(/,\s*/).filter(Boolean);
}

function EvidenceItem({ label, value }: { label: string; value: string | number }) {
  return <div><span>{label}</span><b>{value}</b></div>;
}

export default function CandidatePrintReport({ run, candidate, generatedAt }: {
  run: RunRecord;
  candidate: Candidate;
  generatedAt: string;
}) {
  const trials = trialIds(candidate);
  const release = String(run.upstream_metadata.open_targets_release ?? "not recorded");
  const evidenceCount = candidate.n_evidence === null
    ? "Not checked"
    : `${candidate.n_evidence_returned ?? 0}/${candidate.n_evidence}`;
  const openTargetsUrl = `https://platform.opentargets.org/target/${candidate.ensembl_id}`;

  return <section className="print-report candidate-print-report" data-print-mode="candidate" aria-label={`Candidate evidence print report for ${candidate.gene_symbol}`}>
    <article className="print-page candidate-print-page" data-report-section="candidate-evidence">
      <header className="candidate-print-header">
        <div>
          <p className="print-report-kicker">Candidate evidence report · deterministic saved record</p>
          <h1>{candidate.gene_symbol}</h1>
          <p className="candidate-print-name">{candidate.gene_name ?? "Gene name not returned"}</p>
          <span className={`track-badge track-${candidate.final_call.replace(/[^a-z]/g, "-")}`}>{TRACK_LABEL[candidate.final_call] ?? candidate.final_call}</span>
        </div>
        <div className="candidate-print-context">
          <span>Disease / phenotype</span><b>{run.disease_label ?? run.disease_id}</b><small>{run.disease_id}</small>
          <span>Candidate identifier</span><b>{candidate.ensembl_id}</b>
        </div>
      </header>

      <p className="print-disclaimer">{run.research_use_disclaimer}</p>

      <section className="candidate-print-decision">
        <div><p className="print-report-kicker">Why this track?</p><h2>{candidate.confidence_reason}</h2></div>
        <dl><dt>Deterministic source</dt><dd>{candidate.call_source}</dd><dt>Confidence label</dt><dd>{candidate.confidence_tier}</dd><dt>Shortlist position</dt><dd>{candidate.shortlist_position ?? "Not shortlisted"}</dd></dl>
      </section>

      <div className="candidate-print-metrics">
        <EvidenceItem label="Overall association" value={candidate.overall_score.toFixed(3)}/>
        <EvidenceItem label="Genetic association" value={candidate.genetic_score.toFixed(3)}/>
        <EvidenceItem label="LOEUF" value={candidate.loeuf?.toFixed(3) ?? "Unknown"}/>
        <EvidenceItem label="Evidence returned / total" value={evidenceCount}/>
      </div>

      <div className="candidate-print-columns">
        <section>
          <h2>Mechanism evidence</h2>
          <dl><dt>ClinVar heuristic</dt><dd>{candidate.clinvar_call}</dd><dt>G2P mechanism</dt><dd>{valueOrUnknown(candidate.g2p_mech)}</dd><dt>Inheritance</dt><dd>{valueOrUnknown(candidate.inheritance)}</dd><dt>Final track</dt><dd>{TRACK_LABEL[candidate.final_call] ?? candidate.final_call}</dd></dl>
        </section>
        <section>
          <h2>Variant evidence inventory</h2>
          <dl><dt>Loss-of-function</dt><dd>{valueOrUnknown(candidate.n_lof)}</dd><dt>Missense</dt><dd>{valueOrUnknown(candidate.n_missense)}</dd><dt>Splice</dt><dd>{valueOrUnknown(candidate.n_splice)}</dd><dt>Additional splice</dt><dd>{valueOrUnknown(candidate.n_splice_extra)}</dd><dt>LoF fraction</dt><dd>{fraction(candidate.frac_lof)}</dd><dt>Splice-related fraction</dt><dd>{fraction(candidate.frac_splice_related)}</dd></dl>
        </section>
        <section>
          <h2>Therapeutic precedent</h2>
          <dl><dt>Drug status</dt><dd>{valueOrUnknown(candidate.drug_status)}</dd><dt>Approved drugs</dt><dd>{valueOrUnknown(candidate.approved_drugs)}</dd><dt>Oligonucleotide names</dt><dd>{valueOrUnknown(candidate.oligo_names)}</dd><dt>ASO names</dt><dd>{valueOrUnknown(candidate.aso_names)}</dd><dt>Trial count / best phase</dt><dd>{candidate.aso_trial_n ?? 0} / {valueOrUnknown(candidate.aso_trial_best)}</dd></dl>
          <p>{candidate.aso_precedent || "No ASO precedent was found in the checked sources."}</p>
        </section>
      </div>

      <div className="candidate-print-columns candidate-print-lower">
        <section>
          <h2>Completeness and review</h2>
          <dl><dt>Completeness</dt><dd>{candidate.completeness}</dd><dt>Evidence capped</dt><dd>{candidate.evidence_truncated ? "Yes - manual review required" : "No"}</dd><dt>Review flag</dt><dd>{candidate.flag || "None recorded"}</dd></dl>
          {candidate.note && <p>{candidate.note}</p>}
        </section>
        <section className="candidate-print-sources">
          <h2>Primary records</h2>
          <p><b>Open Targets</b><br/><a href={openTargetsUrl}>{openTargetsUrl}</a></p>
          {trials.length > 0 ? trials.map(id => <p key={id}><b>ClinicalTrials.gov · {id}</b><br/><a href={`https://clinicaltrials.gov/study/${id}`}>{`https://clinicaltrials.gov/study/${id}`}</a></p>) : <p>No trial identifiers were saved for this candidate.</p>}
        </section>
        <section>
          <h2>Report provenance</h2>
          <dl><dt>Saved source ID</dt><dd>candidate:{candidate.ensembl_id}</dd><dt>Run ID</dt><dd>{run.id}</dd><dt>Engine</dt><dd>{run.engine_version}</dd><dt>Open Targets release</dt><dd>{release}</dd><dt>Run completed</dt><dd>{run.completed_at ? new Date(run.completed_at).toISOString() : "Not recorded"}</dd><dt>Report generated</dt><dd>{generatedAt}</dd></dl>
          <p className="candidate-print-ai-note">Optional AI explanations are excluded from this deterministic report.</p>
        </section>
      </div>

      <footer className="print-page-footer"><span>ASO Compass · Candidate {candidate.gene_symbol} · Run {run.id}</span><span>Research use only · Page 1 of 1</span></footer>
    </article>
  </section>;
}
