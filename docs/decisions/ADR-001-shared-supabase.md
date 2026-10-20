# ADR-001: One Supabase project for local and demo in Phase 1

- Status: accepted for initial prototype
- Date: 2026-10-19

## Context

Using separate projects reduces the chance that local development affects the deployed demonstration. The current preference is nevertheless to begin with one shareable Supabase PostgreSQL project for simplicity.

## Decision

Local FastAPI and the deployed Render FastAPI use the same Supabase project. The trusted backend setting identifies records as `local`, `demo`, or `test`. Routine automated tests do not connect to the shared project.

## Consequences

Benefits:

- less initial account/configuration work;
- immediate access to shared demonstration records;
- one schema and one set of migrations.

Costs/risks:

- local schema or data mistakes can affect the demo;
- migrations have no isolated rehearsal target unless a disposable PostgreSQL database is supplied;
- credentials have a larger blast radius;
- quotas are shared;
- environment filtering becomes a required correctness feature.

## Required safeguards

- required/indexed environment on mutable runs;
- backend-derived environment, never trusted from client input;
- tests use temporary SQLite by default;
- guarded cleanup by exact environment and cutoff;
- reviewed backward-compatible migrations;
- backup/export before risky schema operations;
- no broad reset/truncate workflow;
- configuration must permit a second project without code changes.

## Revisit trigger

Split into separate projects before onboarding meaningful external users, preserving important research records, enabling multiple developers, or running destructive migration experiments.

