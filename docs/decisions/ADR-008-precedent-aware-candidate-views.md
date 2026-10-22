# ADR-008: Preserve therapeutic precedent and separate research views

## Status

Accepted for implementation — 2026-10-21. Independent scientific review remains pending.

## Context

The Phase 1 shortlist automatically removed candidates with a target-level approved-drug record whenever
the Open Targets drug lookup completed. That behavior was useful for a narrow novel-target discovery
workflow, but it silently hid strong positive controls and translational precedents. The saved drug summary
also does not yet establish that an approval is for the disease being analyzed, the same intervention
direction, the same modality, or the same patient population.

## Decision

1. New runs retain approved-drug candidates in the deterministic shortlist by default.
2. `exclude_approved=true` and `exclude_aso_precedent=true` remain explicit, opt-in run parameters.
3. Candidate Explorer defaults to **All evidence** and offers independent display views:
   - Saved priority shortlist;
   - Novel-target discovery;
   - Translational precedent.
4. The novelty view may hide target-level approved-drug records, but must state that indication matching
   has not been established.
5. Filtering, sorting, and pagination are presentation operations. They do not modify saved candidates,
   deterministic classifications, scores, shortlist positions, exports, or AI evidence packets.
   The frontend drains the paginated candidate API before applying these browser-side operations, so the
   controls act on the complete saved candidate set rather than only the first API page.
6. Existing completed runs remain immutable and retain the shortlist positions produced by their original
   engine behavior.
7. New runs record engine version `4.2-guided`; the underlying v4.1 track thresholds and evidence precedence
   remain unchanged.

## Consequences

- Known targets remain visible for education, benchmarking, repurposing, and next-generation optimization.
- Novelty screening becomes an explicit user choice rather than a hidden scientific exclusion.
- The interface must use **target-level approved drug** until disease-specific approval provenance is stored.
- A future indication-aware model should store target, drug, disease/indication, modality, direction, stage,
  source identifier, and provenance as structured evidence before offering an “approved for this disease”
  filter.
