import { useEffect, useMemo, useState } from "react";
import { ClinVarLearningCheckpoint, EvidenceSourceMap, MechanismHelp, TermHelp } from "./education";
import type { Candidate, EducationalCase, ExampleBundle } from "./types";

const TRACK_LABELS: Record<string, string> = {
  knockdown: "Knockdown",
  "splice/upregulation": "Splice / upregulation",
  ambiguous: "Ambiguous",
  modifier: "Modifier",
  "insufficient data": "Insufficient data",
};

function valueOrUnknown(value: number | null | undefined, digits = 3) {
  return value === null || value === undefined ? "Not returned" : value.toFixed(digits);
}

export default function CaseStudyPage({ caseStudy, disclaimer, onBack, onOpenResults }: {
  caseStudy: EducationalCase;
  disclaimer: string;
  onBack: () => void;
  onOpenResults: () => void;
}) {
  const [bundle, setBundle] = useState<ExampleBundle | null>(null);
  const [error, setError] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState(caseStudy.teaching_candidates[0] ?? "");

  useEffect(() => {
    if (caseStudy.status !== "published" || !caseStudy.fixture_file) return;
    const controller = new AbortController();
    void fetch(`/examples/${caseStudy.fixture_file}`, { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error("The reviewed case fixture could not be loaded.");
        return response.json() as Promise<ExampleBundle>;
      })
      .then(setBundle)
      .catch(reason => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "The reviewed case fixture could not be loaded.");
      });
    return () => controller.abort();
  }, [caseStudy]);

  const candidates = useMemo(() => {
    if (!bundle) return [];
    const bySymbol = new Map(bundle.candidates.map(candidate => [candidate.gene_symbol, candidate]));
    return caseStudy.teaching_candidates.map(symbol => bySymbol.get(symbol)).filter((candidate): candidate is Candidate => Boolean(candidate));
  }, [bundle, caseStudy.teaching_candidates]);
  const selected = candidates.find(candidate => candidate.gene_symbol === selectedSymbol) ?? candidates[0];
  const selectedLesson = caseStudy.candidate_lessons.find(lesson => lesson.gene_symbol === selected?.gene_symbol);
  const hasClinVarMetadata = selected?.clinvar_interpretation?.metadata_status === "available" || selected?.clinvar_interpretation?.metadata_status === "partial";

  return <main id="main" className="case-study-page">
    <button className="text-button case-back" type="button" onClick={onBack}>← Back to Learn</button>
    <header className="case-study-hero">
      <div>
        <p className="eyebrow">Published educational case · {caseStudy.fixture_version}</p>
        <h1>{caseStudy.title}</h1>
        <p className="lede">A guided exercise using a frozen deterministic result. Read the saved evidence before opening optional AI interpretation.</p>
        <div className="case-meta"><span>{caseStudy.disease_id}</span><span>Engine {caseStudy.engine_version}</span><span>Open Targets {caseStudy.source_releases.open_targets ?? "release not recorded"}</span><span>Versioned fixture</span></div>
      </div>
      <aside aria-labelledby="case-objectives-title"><h2 id="case-objectives-title">Learning objectives</h2><ol>{caseStudy.learning_objectives.map(objective => <li key={objective}>{objective}</li>)}</ol></aside>
    </header>

    {error && <section className="error" role="alert"><b>Case unavailable.</b> {error}</section>}
    {!bundle && !error && <section className="case-loading" aria-live="polite">Loading the frozen teaching record…</section>}

    {bundle && <>
      <section className="case-study-section" aria-labelledby="case-compare-title">
        <p className="eyebrow">Step 1 · Compare</p><h2 id="case-compare-title">{candidates.length} candidates, {candidates.length} different review questions</h2>
        <p className="learn-intro">These candidates are copied unchanged from a completed, versioned run for teaching. Their inclusion is not a therapeutic ranking.</p>
        <div className="case-candidate-tabs" role="group" aria-label="Teaching candidates">{candidates.map(candidate => <button key={candidate.gene_symbol} type="button" aria-pressed={selected?.gene_symbol === candidate.gene_symbol} onClick={() => setSelectedSymbol(candidate.gene_symbol)}><b>{candidate.gene_symbol}</b><span>{TRACK_LABELS[candidate.final_call] ?? candidate.final_call}</span></button>)}</div>

        {selected && <article className="case-candidate-focus">
          <header><div><p className="eyebrow">Saved candidate record</p><h2>{selected.gene_symbol}</h2><p>{selected.gene_name}</p></div><span className={`track-badge track-${selected.final_call.replace(/[^a-z]/g, "-")}`}>{TRACK_LABELS[selected.final_call] ?? selected.final_call}</span></header>
          <div className="case-fact-grid">
            <div><span>Deterministic source</span><b>{selected.call_source}</b></div>
            <div><span>Overall association</span><b>{selected.overall_score.toFixed(3)}</b></div>
            <div><span>Genetic association</span><b>{selected.genetic_score.toFixed(3)}</b></div>
            <div><span><TermHelp term="loeuf"/></span><b>{valueOrUnknown(selected.loeuf)}</b></div>
            <div><span>Evidence returned</span><b>{selected.n_evidence === null ? "Not checked" : `${selected.n_evidence_returned ?? 0}/${selected.n_evidence}`}</b></div>
            <div><span>G2P mechanism</span><b><MechanismHelp value={selected.g2p_mech}/></b></div>
            <div><span>Therapeutic precedent</span><b>{selected.drug_status || "None returned"}</b></div>
          </div>
          {selected.flag && <p className="notice"><b>Review flag:</b> {selected.flag}</p>}
          <details className="case-learning-prompt"><summary>{selectedLesson?.question ?? "What should be reviewed next?"}</summary><p>{selectedLesson?.answer ?? selected.note}</p></details>
        </article>}
      </section>

      {selected && <section className="case-study-section case-evidence-lab" aria-labelledby="case-evidence-title">
        <div><p className="eyebrow">Step 2 · Trace</p><h2 id="case-evidence-title">Follow each claim to its source</h2><p className="learn-intro">Open every source and distinguish supporting context from claims it cannot establish.</p><EvidenceSourceMap candidate={selected}/></div>
        <div><p className="eyebrow">Step 3 · Interpret</p><h2>Check the ClinVar boundary</h2><p className="learn-intro">{hasClinVarMetadata ? "Use the retained review, conflict, date, and condition context without treating an aggregate label as a complete variant interpretation." : "This frozen record demonstrates an important missingness lesson: detailed interpretation metadata was not retained."}</p><ClinVarLearningCheckpoint candidate={selected}/></div>
      </section>}

      <section className="case-study-section case-debrief" aria-labelledby="case-debrief-title">
        <div><p className="eyebrow">Step 4 · Debrief</p><h2 id="case-debrief-title">What this case should leave you with</h2><p>{caseStudy.debrief}</p><ul>{caseStudy.debrief_points.map(point => <li key={point}>{point}</li>)}</ul></div>
        <aside><h3>Continue with the frozen excerpt</h3><p>Open the selected candidate records, comparison tool, printable reports, and optional evidence-bound AI.</p><button className="primary-button compact" type="button" onClick={onOpenResults}>Open saved teaching result →</button><small>Published by {caseStudy.reviewer}. Candidate selection is educational, not clinical.</small></aside>
      </section>

      <section className="case-study-section case-references" aria-labelledby="case-references-title"><p className="eyebrow">Primary reading</p><h2 id="case-references-title">Check the biological premise outside the heuristic</h2><p className="learn-intro">The frozen application result and these external references answer different questions. Follow the primary records before drawing a biological conclusion.</p><ul>{caseStudy.references.map(reference => <li key={reference.url}><a href={reference.url} target="_blank" rel="noreferrer">{reference.label} ↗</a></li>)}</ul>{caseStudy.candidate_count_exception && <p className="notice"><b>Reviewed candidate-count exception:</b> {caseStudy.candidate_count_exception}</p>}</section>
    </>}
    <p className="persistent-disclaimer">{disclaimer}</p>
  </main>;
}
