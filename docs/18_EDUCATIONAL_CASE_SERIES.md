# Educational case series

## Purpose

Extend the existing English Learn view from a single ALS walkthrough into a versioned sequence of
evidence-interpretation cases. Cases teach source scope, mechanism direction, missingness, therapeutic
precedent, and uncertainty. They are educational research demonstrations, not clinical simulations.

## Non-negotiable case contract

Every published case must contain:

- a stable `example_id`, disease ontology identifier, creation date, engine version, and source releases;
- a frozen run record and three to five deliberately selected candidate records;
- explicit learning objectives and a short debrief;
- source identifiers adjacent to scientific claims;
- visible missingness, truncation, and known model limitations;
- a scientific-review status and reviewer attribution before release;
- regression tests proving that the fixture does not change deterministic classifications or thresholds.

Candidate selection is a scientific curation step. Candidate records must come from a reproducible run or
reviewed source fixture; they must not be invented to make a lesson work. The application may explain why a
candidate was selected for teaching, but must not present the selection as a treatment recommendation.

## Progression

### 1. Amyotrophic lateral sclerosis — available foundation

- **Identifier:** `MONDO_0004976`
- **Learning objectives:** compare multiple mechanism tracks; distinguish association from direction;
  recognize constraint warnings, capped evidence, and SOD1 therapeutic precedent.
- **Current teaching candidates:** the bundled fixture contains SOD1, TARDBP, TUBA4A, FUS, C9orf72, and
  NEK1. A future exercise view should select three to five per activity rather than changing the fixture.
- **Debrief:** similar association strength can coexist with different mechanisms, safety context, evidence
  completeness, and translational precedent.

### 2. Huntington disease — pending reviewed fixture

- **Identifier:** `MONDO_0007739`
- **Learning objectives:** understand why a strong gene–disease relationship does not guarantee that ordinary
  small-variant counts represent the causal mechanism; identify repeat expansion and non-coding blind spots.
- **Candidate requirement:** select three to five records from a frozen run only after verifying that the set
  demonstrates the intended contrast without implying that weak candidates are negative controls.
- **Debrief:** HTT is a test of model boundaries; “insufficient data” in a variant-count heuristic is not a
  negative statement about the established disease gene.

### 3. Spinal muscular atrophy — pending reviewed fixture

- **Identifier:** `MONDO_0001516`
- **Learning objectives:** distinguish SMN1 disease biology from SMN2 splice modulation; connect a known ASO
  precedent to mechanism without generalizing efficacy to unrelated targets.
- **Candidate requirement:** a reviewed three-to-five-candidate set must preserve the roles of SMN1 and SMN2
  and clearly label any comparator candidates.
- **Debrief:** splice modulation can change productive transcript output without being the opposite of every
  knockdown strategy.

### 4. Duchenne muscular dystrophy — pending reviewed fixture

- **Identifier:** `MONDO_0010679`
- **Learning objectives:** introduce reading-frame restoration, exon skipping, transcript specificity, and the
  difference between a gene-level track and a sequence-level ASO design.
- **Candidate requirement:** select reviewed records that make the DMD mechanism visible without implying that
  ASO Compass designs an exon-skipping oligonucleotide.
- **Debrief:** target prioritization and sequence/exon design are separate scientific problems.

### 5. Hereditary ATTR amyloidosis — pending reviewed fixture

- **Identifier:** `EFO_0700065`
- **Learning objectives:** connect toxic protein production, knockdown direction, tissue delivery, and existing
  therapeutic precedent while keeping indication-specific claims bounded.
- **Candidate requirement:** select a reviewed set that includes TTR and transparent comparators derived from
  the same frozen run.
- **Debrief:** precedent makes a target translationally informative; it does not make every disease context or
  intervention equivalent.

### 6. Dravet syndrome — pending reviewed fixture

- **Identifier:** `MONDO_0100135`
- **Learning objectives:** understand dominant loss of function and haploinsufficiency; recognize why further
  knockdown may be directionally hazardous; distinguish restoration from unrestricted overexpression.
- **Candidate requirement:** select three to five reviewed records that preserve SCN1A's mechanism and label
  comparator mechanisms accurately.
- **Debrief:** association strength alone cannot choose intervention direction, and restoration-oriented logic
  still requires feasibility and safety review.

## Implementation sequence

1. Keep ALS as the only published case until the next fixture passes scientific review.
2. Add a typed case manifest separate from candidate data; the manifest holds objectives, debrief, review
   status, and fixture filename.
3. Generalize the current example loader and example AI routes from one hard-coded file to the reviewed
   manifest allow-list.
4. Add case selection to Learn only for `published` manifests. Never display placeholder candidate results.
5. Add schema, fixture, golden-case, UI, and AI grounding tests for each case independently.

## ClinVar exercise contract

New runs use `clinvar-interpretation-v1`, which retains bounded review-status, conflict, evidence/release date,
and variant-condition context from Open Targets EVA. The current upstream query does not expose a reliable
submitter count, so the UI reports that field as unavailable and links to primary ClinVar records. Older frozen
fixtures remain valid and explicitly show that interpretation metadata was not retained. These educational
fields do not change deterministic classifications, thresholds, scores, or shortlist order.
