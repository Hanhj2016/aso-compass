import { useMemo, useState } from "react";
import { TERMS, type TermDefinition } from "./glossaryTerms";

type GlossaryEntry = TermDefinition & {
  category: "Core biology" | "Mechanism and direction" | "Evidence sources" | "Results and limitations";
  aliases?: string[];
};

const CONTEXTUAL_ENTRIES: GlossaryEntry[] = [
  { ...TERMS.loeuf, category: "Evidence sources", aliases: ["gnomAD constraint"] },
  { ...TERMS.gof, category: "Mechanism and direction", aliases: ["gain of function"] },
  { ...TERMS.dn, category: "Mechanism and direction", aliases: ["dominant negative"] },
  { ...TERMS.haploinsufficiency, category: "Mechanism and direction", aliases: ["dosage sensitivity"] },
  { ...TERMS.capped, category: "Results and limitations", aliases: ["truncated", "evidence truncated"] },
  { ...TERMS.reviewStatus, category: "Evidence sources", aliases: ["ClinVar stars"] },
  { ...TERMS.lof, category: "Mechanism and direction", aliases: ["loss of function"] },
];

const PAGE_ENTRIES: GlossaryEntry[] = [
  {
    label: "Gene", category: "Core biology",
    plain: "A DNA region associated with a functional product, often a protein or functional RNA.",
    biology: "Genes are expressed through RNA and may produce different transcripts or products in different tissues.",
    app: "ASO Compass organizes candidate evidence at gene level, even when the underlying disease mechanism may be variant- or transcript-specific.",
    mistake: "A gene-level association does not mean every variant or every transcript has the same biological effect.",
  },
  {
    label: "RNA", category: "Core biology",
    plain: "A molecule that carries, processes, or regulates genetic information.",
    biology: "Messenger RNA can be translated into protein, while other RNA types have regulatory or structural functions.",
    app: "RNA is the direct binding substrate for antisense oligonucleotides.",
    mistake: "Changing an RNA does not guarantee a predictable or beneficial change in disease biology.",
  },
  {
    label: "ASO", category: "Core biology", aliases: ["antisense oligonucleotide"],
    plain: "A short synthetic nucleic-acid molecule designed to bind a selected RNA sequence.",
    biology: "Depending on chemistry and design, an ASO may reduce RNA, alter splicing, or modify RNA processing.",
    app: "ASO Compass explores evidence relevant to possible ASO research directions; it does not design sequences or recommend treatment.",
    mistake: "A plausible gene direction is not proof that an effective, deliverable, or safe ASO can be created.",
  },
  {
    label: "Variant", category: "Core biology",
    plain: "A difference in DNA sequence compared with a reference sequence.",
    biology: "A variant may be benign, pathogenic, uncertain, or have effects that depend on condition, transcript, inheritance, and other context.",
    app: "Returned ClinVar/EVA variant records contribute to a bounded gene-level heuristic and its evidence inventory.",
    mistake: "A returned variant record is not necessarily an independent patient, an independent study, or proof of causality.",
  },
  {
    label: "Missense variant", category: "Core biology", aliases: ["missense"],
    plain: "A DNA change that alters one amino acid in a protein.",
    biology: "Missense variants can affect stability, interactions, activity, or have little functional effect.",
    app: "Missense counts form part of the deterministic ClinVar heuristic denominator.",
    mistake: "Missense does not by itself mean gain of function, pathogenic, or suitable for knockdown.",
  },
  {
    label: "Knockdown", category: "Mechanism and direction",
    plain: "A research direction that aims to reduce the amount of a selected RNA or gene product.",
    biology: "Reduction may be relevant when excess or harmful activity contributes to disease, but normal function and dose sensitivity remain important.",
    app: "This deterministic track can arise from curated G2P mechanism evidence or the configured ClinVar record-fraction rule.",
    mistake: "The track is a hypothesis, not a treatment recommendation or proof that full, non-selective reduction is safe.",
  },
  {
    label: "Splice / upregulation", category: "Mechanism and direction", aliases: ["splice modulation", "restoration"],
    plain: "A research direction that considers changing RNA processing or restoring more useful gene product.",
    biology: "Splice modulation can include exon inclusion, exon skipping, or transcript correction; upregulation seeks more functional output.",
    app: "The track signals that reduction is not the inferred direction under the saved deterministic evidence.",
    mistake: "It is not simply the opposite of knockdown and does not prove that a correctable splice event or feasible upregulation method exists.",
  },
  {
    label: "Ambiguous", category: "Mechanism and direction",
    plain: "The saved evidence does not support one clear directional track under the configured thresholds.",
    biology: "Mixed variant mechanisms, multiple disease processes, or incomplete evidence may produce uncertainty.",
    app: "The ClinVar heuristic places a candidate here when the loss-of-function record fraction lies between directional thresholds.",
    mistake: "Ambiguous is not a weak recommendation and should not be forced into knockdown or restoration without additional evidence.",
  },
  {
    label: "Modifier", category: "Mechanism and direction",
    plain: "A gene–disease association is present, but the saved evidence does not resolve a direct intervention direction.",
    biology: "A modifier may influence severity, onset, progression, or another aspect of phenotype without being the primary cause.",
    app: "Association-only candidates or configured modifier evidence can receive this deterministic track.",
    mistake: "Modifier does not mean irrelevant, benign, or low quality.",
  },
  {
    label: "Insufficient data", category: "Mechanism and direction",
    plain: "Too few qualifying records were available for the configured directional heuristic.",
    biology: "The gene may still be biologically important through mechanisms not captured by the current query or record categories.",
    app: "ASO Compass uses this label when the minimum classified-record requirement is not met.",
    mistake: "It is not a negative result and does not mean that the gene is unrelated to the disease.",
  },
  {
    label: "Open Targets", category: "Evidence sources",
    plain: "A platform that integrates public evidence connecting potential targets with diseases.",
    biology: "Its evidence spans genetics, expression, literature, known drugs, and other source types.",
    app: "ASO Compass uses Open Targets association results to identify and score initial candidate genes.",
    mistake: "An association score is not a probability of causality, safety, or therapeutic success.",
  },
  {
    label: "Gene2Phenotype (G2P)", category: "Evidence sources", aliases: ["G2P"],
    plain: "A curated source of gene–disease, mechanism, and inheritance information.",
    biology: "Curated mechanism labels can distinguish loss of function, gain of function, dominant negative effects, and inheritance patterns.",
    app: "When returned, reviewed G2P mechanism evidence has deterministic precedence over the ClinVar heuristic.",
    mistake: "A G2P mechanism does not establish ASO feasibility, tissue delivery, dose, or safety.",
  },
  {
    label: "ClinVar / EVA", category: "Evidence sources", aliases: ["ClinVar", "EVA"],
    plain: "Sources that expose submitted variant classifications and related metadata.",
    biology: "Records can differ by condition, submitter, review status, assertion date, and interpretation.",
    app: "ASO Compass retrieves a bounded inventory through Open Targets EVA for its gene-level heuristic and learning view.",
    mistake: "A pathogenic label should not be interpreted without its variant–condition relationship, review status, conflicts, and date.",
  },
  {
    label: "gnomAD", category: "Evidence sources",
    plain: "A large reference resource describing human genetic variation in populations.",
    biology: "Population depletion of predicted loss-of-function variants can provide gene-constraint context.",
    app: "ASO Compass displays gnomAD-derived LOEUF as safety and review context.",
    mistake: "Population constraint alone does not determine disease mechanism or intervention direction.",
  },
  {
    label: "MONDO", category: "Evidence sources", aliases: ["disease ontology"],
    plain: "A disease ontology that provides stable identifiers and relationships for disease concepts.",
    biology: "Ontologies help align related names and concepts used by different biomedical sources.",
    app: "A MONDO identifier anchors most disease queries and saved runs.",
    mistake: "An ontology identifier standardizes the concept; it does not supply biological evidence by itself.",
  },
  {
    label: "Association score", category: "Results and limitations",
    plain: "A source-derived value used to order the strength of retrieved gene–disease association evidence.",
    biology: "Different evidence types contribute to association without necessarily establishing a causal or therapeutically useful mechanism.",
    app: "Overall and genetic scores are saved alongside each candidate and used by configured filters and ordering.",
    mistake: "The score is not a calibrated probability that an intervention will work.",
  },
  {
    label: "Evidence returned / total", category: "Results and limitations", aliases: ["evidence count"],
    plain: "The number of records retained by the run compared with the number observed by the query.",
    biology: "A truncated record set may not represent the complete mixture of known variant consequences.",
    app: "A value such as 500/629 identifies capped retrieval; 0/0 identifies no qualifying returned records.",
    mistake: "These counts are not patient counts, and 0/0 does not mean benign or unrelated.",
  },
  {
    label: "Not returned / not checked", category: "Results and limitations", aliases: ["missing", "unknown"],
    plain: "Not returned means a field was unavailable; not checked means the run did not perform that lookup.",
    biology: "Absence of retrieved information is different from biological evidence of absence.",
    app: "ASO Compass preserves these states so missingness is not silently converted into a negative result.",
    mistake: "Neither state should be read as benign, no mechanism, or no therapeutic precedent.",
  },
  {
    label: "Therapeutic precedent", category: "Results and limitations", aliases: ["ASO precedent", "drug precedent"],
    plain: "A drug or trial record linked to the candidate target was found by the configured checks.",
    biology: "Precedent can show that a target or modality has entered development, sometimes for a different condition or direction.",
    app: "The interface retains approved-drug, oligonucleotide, and trial context without hiding the candidate from research views.",
    mistake: "Precedent does not establish efficacy, approval for the queried disease, or a treatment recommendation.",
  },
  {
    label: "Priority shortlist", category: "Results and limitations", aliases: ["shortlist rank"],
    plain: "A deterministic review order produced by configured application rules.",
    biology: "It helps focus manual review but cannot combine every factor needed for a therapeutic decision.",
    app: "The shortlist is saved with the run and cannot be changed by optional AI explanations.",
    mistake: "It is not a clinical ranking, treatment recommendation, or probability of success.",
  },
  {
    label: "Review flag", category: "Results and limitations", aliases: ["warning"],
    plain: "A visible signal that safety, completeness, or mechanism uncertainty requires human attention.",
    biology: "Examples include low tolerance for loss of function or incomplete variant retrieval.",
    app: "Flags remain adjacent to the candidate but do not silently rewrite its deterministic track.",
    mistake: "A flag is not an automatic exclusion and its absence is not proof of safety.",
  },
];

const GLOSSARY_ENTRIES = [...CONTEXTUAL_ENTRIES, ...PAGE_ENTRIES]
  .sort((left, right) => left.label.localeCompare(right.label));
const CATEGORIES: GlossaryEntry["category"][] = ["Core biology", "Mechanism and direction", "Evidence sources", "Results and limitations"];

function slug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export default function GlossaryPage({ disclaimer }: { disclaimer: string }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return GLOSSARY_ENTRIES;
    return GLOSSARY_ENTRIES.filter(entry => [entry.label, ...(entry.aliases ?? []), entry.plain, entry.biology, entry.app, entry.mistake]
      .some(value => value.toLowerCase().includes(needle)));
  }, [query]);

  return <main id="main" className="glossary-page">
    <header className="glossary-hero">
      <p className="eyebrow">Research methods reference</p>
      <h1>Methods &amp; Glossary</h1>
      <p className="lede">See how ASO Compass turns source-bounded evidence into reproducible interpretations, then explore plain-language definitions for the concepts, sources, tracks, and limitations used throughout the application.</p>
      <p className="notice"><b>Educational scope:</b> these definitions support interpretation of the application. They are not clinical guidance and do not replace review of primary records.</p>
    </header>

    <section className="methods-overview" aria-labelledby="methods-overview-title">
      <p className="eyebrow">Interpretation method</p>
      <h2 id="methods-overview-title">How the application builds a defensible result</h2>
      <div className="methods-grid">
        <article><span>01</span><h3>Evidence synthesis</h3><p>Combine association, mechanism, submitted variants, population constraint, and therapeutic precedent while preserving each source's scope.</p></article>
        <article><span>02</span><h3>Deterministic interpretation</h3><p>Apply visible precedence and thresholds to assign a research track. The result is reproducible and is not an AI prediction.</p></article>
        <article><span>03</span><h3>Provenance and limitations</h3><p>Retain source identifiers, release metadata, missingness, truncation, conflicts, and review flags beside the claims they qualify.</p></article>
        <article><span>04</span><h3>Bounded AI explanation</h3><p>Allow optional AI to explain saved evidence only; it cannot alter classifications, scores, shortlist order, or warnings.</p></article>
      </div>
    </section>

    <section className="glossary-search" aria-labelledby="glossary-search-title">
      <div><h2 id="glossary-search-title">Find a term</h2><p>{filtered.length} of {GLOSSARY_ENTRIES.length} terms shown</p></div>
      <label><span className="sr-only">Search glossary</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search LOEUF, ClinVar, knockdown…" aria-label="Search glossary"/>{query && <button type="button" onClick={() => setQuery("")}>Clear</button>}</label>
    </section>

    {CATEGORIES.map(category => {
      const entries = filtered.filter(entry => entry.category === category);
      if (!entries.length) return null;
      return <section className="glossary-category" key={category} aria-labelledby={`glossary-${slug(category)}`}>
        <h2 id={`glossary-${slug(category)}`}>{category}</h2>
        <div className="glossary-entry-grid">{entries.map(entry => <article id={`term-${slug(entry.label)}`} key={entry.label}>
          <header><h3>{entry.label}</h3>{entry.aliases?.length ? <small>Also: {entry.aliases.join(" · ")}</small> : null}</header>
          <dl>
            <div><dt>Plain language</dt><dd>{entry.plain}</dd></div>
            <div><dt>Biological meaning</dt><dd>{entry.biology}</dd></div>
            <div><dt>Inside ASO Compass</dt><dd>{entry.app}</dd></div>
            <div><dt>Common interpretation mistake</dt><dd>{entry.mistake}</dd></div>
          </dl>
        </article>)}</div>
      </section>;
    })}
    {!filtered.length && <section className="glossary-empty"><h2>No matching term</h2><p>Try a broader biological, evidence-source, or interface term.</p><button className="secondary-button" type="button" onClick={() => setQuery("")}>Show all terms</button></section>}
    <p className="persistent-disclaimer">{disclaimer}</p>
  </main>;
}
