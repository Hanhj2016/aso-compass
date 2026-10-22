import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { askSavedEvidenceQuestion, compareCandidates, createRun, explainCandidate, exportUrl, getCandidates, getEvents, getPublicConfig, getRun, summarizeRun } from "./api";
import CandidatePrintReport from "./CandidatePrintReport";
import Learn from "./Learn";
import PrintReport from "./PrintReport";
import { normalizeRunWarning, type PrintMode } from "./printReportUtils";
import type { AIQuestionAnswer, Candidate, CandidateComparison, CandidateExplanation, CitedClaim, ExampleBundle, RunEvent, RunRecord, RunSummary } from "./types";

const DISCLAIMER = "For hypothesis generation and education only. Not for clinical decision-making.";
const AI_ACCESS_STORAGE_KEY = "aso-compass-ai-access-token";
type AIConfigStatus = "loading" | "ready" | "error";
const PRESETS = [
  ["MONDO_0004976", "Amyotrophic lateral sclerosis (ALS)"],
  ["MONDO_0004975", "Alzheimer disease"],
  ["MONDO_0005180", "Parkinson disease"],
  ["MONDO_0007739", "Huntington disease"],
  ["MONDO_0010679", "Duchenne muscular dystrophy"],
  ["MONDO_0001516", "Spinal muscular atrophy"],
  ["MONDO_0100135", "Dravet syndrome"],
  ["EFO_0700065", "Hereditary ATTR amyloidosis"],
] as const;
const TRACKS = ["all", "knockdown", "splice/upregulation", "ambiguous", "modifier", "insufficient data"];
const TRACK_LABEL: Record<string, string> = {
  knockdown: "Knockdown", "splice/upregulation": "Splice / upregulation", ambiguous: "Ambiguous",
  modifier: "Modifier", "insufficient data": "Insufficient data",
};

function AIIcon({ size = 16 }: { size?: number }) {
  return <svg className="ai-icon" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M12 2.5c.55 4.35 2.65 6.45 7 7-4.35.55-6.45 2.65-7 7-.55-4.35-2.65-6.45-7-7 4.35-.55 6.45-2.65 7-7Z" />
    <path d="M19 15.5c.25 1.95 1.05 2.75 3 3-1.95.25-2.75 1.05-3 3-.25-1.95-1.05-2.75-3-3 1.95-.25 2.75-1.05 3-3ZM5 2.5c.2 1.35.65 1.8 2 2-1.35.2-1.8.65-2 2-.2-1.35-.65-1.8-2-2 1.35-.2 1.8-.65 2-2Z" />
  </svg>;
}

function Header({ view, onView }: { view: string; onView: (view: "analyze" | "learn") => void }) {
  return <header className="site-header">
    <button className="brand" onClick={() => onView("analyze")}>
      <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
      <span><b>ASO</b> Compass<small>Evidence-guided exploration</small></span>
    </button>
    <nav aria-label="Primary navigation">
      <button className={view === "analyze" ? "active" : ""} onClick={() => onView("analyze")}>Analyze</button>
      <button className={view === "learn" ? "active" : ""} onClick={() => onView("learn")}>Learn</button>
    </nav>
    <span className="research-pill">Research use only</span>
  </header>;
}

function RunForm({ onCreated, onExample }: { onCreated: (run: RunRecord) => void; onExample: () => void }) {
  const [diseaseId, setDiseaseId] = useState("MONDO_0004976");
  const [customId, setCustomId] = useState("");
  const [isCustom, setIsCustom] = useState(false);
  const [label, setLabel] = useState<string>(PRESETS[0][1]);
  const [mode, setMode] = useState<"quick" | "full">("quick");
  const [advanced, setAdvanced] = useState(false);
  const [minScore, setMinScore] = useState(0.2);
  const [minGenetic, setMinGenetic] = useState(0.1);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setSubmitting(true);
    try {
      const run = await createRun({
        disease_id: isCustom ? customId : diseaseId, disease_label: label,
        parameters: { run_mode: mode, min_score: minScore, min_genetic: minGenetic,
          use_variants: true, use_g2p: true, check_drugs: true, check_trials: true,
          include_modifiers: true },
      });
      localStorage.setItem("aso-compass-run", run.id);
      onCreated(run);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The analysis could not be started.");
    } finally { setSubmitting(false); }
  }

  return <section className="analysis-shell" aria-labelledby="new-analysis-title">
    <div className="intro-copy">
      <p className="eyebrow">Deterministic evidence synthesis</p>
      <h1>Find a clearer path through target evidence.</h1>
      <p className="lede">Explore disease-associated genes across genetic mechanism, constraint, therapeutic precedent, and evidence completeness—with every call traceable to a visible rule.</p>
      <div className="source-line"><span>Open Targets</span><span>ClinVar / EVA</span><span>Gene2Phenotype</span><span>ClinicalTrials.gov</span></div>
      <button className="text-button" onClick={onExample}>Explore the precomputed ALS example <span aria-hidden="true">→</span></button>
    </div>
    <form className="run-card" onSubmit={submit}>
      <div className="card-heading"><span className="step-number">01</span><div><p className="eyebrow">New analysis</p><h2 id="new-analysis-title">Choose a disease</h2></div></div>
      <label htmlFor="disease">Disease or phenotype</label>
      <select id="disease" value={isCustom ? "custom" : diseaseId} onChange={(event) => {
        if (event.target.value === "custom") { setIsCustom(true); setLabel(""); return; }
        const preset = PRESETS.find(([id]) => id === event.target.value);
        setIsCustom(false); setDiseaseId(event.target.value); setLabel(preset?.[1] ?? "Custom disease");
      }}>
        {PRESETS.map(([id, name]) => <option key={id} value={id}>{name} — {id}</option>)}
        <option value="custom">Custom ontology identifier</option>
      </select>
      {isCustom && <div className="field-grid">
        <div><label htmlFor="custom-id">MONDO identifier</label><input id="custom-id" required pattern="MONDO[:_]\d+" placeholder="MONDO:0000000" value={customId} onChange={(e) => setCustomId(e.target.value)} /></div>
        <div><label htmlFor="custom-label">Display label</label><input id="custom-label" required maxLength={300} onChange={(e) => setLabel(e.target.value)} /></div>
      </div>}
      <fieldset className="mode-picker"><legend>Analysis depth</legend>
        <label className={mode === "quick" ? "selected" : ""}><input type="radio" name="mode" checked={mode === "quick"} onChange={() => setMode("quick")} /><span><b>Quick</b><small>Up to 25 genes enriched</small></span><em>~2–5 min</em></label>
        <label className={mode === "full" ? "selected" : ""}><input type="radio" name="mode" checked={mode === "full"} onChange={() => setMode("full")} /><span><b>Full</b><small>Up to 300 genes enriched</small></span><em>~15–25 min</em></label>
      </fieldset>
      {mode === "quick" && <p className="notice"><b>Quick mode is incomplete.</b> Association retrieval is complete, but variant and drug enrichment are capped at 25 genes.</p>}
      <button className="advanced-toggle" type="button" aria-expanded={advanced} onClick={() => setAdvanced(!advanced)}>Advanced parameters <span>{advanced ? "−" : "+"}</span></button>
      {advanced && <div className="advanced-panel">
        <label>Minimum overall association <output>{minScore.toFixed(2)}</output><input type="range" min="0" max="1" step="0.05" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} /></label>
        <label>Minimum genetic association <output>{minGenetic.toFixed(2)}</output><input type="range" min="0" max="1" step="0.05" value={minGenetic} onChange={(e) => setMinGenetic(Number(e.target.value))} /></label>
      </div>}
      <label className="consent"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>I understand that this tool is for research and education, not clinical decisions.</span></label>
      {error && <p className="error" role="alert">{error} The example remains available while the service wakes.</p>}
      <button className="primary-button" disabled={!consent || submitting}>{submitting ? "Starting analysis…" : "Begin evidence analysis"}<span aria-hidden="true">→</span></button>
      <p className="privacy-note">Public disease and gene evidence only. Do not enter patient-identifiable information.</p>
    </form>
  </section>;
}

function Progress({ run, events, onReset }: { run: RunRecord; events: RunEvent[]; onReset: () => void }) {
  const latest = events.at(-1);
  const amount = latest?.progress_total ? Math.round(((latest.progress_current ?? 0) / latest.progress_total) * 100) : 12;
  return <section className="progress-view">
    <p className="eyebrow">Analysis in progress</p><h1>{run.disease_label ?? run.disease_id}</h1>
    <p>You can close this page and return later. Progress is stored with the run.</p>
    <div className="progress-card">
      <div className="progress-orbit" style={{ "--progress": `${amount * 3.6}deg` } as React.CSSProperties}><b>{amount}%</b></div>
      <div><h2>{latest?.message ?? "Waiting for the worker"}</h2><p>Run {run.id.slice(0, 8)} · {run.status}</p></div>
    </div>
    <ol className="timeline">{events.map((event) => <li key={event.sequence}><span>{event.sequence}</span><div><b>{event.stage}</b><p>{event.message}</p></div></li>)}</ol>
    <button className="secondary-button" onClick={onReset}>Start another analysis</button>
  </section>;
}

function Metric({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return <article className="metric"><span>{label}</span><b>{value}</b><small>{detail}</small></article>;
}

function ScorePlot({ candidates, onSelect }: { candidates: Candidate[]; onSelect: (row: Candidate) => void }) {
  return <div className="plot" role="group" aria-label="Overall versus genetic association score plot">
    <span className="y-label">Overall score</span><span className="x-label">Genetic association score</span>
    {candidates.slice(0, 80).map((row) => <button key={row.ensembl_id} className={`dot track-${row.final_call.replace(/[^a-z]/g, "-")}`} style={{ left: `${8 + row.genetic_score * 84}%`, bottom: `${8 + row.overall_score * 82}%` }} title={`${row.gene_symbol}: overall ${row.overall_score.toFixed(2)}, genetic ${row.genetic_score.toFixed(2)}`} onClick={() => onSelect(row)}><span className="sr-only">Open {row.gene_symbol}</span></button>)}
  </div>;
}

function sourceLabel(sourceId: string) {
  if (sourceId.startsWith("candidate:")) return "Saved candidate record";
  if (sourceId.startsWith("run-summary:")) return "Deterministic run aggregate";
  if (sourceId.startsWith("run:")) return "Saved run context";
  if (sourceId.startsWith("evidence:")) return "Normalized evidence record";
  return sourceId;
}

function AIClaims({ claims }: { claims: CitedClaim[] }) {
  return <ul className="ai-claims">{claims.map((item, index) => <li key={`${item.claim}-${index}`}><span>{item.claim}</span><small>{item.source_ids.map(sourceId => <b key={sourceId} title={sourceId}>{sourceLabel(sourceId)}</b>)}</small></li>)}</ul>;
}

function AIAccessControl({ enabled, required, accessToken, onUnlock, onLock }: { enabled: boolean; required: boolean; accessToken: string; onUnlock: (token: string) => void; onLock: () => void }) {
  const [draft, setDraft] = useState(accessToken);
  if (!enabled || !required) return null;
  function submit(event: FormEvent) {
    event.preventDefault();
    const token = draft.trim();
    if (token) onUnlock(token);
  }
  return <section className="ai-access-panel" aria-labelledby="ai-access-title">
    <div><p className="eyebrow">Controlled AI access</p><h2 id="ai-access-title"><AIIcon size={19}/>{accessToken ? "AI access token ready" : "Unlock AI features"}</h2><p>The OpenAI credential remains on the server. Enter the separate ASO Compass access token; it is kept only for this browser tab and validated by the server on every AI request.</p></div>
    {accessToken ? <button className="secondary-button" type="button" onClick={() => { setDraft(""); onLock(); }}>Lock AI</button> : <form onSubmit={submit}><label htmlFor="ai-access-token">AI access token</label><div><input id="ai-access-token" type="password" autoComplete="off" value={draft} onChange={(event) => setDraft(event.target.value)} /><button className="secondary-button" disabled={!draft.trim()}>Use token</button></div></form>}
  </section>;
}

function CandidateDrawer({ row, runId, aiEnabled, aiConfigStatus, accessLocked, accessToken, isExample, explanation, onExplanationChange, onPrint, onClose }: { row: Candidate; runId: string; aiEnabled: boolean; aiConfigStatus: AIConfigStatus; accessLocked: boolean; accessToken: string; isExample: boolean; explanation: CandidateExplanation | null; onExplanationChange: (explanation: CandidateExplanation) => void; onPrint: (explanation: CandidateExplanation | null) => void; onClose: () => void }) {
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [maximized, setMaximized] = useState(false);
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (maximized) setMaximized(false);
      else onClose();
    }
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [maximized, onClose]);
  async function requestExplanation() {
    setAiLoading(true); setAiError("");
    try { onExplanationChange(await explainCandidate(runId, row.gene_symbol, accessToken, isExample)); }
    catch (error) { setAiError(error instanceof Error ? error.message : "The explanation could not be generated."); }
    finally { setAiLoading(false); }
  }
  return <div className={`drawer-backdrop${maximized ? " drawer-maximized" : ""}`} role="presentation" onMouseDown={onClose}><aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="gene-title" onMouseDown={(e) => e.stopPropagation()}>
    <div className="drawer-actions"><button className="secondary-button candidate-print-button" type="button" onClick={() => onPrint(explanation)}>{explanation ? "Print evidence + AI" : "Print evidence"}</button><button className="secondary-button drawer-size-button" type="button" aria-label={maximized ? "Restore candidate evidence view" : "Maximize candidate evidence view"} aria-pressed={maximized} onClick={() => setMaximized(current => !current)}><span aria-hidden="true">{maximized ? "↙" : "↗"}</span>{maximized ? "Restore" : "Maximize"}</button><button className="drawer-icon-button close" onClick={onClose} aria-label="Close gene details">×</button></div>
    <div className="drawer-content">
    <p className="eyebrow">Candidate evidence</p><h2 id="gene-title">{row.gene_symbol}</h2><p>{row.gene_name}</p>
    <span className={`track-badge track-${row.final_call.replace(/[^a-z]/g, "-")}`}>{TRACK_LABEL[row.final_call]}</span>
    <section><h3>Why this track?</h3><p>{row.confidence_reason}</p><p className="call-source">Deterministic source: <b>{row.call_source}</b> · Confidence label: <b>{row.confidence_tier}</b></p></section>
    <div className="evidence-grid"><div><span>Overall association</span><b>{row.overall_score.toFixed(3)}</b></div><div><span>Genetic association</span><b>{row.genetic_score.toFixed(3)}</b></div><div><span>LOEUF</span><b>{row.loeuf?.toFixed(3) ?? "Unknown"}</b></div><div><span>Classified variants</span><b>{(row.n_lof ?? 0) + (row.n_missense ?? 0)}</b></div></div>
    <section><h3>Mechanism evidence</h3><dl><dt>ClinVar heuristic</dt><dd>{row.clinvar_call}</dd><dt>G2P mechanism</dt><dd>{row.g2p_mech ?? "Not returned"}</dd><dt>Inheritance</dt><dd>{row.inheritance ?? "Not returned"}</dd></dl></section>
    <section><h3>Therapeutic precedent</h3><p>{row.aso_precedent || "No ASO precedent was found in the checked sources."}</p><p>{row.drug_status}</p>{row.aso_trial_ids && <p>Trial IDs: {row.aso_trial_ids}</p>}</section>
    {(row.flag || row.evidence_truncated) && <p className="notice"><b>Review flag:</b> {row.flag || "Variant evidence was capped and may be incomplete."}</p>}
    <section className="source-links"><h3>Primary records</h3><a href={`https://platform.opentargets.org/target/${row.ensembl_id}`} target="_blank" rel="noreferrer">Open Targets ↗</a>{row.aso_trial_ids.split(", ").filter(Boolean).map(id => <a key={id} href={`https://clinicaltrials.gov/study/${id}`} target="_blank" rel="noreferrer">{id} ↗</a>)}</section>
    <section className="ai-panel" aria-labelledby="ai-explanation-title"><div className="ai-heading"><h3 id="ai-explanation-title"><AIIcon/>AI evidence explainer</h3><span><AIIcon size={11}/>Generated · optional</span></div>
      {!aiEnabled && <p>{aiConfigStatus !== "ready" ? "Connecting to the AI service configuration…" : accessLocked ? "Enter the shared AI access token in the results page to unlock explanations." : "AI explanations are currently off. Deterministic results remain fully available."}</p>}
      {aiEnabled && !explanation && <><p>Generate a plain-language explanation from this saved evidence only. The explanation cannot change the classification or rank.</p><button className="secondary-button ai-button" onClick={() => void requestExplanation()} disabled={aiLoading}><AIIcon/>{aiLoading ? "Generating…" : "Explain saved evidence"}</button></>}
      {aiError && <p className="ai-error" role="alert">{aiError}</p>}
      {explanation && <div className="ai-output"><p className="ai-summary">{explanation.output.summary}</p>
        <h4>Decision basis</h4><AIClaims claims={explanation.output.decision_basis}/>
        {explanation.output.supporting_evidence.length > 0 && <><h4>Supporting evidence</h4><AIClaims claims={explanation.output.supporting_evidence}/></>}
        {explanation.output.conflicting_evidence.length > 0 && <><h4>Conflicting evidence</h4><AIClaims claims={explanation.output.conflicting_evidence}/></>}
        <h4>Uncertainties</h4><ul>{explanation.output.uncertainties.map(item => <li key={item}>{item}</li>)}</ul>
        <h4>What this does not mean</h4><ul>{explanation.output.what_this_does_not_mean.map(item => <li key={item}>{item}</li>)}</ul>
        <h4>Manual review</h4><ul>{explanation.output.manual_review_steps.map(item => <li key={item}>{item}</li>)}</ul>
        <p className="ai-meta">{explanation.cached ? "Reused reviewed input cache" : "New explanation"} · {explanation.model} · sources validated server-side</p>
        <p className="drawer-disclaimer">{explanation.research_use_disclaimer}</p>
      </div>}
    </section>
    <p className="drawer-disclaimer">{DISCLAIMER}</p></div>
  </aside></div>;
}

function AIQuestionPanel({ runId, candidates, enabled, aiConfigStatus, accessLocked, accessToken, isExample }: { runId: string; candidates: Candidate[]; enabled: boolean; aiConfigStatus: AIConfigStatus; accessLocked: boolean; accessToken: string; isExample: boolean }) {
  const [question, setQuestion] = useState("");
  const [geneSymbols, setGeneSymbols] = useState<string[]>([]);
  const [answer, setAnswer] = useState<AIQuestionAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function resetResult() { setAnswer(null); setError(""); }
  function addCandidate(geneSymbol: string) {
    if (!geneSymbol || geneSymbols.includes(geneSymbol) || geneSymbols.length >= 3) return;
    setGeneSymbols(current => [...current, geneSymbol]); resetResult();
  }
  function removeCandidate(geneSymbol: string) {
    setGeneSymbols(current => current.filter(symbol => symbol !== geneSymbol)); resetResult();
  }
  async function submitQuestion(event: FormEvent) {
    event.preventDefault();
    const normalized = question.trim();
    if (!normalized) return;
    setLoading(true); setError(""); setAnswer(null);
    try { setAnswer(await askSavedEvidenceQuestion(runId, normalized, geneSymbols, accessToken, isExample)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The saved-evidence question could not be answered."); }
    finally { setLoading(false); }
  }

  return <section className={`ai-panel qa-panel${answer ? " has-print-answer" : ""}`} aria-labelledby="qa-title">
    <div className="ai-heading"><div><p className="eyebrow">Guarded questions</p><h2 id="qa-title"><AIIcon size={19}/>Ask about this saved result</h2></div><span><AIIcon size={11}/>Generated · evidence only</span></div>
    {!enabled && <p>{aiConfigStatus !== "ready" ? "Connecting to the AI service configuration…" : accessLocked ? "Enter the shared AI access token above to ask questions about saved evidence." : "AI questions are currently off. Deterministic results remain fully available."}</p>}
    {enabled && <>
      <p className="qa-intro">Ask about run warnings, classifications, scores, evidence gaps, or therapeutic precedent. Answers use only this saved run and cannot change its classifications or rank.</p>
      <form className="qa-form" onSubmit={(event) => void submitQuestion(event)}>
        <label htmlFor="qa-question">Research question</label>
        <textarea id="qa-question" maxLength={500} rows={3} value={question} placeholder="For example: Why is HTT classified as insufficient data?" onChange={(event) => { setQuestion(event.target.value); resetResult(); }}/>
        <div className="qa-form-meta"><span>{question.length}/500 characters</span><span>Run-wide questions can be asked without selecting a candidate.</span></div>
        <div className="qa-context"><label htmlFor="qa-candidate">Candidate evidence context <small>optional, up to 3</small></label><select id="qa-candidate" value="" disabled={geneSymbols.length >= 3} onChange={(event) => addCandidate(event.target.value)}><option value="">{geneSymbols.length >= 3 ? "Three candidates selected" : "Add a saved candidate…"}</option>{candidates.filter(candidate => !geneSymbols.includes(candidate.gene_symbol)).map(candidate => <option key={candidate.ensembl_id} value={candidate.gene_symbol}>{candidate.gene_symbol} — {candidate.gene_name ?? "Unnamed gene"}</option>)}</select></div>
        {geneSymbols.length > 0 && <div className="qa-chips" aria-label="Selected candidate evidence">{geneSymbols.map(geneSymbol => <button type="button" key={geneSymbol} onClick={() => removeCandidate(geneSymbol)} aria-label={`Remove ${geneSymbol} from question context`}>{geneSymbol}<span aria-hidden="true">×</span></button>)}</div>}
        <p className="qa-privacy"><b>Do not enter patient information.</b> Questions about treatment, dosing, prognosis, or changing the deterministic ranking are refused.</p>
        <div className="qa-actions"><button className="secondary-button" type="submit" disabled={!question.trim() || loading}><AIIcon/>{loading ? "Checking saved evidence…" : "Ask saved evidence"}</button><span>{DISCLAIMER}</span></div>
      </form>
    </>}
    {error && <p className="ai-error" role="alert">{error}</p>}
    {answer?.mode === "unsupported_by_saved_evidence" && <div className="qa-unsupported" role="status"><b>Not supported by this saved run</b><p>{answer.message}</p><small>No AI answer was generated.</small></div>}
    {(answer?.premise_corrections?.length ?? 0) > 0 && <div className="qa-correction" role="status"><b>Question premise corrected</b>{answer?.premise_corrections?.map(correction => <p key={correction}>{correction}</p>)}</div>}
    {(answer?.authoritative_facts?.length ?? 0) > 0 && <section className="qa-facts" aria-labelledby="qa-facts-title"><div className="qa-facts-heading"><h3 id="qa-facts-title">Saved deterministic facts</h3><span>Server generated · not AI</span></div><div className="qa-fact-grid">{answer?.authoritative_facts?.map(fact => <article key={fact.gene_symbol}><div><b>{fact.gene_symbol}</b><span>{fact.final_call}</span></div><dl><div><dt>Overall</dt><dd>{fact.overall_score.toFixed(3)}</dd></div><div><dt>Genetic</dt><dd>{fact.genetic_score.toFixed(3)}</dd></div><div><dt>Evidence</dt><dd>{fact.n_evidence_returned ?? fact.n_evidence ?? "Not returned"}</dd></div><div><dt>Shortlist</dt><dd>{fact.shortlist_position ?? "Not shortlisted"}</dd></div></dl><small>{fact.confidence_tier} · {fact.completeness}{fact.evidence_truncated ? " · truncated" : ""}</small></article>)}</div></section>}
    {answer?.output && <div className="ai-output qa-output" aria-live="polite"><div className="qa-answer-heading"><h3><AIIcon/>{answer.mode === "insufficient_saved_evidence" ? "Insufficient saved evidence" : "Evidence-bound answer"}</h3><span><AIIcon size={11}/>{answer.cached ? "Cached" : "Generated"}</span></div><p className="ai-summary">{answer.output.answer}</p>
      {answer.output.cited_claims.length > 0 && <><h4>Cited claims</h4><AIClaims claims={answer.output.cited_claims}/></>}
      {answer.output.uncertainties.length > 0 && <><h4>Uncertainties</h4><ul>{answer.output.uncertainties.map(item => <li key={item}>{item}</li>)}</ul></>}
      {answer.output.manual_review_steps.length > 0 && <><h4>Manual review</h4><ul>{answer.output.manual_review_steps.map(item => <li key={item}>{item}</li>)}</ul></>}
      {answer.output.what_this_does_not_mean.length > 0 && <><h4>What this does not mean</h4><ul>{answer.output.what_this_does_not_mean.map(item => <li key={item}>{item}</li>)}</ul></>}
      <p className="ai-meta">{answer.model} · sources validated server-side · {answer.selected_gene_symbols.length ? `candidate context: ${answer.selected_gene_symbols.join(", ")}` : "run context"}</p><p className="drawer-disclaimer">{answer.research_use_disclaimer}</p>
    </div>}
  </section>;
}

type ResearchView = "all" | "shortlist" | "novel" | "translational";
type PrecedentFilter = "all" | "approved" | "aso" | "drug" | "none" | "unknown";
type CandidateSort = "rank" | "overall" | "genetic" | "evidence" | "loeuf" | "gene";
type SortDirection = "asc" | "desc";

const VIEW_HELP: Record<ResearchView, string> = {
  all: "No candidate is hidden because a drug or ASO precedent exists.",
  shortlist: "Shows the deterministic review order saved with this run. It is not a treatment ranking.",
  novel: "Shows only targets whose completed drug lookup found no target-level approved drug. Approval may be for another disease; verify the indication manually.",
  translational: "Shows candidates with an approved drug, another drug record, or an ASO/drug/trial precedent.",
};

function hasTranslationalPrecedent(row: Candidate) {
  return row.has_approved_drug === true || (row.n_drugs ?? 0) > 0 || Boolean(row.aso_precedent);
}

function matchesPrecedent(row: Candidate, filter: PrecedentFilter) {
  const unknown = row.has_approved_drug === null || ["not checked", "lookup failed"].includes(row.drug_status.toLowerCase());
  if (filter === "all") return true;
  if (filter === "approved") return row.has_approved_drug === true;
  if (filter === "aso") return Boolean(row.aso_precedent);
  if (filter === "drug") return (row.n_drugs ?? 0) > 0;
  if (filter === "unknown") return unknown;
  return !unknown && !hasTranslationalPrecedent(row);
}

function compareNullable(a: number | string | null, b: number | string | null, direction: SortDirection) {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  const comparison = typeof a === "string" && typeof b === "string" ? a.localeCompare(b) : Number(a) - Number(b);
  return direction === "asc" ? comparison : -comparison;
}

function printFilenamePart(value: string) {
  const normalized = value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  return normalized.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 72) || "report";
}

function openPrintDialog(title: string) {
  const previousTitle = document.title;
  document.title = title;
  const restoreTitle = () => {
    document.title = previousTitle;
    window.removeEventListener("afterprint", restoreTitle);
  };
  window.addEventListener("afterprint", restoreTitle, { once: true });
  window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
    window.print();
    window.setTimeout(restoreTitle, 0);
  }));
}

function Results({ run, candidates, isExample, aiEnabled, aiConfigStatus, aiAccessRequired, aiAccessToken, onRetryAIConfig, onUnlockAI, onLockAI, onReset }: { run: RunRecord; candidates: Candidate[]; isExample: boolean; aiEnabled: boolean; aiConfigStatus: AIConfigStatus; aiAccessRequired: boolean; aiAccessToken: string; onRetryAIConfig: () => void; onUnlockAI: (token: string) => void; onLockAI: () => void; onReset: () => void }) {
  const [query, setQuery] = useState(""); const [track, setTrack] = useState("all");
  const [researchView, setResearchView] = useState<ResearchView>("all");
  const [precedentFilter, setPrecedentFilter] = useState<PrecedentFilter>("all");
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [sort, setSort] = useState<CandidateSort>("rank");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [printMode, setPrintMode] = useState<PrintMode | "candidate">("summary");
  const [candidatePrintExplanation, setCandidatePrintExplanation] = useState<CandidateExplanation | null>(null);
  const [candidateExplanations, setCandidateExplanations] = useState<Record<string, CandidateExplanation>>({});
  const [reportGeneratedAt, setReportGeneratedAt] = useState(() => new Date().toISOString());
  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const [comparisonSelection, setComparisonSelection] = useState<string[]>([]);
  const [comparison, setComparison] = useState<CandidateComparison | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState("");
  const accessLocked = aiEnabled && aiAccessRequired && !aiAccessToken;
  const aiAvailable = aiEnabled && !accessLocked;
  const counts = useMemo(() => Object.fromEntries(TRACKS.slice(1).map(name => [name, candidates.filter(row => row.final_call === name).length])), [candidates]);
  const filtered = useMemo(() => candidates.filter(row => {
    const inView = researchView === "all"
      || (researchView === "shortlist" && row.shortlist_position !== null)
      || (researchView === "novel" && row.has_approved_drug === false)
      || (researchView === "translational" && hasTranslationalPrecedent(row));
    return inView
      && matchesPrecedent(row, precedentFilter)
      && (track === "all" || row.final_call === track)
      && `${row.gene_symbol} ${row.gene_name ?? ""}`.toLowerCase().includes(query.toLowerCase());
  }).sort((a, b) => {
    if (sort === "overall") return compareNullable(a.overall_score, b.overall_score, sortDirection);
    if (sort === "genetic") return compareNullable(a.genetic_score, b.genetic_score, sortDirection);
    if (sort === "evidence") return compareNullable(a.n_evidence_returned, b.n_evidence_returned, sortDirection);
    if (sort === "loeuf") return compareNullable(a.loeuf, b.loeuf, sortDirection);
    if (sort === "gene") return compareNullable(a.gene_symbol, b.gene_symbol, sortDirection);
    return compareNullable(a.shortlist_position, b.shortlist_position, sortDirection)
      || compareNullable(a.overall_score, b.overall_score, "desc");
  }), [candidates, precedentFilter, query, researchView, sort, sortDirection, track]);
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageStart = (safePage - 1) * pageSize;
  const pageEnd = Math.min(pageStart + pageSize, filtered.length);
  const shortlistCount = candidates.filter(row => row.shortlist_position !== null).length;
  const capped = candidates.filter(row => row.evidence_truncated).length;
  async function requestRunSummary() {
    setSummaryLoading(true); setSummaryError("");
    try { setRunSummary(await summarizeRun(run.id, aiAccessToken, isExample)); }
    catch (error) { setSummaryError(error instanceof Error ? error.message : "The run summary could not be generated."); }
    finally { setSummaryLoading(false); }
  }
  function toggleComparison(geneSymbol: string) {
    setComparison(null); setComparisonError("");
    setComparisonSelection(current => current.includes(geneSymbol) ? current.filter(symbol => symbol !== geneSymbol) : current.length < 3 ? [...current, geneSymbol] : current);
  }
  async function requestComparison() {
    if (comparisonSelection.length < 2 || comparisonSelection.length > 3) return;
    setComparisonLoading(true); setComparisonError("");
    try { setComparison(await compareCandidates(run.id, comparisonSelection, aiAccessToken, isExample)); }
    catch (error) { setComparisonError(error instanceof Error ? error.message : "The candidate comparison could not be generated."); }
    finally { setComparisonLoading(false); }
  }
  function printReport(mode: PrintMode) {
    setPrintMode(mode);
    setReportGeneratedAt(new Date().toISOString());
    const disease = printFilenamePart(run.disease_label ?? run.disease_id);
    openPrintDialog(`ASO-Compass_${disease}_${mode}-report_${run.id.slice(0, 8)}`);
  }
  function printCandidate(explanation: CandidateExplanation | null) {
    setCandidatePrintExplanation(explanation);
    setPrintMode("candidate");
    setReportGeneratedAt(new Date().toISOString());
    if (!selected) return;
    const disease = printFilenamePart(run.disease_label ?? run.disease_id);
    const gene = printFilenamePart(selected.gene_symbol);
    openPrintDialog(`ASO-Compass_${disease}_${gene}_candidate-evidence_${run.id.slice(0, 8)}`);
  }

  return <section className={`results-view${selected ? " evidence-open" : ""}`}>
    {printMode === "candidate" && selected
      ? <CandidatePrintReport run={run} candidate={selected} explanation={candidatePrintExplanation} generatedAt={reportGeneratedAt}/>
      : <PrintReport run={run} candidates={candidates} mode={printMode === "candidate" ? "summary" : printMode} generatedAt={reportGeneratedAt} runSummary={runSummary}/>}
    <div className="results-header"><div><p className="eyebrow">{isExample ? "Precomputed example" : "Completed analysis"}</p><h1>{run.disease_label ?? run.disease_id}</h1><p>{run.disease_id} · Engine {run.engine_version} · Open Targets {String(run.upstream_metadata.open_targets_release ?? "release unknown")}</p></div><div className="header-actions"><button className="secondary-button print-report-button" type="button" onClick={() => printReport("summary")}>Print summary</button><button className="secondary-button print-report-button" type="button" onClick={() => printReport("full")}>{runSummary ? "Print full report + AI" : "Print full report"}</button>{!isExample && <><a className="secondary-button" href={exportUrl(run.id, "csv")}>Export CSV</a><a className="secondary-button" href={exportUrl(run.id, "json")}>Export JSON</a></>}<button className="primary-button compact" onClick={onReset}>New analysis</button></div></div>
    {isExample && <p className="example-banner"><b>Offline-ready deterministic example.</b> These versioned results are illustrative and do not refresh with current sources. Optional AI interpretation requires the API and an unlocked access token.</p>}
    {[...new Set(run.warnings.map(normalizeRunWarning))].map((warning) => <p className="notice" key={warning}>{warning}</p>)}
    <div className="metrics"><Metric label="Candidates" value={candidates.length} detail="Passed association filters"/><Metric label="Priority shortlist" value={shortlistCount} detail="Retained by configured shortlist rules"/><Metric label="Evidence capped" value={capped} detail={capped ? "Manual review required" : "No truncated gene records"}/><Metric label="ASO precedent" value={candidates.filter(row => row.aso_precedent).length} detail="Drug or trial source match"/></div>
    {aiConfigStatus !== "ready" && <section className="ai-access-panel" aria-labelledby="ai-connection-title"><div><p className="eyebrow">AI service connection</p><h2 id="ai-connection-title"><AIIcon size={19}/>{aiConfigStatus === "loading" ? "Connecting to AI configuration" : "AI configuration is temporarily unavailable"}</h2><p>{aiConfigStatus === "loading" ? "The API may be waking from an idle state. Deterministic results remain available while the app retries." : "The configuration request did not complete. Retry without reloading the evidence example."}</p></div><button className="secondary-button" type="button" onClick={onRetryAIConfig}>Retry now</button></section>}
    <AIAccessControl enabled={aiEnabled} required={aiAccessRequired} accessToken={aiAccessToken} onUnlock={onUnlockAI} onLock={onLockAI}/>
    <section className={`ai-panel run-summary-panel${runSummary ? " has-print-content" : ""}`} aria-labelledby="run-summary-title"><div className="ai-heading"><div><p className="eyebrow">Optional interpretation</p><h2 id="run-summary-title"><AIIcon size={19}/>AI run summary</h2></div><span><AIIcon size={11}/>Generated · evidence only</span></div>
      {!aiAvailable && <p>{aiConfigStatus !== "ready" ? "Connecting to the AI service configuration…" : accessLocked ? "Enter the shared AI access token above to unlock summaries." : "AI summaries are currently off. Deterministic results remain fully available."}</p>}
      {aiAvailable && !runSummary && <div className="run-summary-intro"><p>Summarize saved track counts, evidence gaps, warnings, and review priorities. The summary cannot change classifications, scores, or shortlist order.</p><button className="secondary-button" onClick={() => void requestRunSummary()} disabled={summaryLoading}><AIIcon/>{summaryLoading ? "Generating summary…" : "Summarize this run"}</button></div>}
      {summaryError && <p className="ai-error" role="alert">{summaryError}</p>}
      {runSummary && <div className="ai-output run-summary-output"><p className="ai-summary">{runSummary.output.overview}</p>
        <div className="run-summary-columns"><div><h4>Key findings</h4><AIClaims claims={runSummary.output.key_findings}/></div><div><h4>Review priorities</h4><AIClaims claims={runSummary.output.review_priorities}/></div></div>
        {runSummary.output.track_breakdown.length > 0 && <><h4>Track breakdown</h4><div className="ai-track-grid">{runSummary.output.track_breakdown.map(item => <article key={item.track}><b>{TRACK_LABEL[item.track] ?? item.track}</b><strong>{item.count}</strong><p>{item.interpretation}</p><small>{item.source_ids.map(sourceId => <span key={sourceId} title={sourceId}>{sourceLabel(sourceId)}</span>)}</small></article>)}</div></>}
        {runSummary.output.evidence_gaps.length > 0 && <><h4>Evidence gaps</h4><AIClaims claims={runSummary.output.evidence_gaps}/></>}
        <div className="run-summary-columns"><div><h4>Limitations</h4><ul>{runSummary.output.limitations.map(item => <li key={item}>{item}</li>)}</ul></div><div><h4>What this does not mean</h4><ul>{runSummary.output.what_this_does_not_mean.map(item => <li key={item}>{item}</li>)}</ul></div></div>
        <p className="ai-meta">{runSummary.cached ? "Reused identical-input cache" : "New summary"} · {runSummary.model} · sources validated server-side</p><p className="drawer-disclaimer">{runSummary.research_use_disclaimer}</p>
      </div>}
    </section>
    <AIQuestionPanel runId={run.id} candidates={candidates} enabled={aiAvailable} aiConfigStatus={aiConfigStatus} accessLocked={accessLocked} accessToken={aiAccessToken} isExample={isExample}/>
    <div className="visual-grid"><article className="panel"><div className="panel-title"><div><p className="eyebrow">Mechanism landscape</p><h2>Candidate tracks</h2></div><span>{candidates.length} genes</span></div><div className="track-bars">{TRACKS.slice(1).map(name => <button key={name} onClick={() => setTrack(name)}><span>{TRACK_LABEL[name]}</span><i><em className={`track-${name.replace(/[^a-z]/g, "-")}`} style={{ width: `${Math.max(3, ((counts[name] ?? 0) / candidates.length) * 100)}%` }} /></i><b>{counts[name] ?? 0}</b></button>)}</div></article><article className="panel"><div className="panel-title"><div><p className="eyebrow">Association landscape</p><h2>Evidence scores</h2></div><span>Click a point</span></div><ScorePlot candidates={candidates} onSelect={setSelected}/></article></div>
    <article className="table-panel"><div className="table-tools"><div><p className="eyebrow">Candidate explorer</p><h2>Trace every classification</h2></div><div className="filters">
      <label><span>Research view</span><select aria-label="Research view" value={researchView} onChange={(e) => { setResearchView(e.target.value as ResearchView); setPage(1); }}><option value="all">All evidence</option><option value="shortlist">Saved priority shortlist</option><option value="novel">Novel-target discovery</option><option value="translational">Translational precedent</option></select></label>
      <label><span>Precedent</span><select aria-label="Filter therapeutic precedent" value={precedentFilter} onChange={(e) => { setPrecedentFilter(e.target.value as PrecedentFilter); setPage(1); }}><option value="all">All precedent statuses</option><option value="approved">Target-level approved drug</option><option value="aso">ASO / trial precedent</option><option value="drug">Any drug record</option><option value="none">No known precedent</option><option value="unknown">Drug evidence unknown</option></select></label>
      <label><span>Track</span><select aria-label="Filter track" value={track} onChange={(e) => { setTrack(e.target.value); setPage(1); }}>{TRACKS.map(name => <option key={name} value={name}>{name === "all" ? "All tracks" : TRACK_LABEL[name]}</option>)}</select></label>
      <label><span>Search</span><input aria-label="Search candidates" type="search" placeholder="Gene symbol or name…" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }}/></label>
      <label><span>Sort by</span><select aria-label="Sort candidates" value={sort} onChange={(e) => { setSort(e.target.value as CandidateSort); setPage(1); }}><option value="rank">Shortlist rank</option><option value="overall">Overall score</option><option value="genetic">Genetic score</option><option value="evidence">Returned evidence</option><option value="loeuf">LOEUF</option><option value="gene">Gene symbol</option></select></label>
      <button className="sort-direction" type="button" aria-label={`Sort ${sortDirection === "asc" ? "descending" : "ascending"}`} onClick={() => { setSortDirection(current => current === "asc" ? "desc" : "asc"); setPage(1); }}>{sortDirection === "asc" ? "↑ Asc" : "↓ Desc"}</button>
    </div></div>
      <p className="view-explainer"><b>{researchView === "all" ? "All evidence" : researchView === "shortlist" ? "Saved priority shortlist" : researchView === "novel" ? "Novel-target discovery" : "Translational precedent"}:</b> {VIEW_HELP[researchView]}</p>
      {aiAvailable && <div className="comparison-toolbar"><div><b><AIIcon/>Compare saved evidence</b><span>{comparisonSelection.length ? `${comparisonSelection.join(", ")} selected` : "Select two or three candidates below"}</span></div><div><button className="text-button" type="button" disabled={!comparisonSelection.length} onClick={() => { setComparisonSelection([]); setComparison(null); setComparisonError(""); }}>Clear</button><button className="secondary-button" type="button" disabled={comparisonSelection.length < 2 || comparisonLoading} onClick={() => void requestComparison()}><AIIcon/>{comparisonLoading ? "Comparing…" : `Compare selected (${comparisonSelection.length})`}</button></div></div>}
      {comparisonError && <p className="ai-error comparison-error" role="alert">{comparisonError}</p>}
      <div className="table-wrap"><table><thead><tr>{aiAvailable && <th className="comparison-select-cell"><span className="sr-only">Compare</span></th>}<th>Gene</th><th>Track</th><th>Overall</th><th>Genetic</th><th>Evidence</th><th>LOEUF</th><th>Therapeutic precedent</th><th className="candidate-actions-cell"><span className="sr-only">Details</span></th></tr></thead><tbody>{filtered.map((row, index) => { const selectedForComparison = comparisonSelection.includes(row.gene_symbol); const outsidePage = index < pageStart || index >= pageEnd; return <tr key={row.ensembl_id} className={`${selectedForComparison ? "comparison-selected " : ""}${outsidePage ? "page-hidden" : ""}`.trim()}>{aiAvailable && <td className="comparison-select-cell"><input type="checkbox" aria-label={`Select ${row.gene_symbol} for comparison`} checked={selectedForComparison} disabled={!selectedForComparison && comparisonSelection.length >= 3} onChange={() => toggleComparison(row.gene_symbol)}/></td>}<td><b>{row.gene_symbol}</b><small>{row.gene_name}</small></td><td><span className={`track-badge track-${row.final_call.replace(/[^a-z]/g, "-")}`}>{TRACK_LABEL[row.final_call]}</span></td><td>{row.overall_score.toFixed(3)}</td><td>{row.genetic_score.toFixed(3)}</td><td>{row.evidence_truncated ? <span className="status-warn">Capped</span> : row.n_evidence === null ? "Not checked" : `${row.n_evidence_returned}/${row.n_evidence}`}</td><td>{row.loeuf?.toFixed(2) ?? "—"}</td><td><span className={row.has_approved_drug ? "precedent-approved" : ""}>{row.drug_status}</span>{row.aso_precedent && <small>ASO / trial precedent</small>}</td><td className="candidate-actions-cell"><button className="row-button" onClick={() => setSelected(row)} aria-label={`View evidence for ${row.gene_symbol}`}>→</button></td></tr>;})}</tbody></table>{filtered.length === 0 && <p className="empty">No candidates match these filters.</p>}</div>
      {filtered.length > 0 && <div className="pagination"><span>Showing {pageStart + 1}–{pageEnd} of {filtered.length}</span><label>Rows per page <select aria-label="Rows per page" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}><option value="10">10</option><option value="25">25</option><option value="50">50</option><option value="100">100</option></select></label><div><button type="button" onClick={() => setPage(1)} disabled={safePage === 1} aria-label="First page">«</button><button type="button" onClick={() => setPage(current => Math.max(1, current - 1))} disabled={safePage === 1}>Previous</button><span>Page {safePage} of {totalPages}</span><button type="button" onClick={() => setPage(current => Math.min(totalPages, current + 1))} disabled={safePage === totalPages}>Next</button><button type="button" onClick={() => setPage(totalPages)} disabled={safePage === totalPages} aria-label="Last page">»</button></div></div>}
    </article>
    {comparison && <section className="ai-panel comparison-panel" aria-labelledby="comparison-title"><div className="ai-heading"><div><p className="eyebrow">Optional interpretation</p><h2 id="comparison-title"><AIIcon size={19}/>Evidence comparison: {comparison.compared_gene_symbols.join(" · ")}</h2></div><span><AIIcon size={11}/>Generated · no ranking</span></div><div className="ai-output"><p className="ai-summary">{comparison.output.overview}</p>
      <div className="comparison-profiles">{comparison.output.candidate_summaries.map(item => <article key={item.gene_symbol}><h3>{item.gene_symbol}</h3><p>{item.evidence_summary}</p><small>{item.source_ids.map(sourceId => <b key={sourceId} title={sourceId}>{sourceLabel(sourceId)}</b>)}</small></article>)}</div>
      {comparison.output.key_differences.length > 0 && <><h4>Key differences</h4><div className="comparison-differences">{comparison.output.key_differences.map(item => <article key={item.dimension}><b>{item.dimension}</b><p>{item.explanation}</p><small>{item.source_ids.map(sourceId => <span key={sourceId} title={sourceId}>{sourceLabel(sourceId)}</span>)}</small></article>)}</div></>}
      <div className="run-summary-columns"><div><h4>Shared features</h4><AIClaims claims={comparison.output.shared_features}/></div><div><h4>Evidence gaps</h4><AIClaims claims={comparison.output.evidence_gaps}/></div></div>
      <h4>Review priorities</h4><AIClaims claims={comparison.output.review_priorities}/>
      <div className="run-summary-columns"><div><h4>Limitations</h4><ul>{comparison.output.limitations.map(item => <li key={item}>{item}</li>)}</ul></div><div><h4>What this does not mean</h4><ul>{comparison.output.what_this_does_not_mean.map(item => <li key={item}>{item}</li>)}</ul></div></div>
      <p className="ai-meta">{comparison.cached ? "Reused identical-input cache" : "New comparison"} · {comparison.model} · selected candidates and sources validated server-side</p><p className="drawer-disclaimer">{comparison.research_use_disclaimer}</p>
    </div></section>}
    <Glossary />{selected && <CandidateDrawer key={selected.ensembl_id} row={selected} runId={run.id} aiEnabled={aiAvailable} aiConfigStatus={aiConfigStatus} accessLocked={accessLocked} accessToken={aiAccessToken} isExample={isExample} explanation={candidateExplanations[selected.ensembl_id] ?? null} onExplanationChange={(explanation) => setCandidateExplanations(current => ({ ...current, [selected.ensembl_id]: explanation }))} onPrint={printCandidate} onClose={() => setSelected(null)}/>}<p className="persistent-disclaimer">{DISCLAIMER}</p>
  </section>;
}

function Glossary() {
  const entries = [["LOEUF","A population constraint measure. Lower values suggest less tolerance for loss-of-function variation."],["G2P","Gene2Phenotype annotations that can provide mechanism and inheritance evidence."],["Modifier","An association without enough directional variant evidence to infer knockdown or upregulation."],["ASO precedent","A target-linked oligonucleotide drug or text-matched interventional trial that still requires manual confirmation."]];
  return <section className="glossary"><p className="eyebrow">Educational glossary</p><h2>Read the evidence, not just the rank</h2><div className="glossary-cards">{entries.map(([term, definition]) => <details key={term}><summary>{term}<span>+</span></summary><p>{definition}</p></details>)}</div><div className="print-glossary" aria-hidden="true">{entries.map(([term, definition]) => <article key={term}><b>{term}</b><p>{definition}</p></article>)}</div></section>;
}

export default function App() {
  const [view, setView] = useState<"analyze" | "learn">("analyze");
  const [run, setRun] = useState<RunRecord | null>(null); const [events, setEvents] = useState<RunEvent[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]); const [example, setExample] = useState(false);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiAccessRequired, setAiAccessRequired] = useState(false);
  const [aiConfigStatus, setAiConfigStatus] = useState<AIConfigStatus>("loading");
  const [aiAccessToken, setAiAccessToken] = useState(() => sessionStorage.getItem(AI_ACCESS_STORAGE_KEY) ?? "");
  const runId = run?.id;
  const runStatus = run?.status;

  const refreshAIConfig = useCallback(async () => {
    try {
      const config = await getPublicConfig();
      setAiEnabled(config.ai_enabled);
      setAiAccessRequired(config.ai_access_required ?? false);
      setAiConfigStatus("ready");
    } catch {
      setAiEnabled(false);
      setAiAccessRequired(false);
      setAiConfigStatus("error");
    }
  }, []);

  useEffect(() => {
    const configTimer = window.setTimeout(() => void refreshAIConfig(), 0);
    const saved = localStorage.getItem("aso-compass-run");
    if (saved) {
      void (async () => {
        try {
          const restored = await getRun(saved);
          setRun(restored);
          setEvents(await getEvents(saved));
          if (restored.status === "succeeded") setCandidates(await getCandidates(saved));
        } catch {
          localStorage.removeItem("aso-compass-run");
        }
      })();
    }
    return () => window.clearTimeout(configTimer);
  }, [refreshAIConfig]);

  useEffect(() => { if (!runId || !runStatus || example || !["queued", "running"].includes(runStatus)) return;
    const poll = async () => { try { const [next, nextEvents] = await Promise.all([getRun(runId), getEvents(runId)]); setRun(next); setEvents(nextEvents); if (next.status === "succeeded") setCandidates(await getCandidates(next.id)); } catch { /* transient cold start */ } };
    void poll(); const timer = window.setInterval(() => void poll(), 2500); return () => window.clearInterval(timer);
  }, [runId, runStatus, example]);

  async function loadExample() { const response = await fetch("/examples/als-v4.1.json"); const bundle = await response.json() as ExampleBundle; setRun(bundle.run); setCandidates(bundle.candidates); setEvents(bundle.events); setExample(true); setView("analyze"); }
  function reset() { setRun(null); setCandidates([]); setEvents([]); setExample(false); localStorage.removeItem("aso-compass-run"); }
  function unlockAI(token: string) { sessionStorage.setItem(AI_ACCESS_STORAGE_KEY, token); setAiAccessToken(token); }
  function lockAI() { sessionStorage.removeItem(AI_ACCESS_STORAGE_KEY); setAiAccessToken(""); }
  function retryAIConfig() { setAiConfigStatus("loading"); void refreshAIConfig(); }
  let content = <RunForm onCreated={(created) => { setRun(created); setExample(false); }} onExample={() => void loadExample()} />;
  if (run && ["queued", "running"].includes(run.status)) content = <Progress run={run} events={events} onReset={reset}/>;
  if (run?.status === "succeeded" && candidates.length) content = <Results run={run} candidates={candidates} isExample={example} aiEnabled={aiEnabled} aiConfigStatus={aiConfigStatus} aiAccessRequired={aiAccessRequired} aiAccessToken={aiAccessToken} onRetryAIConfig={retryAIConfig} onUnlockAI={unlockAI} onLockAI={lockAI} onReset={reset}/>;
  if (run?.status === "failed") content = <section className="progress-view"><p className="eyebrow">Analysis stopped</p><h1>The run could not be completed.</h1><p>{run.error_message}</p><button className="primary-button compact" onClick={reset}>Start again</button><button className="text-button" onClick={() => void loadExample()}>Open the example instead →</button></section>;
  return <><Header view={view} onView={setView}/>{view === "learn" ? <Learn disclaimer={DISCLAIMER} onExample={() => void loadExample()}/> : <main id="main">{content}</main>}<footer><span><b>ASO Compass</b> · Deterministic evidence synthesis · <a href="https://github.com/Hanhj2016/aso-compass" target="_blank" rel="noreferrer">Deployed automatically from GitHub ↗</a></span><span>{DISCLAIMER}</span></footer></>;
}
