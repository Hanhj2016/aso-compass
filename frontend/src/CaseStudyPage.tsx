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

const CANDIDATE_PROMPTS: Record<string, { question: string; answer: string }> = {
  SOD1: {
    question: "What does the recorded therapeutic precedent add—and what does it not prove?",
    answer: "The saved fixture records approved tofersen and target-linked trial context. That makes SOD1 useful for learning about precedent, but it does not turn this educational record into treatment advice or establish efficacy for another candidate or disease context.",
  },
  TARDBP: {
    question: "Why should the knockdown track and the LOEUF warning be read together?",
    answer: "The saved G2P and ClinVar evidence supports the deterministic knockdown direction, while the low LOEUF and review flag warn that reducing normal function may be risky. Direction and safety are different questions.",
  },
  FUS: {
    question: "Why does capped evidence require manual review even when a track is assigned?",
    answer: "Only 500 of 542 reported records were retained in this frozen run. The deterministic G2P track remains saved, but the observed variant mixture is incomplete and should not be treated as the complete ClinVar record set.",
  },
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
        <p className="eyebrow">Step 1 · Compare</p><h2 id="case-compare-title">Three candidates, three different review questions</h2>
        <p className="learn-intro">These candidates are selected from the existing versioned ALS fixture for teaching. Their inclusion is not a therapeutic ranking.</p>
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
          <details className="case-learning-prompt"><summary>{CANDIDATE_PROMPTS[selected.gene_symbol]?.question ?? "What should be reviewed next?"}</summary><p>{CANDIDATE_PROMPTS[selected.gene_symbol]?.answer ?? selected.note}</p></details>
        </article>}
      </section>

      {selected && <section className="case-study-section case-evidence-lab" aria-labelledby="case-evidence-title">
        <div><p className="eyebrow">Step 2 · Trace</p><h2 id="case-evidence-title">Follow each claim to its source</h2><p className="learn-intro">Open every source and distinguish supporting context from claims it cannot establish.</p><EvidenceSourceMap candidate={selected}/></div>
        <div><p className="eyebrow">Step 3 · Interpret</p><h2>Check the ClinVar boundary</h2><p className="learn-intro">This older frozen fixture demonstrates an important missingness lesson: detailed interpretation metadata was not retained.</p><ClinVarLearningCheckpoint candidate={selected}/></div>
      </section>}

      <section className="case-study-section case-debrief" aria-labelledby="case-debrief-title">
        <div><p className="eyebrow">Step 4 · Debrief</p><h2 id="case-debrief-title">What this case should leave you with</h2><p>{caseStudy.debrief}</p><ul><li>SOD1 demonstrates therapeutic precedent without turning precedent into a recommendation.</li><li>TARDBP demonstrates why direction and population-constraint safety context must be read separately.</li><li>FUS demonstrates why a saved track does not remove the need to review capped evidence.</li></ul></div>
        <aside><h3>Continue with the complete record</h3><p>Open all six frozen candidates, the comparison tool, printable reports, and optional evidence-bound AI.</p><button className="primary-button compact" type="button" onClick={onOpenResults}>Open full saved result →</button><small>Published by {caseStudy.reviewer}. Candidate selection is educational, not clinical.</small></aside>
      </section>
    </>}
    <p className="persistent-disclaimer">{disclaimer}</p>
  </main>;
}
