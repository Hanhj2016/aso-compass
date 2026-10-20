# Validation record — v4 guided package

Date: 2026-10-18

## Live bounded Python test

Settings: disease `MONDO_0004976`; overall score ≥ 0.85; genetic score ≥ 0.80; one gene maximum for variant/G2P and drug enrichment; ClinicalTrials.gov enabled; CSV writing initially disabled.

Observed:

- Open Targets release: `26.09`
- linked targets: 6,329
- passing targets: 1 (`SOD1`, `ENSG00000142168`)
- EVA evidence: 11 LoF, 129 missense, 0 additional splice-related; 277/277 rows returned; not truncated
- G2P mechanism/inheritance for this disease-gene query: not returned
- final track/source: `knockdown`, ClinVar heuristic
- drug status: `Approved: TOFERSEN`
- ASO precedent: Open Targets TOFERSEN plus one strongly gene-matched interventional trial; the full condition query returned 17 candidate studies for review
- five-track invariant validation: PASS
- identifier uniqueness, score ranges, evidence-cap coherence, metadata, confidence tiers, and cache metadata: PASS

This is a connectivity, schema, transformation, and invariant smoke test—not scientific validation of the target ranking.

## Export test

A second bounded run wrote and verified:

- 8 candidate CSVs;
- 1 condition-trials CSV;
- `run_summary.csv`;
- `run_metadata.json` with implementation version `4.1-guided` and the modifier track;
- `concise_report.html`.

Export validation: PASS (12 files total).

## Static and notebook checks

- Python module imports and compiles: PASS.
- Every non-magic Python notebook code cell compiles: PASS.
- Both v4 notebook files parse as notebook format v4: PASS.
- Enhanced R source passed a quote/comment-aware delimiter balance check: PASS (1,308 lines).
- Enhanced R contains retries, 60-second timeouts, SHA-256 response caching for Open Targets and ClinicalTrials.gov, evidence-return/truncation fields, five-track metadata, and the standalone report generator.
- A Colab full R run exposed an export-only regression (`n_files` was referenced before assignment). The export block was corrected to initialize the count and write the optional trials CSV before writing summary/metadata; the enhanced source, notebook, and package were rebuilt.

An R interpreter was not installed locally, so the enhanced R implementation was not executed here. Run its built-in validation cell in a Colab R runtime before interpreting results. Exact live counts can change with source releases.
