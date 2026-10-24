import { createPortal } from "react-dom";
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { TERMS, type TermKey } from "./glossaryTerms";
import type { Candidate } from "./types";

const FULL_GLOSSARY_URL = "#/glossary";

let activeTermHelpId: string | null = null;
const termHelpListeners = new Set<() => void>();

function subscribeToActiveTermHelp(listener: () => void) {
  termHelpListeners.add(listener);
  return () => termHelpListeners.delete(listener);
}

function setActiveTermHelp(id: string | null) {
  if (activeTermHelpId === id) return;
  activeTermHelpId = id;
  termHelpListeners.forEach(listener => listener());
}

function getActiveTermHelp() {
  return activeTermHelpId;
}

export function TermHelp({ term, children }: { term: TermKey; children?: ReactNode }) {
  const entry = TERMS[term];
  const reactId = useId();
  const id = `term-help-${reactId.replaceAll(":", "")}`;
  const activeId = useSyncExternalStore(subscribeToActiveTermHelp, getActiveTermHelp, getActiveTermHelp);
  const open = activeId === id;
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [mobile, setMobile] = useState(false);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);

  const close = useCallback((restoreFocus = false) => {
    setActiveTermHelp(null);
    if (restoreFocus) triggerRef.current?.focus();
  }, []);

  useEffect(() => {
    const query = window.matchMedia?.("(max-width: 650px)");
    if (!query) return;
    const update = () => setMobile(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useLayoutEffect(() => {
    if (!open || mobile) return;
    const place = () => {
      const trigger = triggerRef.current?.getBoundingClientRect();
      const popover = popoverRef.current?.getBoundingClientRect();
      if (!trigger || !popover) return;
      const margin = 12;
      const gap = 8;
      const left = Math.min(
        Math.max(margin, trigger.left),
        Math.max(margin, window.innerWidth - popover.width - margin),
      );
      const fitsBelow = trigger.bottom + gap + popover.height <= window.innerHeight - margin;
      const top = fitsBelow
        ? trigger.bottom + gap
        : Math.max(margin, trigger.top - gap - popover.height);
      setPosition({ left, top });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [mobile, open]);

  useEffect(() => {
    if (!open) return;
    const dismissOutside = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!triggerRef.current?.contains(target) && !popoverRef.current?.contains(target)) close(false);
    };
    const dismissWithKeyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close(true);
      } else if (mobile && event.key === "Tab" && popoverRef.current) {
        const focusable = [...popoverRef.current.querySelectorAll<HTMLElement>("button, a[href]")];
        const first = focusable.at(0);
        const last = focusable.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("keydown", dismissWithKeyboard);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("keydown", dismissWithKeyboard);
    };
  }, [close, mobile, open]);

  useEffect(() => {
    if (!open || !mobile) return;
    closeButtonRef.current?.focus();
  }, [mobile, open]);

  useEffect(() => () => {
    if (getActiveTermHelp() === id) setActiveTermHelp(null);
  }, [id]);

  const popover = open && createPortal(<>
    {mobile && <button className="term-popover-backdrop" type="button" aria-label={`Close ${entry.label} explanation`} onClick={() => close(true)}/>}
    <div
      ref={popoverRef}
      id={`${id}-popover`}
      className={`term-popover${mobile || position ? " term-popover-positioned" : ""}`}
      role="dialog"
      aria-modal={mobile || undefined}
      aria-labelledby={`${id}-title`}
      style={!mobile && position ? position : undefined}
    >
      <div className="term-popover-heading">
        <b id={`${id}-title`} className="term-popover-title">{entry.label}</b>
        <button ref={closeButtonRef} type="button" aria-label={`Close ${entry.label} explanation`} onClick={() => close(true)}>×</button>
      </div>
      <span className="term-popover-entry"><b>Plain language</b><span>{entry.plain}</span></span>
      <span className="term-popover-entry"><b>Biological meaning</b><span>{entry.biology}</span></span>
      <span className="term-popover-entry"><b>Inside ASO Compass</b><span>{entry.app}</span></span>
      <span className="term-popover-entry"><b>Common mistake</b><span>{entry.mistake}</span></span>
      <a href={FULL_GLOSSARY_URL}>Open the full glossary →</a>
    </div>
  </>, document.body);

  return <span className="term-help">
    <button
      ref={triggerRef}
      type="button"
      aria-label={`Explain ${entry.label}`}
      aria-expanded={open}
      aria-controls={`${id}-popover`}
      onClick={() => {
        setPosition(null);
        setActiveTermHelp(open ? null : id);
      }}
    >{children ?? entry.label}<span aria-hidden="true">?</span></button>
    {popover}
  </span>;
}

function sourceAvailability(candidate: Candidate) {
  return {
    openTargets: `Association scores available: overall ${candidate.overall_score.toFixed(3)}, genetic ${candidate.genetic_score.toFixed(3)}.`,
    g2p: candidate.g2p_mech || candidate.inheritance
      ? `Returned mechanism: ${candidate.g2p_mech ?? "not returned"}; inheritance: ${candidate.inheritance ?? "not returned"}.`
      : "No mechanism or inheritance annotation was returned for this candidate.",
    clinvar: candidate.n_evidence === null
      ? "Variant enrichment was not checked."
      : `${candidate.n_evidence_returned ?? 0} of ${candidate.n_evidence} evidence records were returned${candidate.evidence_truncated ? "; retrieval was capped" : ""}.`,
    gnomad: candidate.loeuf === null ? "LOEUF was not returned." : `LOEUF ${candidate.loeuf.toFixed(3)} was returned as population-constraint context.`,
    precedent: candidate.aso_precedent || candidate.drug_status || "No therapeutic-precedent summary was returned.",
  };
}

export function EvidenceSourceMap({ candidate }: { candidate: Candidate }) {
  const available = sourceAvailability(candidate);
  const sources = [
    ["Open Targets", "Association", available.openTargets, "Supports a retrieved gene–disease association and its source scores.", "Does not prove causation, intervention direction, safety, or therapeutic success."],
    ["Gene2Phenotype", "Mechanism + inheritance", available.g2p, "Can support curated disease mechanism and inheritance context.", "Does not establish that an ASO modality is feasible or safe for this candidate."],
    ["ClinVar / EVA", "Submitted variant evidence", available.clinvar, "Supports the returned variant-consequence inventory and, for new runs, bounded review-status and variant–condition context.", "It does not establish causality, retain every source record, or expose a reliable submitter count through this query."],
    ["gnomAD", "Population constraint", available.gnomad, "Supports population constraint context through LOEUF.", "Does not determine the disease mechanism or prove that knockdown is safe or unsafe."],
    ["Drug / trials", "Therapeutic precedent", available.precedent, "Supports that a target-linked drug or trial record was found by the configured checks.", "Does not establish efficacy for this disease, approval for this indication, or a treatment recommendation."],
  ];
  return <section className="source-map" aria-labelledby="source-map-title">
    <p className="eyebrow">Evidence-source map</p>
    <h3 id="source-map-title">How the saved evidence reaches this track</h3>
    <p>Follow the numbered evidence streams into the rule engine. Open any source to inspect its claim boundary.</p>
    <div className="source-map-list" aria-label="Five evidence streams converging on the deterministic track">
      {sources.map(([name, role, status, supports, limitation], index) => <details key={name}>
        <summary><span className="source-map-step" aria-hidden="true">{index + 1}</span><span><b>{name}</b><small>{role}</small></span><span aria-hidden="true">→</span></summary>
        <div><p className="source-map-status">{status}</p>{name === "gnomAD" && <p className="mechanism-term-note">Context concept: <TermHelp term="loeuf"/></p>}{name === "ClinVar / EVA" && <p className="mechanism-term-note">Interpretation concept: <TermHelp term="reviewStatus"/></p>}<dl><div><dt>Can support</dt><dd>{supports}</dd></div><div><dt>Cannot support</dt><dd>{limitation}</dd></div></dl></div>
      </details>)}
    </div>
    <div className="source-map-convergence" aria-hidden="true"><span>Independent evidence roles remain separate</span><b>↓</b></div>
    <div className="source-map-result"><small>Deterministic rule engine</small><b>{candidate.final_call}</b><p>Combines the saved inputs by visible rules. Neither this diagram nor AI changes the track.</p></div>
  </section>;
}

export function MechanismHelp({ value }: { value: string | null }) {
  if (!value) return <>Not returned</>;
  if (value === "GoF/DN") return <><TermHelp term="gof"/> / <TermHelp term="dn"/></>;
  if (value === "GoF") return <TermHelp term="gof"/>;
  if (value === "DN") return <TermHelp term="dn"/>;
  if (value === "LoF") return <TermHelp term="lof"/>;
  return <>{value}</>;
}

export function ClinVarLearningCheckpoint({ candidate }: { candidate: Candidate }) {
  const returned = candidate.n_evidence_returned ?? 0;
  const interpretation = candidate.clinvar_interpretation;
  const available = interpretation?.metadata_status === "available" || interpretation?.metadata_status === "partial";
  const reviewCounts = Object.entries(interpretation?.review_status_counts ?? {});
  const starCounts = Object.entries(interpretation?.review_star_counts ?? {}).sort(([a], [b]) => Number(b) - Number(a));
  const representatives = interpretation?.representative_records ?? [];
  return <section className="clinvar-checkpoint" aria-labelledby="clinvar-checkpoint-title">
    <p className="eyebrow">Interpretation checkpoint</p>
    <h3 id="clinvar-checkpoint-title">A ClinVar classification is more than a label</h3>
    <div className="clinvar-retained">
      <div><span>Returned / reported</span><b>{candidate.n_evidence === null ? "Not checked" : `${returned} / ${candidate.n_evidence}`}</b></div>
      <div><span>Completeness</span><b>{candidate.evidence_truncated ? <TermHelp term="capped"/> : candidate.completeness}</b></div>
      <div><span>Heuristic result</span><b>{candidate.clinvar_call}</b></div>
    </div>
    {available ? <>
      <div className="clinvar-metadata-grid">
        <div><span><TermHelp term="reviewStatus"/> coverage</span><b>{interpretation?.records_with_review_status ?? 0} / {returned}</b></div>
        <div><span>Conflict-marked records</span><b>{interpretation?.conflict_records ?? 0}</b></div>
        <div><span>Latest evidence date</span><b>{interpretation?.latest_evidence_date ?? "Not returned"}</b></div>
        <div><span>Submitter count</span><b>{interpretation?.submitter_count ?? "Not exposed"}</b></div>
        <div><span>Latest source release</span><b>{interpretation?.latest_release_date ?? "Not returned"}</b></div>
        <div><span>Release version(s)</span><b>{interpretation?.release_versions?.join(", ") || "Not returned"}</b></div>
      </div>
      {reviewCounts.length > 0 && <div className="review-status-list" aria-label="Review status distribution">{reviewCounts.map(([status, count]) => <span key={status}><b>{count}</b>{status}</span>)}</div>}
      {starCounts.length > 0 && <div className="review-star-distribution" aria-label="ClinVar review-star distribution"><h4><TermHelp term="reviewStatus">Review-star distribution</TermHelp></h4>{starCounts.map(([stars, count]) => <span key={stars}><b>{"★".repeat(Number(stars)) || "No stars"}</b><small>{count} record{count === 1 ? "" : "s"}</small></span>)}</div>}
      {(interpretation?.conditions?.length ?? 0) > 0 && <details className="learning-question"><summary>Variant–condition relationships returned</summary><ul>{interpretation?.conditions?.map(condition => <li key={`${condition.id}-${condition.label}`}>{condition.label ?? condition.id ?? "Unlabelled condition"} <small>({condition.record_count} records)</small></li>)}</ul></details>}
      {representatives.length > 0 && <details className="learning-question representative-records"><summary>Inspect representative variant records ({representatives.length})</summary><div>{representatives.map((record, index) => <article key={record.source_record_id ?? `${record.rs_id}-${index}`}>
        <div><b>{record.rs_id ?? "Variant ID not returned"}</b><span>{record.review_stars === null ? "Stars not returned" : `${"★".repeat(record.review_stars)}${"☆".repeat(4 - record.review_stars)} (${record.review_stars})`}</span></div>
        <p>{record.clinical_significances.join(", ") || "Clinical significance not returned"} · {record.consequence_label?.replaceAll("_", " ") ?? "consequence not returned"}</p>
        <p>{record.review_status ?? "Review status not returned"}</p>
        <small>{record.condition_label ?? record.condition_id ?? "Condition not returned"} · evidence {record.evidence_date ?? "date not returned"} · release {record.release_date ?? "date not returned"}{record.release_version ? ` (${record.release_version})` : ""}</small>
        {record.rs_id && <a href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(record.rs_id)}`} target="_blank" rel="noreferrer">Review in ClinVar ↗</a>}
      </article>)}</div></details>}
      <p><b>Still not available here:</b> reliable submitter count and the full submission-level evidence. This is a bounded learning view; inspect the primary ClinVar record before variant-level interpretation.</p>
    </> : <p><b>Interpretation metadata unavailable:</b> this saved candidate does not retain review status, submitter count, agreement/conflict, assertion date/version, or per-variant condition context. This is expected for older bundled examples. Inspect the primary record before variant-level interpretation.</p>}
    <details className="learning-question"><summary>Question: if zero qualifying records were returned, does that mean “benign”?</summary><p><b>No.</b> It means this workflow returned no qualifying evidence records. Source scope, query rules, missingness, and unmodeled mechanisms remain possible explanations.</p></details>
    <details className="learning-question"><summary>Question: can these aggregate counts establish a variant's clinical significance?</summary><p><b>No.</b> They support the application’s gene-level heuristic only. Variant-level interpretation requires the specific variant–condition record, review status, submissions, criteria, dates, and supporting evidence.</p></details>
  </section>;
}
