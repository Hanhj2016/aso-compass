import type { Candidate, CandidateExplanation, CitedClaim, RunRecord } from "./types";

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

function PrintClaims({ claims }: { claims: CitedClaim[] }) {
  return <ul className="candidate-print-ai-claims">{claims.map((item, index) => <li key={`${item.claim}-${index}`}><span>{item.claim}</span><small>Validated saved sources: {item.source_ids.join(", ")}</small></li>)}</ul>;
}

export default function CandidatePrintReport({ run, candidate, explanation, generatedAt }: {
  run: RunRecord;
  candidate: Candidate;
  explanation: CandidateExplanation | null;
  generatedAt: string;
}) {
  const trials = trialIds(candidate);
  const release = String(run.upstream_metadata.open_targets_release ?? "not recorded");
  const evidenceCount = candidate.n_evidence === null
    ? "Not checked"
    : `${candidate.n_evidence_returned ?? 0}/${candidate.n_evidence}`;
  const openTargetsUrl = `https://platform.opentargets.org/target/${candidate.ensembl_id}`;
  const clinvar = candidate.clinvar_interpretation;
  const reviewCoverage = clinvar?.metadata_status === "available" || clinvar?.metadata_status === "partial"
    ? `${clinvar.records_with_review_status ?? 0}/${clinvar.records_returned ?? candidate.n_evidence_returned ?? 0}`
    : "Not retained";
  const reviewStars = Object.entries(clinvar?.review_star_counts ?? {})
    .sort(([a], [b]) => Number(b) - Number(a))
    .map(([stars, count]) => `${stars} star${stars === "1" ? "" : "s"}: ${count}`)
    .join("; ") || "Not retained";

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
          <dl><dt>Loss-of-function</dt><dd>{valueOrUnknown(candidate.n_lof)}</dd><dt>Missense</dt><dd>{valueOrUnknown(candidate.n_missense)}</dd><dt>Splice</dt><dd>{valueOrUnknown(candidate.n_splice)}</dd><dt>Additional splice</dt><dd>{valueOrUnknown(candidate.n_splice_extra)}</dd><dt>LoF fraction</dt><dd>{fraction(candidate.frac_lof)}</dd><dt>Splice-related fraction</dt><dd>{fraction(candidate.frac_splice_related)}</dd><dt>Review-status coverage</dt><dd>{reviewCoverage}</dd><dt>Review stars</dt><dd>{reviewStars}</dd><dt>Conflict-marked records</dt><dd>{valueOrUnknown(clinvar?.conflict_records)}</dd><dt>Latest evidence date</dt><dd>{valueOrUnknown(clinvar?.latest_evidence_date)}</dd><dt>Latest source release</dt><dd>{valueOrUnknown(clinvar?.latest_release_date)}</dd><dt>Release version(s)</dt><dd>{clinvar?.release_versions?.join(", ") || "Not returned"}</dd><dt>Submitter count</dt><dd>{valueOrUnknown(clinvar?.submitter_count ?? "Not exposed by upstream query")}</dd></dl>
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
          <p className="candidate-print-ai-note">{explanation ? "A separately labeled optional AI appendix follows this deterministic record." : "No AI explanation had been generated when this report was printed."}</p>
        </section>
      </div>

      <section className="candidate-print-terminology">
        <h2>Terminology notes</h2>
        <div><p><b>LOEUF</b> Population loss-of-function constraint context; a low value is a safety flag, not proof that a target is undruggable.</p><p><b>Evidence capped</b> Retrieval stopped at the configured limit; it does not mean absent, benign, or low-quality evidence.</p><p><b>Review status / stars</b> Context about review and consensus behind ClinVar classifications; the label alone is not a complete variant interpretation.</p></div>
      </section>

      <footer className="print-page-footer"><span>ASO Compass · Candidate {candidate.gene_symbol} · Run {run.id}</span><span>Research use only · Deterministic evidence</span></footer>
    </article>
    {explanation && <article className="print-page candidate-print-ai-page" data-report-section="candidate-ai-explanation">
      <header className="candidate-print-ai-header">
        <div><p className="print-report-kicker">Optional AI appendix · generated from saved evidence</p><h1>AI evidence explanation</h1><p>{candidate.gene_symbol} · This appendix cannot change the deterministic classification, scores, or shortlist order.</p></div>
        <dl><dt>Model</dt><dd>{explanation.model}</dd><dt>Generated</dt><dd>{new Date(explanation.generated_at).toISOString()}</dd><dt>Prompt version</dt><dd>{explanation.prompt_version}</dd><dt>Output schema</dt><dd>{explanation.output_schema_version}</dd><dt>Cache status</dt><dd>{explanation.cached ? "Reused identical-input cache" : "New generation"}</dd></dl>
      </header>
      <p className="print-disclaimer">{explanation.research_use_disclaimer}</p>
      <section className="candidate-print-ai-summary"><h2>Summary</h2><p>{explanation.output.summary}</p></section>
      <div className="candidate-print-ai-grid">
        <section><h2>Decision basis</h2><PrintClaims claims={explanation.output.decision_basis}/></section>
        {explanation.output.supporting_evidence.length > 0 && <section><h2>Supporting evidence</h2><PrintClaims claims={explanation.output.supporting_evidence}/></section>}
        {explanation.output.conflicting_evidence.length > 0 && <section><h2>Conflicting evidence</h2><PrintClaims claims={explanation.output.conflicting_evidence}/></section>}
        <section><h2>Uncertainties</h2><ul>{explanation.output.uncertainties.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section><h2>Manual review</h2><ul>{explanation.output.manual_review_steps.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section><h2>What this does not mean</h2><ul>{explanation.output.what_this_does_not_mean.map(item => <li key={item}>{item}</li>)}</ul></section>
        {explanation.output.glossary.length > 0 && <section><h2>Generated glossary</h2><dl>{explanation.output.glossary.map(item => <div key={item.term}><dt>{item.term}</dt><dd>{item.definition}</dd></div>)}</dl></section>}
      </div>
      <section className="candidate-print-ai-sources"><h2>Validated source identifiers</h2><p>{explanation.source_ids.join(" · ")}</p><p>Insight ID: {explanation.insight_id}</p></section>
      <footer className="print-page-footer"><span>ASO Compass · Candidate {candidate.gene_symbol} · Optional AI appendix</span><span>Generated · evidence only</span></footer>
    </article>}
  </section>;
}
