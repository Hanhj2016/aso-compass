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
    <button className="text-button case-back" type="button" onClick={onBack}>← Back to Case Studies</button>
    <header className="case-study-hero">
      <div>
        <p className="eyebrow">Curated case study · {caseStudy.fixture_version}</p>
        <h1>{caseStudy.title}</h1>
        <p className="lede">A source-bounded analysis of a versioned deterministic result. Examine the evidence, defend an interpretation, and keep every conclusion within the recorded limitations.</p>
        <div className="case-meta"><span>{caseStudy.disease_id}</span><span>Engine {caseStudy.engine_version}</span><span>Open Targets {caseStudy.source_releases.open_targets ?? "release not recorded"}</span><span>Versioned fixture</span></div>
      </div>
      <aside aria-labelledby="case-question-title"><p className="eyebrow">Research question</p><h2 id="case-question-title">Question guiding this case</h2><p>{caseStudy.research_question}</p></aside>
    </header>

    <section className="case-portfolio-context" aria-label="Case study capabilities and learning objectives">
      <div><h2 className="eyebrow">Capabilities demonstrated</h2><div className="case-capability-tags">{caseStudy.capabilities_demonstrated.map(capability => <span key={capability}>{capability}</span>)}</div></div>
      <div><h2 className="eyebrow">Learning objectives</h2><ul>{caseStudy.learning_objectives.map(objective => <li key={objective}>{objective}</li>)}</ul></div>
    </section>

    {error && <section className="error" role="alert"><b>Case unavailable.</b> {error}</section>}
    {!bundle && !error && <section className="case-loading" aria-live="polite">Loading the frozen teaching record…</section>}

    {bundle && <>
      <section className="case-study-section" aria-labelledby="case-compare-title">
        <p className="eyebrow">Candidate comparison</p><h2 id="case-compare-title">{candidates.length} candidates, {candidates.length} different review questions</h2>
        <p className="learn-intro">These records are copied unchanged from a completed, versioned run for source-bounded analysis. Their inclusion is not a therapeutic ranking.</p>
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
        <div><p className="eyebrow">Evidence provenance</p><h2 id="case-evidence-title">Follow each claim to its source</h2><p className="learn-intro">Open every source and distinguish supporting context from claims it cannot establish.</p><EvidenceSourceMap candidate={selected}/></div>
        <div><p className="eyebrow">Source interpretation</p><h2>Check the ClinVar boundary</h2><p className="learn-intro">{hasClinVarMetadata ? "Use the retained review, conflict, date, and condition context without treating an aggregate label as a complete variant interpretation." : "This frozen record demonstrates an important missingness lesson: detailed interpretation metadata was not retained."}</p><ClinVarLearningCheckpoint candidate={selected}/></div>
      </section>}

      <section className="case-study-section case-conclusions" aria-labelledby="case-conclusions-title">
        <p className="eyebrow">Conclusion and limitations</p><h2 id="case-conclusions-title">Interpretation summary</h2>
        <div className="case-conclusion-grid">
          <article><h3>Interpretation</h3><p>{caseStudy.debrief}</p><ul>{caseStudy.debrief_points.map(point => <li key={point}>{point}</li>)}</ul></article>
          <article><h3>Important limitations</h3><ul>{caseStudy.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}</ul></article>
          <article><h3>Next research questions</h3><ol>{caseStudy.next_research_questions.map(question => <li key={question}>{question}</li>)}</ol></article>
        </div>
        <aside className="case-workspace-cta"><div><h3>Examine the complete saved evidence</h3><p>Review candidate records, compare deterministic classifications, inspect source provenance, and explore optional evidence-bound AI explanations.</p></div><button className="primary-button compact" type="button" onClick={onOpenResults}>Open evidence workspace →</button></aside>
        <p className="case-provenance"><b>Evidence provenance:</b> candidate records were frozen from a completed ASO Compass run and selected for source-bounded educational analysis by {caseStudy.reviewer}. This is not a clinical interpretation.</p>
      </section>

      <section className="case-study-section case-references" aria-labelledby="case-references-title"><p className="eyebrow">Biological context and references</p><h2 id="case-references-title">Check the biological premise outside the heuristic</h2><p className="learn-intro">The frozen application result and these external references answer different questions. Follow the primary records before drawing a biological conclusion.</p><ul>{caseStudy.references.map(reference => <li key={reference.url}><a href={reference.url} target="_blank" rel="noreferrer">{reference.label} ↗</a></li>)}</ul>{caseStudy.candidate_count_exception && <p className="notice"><b>Reviewed candidate-count exception:</b> {caseStudy.candidate_count_exception}</p>}</section>
    </>}
    <p className="persistent-disclaimer">{disclaimer}</p>
  </main>;
}
