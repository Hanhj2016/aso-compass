import { EDUCATIONAL_CASES } from "./caseStudies";

type PortfolioPageProps = {
  disclaimer: string;
  onCases: () => void;
  onWorkspace: () => void;
  onMethods: () => void;
  onCase: (slug: string) => void;
  onResumeSaved?: () => void;
};

const FEATURED_SLUGS = new Set(["als", "huntington-disease", "dravet-syndrome"]);

const CAPABILITIES = [
  ["Biomedical interpretation", "Translate gene–disease association, mechanism, inheritance, constraint, and variant evidence into bounded research questions."],
  ["Evidence synthesis", "Compare independent sources while preserving provenance, conflicts, missingness, retrieval limits, and alternative explanations."],
  ["Reproducible research software", "Implement a typed, tested application around a deterministic rule engine, versioned evidence fixtures, and persistent records."],
  ["Responsible AI", "Use source-bound generation for explanation only, with server-side validation that protects deterministic classifications and citations."],
] as const;

export default function PortfolioPage({ disclaimer, onCases, onWorkspace, onMethods, onCase, onResumeSaved }: PortfolioPageProps) {
  const featuredCases = EDUCATIONAL_CASES.filter(caseStudy => FEATURED_SLUGS.has(caseStudy.slug));

  return <main id="main" className="portfolio-page">
    <section className="portfolio-hero">
      <div>
        <p className="eyebrow">Biomedical research-software portfolio</p>
        <h1>From public evidence to a defensible research interpretation.</h1>
        <p className="lede">ASO Compass demonstrates how biological reasoning, evidence provenance, and reproducible software can be combined to investigate antisense-oligonucleotide target hypotheses—without presenting them as clinical conclusions.</p>
        <div className="portfolio-actions">
          <button className="primary-button compact" type="button" onClick={onCases}>Explore case studies <span aria-hidden="true">→</span></button>
          <button className="secondary-button" type="button" onClick={onWorkspace}>Open research workspace</button>
          {onResumeSaved && <button className="text-button" type="button" onClick={onResumeSaved}>Resume latest saved analysis →</button>}
        </div>
      </div>
      <aside aria-label="Portfolio evidence at a glance">
        <p className="eyebrow">Evidence at a glance</p>
        <dl>
          <div><dt>6</dt><dd>curated case studies</dd></div>
          <div><dt>5</dt><dd>evidence domains integrated</dd></div>
          <div><dt>5</dt><dd>deterministic research tracks</dd></div>
          <div><dt>1</dt><dd>source-bound interpretation layer</dd></div>
        </dl>
        <p>Every result keeps its decision rule, limitations, and primary evidence links visible.</p>
      </aside>
    </section>

    <section className="portfolio-question" aria-labelledby="portfolio-question-title">
      <p className="eyebrow">Research question</p>
      <h2 id="portfolio-question-title">How can public gene–disease evidence be synthesized into transparent, reviewable ASO research directions without hiding uncertainty?</h2>
      <p>The application treats that question as both a biomedical interpretation problem and a research-software design problem.</p>
    </section>

    <section className="portfolio-section" aria-labelledby="portfolio-capabilities-title">
      <p className="eyebrow">Capabilities demonstrated</p>
      <h2 id="portfolio-capabilities-title">Scientific judgment made inspectable</h2>
      <div className="portfolio-capability-grid">
        {CAPABILITIES.map(([title, description], index) => <article key={title}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <h3>{title}</h3>
          <p>{description}</p>
        </article>)}
      </div>
    </section>

    <section className="portfolio-section" aria-labelledby="portfolio-cases-title">
      <div className="portfolio-section-heading">
        <div><p className="eyebrow">Selected work</p><h2 id="portfolio-cases-title">Three cases that expose different reasoning challenges</h2></div>
        <button className="text-button" type="button" onClick={onCases}>View all six case studies →</button>
      </div>
      <div className="portfolio-case-grid">
        {featuredCases.map(caseStudy => <article key={caseStudy.case_id}>
          <small>{caseStudy.title}</small>
          <h3>{caseStudy.research_question}</h3>
          <div>{caseStudy.capabilities_demonstrated.slice(0, 3).map(capability => <span key={capability}>{capability}</span>)}</div>
          <button className="secondary-button" type="button" onClick={() => onCase(caseStudy.slug)}>Review this case <span aria-hidden="true">→</span></button>
        </article>)}
      </div>
    </section>

    <section className="portfolio-project" aria-labelledby="portfolio-project-title">
      <div>
        <p className="eyebrow">Project contribution</p>
        <h2 id="portfolio-project-title">Biomedical reasoning supported by production-minded engineering</h2>
        <p>This student research-software project covers scientific framing, deterministic rule translation, evidence-aware interface design, validation, deployment, and communication of uncertainty.</p>
        <div className="portfolio-stack" aria-label="Technical stack"><span>FastAPI</span><span>SQLModel</span><span>PostgreSQL</span><span>React</span><span>TypeScript</span><span>Alembic</span></div>
      </div>
      <aside>
        <h3>Inspect the work</h3>
        <button className="secondary-button" type="button" onClick={onMethods}>Review methods &amp; glossary</button>
        <a href="https://github.com/Hanhj2016/aso-compass" target="_blank" rel="noreferrer">Source code and documentation ↗</a>
      </aside>
    </section>

    <p className="persistent-disclaimer">{disclaimer}</p>
  </main>;
}
