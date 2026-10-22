# ADR-009: Render deterministic paged print reports

## Status

Accepted and implemented — 2026-10-21.

## Context

Printing the live results page delegated pagination of one long candidate table to Chromium. Reports with
more than a few dozen candidates intermittently lost or clipped columns on continuation pages. The live
page also mixed interactive controls, optional AI output, and deterministic results, making the scope of a
printed report unclear.

## Decision

1. The interactive results view and print report use separate render structures.
2. Candidate rows are split into bounded groups of at most 12. Every group is an independent CSS Grid on
   an explicit print page with its own complete column header. The print grid avoids Chromium's native
   table-fragmentation path while retaining table roles for accessibility and testability.
3. **Print summary** includes the deterministic run overview, saved priority shortlist, and a manual-review
   queue for capped, ambiguous, precedent-bearing, or incompletely checked candidates.
4. **Print full report** adds the complete saved candidate set as an appendix.
5. Both reports show shortlist rank, run ID, engine and source release, run mode, timestamps, warnings,
   terminology guidance, research-use disclaimer, and page numbers.
6. Target-level approved-drug and ASO/trial matches are labelled as precedent requiring indication and
   source confirmation; they are not represented as treatment recommendations.
7. Optional AI output is excluded from the deterministic print report. AI content remains available in the
   interactive interface and can be copied or exported separately if a future reviewed format is added.
8. Browser regression coverage must verify page chunk bounds, complete headers, complete appendix rows,
   settled print layout, and successful PDF generation.
9. The candidate-evidence drawer provides a separate one-page deterministic report containing the saved
   classification, scores, mechanism and variant evidence, therapeutic precedent, primary-record URLs,
   completeness indicators, run provenance, and research-use disclaimer. Optional AI explanations are
   excluded from this report.
10. The interactive candidate-evidence drawer can expand to the full application viewport and restore to
    its split-pane width without changing the saved record or its print representation. Embedded-space
    spacing keeps drawer actions below the hosting toolbar.

## Consequences

- Browser table-fragmentation behavior no longer controls candidate pagination.
- Summary reports are shorter and focus review on actionable and uncertain records.
- Full reports remain available for audit and archival use.
- A report generated from a completed run does not change classifications, scores, shortlist positions,
  evidence, or provenance.
- Candidate reports can be reviewed or archived without printing the obscured interactive results page.
