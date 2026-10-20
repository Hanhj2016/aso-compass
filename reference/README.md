# Reference artifacts

These files are the reviewed source baseline for **ASO Compass**. Their legacy ASO Target Finder names are intentionally preserved for provenance and compatibility.

## Engine

- `engine/aso_target_finder_enhanced.py` — enhanced Python v4.1 implementation; primary backend porting reference.
- `engine/aso_target_finder_v4_enhanced.R` — enhanced R counterpart.
- `engine/aso_target_finder_v4.R` — supplied v4 R source before the aligned enhancements.
- `engine/requirements_colab.txt` — dependencies for the existing notebook/module, not the future FastAPI project lockfile.
- `engine/COLAB_PACKAGE_README.md` — existing behavior, inputs, outputs, and caveats.
- `engine/REFERENCE_VALIDATION.md` — validation record and its limitations.

## Notebooks

- `notebooks/ASO_Target_Finder_Python_v4_Colab_Enhanced.ipynb`
- `notebooks/ASO_Target_Finder_R_v4_Colab_Enhanced.ipynb`

## Rules

- Do not edit these reference copies while implementing the web application.
- Characterize behavior with fixtures/tests before extracting/refactoring.
- The Python engine is synchronous and notebook-oriented; wrap its scientific transformations, but redesign execution/progress/persistence for the web.
- Live upstream counts are not stable golden values.
- Preserve source attributions and scientific caveats.
