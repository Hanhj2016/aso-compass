# ADR-010: Generate explicitly named PDF downloads in the browser

## Status

Accepted.

## Context

ASO Compass runs inside a cross-origin Hugging Face Space iframe. Chromium and the Linux GTK save
dialog derive the filename for native `window.print()` output from the outer Hugging Face document,
even when the embedded application prints a separately titled document. The web print API has no
standard parameter for a suggested output filename.

## Decision

1. The results and candidate-evidence actions generate PDF files in the browser with jsPDF and
   jsPDF-AutoTable instead of relying on the native print dialog.
2. The application supplies explicit, sanitized filenames:
   - `ASO-Compass_<disease>_<summary|full>-report_<run>.pdf`
   - `ASO-Compass_<disease>_<gene>_candidate-evidence_<run>.pdf`
3. Run reports preserve deterministic classifications, scores, warnings, shortlist order, provenance,
   completeness signals, and the research-use disclaimer.
4. An already-generated AI run summary or candidate explanation may be appended as a separately
   labeled optional section. Generating a PDF never invokes AI and never changes deterministic data.
5. PDF generation is dynamically imported so the PDF libraries are not part of the initial application
   bundle.
6. End-to-end tests exercise the Hugging Face-equivalent iframe sandbox and assert the browser download's
   suggested filename for run and candidate reports.

## Consequences

- Filenames are stable across direct hosting and embedded Hugging Face Spaces.
- Users download a ready PDF instead of passing through the browser print-preview dialog. A downloaded
  report can still be printed with the system PDF viewer.
- The generated PDF is deliberately implemented from saved structured data rather than a screenshot, so
  text remains selectable and tabular evidence remains legible.
- PDF rendering is a second presentation implementation and must remain covered by tests when report
  fields change.
