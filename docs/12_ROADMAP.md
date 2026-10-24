# Roadmap

## Release 0 — reference baseline

- characterization tests around v4.1;
- documented API/data contracts;
- reproducible small fixtures;
- license and citation decisions.

## Release 1 — public demonstration MVP

- FastAPI + SQLModel + Alembic;
- React/Vite/TypeScript guided UI;
- shared Supabase PostgreSQL tagged by environment;
- Render backend and Hugging Face Static Space;
- one active run, persisted queue/progress, retries, metadata, warnings, exports;
- precomputed examples and educational glossary;
- no authentication required; conservative anonymous retention.

## Release 1.1 — usability and evidence depth

- richer plots and comparison views;
- contextual terminology popovers and candidate evidence-source maps;
- a bounded ClinVar interpretation checkpoint with versioned review-status, conflict, date, and
  variant-condition metadata; submitter count remains explicitly unavailable in the current upstream contract;
- a scientifically reviewed educational case series following `docs/18_EDUCATIONAL_CASE_SERIES.md`;
- saved parameter presets and shareable read-only run links;
- stronger accessibility/usability testing with students;
- source-status dashboard; deterministic summary/full print reports are implemented, while signed or
  server-generated archival report bundles remain future work;
- validated disease preset catalog.

## Release 1.2 — optional OpenAI explanations

- run summary, gene explanation, constrained Q&A;
- structured outputs, audit records, caching, budgets, evaluation;
- no web search initially; saved deterministic evidence only.

## Release 2 — collaboration

- Supabase Auth;
- private histories and ownership;
- reviewed RLS/grants;
- comments/review state and curated overrides with attribution;
- separate development and demonstration Supabase projects.

## Release 3 — science ecosystem integration

- Galaxy wrapper for reproducible workflow execution and domain visibility;
- richer notebook tutorials and classroom exercises;
- versioned data snapshots and DOI-capable archive release;
- standards-based provenance/export where useful.

## Release 4 — scalable execution and optional GPU stage

- durable external job queue/worker;
- autoscaling and observability appropriate to traffic;
- separately validated sequence-level downstream models;
- GPU only for workloads that demonstrably benefit;
- governance and scientific evaluation before any expanded clinical framing.

## Deferred intentionally

- patient data or clinical record ingestion;
- automated treatment recommendations;
- opaque AI reranking;
- arbitrary SQL/agent access;
- large-scale literature crawling without citation validation;
- reliance on free-tier hosting for important research records.
