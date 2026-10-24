import type { Candidate, CitedClaim, RunRecord, RunSummary } from "./types";
import { normalizeRunWarning, type PrintMode } from "./printReportUtils";

// Keep a conservative row budget. Candidate names and browser font metrics can
// make a nominally fixed table row taller in Chromium's paged-media renderer.
const PRINT_ROWS_PER_PAGE = 12;

const TRACK_LABEL: Record<string, string> = {
  knockdown: "Knockdown",
  "splice/upregulation": "Splice / upregulation",
  ambiguous: "Ambiguous",
  modifier: "Modifier",
  "insufficient data": "Insufficient data",
};

function chunk<T>(rows: T[], size: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < rows.length; index += size) chunks.push(rows.slice(index, index + size));
  return chunks;
}

function evidenceLabel(row: Candidate) {
  if (row.evidence_truncated) return "Capped";
  if (row.n_evidence === null) return "Not checked";
  return `${row.n_evidence_returned ?? 0}/${row.n_evidence}`;
}

function precedentLabel(row: Candidate) {
  const labels: string[] = [];
  if (row.has_approved_drug) labels.push(row.drug_status);
  else if (["not checked", "lookup failed"].includes(row.drug_status.toLowerCase())) labels.push(row.drug_status);
  else if ((row.n_drugs ?? 0) > 0) labels.push(row.drug_status);
  else labels.push("None found");
  if (row.aso_precedent) labels.push("ASO / trial match");
  return labels.join(" · ");
}

function reviewReasons(row: Candidate) {
  const reasons: string[] = [];
  if (row.evidence_truncated) reasons.push("Capped evidence");
  if (row.final_call === "ambiguous") reasons.push("Ambiguous direction");
  if (row.has_approved_drug) reasons.push("Target-level approved drug");
  if (row.aso_precedent) reasons.push("ASO / trial match");
  if (row.has_approved_drug === null || ["not checked", "lookup failed"].includes(row.drug_status.toLowerCase())) {
    reasons.push("Drug evidence unknown");
  }
  return reasons;
}

function stableCandidateOrder(rows: Candidate[]) {
  return [...rows].sort(
    (left, right) =>
      (left.shortlist_position ?? Number.MAX_SAFE_INTEGER) -
        (right.shortlist_position ?? Number.MAX_SAFE_INTEGER) ||
      right.overall_score - left.overall_score ||
      left.gene_symbol.localeCompare(right.gene_symbol),
  );
}

interface CandidateSection {
  key: string;
  title: string;
  subtitle: string;
  rows: Candidate[];
  section: "shortlist" | "review" | "appendix";
}

function CandidateTable({ rows, review }: { rows: Candidate[]; review?: boolean }) {
  const headers = ["Rank", "Gene", "Track", "Overall", "Genetic", "Evidence", "LOEUF", review ? "Review reason / precedent" : "Therapeutic precedent"];
  return <div className="print-candidate-grid" role="table">
    <div className="print-candidate-head" role="row">{headers.map(header => <span role="columnheader" key={header}>{header}</span>)}</div>
    {rows.map(row => <div className="print-candidate-row" role="row" key={row.ensembl_id}>
      <span role="cell">{row.shortlist_position ?? "—"}</span>
      <span role="cell"><b>{row.gene_symbol}</b><small className="print-candidate-name">{row.gene_name ?? "Unnamed gene"}</small></span>
      <span role="cell"><span className={`track-badge track-${row.final_call.replace(/[^a-z]/g, "-")}`}>{TRACK_LABEL[row.final_call] ?? row.final_call}</span></span>
      <span role="cell">{row.overall_score.toFixed(3)}</span><span role="cell">{row.genetic_score.toFixed(3)}</span>
      <span role="cell" className={row.evidence_truncated ? "status-warn" : ""}>{evidenceLabel(row)}</span>
      <span role="cell">{row.loeuf?.toFixed(2) ?? "—"}</span>
      <span role="cell" className="print-precedent">{review ? [...reviewReasons(row), precedentLabel(row)].join(" · ") : precedentLabel(row)}</span>
    </div>)}
  </div>;
}

function PageFooter({ run, page, total }: { run: RunRecord; page: number; total: number }) {
  return <footer className="print-page-footer">
    <span>ASO Compass · Run {run.id}</span>
    <span>Research use only · Page {page} of {total}</span>
  </footer>;
}

function SummaryClaims({ claims }: { claims: CitedClaim[] }) {
  if (claims.length === 0) return <p className="print-ai-empty">None returned.</p>;
  return <ul className="print-run-ai-claims">{claims.map((item, index) => <li key={`${item.claim}-${index}`}>
    <span>{item.claim}</span>
    <small>Validated saved sources: {item.source_ids.join(", ")}</small>
  </li>)}</ul>;
}

function SummaryList({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="print-ai-empty">None returned.</p>;
  return <ul>{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>;
}

function RunSummaryAppendix({ run, summary, page, total }: { run: RunRecord; summary: RunSummary; page: number; total: number }) {
  return <article className="print-page print-run-ai-page" data-report-section="run-ai-summary">
    <header className="print-run-ai-header">
      <div><p className="print-report-kicker">Optional AI appendix · generated from saved evidence</p><h2>AI run summary</h2><p>This interpretation is separate from the deterministic report and cannot change its classifications, scores, shortlist, or warnings.</p></div>
      <dl><dt>Model</dt><dd>{summary.model}</dd><dt>Generated</dt><dd>{summary.generated_at}</dd><dt>Prompt</dt><dd>{summary.prompt_version}</dd><dt>Schema</dt><dd>{summary.output_schema_version}</dd></dl>
    </header>
    <p className="print-disclaimer">{summary.research_use_disclaimer}</p>
    <section className="print-run-ai-overview"><h3>Overview</h3><p>{summary.output.overview}</p></section>
    <div className="print-run-ai-grid">
      <section><h3>Key findings</h3><SummaryClaims claims={summary.output.key_findings}/></section>
      <section><h3>Review priorities</h3><SummaryClaims claims={summary.output.review_priorities}/></section>
      <section><h3>Track breakdown</h3><div className="print-run-ai-tracks">{summary.output.track_breakdown.map(item => <article key={item.track}><div><b>{TRACK_LABEL[item.track] ?? item.track}</b><strong>{item.count}</strong></div><p>{item.interpretation}</p><small>Validated saved sources: {item.source_ids.join(", ")}</small></article>)}</div></section>
      <section><h3>Evidence gaps</h3><SummaryClaims claims={summary.output.evidence_gaps}/></section>
      <section><h3>Limitations</h3><SummaryList items={summary.output.limitations}/></section>
      <section><h3>What this does not mean</h3><SummaryList items={summary.output.what_this_does_not_mean}/></section>
    </div>
    <section className="print-run-ai-provenance"><h3>Validated provenance</h3><p>Insight {summary.insight_id} · {summary.cached ? "Reused identical-input cache" : "New generation"} · source identifiers were validated server-side.</p><p>{summary.source_ids.join(", ")}</p></section>
    <PageFooter run={run} page={page} total={total}/>
  </article>;
}

export default function PrintReport({ run, candidates, mode, generatedAt, runSummary }: {
  run: RunRecord;
  candidates: Candidate[];
  mode: PrintMode;
  generatedAt: string;
  runSummary: RunSummary | null;
}) {
  const ordered = stableCandidateOrder(candidates);
  const shortlist = ordered.filter(row => row.shortlist_position !== null);
  const reviewQueue = ordered.filter(row => reviewReasons(row).length > 0);
  const sections: CandidateSection[] = [
    ...chunk(shortlist, PRINT_ROWS_PER_PAGE).map((rows, index) => ({
      key: `shortlist-${index}`,
      title: "Saved priority shortlist",
      subtitle: "Deterministic review order; this is not a treatment ranking.",
      rows,
      section: "shortlist" as const,
    })),
    ...chunk(reviewQueue, PRINT_ROWS_PER_PAGE).map((rows, index) => ({
      key: `review-${index}`,
      title: "Manual review queue",
      subtitle: "Capped, ambiguous, precedent-bearing, or incompletely checked candidates.",
      rows,
      section: "review" as const,
    })),
    ...(mode === "full" ? chunk(ordered, PRINT_ROWS_PER_PAGE).map((rows, index) => ({
      key: `appendix-${index}`,
      title: "All candidates appendix",
      subtitle: "Complete saved candidate set in deterministic display order.",
      rows,
      section: "appendix" as const,
    })) : []),
  ];
  const includeRunSummary = mode === "full" && runSummary !== null;
  const totalPages = 1 + sections.length + (includeRunSummary ? 1 : 0);
  const warnings = [...new Set(run.warnings.map(normalizeRunWarning))];
  const tracks = Object.entries(TRACK_LABEL).map(([track, label]) => ({
    track,
    label,
    count: candidates.filter(row => row.final_call === track).length,
  }));
  const runMode = String(run.parameters.run_mode ?? "not recorded");
  const release = String(run.upstream_metadata.open_targets_release ?? "not recorded");

  return <section className="print-report" data-print-mode={mode} aria-label={`${mode === "full" ? "Full" : "Summary"} print report`}>
    <article className="print-page print-cover" data-report-section="cover">
      <div className="print-report-kicker">{mode === "full" ? "Full evidence report" : "Summary evidence report"}</div>
      <h1>{run.disease_label ?? run.disease_id}</h1>
      <p className="print-subtitle">{run.disease_id} · Engine {run.engine_version} · Open Targets {release}</p>
      <p className="print-disclaimer">{run.research_use_disclaimer}</p>
      {warnings.length > 0 && <div className="print-warnings">{warnings.map(warning => <p key={warning}>{warning}</p>)}</div>}
      <div className="print-metadata">
        <div><span>Run ID</span><b>{run.id}</b></div><div><span>Mode</span><b>{runMode}</b></div>
        <div><span>Completed</span><b>{run.completed_at ? new Date(run.completed_at).toISOString() : "Not recorded"}</b></div>
        <div><span>Report generated</span><b>{generatedAt}</b></div>
      </div>
      <div className="print-metrics">
        <div><span>Candidates</span><b>{candidates.length}</b><small>Passed association filters</small></div>
        <div><span>Priority shortlist</span><b>{shortlist.length}</b><small>Directionally reviewable tracks</small></div>
        <div><span>Evidence capped</span><b>{candidates.filter(row => row.evidence_truncated).length}</b><small>Manual review required</small></div>
        <div><span>ASO precedent</span><b>{candidates.filter(row => row.aso_precedent).length}</b><small>Drug or trial source match</small></div>
      </div>
      <section className="print-track-summary"><h2>Candidate tracks</h2><div>{tracks.map(item => <article key={item.track}><span>{item.label}</span><b>{item.count}</b></article>)}</div></section>
      <section className="print-reading-guide"><h2>Reading guide</h2><div>
        <p><b>Capped</b> Source evidence exceeded the per-gene retrieval limit; observed fractions may be incomplete.</p>
        <p><b>LOEUF</b> Population constraint context; lower values indicate less tolerance to loss of function, not automatic unsuitability or safety.</p>
        <p><b>Review status</b> ClinVar review and consensus context; classifications should not be interpreted without condition, date, and primary record.</p>
        <p><b>Not checked</b> Enrichment was not performed. This is missing information, not negative evidence.</p>
        <p><b>None found</b> The checked sources returned no match; absence is limited to those sources and that run.</p>
        <p><b>Target-level approval</b> A drug may be approved for another disease, direction, modality, or population.</p>
      </div></section>
      {mode === "full" && <p className="print-ai-inclusion-note"><b>Optional AI appendix:</b> {includeRunSummary ? "Included from the already-generated, server-validated run summary." : "Not included because no AI run summary had been generated before printing."}</p>}
      <PageFooter run={run} page={1} total={totalPages}/>
    </article>
    {sections.map((section, index) => <article className="print-page print-table-page" data-report-section={section.section} key={section.key}>
      <header><p className="print-report-kicker">ASO Compass · {mode === "full" ? "Full report" : "Summary report"}</p><h2>{section.title}</h2><p>{section.subtitle}</p></header>
      <CandidateTable rows={section.rows} review={section.section === "review"}/>
      <p className="print-source-note">Therapeutic precedent is target-level unless indication-matched provenance is explicitly shown. ASO/trial text matches require manual confirmation.</p>
      <PageFooter run={run} page={index + 2} total={totalPages}/>
    </article>)}
    {includeRunSummary && <RunSummaryAppendix run={run} summary={runSummary} page={totalPages} total={totalPages}/>}
  </section>;
}
