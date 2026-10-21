# Product and scientific behavior

## Product identity

- Name: **ASO Compass**
- Tagline: **Evidence-guided target exploration for research and education**
- Short description: A transparent application for exploring disease-associated genes, genetic mechanisms, safety signals, therapeutic precedent, and potential antisense oligonucleotide strategies.
- Persistent qualification: **For hypothesis generation and education only. Not for clinical decision-making.**

## Audience and purpose

The primary audience is life-science, biochemistry, genetics, and medical-research students and researchers exploring ASO target hypotheses. The application should teach how evidence contributes to a candidate classification, not merely display a ranking.

The tool is for hypothesis generation and research demonstration. It is not scientifically validated for patient selection, diagnosis, treatment, dosing, or clinical prioritization.

## Current engine behavior

Given an Open Targets disease or phenotype identifier, the enhanced v4.1 engine:

1. retrieves target associations and applies overall/genetic score thresholds;
2. retrieves gnomAD LOEUF constraint;
3. counts selected pathogenic/likely-pathogenic EVA/ClinVar consequence groups;
4. retrieves Gene2Phenotype mechanism and inheritance evidence;
5. discovers Open Targets drug fields and records drug/oligonucleotide/ASO precedent;
6. searches ClinicalTrials.gov API v2 and text-matches candidate genes;
7. classifies each candidate into one of five tracks;
8. creates a shortlist, validation data, run metadata, CSVs, and an HTML report.

Mechanism precedence is manual override, then G2P, then the ClinVar heuristic, then modifier. LOEUF affects safety warnings rather than the mechanism call.

## Heuristic boundaries that must remain visible

- Fewer than five classified LoF + missense records: insufficient data.
- LoF fraction at least 0.60: splice/upregulation.
- LoF fraction at most 0.25: knockdown.
- Intermediate fraction: ambiguous.
- Genetic association with no returned directional variant evidence may enter modifier.

These rules are simplifying heuristics. Missense-heavy evidence does not prove toxic gain of function, and truncating evidence does not prove that upregulation is feasible or safe.

## Recommended screens

1. **Learn / About** — an English guided tutorial covering the evidence pipeline, deterministic track meanings, source and missingness caveats, AI boundaries, knowledge checks, and an offline example walkthrough.
2. **New analysis** — disease selector, Basic/Advanced parameters, workload warning, consent to research-use statement.
3. **Run progress** — stage timeline, retries/cache status, current counts, warnings, and recoverable errors.
4. **Results overview** — run metadata, cards, mechanism distribution, association scatter, evidence completeness, and concise interpretation.
5. **Candidate explorer** — searchable/filterable table and a gene-detail panel with source-specific evidence.
6. **Exports** — CSV/JSON/report bundle with a manifest and warnings.
7. **Examples** — precomputed, versioned results for education and cold-start resilience.

## Visualization set

- track distribution bar or donut with labels and counts;
- overall versus genetic-association score scatter, colored and shaped by track;
- LOEUF versus evidence strength plot with missingness clearly marked;
- sortable evidence matrix for top candidates;
- pipeline/provenance timeline showing complete, skipped, failed, cached, or truncated stages;
- per-gene evidence cards for association, variants, G2P, constraint, drugs, and trials.

Avoid charts that imply calibrated probabilities or therapeutic efficacy. Tooltips should explain data limitations.

## Educational additions

- beginner/advanced explanations;
- contextual glossary for LOEUF, LoF, haploinsufficiency, G2P, ASO, siRNA, modifier, and ontology IDs;
- “Why this track?” decomposition based on deterministic fields;
- guided example questions and short knowledge checks;
- links to primary databases and retrieval timestamps;
- side-by-side “evidence” and “interpretation” language.

## Required caveats

The UI and exports must explain at least:

- source releases and schemas change;
- indirect ontology associations improve recall but can reduce specificity;
- rows are not independent patient counts;
- response caps and Quick mode make some evidence incomplete;
- trial matching is text-based and must be manually confirmed;
- target-centric drug status may refer to another indication;
- repeat expansions, non-coding mechanisms, allele specificity, isoforms, delivery, chemistry, toxicity, and off-targets are not adequately modeled;
- missing or failed lookups are not evidence of absence.
