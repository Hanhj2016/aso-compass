---
title: ASO Compass
emoji: 🧭
colorFrom: green
colorTo: yellow
sdk: static
app_file: dist/index.html
fullWidth: true
header: mini
short_description: Evidence-guided ASO target exploration and education
tags:
  - biology
  - genetics
  - bioinformatics
  - antisense-oligonucleotides
  - education
---

# ASO Compass

**Evidence-guided target exploration for research and education.**

ASO Compass is a transparent research demonstration for exploring disease-associated genes, genetic mechanisms, safety signals, therapeutic precedent, and candidate antisense oligonucleotide strategy tracks.

For hypothesis generation and education only. Not for clinical decision-making. Live evidence can be incomplete, truncated, or unavailable; inspect source links and warnings.

The application source, methodology, validation notes, and citation guidance are maintained in the
[ASO Compass GitHub repository](https://github.com/Hanhj2016/aso-compass). The static interface calls the
[ASO Compass API](https://aso-compass-api.onrender.com/api/v1/config/public).

The production bundle is built and published from GitHub Actions. `VITE_API_BASE_URL` is public build-time
configuration; database credentials, OpenAI credentials, and application access tokens must never be placed in
the Space repository or in a `VITE_` variable.
