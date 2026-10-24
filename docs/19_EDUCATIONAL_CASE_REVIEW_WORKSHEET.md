# Educational case review worksheet

Use this worksheet before publishing any Huntington disease, spinal muscular atrophy, Duchenne muscular
dystrophy, hereditary ATTR amyloidosis, or Dravet syndrome module. It is a scientific release gate, not a
substitute for domain review.

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
