# Educational case series

## Purpose

The English Case Studies view provides a versioned sequence of evidence-interpretation cases. It is organized
as a student research portfolio: each case demonstrates biomedical reasoning, source evaluation, reproducible
analysis, and scientific communication. Cases are educational research demonstrations, not clinical simulations.

## Publication contract

Every published case contains:

- a stable `example_id`, disease ontology identifier, creation date, engine version, and source releases;
- a frozen run copied from a completed application run and a deliberately selected teaching subset;
- an explicit research question, demonstrated capabilities, learning objectives, and candidate-specific questions;
- separate interpretation, limitation, and next-research-question sections;
- primary references for the biological premise and source identifiers beside application claims;
- visible missingness, truncation, and known model limitations;
- reviewer attribution, the source run ID, and a verified SHA-256 fixture digest;
- regression tests proving that the fixture does not change deterministic classifications or thresholds.

The ordinary teaching set contains three to five candidates. A smaller set is allowed only when the unchanged
run does not contain a third defensible candidate and the reason is recorded. Candidate records are copied
unchanged from completed runs; the teaching layer must not invent values or present candidate selection as a
treatment ranking.

The cases received a **source-bounded educational review by the ASO Compass maintainers**.
That review checks saved evidence, primary references, wording boundaries, fixture identity, and application
behavior. It is not represented as independent clinical or specialist review.

## Published progression

### 1. Amyotrophic lateral sclerosis

- **Identifier:** `MONDO_0004976`
- **Teaching candidates:** SOD1, TARDBP, FUS.
- **Learning focus:** multiple mechanism tracks, direction versus population-constraint context, capped
  evidence, and therapeutic precedent.
- **Debrief:** similar association strength can coexist with different mechanisms, safety context, evidence
  completeness, and translational precedent.

### 2. Huntington disease

- **Identifier:** `MONDO_0007739`
- **Teaching candidates:** HTT and SLC2A3.
- **Reviewed exception:** the unchanged default-threshold run returned only two candidates. Adding a third
  would require changing scientific thresholds or inventing a record.
- **Learning focus:** ordinary small-variant counts do not represent HTT repeat-expansion biology; association
  alone does not establish direction.
- **Debrief:** an `insufficient data` heuristic is not a negative statement about an established disease gene.

### 3. Spinal muscular atrophy

- **Identifier:** `MONDO_0001516`
- **Teaching candidates:** SMN1, SMN2, IGHMBP2.
- **Learning focus:** separate SMN1 disease biology from SMN2 splice modulation and therapeutic precedent;
  retain condition and inheritance context for comparator genes.
- **Debrief:** splice modulation can change productive transcript output without being the opposite of every
  knockdown strategy.

### 4. Duchenne muscular dystrophy

- **Identifier:** `MONDO_0010679`
- **Teaching candidates:** DMD, UTRN, LTBP4.
- **Learning focus:** distinguish gene-level direction from exon choice, reading-frame restoration, sequence
  design, and modifier evidence.
- **Debrief:** target prioritization and sequence or exon design are separate scientific problems.

### 5. Hereditary ATTR amyloidosis

- **Identifier:** `EFO_0700065`
- **Teaching candidates:** TTR, LYZ, B2M.
- **Learning focus:** connect toxic-protein reduction and precedent while keeping tissue delivery,
  indication, and unrelated amyloid biology separate.
- **Debrief:** precedent is useful context, not proof that every intervention or disease context is equivalent.

### 6. Dravet syndrome

- **Identifier:** `MONDO_0100135`
- **Teaching candidates:** SCN1A, SNX27, PCDH19.
- **Learning focus:** haploinsufficiency, the danger of indiscriminate knockdown reasoning, aggregate-variant
  model limits, and association-only comparators.
- **Debrief:** association strength cannot choose intervention direction; restoration-oriented logic still
  requires feasibility and safety review.

## Implemented application behavior

1. A shared typed manifest is the curriculum source for backend and frontend.
2. Backend and frontend loaders fail closed unless a published case has provenance, a verified fixture digest,
   candidate lessons, debrief points, references, and candidate-count compliance.
3. The backend verifies the disease, engine version, and selected symbols against each frozen fixture.
4. Case Studies routes directly to every published module and then to its complete saved evidence workspace.
5. Each module includes a research question, capabilities demonstrated, candidate comparisons, a visual
   evidence-source flow, source claim boundaries, ClinVar metadata exercises, interpretation, limitations,
   next research questions, primary reading, and optional evidence-bound AI on the saved fixture.
6. Tests verify manifest parity, fixture mirroring, candidate presence, route allow-listing, and deterministic
   fixture loading. The fixture generator performs read-only extraction and does no scientific recalculation.

## ClinVar exercise contract

New runs use `clinvar-interpretation-v1`, which retains bounded review-status, conflict, evidence/release date,
and variant-condition context from Open Targets EVA. The upstream query does not expose a reliable submitter
count, so that field remains explicitly unavailable and is deferred. Older fixtures show missing metadata
rather than fabricating it. These educational fields do not change classifications, thresholds, scores, or
shortlist order.
