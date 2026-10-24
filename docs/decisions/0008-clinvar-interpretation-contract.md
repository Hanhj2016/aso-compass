# ADR 0008: Bounded ClinVar interpretation metadata

## Status

Accepted on 2026-10-23.

## Context

The deterministic engine currently uses Open Targets EVA records to count pathogenic consequence categories. Educational interpretation also needs review status, conflicts, dates, version, and variant–condition context. The current Open Targets evidence contract exposes review-status text, rsID, evidence/release dates, release version, and source condition, but not a reliable submitter count.

## Decision

- Keep the existing classification inputs, thresholds, precedence, and shortlist behavior unchanged.
- Persist a versioned, bounded `clinvar_interpretation` JSON object on each candidate.
- Retain candidate-level coverage summaries and at most 12 representative records. Prefer conflicting and higher-review records in that learning sample.
- Persist the same object in normalized evidence provenance.
- Mark unavailable fields explicitly. `submitter_count` remains `null`; the UI must not infer it from review-status text.
- Treat these fields as educational interpretation context, not new deterministic classification inputs.

## Consequences

Existing candidates migrate with an empty object and remain readable. New runs expose richer ClinVar context without increasing the number of upstream calls. The representative sample is not a replacement for reviewing the primary ClinVar record, and truncation continues to require manual review.
