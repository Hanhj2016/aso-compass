import { EDUCATIONAL_CASES } from "./caseStudies";
import { TermHelp } from "./education";

type LearnProps = {
  disclaimer: string;
  onExample: () => void;
  onCase: (slug: string) => void;
  onResumeSaved?: () => void;
};

const COPY = {
  en: {
    eyebrow: "Capability-guided learning",
    title: "Understand why a candidate was classified—and what the evidence cannot prove.",
    intro: "ASO Compass brings disease association, mechanism, constraint, variant, and therapeutic-precedent evidence into one traceable research view. Use it to compare candidates, inspect uncertainty, and learn how evidence supports—or fails to support—an intervention direction.",
    start: "Open the guided ALS example",
    capabilitiesEyebrow: "Core application capabilities",
    capabilitiesTitle: "What ASO Compass helps you investigate",
    capabilitiesIntro: "Start with the scientific questions the application can help you examine. The workflow that assembles the result is supporting context, not the main lesson.",
    capabilities: [
      ["Synthesize target evidence", "Bring association, variant, mechanism, constraint, drug, and trial context together without treating any one source as a complete answer."],
      ["Interpret mechanism direction", "Use visible deterministic rules to distinguish knockdown, splice/upregulation, ambiguous, modifier, and insufficient-data tracks."],
      ["Compare candidates", "Examine candidates side by side without allowing therapeutic precedent or a single high score to silently decide the ranking."],
      ["Audit evidence completeness", "See missing, capped, conflicting, or unreturned evidence so that absence and truncation are not mistaken for negative biology."],
      ["Trace claims to sources", "Open the evidence-source map and primary records to learn what each source can support—and what it cannot establish."],
      ["Ask bounded AI questions", "Generate explanations from saved evidence while preserving deterministic classifications, warnings, citations, and shortlist order."],
    ],
    boundaryTitle: "Four boundaries to remember",
    boundaries: [
      ["Association is not causation", "A score says that public evidence links a gene to a disease. It does not prove that changing the gene will help."],
      ["A track is not a treatment", "A track is a research direction produced by visible rules—not a recommendation for a patient, dose, or therapy."],
      ["Missing is not negative", "A failed, capped, or empty lookup cannot be interpreted as evidence that the biology is absent."],
      ["AI explains; it does not decide", "Generated text can summarize saved evidence, but it cannot change classifications, scores, shortlist order, or warnings."],
    ],
    pipelineTitle: "How a result is assembled",
    pipelineIntro: "This operational flow is useful when you need to audit provenance or diagnose missing data. It is secondary to interpreting the scientific evidence shown above.",
    pipeline: [
      ["01", "Disease query", "Choose a disease or phenotype identifier. The identifier anchors the analysis to an ontology record."],
      ["02", "Association", "Open Targets supplies genes and association scores that pass the configured filters."],
      ["03", "Enrichment", "ClinVar/EVA, Gene2Phenotype, constraint, drug, and trial sources add mechanism and context."],
      ["04", "Rule engine", "Deterministic precedence and thresholds assign exactly one of five tracks. This is not a machine-learned prediction."],
      ["05", "Human review", "The interface keeps source links, missingness, caps, warnings, and uncertainty next to each result."],
    ],
    tracksEyebrow: "Deterministic outputs",
    tracksTitle: "The five research tracks",
    means: "What it means here",
    notMeans: "What it does not establish",
    tracks: [
      ["Knockdown", "Enough classified records were returned and the loss-of-function fraction is at or below 0.25.", "It does not prove toxic gain of function or that knockdown is safe or effective."],
      ["Splice / upregulation", "Enough records were returned and the loss-of-function fraction is at or above 0.60.", "It does not prove that restoring expression is technically feasible or safe."],
      ["Ambiguous", "The loss-of-function fraction lies between the directional thresholds.", "It is not a tie-breaker or a weaker form of another track."],
      ["Modifier", "Association exists, but returned evidence does not provide a clear directional mechanism.", "It does not mean the gene is unimportant or unrelated to disease."],
      ["Insufficient data", "Fewer than five classified loss-of-function plus missense records were available to the heuristic.", "It is not a negative finding about the gene."],
    ],
    precedence: "Mechanism precedence is: reviewed manual override → Gene2Phenotype → ClinVar heuristic → modifier. LOEUF adds safety context; it does not select the mechanism track.",
    readEyebrow: "Candidate evidence",
    readTitle: "Read a candidate in this order",
    readSteps: [
      ["Final track", "Start with the saved deterministic call, its decision source, and confidence explanation."],
      ["Association scores", "These describe strength of linkage in the retrieved source—not probability of therapeutic success."],
      ["Mechanism evidence", "Compare ClinVar/EVA patterns with Gene2Phenotype mechanism and inheritance fields."],
      ["Evidence count", "Check how many records were expected and returned, and whether enrichment was capped."],
      ["LOEUF", "Use it as constraint and safety context. Lower values indicate less tolerance for loss-of-function variation."],
      ["Therapeutic precedent", "A drug or trial connection supplies context, but may concern another indication and requires manual confirmation."],
      ["Warnings and sources", "Finish with missingness, truncation, retrieval dates, and primary-record links."],
    ],
    exampleEyebrow: "Hands-on walkthrough",
    exampleTitle: "Use the bundled ALS result",
    exampleIntro: "Open the offline example and inspect SOD1, TARDBP, and FUS. For each candidate, answer the same questions before reading any AI explanation.",
    questions: [
      "What is the saved final track?",
      "Which deterministic source selected it?",
      "How many evidence records were returned, and were they capped?",
      "What do the association scores say—and not say?",
      "Is there drug or trial precedent?",
      "Which uncertainty still requires human review?",
    ],
    casesEyebrow: "Curated case series",
    casesTitle: "Build interpretation skills one mechanism at a time",
    casesIntro: "Each module has a distinct learning objective. Only scientifically reviewed, frozen evidence fixtures become runnable; pending modules are a curriculum roadmap, not candidate results.",
    aiEyebrow: "Optional interpretation",
    aiTitle: "Where the LLM fits",
    aiFlow: ["Saved deterministic record", "Bounded evidence packet", "Structured model output", "Server-side fact and citation validation", "Separately labeled explanation"],
    aiText: "Use AI after you have read the deterministic record. A good explanation restates the saved decision basis, cites supplied source IDs, preserves uncertainty, and clearly says what the evidence does not mean.",
    glossaryEyebrow: "Minimum vocabulary",
    glossaryTitle: "Enough biology to navigate the application",
    glossary: [
      ["Gene", "A DNA region associated with a functional product, often a protein."],
      ["RNA", "A molecule through which genetic information is expressed and processed."],
      ["ASO", "A short synthetic nucleic-acid molecule designed to bind RNA and alter its abundance or processing."],
      ["Variant", "A difference in DNA sequence."],
      ["Loss of function (LoF)", "A consequence category associated with reduced normal gene function."],
      ["Missense", "A DNA change that alters one amino acid in a protein."],
      ["ClinVar / EVA", "Sources of submitted variant records and clinical-significance classifications used by the heuristic."],
      ["Gene2Phenotype (G2P)", "Curated gene–disease mechanism and inheritance evidence."],
      ["LOEUF", "A population constraint measure; lower values indicate less tolerance for loss-of-function variation."],
      ["MONDO", "A disease ontology that provides stable identifiers for disease concepts."],
    ],
    checkEyebrow: "Knowledge check",
    checkTitle: "Test the mental model",
    reveal: "Reveal answer",
    checks: [
      ["Does the candidate with the highest association score automatically become the best therapeutic target?", "No. Association strength is one evidence dimension and is not a calibrated probability of efficacy, safety, or causal direction."],
      ["Does zero returned variant evidence mean the gene has no role in the disease?", "No. It means the checked workflow returned no qualifying records. Missingness, source scope, and unmodeled mechanisms remain important."],
      ["Can an AI summary change a candidate from modifier to knockdown?", "No. AI output is optional commentary. Only the deterministic engine creates the saved classification."],
    ],
    finalNote: "Suggested practice: explain one candidate in your own words before asking the AI explainer. Then compare your explanation with the generated one and inspect every cited source label.",
  },
} as const;

export default function Learn({ disclaimer, onExample, onCase, onResumeSaved }: LearnProps) {
  const copy = COPY.en;

  return <main id="main" className="learn-view">

    <section className="learn-hero">
      <p className="eyebrow">{copy.eyebrow}</p>
      <h1>{copy.title}</h1>
      <p className="lede">{copy.intro}</p>
      <div className="learn-hero-actions">
        <button className="primary-button compact" onClick={onExample}>{copy.start}<span aria-hidden="true">→</span></button>
        {onResumeSaved && <button className="secondary-button" onClick={onResumeSaved}>Return to latest saved analysis</button>}
      </div>
    </section>

    <section className="learn-section learn-capabilities" aria-labelledby="learn-capabilities">
      <p className="eyebrow">{copy.capabilitiesEyebrow}</p><h2 id="learn-capabilities">{copy.capabilitiesTitle}</h2><p className="learn-intro">{copy.capabilitiesIntro}</p>
      <div>{copy.capabilities.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>

    <section className="learn-section" aria-labelledby="learn-tracks">
      <p className="eyebrow">{copy.tracksEyebrow}</p><h2 id="learn-tracks">{copy.tracksTitle}</h2>
      <div className="learn-track-grid">{copy.tracks.map(([title, meaning, caution], index) => <article key={title} className={`learn-track track-border-${index}`}><h3>{title}</h3><b>{copy.means}</b><p>{meaning}</p><b>{copy.notMeans}</b><p>{caution}</p></article>)}</div>
      <p className="notice learn-precedence">Mechanism precedence is: reviewed manual override → Gene2Phenotype → ClinVar heuristic → modifier. <TermHelp term="loeuf"/> adds safety context; it does not select the mechanism track.</p>
    </section>

    <section className="learn-section" aria-labelledby="learn-reading">
      <p className="eyebrow">{copy.readEyebrow}</p><h2 id="learn-reading">{copy.readTitle}</h2>
      <ol className="learn-reading">{copy.readSteps.map(([title, text], index) => <li key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{title === "LOEUF" ? <TermHelp term="loeuf"/> : title}</h3><p>{text}</p></div></li>)}</ol>
    </section>

    <section className="learn-section learn-example" aria-labelledby="learn-example">
      <div><p className="eyebrow">{copy.exampleEyebrow}</p><h2 id="learn-example">{copy.exampleTitle}</h2><p>{copy.exampleIntro}</p><button className="secondary-button" onClick={onExample}>{copy.start}<span aria-hidden="true">→</span></button></div>
      <ol>{copy.questions.map((question) => <li key={question}>{question}</li>)}</ol>
    </section>

    <section className="learn-section" aria-labelledby="learn-cases">
      <p className="eyebrow">{copy.casesEyebrow}</p><h2 id="learn-cases">{copy.casesTitle}</h2><p className="learn-intro">{copy.casesIntro}</p>
      <div className="learn-case-grid">{EDUCATIONAL_CASES.map((caseStudy, index) => <article key={caseStudy.case_id} className={caseStudy.status === "published" ? "case-available" : "case-pending"}>
        <div><span>{String(index + 1).padStart(2, "0")}</span><small>{caseStudy.status === "published" ? "Available" : "Fixture review pending"}</small></div><h3>{caseStudy.title}</h3><p>{caseStudy.learning_objectives[0]}</p><b>{caseStudy.status === "published" ? `${caseStudy.teaching_candidates.length} guided candidates` : "Curriculum roadmap"}</b>
        {caseStudy.status === "published" && <button className="secondary-button" onClick={() => onCase(caseStudy.slug)}>Open published case <span aria-hidden="true">→</span></button>}
      </article>)}</div>
    </section>

    <section className="learn-section" aria-labelledby="learn-boundaries">
      <h2 id="learn-boundaries">{copy.boundaryTitle}</h2>
      <div className="learn-boundaries">{copy.boundaries.map(([title, text]) => <article key={title}><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>

    <section className="learn-section" aria-labelledby="learn-ai">
      <p className="eyebrow">{copy.aiEyebrow}</p><h2 id="learn-ai">{copy.aiTitle}</h2>
      <div className="learn-ai-flow">{copy.aiFlow.map((step, index) => <div key={step}><span>{index + 1}</span><b>{step}</b></div>)}</div>
      <p className="learn-intro">{copy.aiText}</p>
    </section>

    <section className="learn-section glossary learn-glossary" aria-labelledby="learn-glossary">
      <p className="eyebrow">{copy.glossaryEyebrow}</p><h2 id="learn-glossary">{copy.glossaryTitle}</h2>
      <div>{copy.glossary.map(([term, definition]) => <details key={term}><summary>{term}<span>+</span></summary><p>{definition}</p></details>)}</div>
    </section>

    <details className="learn-section learn-operations">
      <summary><span><b>Supporting context</b>{copy.pipelineTitle}</span><span aria-hidden="true">+</span></summary>
      <p className="learn-intro">{copy.pipelineIntro}</p>
      <ol className="learn-pipeline">{copy.pipeline.map(([number, title, text]) => <li key={number}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}</ol>
    </details>

    <section className="learn-section" aria-labelledby="learn-check">
      <p className="eyebrow">{copy.checkEyebrow}</p><h2 id="learn-check">{copy.checkTitle}</h2>
      <div className="learn-checks">{copy.checks.map(([question, answer], index) => <article key={question}><span>{String(index + 1).padStart(2, "0")}</span><h3>{question}</h3><details><summary>{copy.reveal}</summary><p>{answer}</p></details></article>)}</div>
    </section>

    <p className="learn-final-note">{copy.finalNote}</p>
    <p className="persistent-disclaimer">{disclaimer}</p>
  </main>;
}
