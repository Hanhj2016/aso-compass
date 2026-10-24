# Educational case review worksheet

Use this worksheet before publishing or replacing any curated teaching module. It is a scientific-content
release gate, not a substitute for independent domain or clinical review.

## 1. Freeze and identify the evidence

- Case ID and disease ontology identifier:
- Run ID, run mode, engine version, and completion time:
- Open Targets and other source release/version dates:
- Fixture filename and SHA-256 digest:
- Run warnings, caps, failed sources, and known unmodeled mechanisms:

The fixture must be copied from a reproducible completed run. Never invent or edit candidate values to make
the lesson clearer.

## 2. Select three to five teaching candidates

For every selected gene, record:

| Gene | Why it is educational | Deterministic track and source | Important limitation | Primary record checked |
|---|---|---|---|---|
|  |  |  |  |  |

Selection must demonstrate the stated learning objective without implying a treatment ranking or treating a
comparator as a negative control. Confirm that every symbol exists unchanged in the frozen fixture.

## 3. Review the scientific teaching claims

- [ ] Association is kept separate from causation and intervention direction.
- [ ] Mechanism and inheritance claims are supported by the cited source record.
- [ ] ClinVar labels retain condition, review status/stars, date/version, and conflict context when available.
- [ ] “No evidence returned,” “not checked,” “capped,” and “benign” are not conflated.
- [ ] Population constraint is presented as context, not a safety verdict.
- [ ] Drug or trial precedent is bounded to the saved target, indication, modality, and source scope.
- [ ] The debrief names the model boundary specific to the disease.
- [ ] The research-use disclaimer remains visible in the case and exports.

## 4. Disease-specific check

- **Huntington disease:** ordinary small-variant counts must not be presented as covering repeat expansions.
- **Spinal muscular atrophy:** distinguish SMN1 disease biology from SMN2 splice modulation.
- **Duchenne muscular dystrophy:** distinguish gene-level direction from exon and sequence design.
- **Hereditary ATTR amyloidosis:** separate knockdown direction, delivery, and indication-specific precedent.
- **Dravet syndrome:** make haploinsufficiency and the risk of non-selective knockdown explicit.

## 5. Approval and publication

- Scientific reviewer and role:
- Review date:
- Reviewed fixture digest:
- Corrections or unresolved limitations:
- Approval decision:

Only after approval should the identical backend and frontend manifests receive the fixture metadata,
three-to-five candidate symbols, reviewer attribution, and `published` status. The manifest loaders fail closed
if provenance is incomplete, a planned case exposes candidates, or a selected candidate is absent from the
fixture. Run schema, golden-case, UI, AI-grounding, print, and production-build tests before deployment.

## Published fixture ledger — 2026-10-24

The five additions below were reviewed by the ASO Compass maintainers for source-bounded educational use.
Candidate data were copied unchanged from completed runs. This ledger does not claim independent specialist
or clinical review.

| Case | Source run | Teaching candidates | Fixture SHA-256 | Important boundary |
|---|---|---|---|---|
| Huntington disease | `cb86fd11-85e4-41cb-9b71-803516a39259` | HTT, SLC2A3 | `24698af59e821f9c9fc5b744005684316514b7e7f2227e8d945fa88f18c15610` | Repeat expansions are outside ordinary small-variant consequence counts. Only two candidates passed the unchanged run; this reviewed exception is explicit. |
| Spinal muscular atrophy | `abb11b37-ebef-47a1-896f-a65746f72852` | SMN1, SMN2, IGHMBP2 | `fcc5d283dd6d43059ff2dec6d0d6fbaa7b4ef8d080b47106ddcefb93c5f7663c` | SMN1 disease causation and SMN2-directed splice modulation are separate biological questions. |
| Duchenne muscular dystrophy | `85686299-3d81-449e-b40f-8a1736688392` | DMD, UTRN, LTBP4 | `9cb39d1320170d19035d18bcd966569daf3d75ff271801ab3ee6e6b84364b98e` | A gene-level direction cannot choose an exon, sequence, dose, or mutation-amenable population. |
| Hereditary ATTR amyloidosis | `0f93020b-0386-42d9-b309-c005175b29dc` | TTR, LYZ, B2M | `f0ed1b70853a7416e7d30bded6b3cd250806c406e5d61ad67b9f3ffabf64bfb6` | Precedent remains bounded by indication, modality, tissue, and phenotype. |
| Dravet syndrome | `b0bae039-c790-43c8-80d1-f9d2138ce42c` | SCN1A, SNX27, PCDH19 | `a50b2c31aacd62253b7fb27ff8724bfc2d44eb057d68a04f0d756cda842121ee` | Aggregate variant mixtures cannot replace dosage-sensitive mechanism review; indiscriminate knockdown reasoning is hazardous. |

Primary biological references are stored beside each case in the manifest. The backend verifies every digest at
load time, and the frontend/backend fixture-mirroring test prevents the two deployment copies from drifting.
