# Bounded ALS live smoke test

Date: 2026-10-19

This is a connectivity, current-schema, transformation, and invariant check—not scientific validation.

## Parameters

- disease: `MONDO_0004976`
- overall association score: at least `0.85`
- genetic association score: at least `0.80`
- variant, G2P, and drug enrichment: capped at one gene
- ClinicalTrials.gov: enabled
- Open Targets association page size: 500

## Observed

- Open Targets release: `26.09`
- linked targets: 6,329
- passing candidates: one (`SOD1`, `ENSG00000142168`)
- final track/source: `knockdown`, ClinVar heuristic
- drug status: `Approved: TOFERSEN`
- gene-matched interventional trials: one
- condition-level candidate studies returned: 17
- drug schema source: `Target.drugAndClinicalCandidates`
- five-track and score invariants: PASS
- warnings: none

The stable regression assertions remain fixture-based. Live counts and source releases may change.
