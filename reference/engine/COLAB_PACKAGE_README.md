# ASO Target Finder v4 — Google Colab package

This package aligns the supplied `aso_target_finder_v4.R` with guided R and Python editions. The recommended notebooks are:

- `ASO_Target_Finder_R_v4_Colab_Enhanced.ipynb`
- `ASO_Target_Finder_Python_v4_Colab_Enhanced.ipynb`

Compatibility filenames without `v4` contain the same enhanced notebooks. The package also includes the original v4 R source, enhanced R source, reusable Python module, validation notes, and dependencies.

## What v4 does

For one Open Targets disease/phenotype ID, the workflow:

1. Retrieves target associations and filters on overall and genetic-association scores.
2. Retrieves gnomAD LOEUF constraint.
3. Counts pathogenic/likely pathogenic EVA/ClinVar LoF, canonical-splice, additional splice-related, and missense/in-frame consequences.
4. Retrieves Gene2Phenotype (G2P) mechanism and inheritance evidence.
5. Discovers the current Open Targets drug schema and distinguishes generic oligonucleotide records from named ASO/siRNA precedent.
6. Searches ClinicalTrials.gov API v2 for condition-related antisense/oligonucleotide/siRNA studies and text-matches genes.
7. Assigns mechanism tracks and exports a priority shortlist.

Mechanism precedence is: **user-supplied manual override → G2P → ClinVar count heuristic → modifier**. V4 intentionally has no pre-seeded memory-derived override table.

ClinVar rules remain heuristic:

- fewer than 5 classified LoF + missense records: `insufficient data`;
- LoF fraction ≥ 0.60: `splice/upregulation`;
- LoF fraction ≤ 0.25: `knockdown`;
- otherwise: `ambiguous`;
- association evidence with zero returned directional variant evidence can enter the `modifier` track.

LOEUF changes safety warnings, not the mechanism classification. Splice-related fraction includes canonical splice and selected non-canonical/intronic/UTR/synonymous consequence categories, matching v4.

## Inputs and guided controls

The required input is an Open Targets disease ID such as `MONDO_0004976`; colon form (`MONDO:0004976`) is also accepted. Both enhanced notebooks provide a dropdown with ALS, Alzheimer disease, Parkinson disease, Huntington disease, Duchenne muscular dystrophy, spinal muscular atrophy, Dravet syndrome, and hereditary ATTR amyloidosis, plus a custom-ID option.

| Input | Default | Meaning |
|---|---:|---|
| `min_score` | 0.20 | Minimum overall association score |
| `min_genetic` | 0.10 | Minimum genetic-association score |
| `loeuf_intolerant` | 0.60 | Threshold for the LoF-intolerance warning |
| `use_variants` | true | Retrieve EVA/ClinVar consequence evidence |
| `use_g2p` | true | Retrieve G2P mechanism/inheritance |
| `check_drugs` | true | Retrieve Open Targets drug/ASO records |
| `check_trials` | true | Search ClinicalTrials.gov API v2 |
| `exclude_approved` | false | Remove approved-drug targets after annotation |
| `exclude_aso_precedent` | false | Remove existing ASO precedent from the shortlist |
| `include_modifiers` | true | Include modifiers after mechanism-called genes in the shortlist |
| `curated` | `NULL`/`None` | Optional manual table: `gene_symbol`, `strategy`, `precedent` |

Enhanced editions add Full/Quick mode, a 24-hour response cache, explicit refresh, evidence-cap warnings, confidence explanations, filters, a per-gene evidence explorer, plots, comprehensive metadata, and a standalone searchable HTML report. Quick mode caps variant/G2P and drug enrichment at 25 genes and is explicitly incomplete.

## Run in Colab

### R

1. Upload `ASO_Target_Finder_R_v4_Colab_Enhanced.ipynb` to Google Colab.
2. Select **Runtime → Change runtime type → R**, accelerator **None**.
3. Run all cells from top to bottom.
4. Choose the disease and controls, then inspect concise results, warnings, evidence explorer, validation, and charts.
5. Run export. The ZIP is created under `/content`, for example `/content/MONDO_0004976_aso_results_enhanced.zip`.
6. Download it from Colab’s **Files** pane.

### Python

1. Upload `ASO_Target_Finder_Python_v4_Colab_Enhanced.ipynb`.
2. Select **Python 3**, accelerator **None**.
3. Run the install and implementation cells, then the controls cell.
4. Select settings and press **Run ASO Finder**.
5. Run the result, visualization, and export cells. Colab will attempt to download the ZIP automatically.

The notebooks are standalone; separate `.R` and `.py` files are supplied for reuse and auditing.

## Network and dependencies

R: `httr`, `jsonlite`, `dplyr`, `digest`; notebook visuals use `ggplot2` and `IRdisplay`.

Python: `requests`, `pandas`; notebook controls/visuals use `ipywidgets`, `plotly`, and IPython.

Outbound HTTPS is required for:

- `https://api.platform.opentargets.org/api/v4/graphql`
- `https://clinicaltrials.gov/api/v2/studies`

No GPU is useful for the current network/tabular pipeline. A future GPU stage should consume a frozen shortlist and run a specifically GPU-capable sequence, activity, accessibility, toxicity, or off-target model separately.

## Outputs

Every completed run writes eight candidate CSVs:

1. `all_candidates_annotated.csv`
2. `knockdown_candidates.csv`
3. `splice_upregulation_candidates.csv`
4. `ambiguous_candidates.csv`
5. `modifier_candidates.csv`
6. `insufficient_data.csv`
7. `positive_controls.csv`
8. `priority_shortlist.csv`

When studies are found, `aso_trials_for_condition.csv` is also written. Enhanced editions additionally write `run_summary.csv`, `run_metadata.json`, and `concise_report.html`. The ZIP path exists only after the run and export cells execute; it is not a pre-hosted download.

## Scientific caveats

- This is hypothesis generation, not a clinical decision tool or validated therapeutic ranking.
- G2P depends on current panel content and allelic-requirement annotation. Review its underlying evidence.
- Missense-heavy evidence does not establish toxic gain of function; truncating evidence does not prove that upregulation is feasible or safe.
- EVA/ClinVar rows are not independent patient counts and can reflect duplicate submissions, ascertainment, reclassification, indirect disease evidence, and the 500-row response cap.
- Trial matching is text-based. Intervention/title matches are stronger than summary-only matches, but both need manual confirmation; an absence is not proof that no relevant trial exists.
- Drug status is target-centric and can concern another indication. Failed or skipped lookups are not negative evidence.
- Repeat expansions, regulatory/non-coding mechanisms, allele specificity, dominant-negative biology, isoforms, expression, delivery, chemistry, toxicity, and off-targets are not modeled adequately.
- `enableIndirect: true` increases recall through ontology-related diseases but reduces specificity.
- Live sources and schemas change. Preserve `run_metadata.json`, review warnings, and rerun validation.
