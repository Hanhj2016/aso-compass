import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

import { normalizeRunWarning, type PrintMode } from "./printReportUtils";
import type { Candidate, CandidateExplanation, CitedClaim, RunRecord, RunSummary } from "./types";

const INK: [number, number, number] = [23, 49, 45];
const GREEN: [number, number, number] = [29, 112, 95];
const MUTED: [number, number, number] = [88, 112, 105];
const PALE: [number, number, number] = [234, 244, 240];
const WARNING: [number, number, number] = [247, 240, 223];
const MARGIN = 38;

const TRACK_LABEL: Record<string, string> = {
  knockdown: "Knockdown",
  "splice/upregulation": "Splice / upregulation",
  ambiguous: "Ambiguous",
  modifier: "Modifier",
  "insufficient data": "Insufficient data",
};

function pdfText(value: unknown) {
  return String(value ?? "")
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2012-\u2015]/g, "-")
    .replace(/\u2026/g, "...")
    .replace(/\u00b7/g, " | ")
    .replace(/[^\x20-\x7e\n]/g, "?");
}

function valueOrUnknown(value: unknown) {
  return value === null || value === undefined || value === "" ? "Not returned" : pdfText(value);
}

function evidenceLabel(row: Candidate) {
  if (row.evidence_truncated) return "Capped";
  if (row.n_evidence === null) return "Not checked";
  return `${row.n_evidence_returned ?? 0}/${row.n_evidence}`;
}

function precedentLabel(row: Candidate) {
  const labels: string[] = [];
  if (row.has_approved_drug || (row.n_drugs ?? 0) > 0) labels.push(row.drug_status);
  else if (["not checked", "lookup failed"].includes(row.drug_status.toLowerCase())) labels.push(row.drug_status);
  else labels.push("None found");
  if (row.aso_precedent) labels.push("ASO / trial match");
  return labels.join(" | ");
}

function reviewReasons(row: Candidate) {
  const reasons: string[] = [];
  if (row.evidence_truncated) reasons.push("Capped evidence");
  if (row.final_call === "ambiguous") reasons.push("Ambiguous direction");
  if (row.has_approved_drug) reasons.push("Target-level approved drug");
  if (row.aso_precedent) reasons.push("ASO / trial match");
  if (row.has_approved_drug === null || ["not checked", "lookup failed"].includes(row.drug_status.toLowerCase())) reasons.push("Drug evidence unknown");
  return reasons;
}

function orderedCandidates(rows: Candidate[]) {
  return [...rows].sort((left, right) =>
    (left.shortlist_position ?? Number.MAX_SAFE_INTEGER) - (right.shortlist_position ?? Number.MAX_SAFE_INTEGER)
    || right.overall_score - left.overall_score
    || left.gene_symbol.localeCompare(right.gene_symbol));
}

function createDocument() {
  return new jsPDF({ orientation: "landscape", unit: "pt", format: "letter", compress: true });
}

function pageWidth(doc: jsPDF) {
  return doc.internal.pageSize.getWidth();
}

function pageHeight(doc: jsPDF) {
  return doc.internal.pageSize.getHeight();
}

function heading(doc: jsPDF, kicker: string, title: string, subtitle?: string) {
  doc.setTextColor(...GREEN).setFont("helvetica", "bold").setFontSize(8);
  doc.text(pdfText(kicker).toUpperCase(), MARGIN, 35);
  doc.setTextColor(...INK).setFontSize(22);
  doc.text(pdfText(title), MARGIN, 62);
  if (subtitle) {
    doc.setTextColor(...MUTED).setFont("helvetica", "normal").setFontSize(9);
    doc.text(pdfText(subtitle), MARGIN, 80);
  }
}

function footer(doc: jsPDF, label: string) {
  const total = doc.getNumberOfPages();
  for (let page = 1; page <= total; page += 1) {
    doc.setPage(page);
    doc.setDrawColor(185, 203, 197).line(MARGIN, pageHeight(doc) - 24, pageWidth(doc) - MARGIN, pageHeight(doc) - 24);
    doc.setTextColor(...MUTED).setFont("helvetica", "normal").setFontSize(7);
    doc.text(pdfText(label), MARGIN, pageHeight(doc) - 12);
    doc.text(`Research use only | Page ${page} of ${total}`, pageWidth(doc) - MARGIN, pageHeight(doc) - 12, { align: "right" });
  }
}

function addWrappedText(doc: jsPDF, text: string, x: number, y: number, width: number, options: { bold?: boolean; size?: number; color?: [number, number, number] } = {}) {
  doc.setFont("helvetica", options.bold ? "bold" : "normal").setFontSize(options.size ?? 9).setTextColor(...(options.color ?? INK));
  const lines = doc.splitTextToSize(pdfText(text), width) as string[];
  doc.text(lines, x, y);
  return y + lines.length * ((options.size ?? 9) * 1.25);
}

function addSection(doc: jsPDF, title: string, items: string[], y: number) {
  const usableWidth = pageWidth(doc) - MARGIN * 2;
  const estimate = 28 + items.reduce((sum, item) => sum + (doc.splitTextToSize(pdfText(item), usableWidth - 20) as string[]).length * 11, 0);
  if (y + estimate > pageHeight(doc) - 42) {
    doc.addPage();
    y = 42;
  }
  doc.setFillColor(...PALE).roundedRect(MARGIN, y - 13, usableWidth, 19, 3, 3, "F");
  doc.setTextColor(...INK).setFont("helvetica", "bold").setFontSize(10).text(pdfText(title), MARGIN + 7, y);
  y += 17;
  for (const item of items.length ? items : ["None returned."]) {
    const lines = doc.splitTextToSize(`- ${pdfText(item)}`, usableWidth - 12) as string[];
    if (y + lines.length * 11 > pageHeight(doc) - 42) {
      doc.addPage();
      y = 42;
    }
    doc.setFont("helvetica", "normal").setFontSize(8.5).setTextColor(...INK).text(lines, MARGIN + 6, y);
    y += lines.length * 11 + 3;
  }
  return y + 6;
}

function claimText(claims: CitedClaim[]) {
  return claims.map(item => `${item.claim} [Saved sources: ${item.source_ids.join(", ")}]`);
}

function addCandidateTable(doc: jsPDF, title: string, subtitle: string, rows: Candidate[], review = false) {
  doc.addPage();
  heading(doc, "ASO Compass evidence report", title, subtitle);
  autoTable(doc, {
    startY: 94,
    margin: { left: MARGIN, right: MARGIN, bottom: 34 },
    head: [["Rank", "Gene", "Track", "Overall", "Genetic", "Evidence", "LOEUF", review ? "Review reason / precedent" : "Therapeutic precedent"]],
    body: rows.map(row => [
      row.shortlist_position ?? "-",
      `${row.gene_symbol}\n${row.gene_name ?? "Unnamed gene"}`,
      TRACK_LABEL[row.final_call] ?? row.final_call,
      row.overall_score.toFixed(3),
      row.genetic_score.toFixed(3),
      evidenceLabel(row),
      row.loeuf?.toFixed(2) ?? "-",
      review ? [...reviewReasons(row), precedentLabel(row)].join(" | ") : precedentLabel(row),
    ].map(pdfText)),
    theme: "grid",
    styles: { font: "helvetica", fontSize: 7, textColor: INK, lineColor: [220, 230, 226], lineWidth: 0.4, cellPadding: 3, overflow: "linebreak" },
    headStyles: { fillColor: PALE, textColor: MUTED, fontStyle: "bold" },
    alternateRowStyles: { fillColor: [248, 250, 249] },
    columnStyles: { 0: { cellWidth: 28 }, 1: { cellWidth: 96 }, 2: { cellWidth: 82 }, 3: { cellWidth: 43 }, 4: { cellWidth: 43 }, 5: { cellWidth: 52 }, 6: { cellWidth: 40 } },
  });
}

function addRunCover(doc: jsPDF, run: RunRecord, candidates: Candidate[], mode: PrintMode, generatedAt: string, includeAI: boolean) {
  heading(doc, mode === "full" ? "Full evidence report" : "Summary evidence report", run.disease_label ?? run.disease_id, `${run.disease_id} | Engine ${run.engine_version} | Open Targets ${String(run.upstream_metadata.open_targets_release ?? "not recorded")}`);
  doc.setFillColor(...WARNING).roundedRect(MARGIN, 96, pageWidth(doc) - MARGIN * 2, 31, 3, 3, "F");
  addWrappedText(doc, run.research_use_disclaimer, MARGIN + 8, 114, pageWidth(doc) - MARGIN * 2 - 16, { bold: true, size: 8, color: [113, 91, 46] });
  const warnings = [...new Set(run.warnings.map(normalizeRunWarning))];
  let y = 144;
  if (warnings.length) y = addSection(doc, "Run warnings", warnings, y);
  const shortlist = candidates.filter(row => row.shortlist_position !== null).length;
  const metrics = [
    ["Candidates", candidates.length],
    ["Priority shortlist", shortlist],
    ["Evidence capped", candidates.filter(row => row.evidence_truncated).length],
    ["ASO precedent", candidates.filter(row => row.aso_precedent).length],
  ];
  autoTable(doc, {
    startY: y,
    margin: { left: MARGIN, right: MARGIN },
    body: [metrics.map(([label, value]) => `${label}\n${value}`)],
    theme: "grid",
    styles: { font: "helvetica", fontSize: 9, fontStyle: "bold", textColor: INK, fillColor: [248, 250, 249], lineColor: [185, 203, 197], cellPadding: 8 },
  });
  y += 53;
  autoTable(doc, {
    startY: y,
    margin: { left: MARGIN, right: MARGIN },
    head: [["Run ID", "Mode", "Completed", "Report generated"]],
    body: [[run.id, String(run.parameters.run_mode ?? "not recorded"), run.completed_at ? new Date(run.completed_at).toISOString() : "Not recorded", generatedAt].map(pdfText)],
    theme: "grid",
    styles: { font: "helvetica", fontSize: 7, textColor: INK, lineColor: [197, 212, 207], cellPadding: 4 },
    headStyles: { fillColor: PALE, textColor: MUTED },
  });
  y += 55;
  const tracks = Object.entries(TRACK_LABEL).map(([track, label]) => `${label}: ${candidates.filter(row => row.final_call === track).length}`);
  y = addSection(doc, "Candidate tracks", tracks, y);
  y = addSection(doc, "Terminology notes", [
    "LOEUF is population loss-of-function constraint context; a low value is a safety flag, not proof that a target is undruggable.",
    "Evidence capped means retrieval stopped at the configured limit; it does not mean absent, benign, or low-quality evidence.",
    "ClinVar review status and stars describe review and consensus context; the classification label alone is incomplete.",
  ], y);
  if (mode === "full") addSection(doc, "Optional AI appendix", [includeAI ? "Included from the already-generated, server-validated run summary." : "Not included because no AI run summary had been generated before export."], y);
}

function addRunSummary(doc: jsPDF, summary: RunSummary) {
  doc.addPage();
  heading(doc, "Optional AI appendix | generated from saved evidence", "AI run summary", `Model ${summary.model} | Generated ${summary.generated_at} | Prompt ${summary.prompt_version}`);
  let y = addWrappedText(doc, summary.research_use_disclaimer, MARGIN, 101, pageWidth(doc) - MARGIN * 2, { bold: true, size: 8, color: [113, 91, 46] }) + 10;
  y = addSection(doc, "Overview", [summary.output.overview], y);
  y = addSection(doc, "Key findings", claimText(summary.output.key_findings), y);
  y = addSection(doc, "Review priorities", claimText(summary.output.review_priorities), y);
  y = addSection(doc, "Track breakdown", summary.output.track_breakdown.map(item => `${TRACK_LABEL[item.track] ?? item.track} (${item.count}): ${item.interpretation} [Saved sources: ${item.source_ids.join(", ")}]`), y);
  y = addSection(doc, "Evidence gaps", claimText(summary.output.evidence_gaps), y);
  y = addSection(doc, "Limitations", summary.output.limitations, y);
  addSection(doc, "What this does not mean", summary.output.what_this_does_not_mean, y);
}

export function downloadRunPdf(run: RunRecord, candidates: Candidate[], mode: PrintMode, generatedAt: string, runSummary: RunSummary | null, filename: string) {
  const doc = createDocument();
  const ordered = orderedCandidates(candidates);
  const shortlist = ordered.filter(row => row.shortlist_position !== null);
  const review = ordered.filter(row => reviewReasons(row).length > 0);
  const includeAI = mode === "full" && runSummary !== null;
  addRunCover(doc, run, candidates, mode, generatedAt, includeAI);
  if (shortlist.length) addCandidateTable(doc, "Saved priority shortlist", "Deterministic review order; this is not a treatment ranking.", shortlist);
  if (review.length) addCandidateTable(doc, "Manual review queue", "Capped, ambiguous, precedent-bearing, or incompletely checked candidates.", review, true);
  if (mode === "full") addCandidateTable(doc, "All candidates appendix", "Complete saved candidate set in deterministic display order.", ordered);
  if (includeAI) addRunSummary(doc, runSummary);
  doc.setProperties({ title: filename, subject: "ASO Compass evidence report", author: "ASO Compass", creator: "ASO Compass" });
  footer(doc, `ASO Compass | Run ${run.id}`);
  doc.save(`${filename}.pdf`);
}

function candidateFacts(candidate: Candidate) {
  const evidenceCount = candidate.n_evidence === null ? "Not checked" : `${candidate.n_evidence_returned ?? 0}/${candidate.n_evidence}`;
  return [
    ["Final track", TRACK_LABEL[candidate.final_call] ?? candidate.final_call],
    ["Deterministic source", candidate.call_source],
    ["Confidence", candidate.confidence_tier],
    ["Shortlist position", candidate.shortlist_position ?? "Not shortlisted"],
    ["Overall association", candidate.overall_score.toFixed(3)],
    ["Genetic association", candidate.genetic_score.toFixed(3)],
    ["LOEUF", candidate.loeuf?.toFixed(3) ?? "Unknown"],
    ["Evidence returned / total", evidenceCount],
  ];
}

function addCandidateExplanation(doc: jsPDF, candidate: Candidate, explanation: CandidateExplanation) {
  doc.addPage();
  heading(doc, "Optional AI appendix | generated from saved evidence", "AI evidence explanation", `${candidate.gene_symbol} | Model ${explanation.model} | Generated ${explanation.generated_at}`);
  let y = addWrappedText(doc, explanation.research_use_disclaimer, MARGIN, 101, pageWidth(doc) - MARGIN * 2, { bold: true, size: 8, color: [113, 91, 46] }) + 10;
  y = addSection(doc, "Summary", [explanation.output.summary], y);
  y = addSection(doc, "Decision basis", claimText(explanation.output.decision_basis), y);
  y = addSection(doc, "Supporting evidence", claimText(explanation.output.supporting_evidence), y);
  y = addSection(doc, "Conflicting evidence", claimText(explanation.output.conflicting_evidence), y);
  y = addSection(doc, "Uncertainties", explanation.output.uncertainties, y);
  y = addSection(doc, "Manual review", explanation.output.manual_review_steps, y);
  y = addSection(doc, "What this does not mean", explanation.output.what_this_does_not_mean, y);
  addSection(doc, "Generated glossary", explanation.output.glossary.map(item => `${item.term}: ${item.definition}`), y);
}

export function downloadCandidatePdf(run: RunRecord, candidate: Candidate, explanation: CandidateExplanation | null, generatedAt: string, filename: string) {
  const doc = createDocument();
  heading(doc, "Candidate evidence report | deterministic saved record", candidate.gene_symbol, `${candidate.gene_name ?? "Gene name not returned"} | ${run.disease_label ?? run.disease_id} | ${candidate.ensembl_id}`);
  doc.setFillColor(...WARNING).roundedRect(MARGIN, 96, pageWidth(doc) - MARGIN * 2, 31, 3, 3, "F");
  addWrappedText(doc, run.research_use_disclaimer, MARGIN + 8, 114, pageWidth(doc) - MARGIN * 2 - 16, { bold: true, size: 8, color: [113, 91, 46] });
  let y = addSection(doc, "Why this track?", [candidate.confidence_reason], 149);
  autoTable(doc, {
    startY: y,
    margin: { left: MARGIN, right: MARGIN },
    body: candidateFacts(candidate).map(([label, value]) => [pdfText(label), pdfText(value)]),
    theme: "grid",
    tableWidth: 330,
    styles: { font: "helvetica", fontSize: 8, textColor: INK, lineColor: [211, 223, 219], cellPadding: 4 },
    columnStyles: { 0: { fillColor: PALE, fontStyle: "bold", cellWidth: 135 } },
  });
  const factBottom = (doc as jsPDF & { lastAutoTable: { finalY: number } }).lastAutoTable.finalY;
  autoTable(doc, {
    startY: y,
    margin: { left: MARGIN + 350, right: MARGIN },
    body: [
      ["ClinVar heuristic", candidate.clinvar_call], ["G2P mechanism", valueOrUnknown(candidate.g2p_mech)], ["Inheritance", valueOrUnknown(candidate.inheritance)],
      ["Loss-of-function", valueOrUnknown(candidate.n_lof)], ["Missense", valueOrUnknown(candidate.n_missense)], ["Splice", valueOrUnknown(candidate.n_splice)],
      ["Drug status", valueOrUnknown(candidate.drug_status)], ["Approved drugs", valueOrUnknown(candidate.approved_drugs)], ["ASO names", valueOrUnknown(candidate.aso_names)],
      ["Trial count / best phase", `${candidate.aso_trial_n ?? 0} / ${valueOrUnknown(candidate.aso_trial_best)}`],
    ].map(row => row.map(pdfText)),
    theme: "grid",
    styles: { font: "helvetica", fontSize: 8, textColor: INK, lineColor: [211, 223, 219], cellPadding: 4 },
    columnStyles: { 0: { fillColor: PALE, fontStyle: "bold", cellWidth: 125 } },
  });
  y = Math.max(factBottom, (doc as jsPDF & { lastAutoTable: { finalY: number } }).lastAutoTable.finalY) + 18;
  y = addSection(doc, "Completeness and review", [`Completeness: ${candidate.completeness}`, `Evidence capped: ${candidate.evidence_truncated ? "Yes - manual review required" : "No"}`, `Review flag: ${candidate.flag || "None recorded"}`, candidate.note].filter(Boolean), y);
  const clinvar = candidate.clinvar_interpretation;
  y = addSection(doc, "ClinVar interpretation context", [
    `Review-status coverage: ${clinvar?.records_with_review_status ?? "Not retained"} / ${clinvar?.records_returned ?? candidate.n_evidence_returned ?? "Not retained"}`,
    `Review stars: ${Object.entries(clinvar?.review_star_counts ?? {}).map(([stars, count]) => `${stars} star(s): ${count}`).join("; ") || "Not retained"}`,
    `Latest evidence date: ${clinvar?.latest_evidence_date ?? "Not returned"}`,
    `Latest source release: ${clinvar?.latest_release_date ?? "Not returned"}`,
    `Release version(s): ${clinvar?.release_versions?.join(", ") || "Not returned"}`,
    `Submitter count: ${clinvar?.submitter_count ?? "Not exposed by upstream query"}`,
  ], y);
  y = addSection(doc, "Therapeutic precedent", [candidate.aso_precedent || "No ASO precedent was found in the checked sources.", `Trial IDs: ${candidate.aso_trial_ids || "None saved"}`], y);
  y = addSection(doc, "Terminology notes", [
    "LOEUF: population loss-of-function constraint context; a low value is a safety flag, not proof that a target is undruggable.",
    "Evidence capped: retrieval stopped at the configured limit; it does not mean absent, benign, or low-quality evidence.",
    "Review status / stars: review and consensus context behind ClinVar classifications; the label alone is incomplete.",
  ], y);
  if (y > pageHeight(doc) - 67) {
    doc.addPage();
    y = 42;
  }
  doc.setTextColor(...GREEN).setFont("helvetica", "bold").setFontSize(8).text("REPORT PROVENANCE", MARGIN, y);
  addWrappedText(doc, `Saved source ID: candidate:${candidate.ensembl_id} | Run ID: ${run.id} | Engine: ${run.engine_version} | Report generated: ${generatedAt}`, MARGIN, y + 13, pageWidth(doc) - MARGIN * 2, { size: 6.5, color: MUTED });
  if (explanation) addCandidateExplanation(doc, candidate, explanation);
  doc.setProperties({ title: filename, subject: `ASO Compass candidate evidence - ${candidate.gene_symbol}`, author: "ASO Compass", creator: "ASO Compass" });
  footer(doc, `ASO Compass | Candidate ${candidate.gene_symbol} | Run ${run.id}`);
  doc.save(`${filename}.pdf`);
}
