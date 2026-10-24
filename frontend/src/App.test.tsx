import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const { downloadRunPdfMock, downloadCandidatePdfMock } = vi.hoisted(() => ({
  downloadRunPdfMock: vi.fn(),
  downloadCandidatePdfMock: vi.fn(),
}));
vi.mock("./pdfExport", () => ({
  downloadRunPdf: downloadRunPdfMock,
  downloadCandidatePdf: downloadCandidatePdfMock,
}));

afterEach(() => { cleanup(); localStorage.clear(); sessionStorage.clear(); window.history.replaceState(null, "", "/"); vi.clearAllMocks(); vi.restoreAllMocks(); });

describe("ASO Compass", () => {
  it("requires acknowledgement before a run can start", async () => {
    const user = userEvent.setup();
    render(<App />);
    const button = screen.getByRole("button", { name: /begin evidence analysis/i });
    expect(button).toBeDisabled();
    await user.click(screen.getByRole("checkbox"));
    expect(button).toBeEnabled();
    expect(screen.getByText(/quick mode is incomplete/i)).toBeVisible();
  });

  it("leads with application capabilities and keeps operations secondary", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Case Studies" }));
    expect(screen.getByRole("heading", { name: /biological evidence becomes a defensible research interpretation/i })).toBeVisible();
    expect(screen.getByRole("heading", { name: "What this portfolio demonstrates" })).toBeVisible();
    expect(screen.getByRole("heading", { name: /portfolio in biomedical reasoning and research software/i })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Synthesize target evidence" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "The five research tracks" })).toBeVisible();
    expect(screen.getByText("Disease query", { selector: "h3" })).not.toBeVisible();
    await user.click(screen.getByText("Supporting context"));
    expect(screen.getByText("Disease query", { selector: "h3" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "简体中文" })).not.toBeInTheDocument();
  });

  it("provides a searchable English in-application glossary", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Methods & Glossary" }));

    expect(window.location.hash).toBe("#/glossary");
    expect(screen.getByRole("heading", { name: "Methods & Glossary" })).toBeVisible();
    expect(screen.getByRole("heading", { name: /how the application builds a defensible result/i })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Core biology" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "LOEUF" })).toBeVisible();
    expect(screen.queryByText("简体中文")).not.toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Search glossary" }), "dominant negative");
    expect(screen.getByRole("heading", { name: "DN" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "ASO" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByRole("heading", { name: "ASO" })).toBeVisible();
  });

  it("constrains AI comparison selection to saved candidates", async () => {
    const run = {
      id: "00000000-0000-0000-0000-000000000001", environment: "test", disease_id: "MONDO_1",
      disease_label: "Example disease", status: "succeeded", parameters: {}, engine_version: "4.1-guided",
      upstream_metadata: {}, warnings: [], validation: {}, started_at: null, completed_at: null,
      error_code: null, error_message: null, created_at: "2026-01-01", updated_at: "2026-01-01",
      research_use_disclaimer: "For hypothesis generation and education only. Not for clinical decision-making.",
    };
    const candidate = (gene: string, ensembl: string) => ({
      ensembl_id: ensembl, gene_symbol: gene, gene_name: `${gene} name`, overall_score: 0.8,
      genetic_score: 0.7, loeuf: null, n_evidence: null, n_evidence_returned: null,
      evidence_truncated: false, n_lof: null, n_splice: null, n_splice_extra: null, n_missense: null,
      frac_lof: null, frac_splice_related: null, g2p_mech: null, inheritance: null,
      clinvar_call: "modifier", final_call: "modifier", call_source: "assoc only",
      confidence_tier: "Association only", confidence_reason: "Direction unknown.", flag: "", note: "",
      drug_status: gene === "GENEA" ? "Approved: Example drug" : "None found",
      has_approved_drug: gene === "GENEA", n_drugs: gene === "GENEA" ? 1 : 0,
      drug_max_stage: gene === "GENEA" ? "Approved" : null,
      approved_drugs: gene === "GENEA" ? "Example drug" : "", oligo_drug: null, oligo_names: "", aso_drug: null, aso_names: "",
      aso_trial_n: 0, aso_trial_weak: 0, aso_trial_best: null, aso_trial_ids: "", aso_precedent: "",
      shortlist_position: null, completeness: "complete",
    });
    const candidates = [candidate("GENEA", "ENSG1"), candidate("GENEB", "ENSG2"), candidate("GENEC", "ENSG3"), candidate("GENED", "ENSG4")];
    const comparison = {
      insight_id: "00000000-0000-0000-0000-000000000002", cached: false, generated_at: "2026-01-01",
      model: "test-model", prompt_version: "candidate-comparison-v1",
      output_schema_version: "candidate-comparison-v1", compared_gene_symbols: ["GENEA", "GENEB"],
      source_ids: ["candidate:ENSG1", "candidate:ENSG2"], ai_generated: true,
      research_use_disclaimer: run.research_use_disclaimer,
      output: {
        overview: "A saved-evidence comparison without ranking.",
        candidate_summaries: candidates.slice(0, 2).map(row => ({ gene_symbol: row.gene_symbol, evidence_summary: "Saved evidence only.", source_ids: [`candidate:${row.ensembl_id}`] })),
        key_differences: [], shared_features: [], evidence_gaps: [], review_priorities: [],
        limitations: ["Saved evidence only."], what_this_does_not_mean: ["This does not select a target."],
      },
    };
    const questionAnswer = {
      mode: "evidence_answer", message: "Answer generated from the supplied saved evidence.",
      selected_gene_symbols: ["GENEA"], insight_id: "00000000-0000-0000-0000-000000000003",
      authoritative_facts: [{ gene_symbol: "GENEA", final_call: "modifier", confidence_tier: "Association only", overall_score: 0.8, genetic_score: 0.7, n_evidence: 0, n_evidence_returned: 0, evidence_truncated: false, shortlist_position: null, completeness: "complete", source_id: "candidate:ENSG1" }],
      premise_corrections: ["GENEA is not classified as insufficient data in this saved run. Its deterministic final call is modifier."],
      cached: false, generated_at: "2026-01-01", model: "test-model",
      prompt_version: "saved-evidence-question-v2", output_schema_version: "saved-evidence-question-v2",
      source_ids: ["candidate:ENSG1"], ai_generated: true,
      research_use_disclaimer: run.research_use_disclaimer,
      output: {
        answer_status: "answered", answer: "GENEA is a modifier because its saved direction is unresolved.",
        candidate_fact_checks: [{ gene_symbol: "GENEA", final_call: "modifier", overall_score: 0.8, genetic_score: 0.7, n_evidence: 0, n_evidence_returned: 0, evidence_truncated: false, shortlist_position: null, source_ids: ["candidate:ENSG1"] }],
        cited_claims: [{ claim: "The saved classification is modifier.", source_ids: ["candidate:ENSG1"] }],
        uncertainties: ["Only saved evidence was considered."], manual_review_steps: ["Review the saved record."],
        what_this_does_not_mean: ["This is not a treatment recommendation."],
      },
    };
    const unsupportedAnswer = {
      mode: "unsupported_by_saved_evidence", message: "This question is not supported by the saved run evidence.",
      selected_gene_symbols: ["GENEA"], insight_id: null, cached: false, generated_at: null, model: null,
      prompt_version: null, output_schema_version: null, source_ids: [], output: null, ai_generated: false,
      research_use_disclaimer: run.research_use_disclaimer,
    };
    const candidateExplanation = {
      insight_id: "00000000-0000-0000-0000-000000000004", cached: false,
      generated_at: "2026-01-01T00:00:00Z", model: "test-model",
      prompt_version: "candidate-explanation-v1", output_schema_version: "candidate-explanation-v1",
      source_ids: ["candidate:ENSG1"], ai_generated: true,
      research_use_disclaimer: run.research_use_disclaimer,
      output: {
        summary: "GENEA is a modifier based on the saved evidence.",
        decision_basis: [{ claim: "The fixed final call is modifier.", source_ids: ["candidate:ENSG1"] }],
        supporting_evidence: [], conflicting_evidence: [],
        uncertainties: ["Direction remains unresolved."],
        manual_review_steps: ["Review the saved candidate record."],
        what_this_does_not_mean: ["This is not a treatment recommendation."],
        glossary: [{ term: "Modifier", definition: "Association evidence without a resolved intervention direction." }],
      },
    };
    const runSummary = {
      insight_id: "00000000-0000-0000-0000-000000000005", cached: false,
      generated_at: "2026-01-01T00:00:00Z", model: "test-model",
      prompt_version: "run-summary-v1", output_schema_version: "run-summary-v1",
      source_ids: ["run:00000000-0000-0000-0000-000000000001", "candidate:ENSG1"],
      ai_generated: true, research_use_disclaimer: run.research_use_disclaimer,
      output: {
        overview: "The saved run contains four candidates and one target-level approved-drug precedent.",
        key_findings: [{ claim: "GENEA has target-level approved-drug precedent.", source_ids: ["candidate:ENSG1"] }],
        track_breakdown: [{ track: "modifier", count: 4, interpretation: "Direction remains unresolved.", source_ids: ["run:00000000-0000-0000-0000-000000000001"] }],
        evidence_gaps: [{ claim: "Variant evidence was not checked.", source_ids: ["candidate:ENSG1"] }],
        review_priorities: [{ claim: "Review indication and direction for GENEA.", source_ids: ["candidate:ENSG1"] }],
        limitations: ["Only saved evidence was summarized."],
        what_this_does_not_mean: ["This is not a treatment recommendation."],
      },
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const requestBody = init?.body ? JSON.parse(String(init.body)) as { question?: string } : null;
      if ((url.endsWith("/ai-summary") || url.endsWith("/ai-explanation")) && init?.method !== "POST") {
        return new Response(JSON.stringify({ detail: { code: "AI_INSIGHT_NOT_FOUND", message: "No saved insight." } }), { status: 404, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/ai-question") && requestBody?.question?.includes("dose")) {
        return new Response(JSON.stringify({ detail: { code: "CLINICAL_ADVICE", message: "Clinical, treatment, and dosing advice is outside this research tool." } }), { status: 422, headers: { "Content-Type": "application/json" } });
      }
      const body = url.endsWith("/config/public") ? { ai_enabled: true, ai_access_required: true }
        : url.endsWith(`/runs/${run.id}`) ? run
        : url.endsWith("/events") ? []
        : url.includes("/candidates?limit=500") ? candidates
        : url.endsWith("/candidates/GENEA/ai-explanation") && init?.method === "POST" ? candidateExplanation
        : url.endsWith("/ai-summary") && init?.method === "POST" ? runSummary
        : url.endsWith("/ai-compare") && init?.method === "POST" ? comparison
        : url.endsWith("/ai-question") && requestBody?.question?.includes("weather") ? unsupportedAnswer
        : url.endsWith("/ai-question") && init?.method === "POST" ? questionAnswer
        : {};
      return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("aso-compass-run", run.id);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Download summary PDF" }));
    await waitFor(() => expect(downloadRunPdfMock).toHaveBeenCalledOnce());
    expect(downloadRunPdfMock.mock.calls[0]?.[5]).toBe("ASO-Compass_Example-disease_summary-report_00000000");
    expect(document.querySelector(".print-report")).toHaveAttribute("data-print-mode", "summary");
    expect(document.querySelector('[data-report-section="review"]')).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Download full PDF" }));
    await waitFor(() => expect(downloadRunPdfMock).toHaveBeenCalledTimes(2));
    expect(downloadRunPdfMock.mock.calls[1]?.[5]).toBe("ASO-Compass_Example-disease_full-report_00000000");
    expect(document.querySelector(".print-report")).toHaveAttribute("data-print-mode", "full");
    expect(document.querySelector('[data-report-section="appendix"]')).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "View evidence for GENEA" }));
    expect(screen.getByRole("dialog", { name: "GENEA" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Maximize candidate evidence view" }));
    expect(document.querySelector(".drawer-backdrop")).toHaveClass("drawer-maximized");
    expect(screen.getByRole("button", { name: "Restore candidate evidence view" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "Restore candidate evidence view" }));
    expect(document.querySelector(".drawer-backdrop")).not.toHaveClass("drawer-maximized");
    await user.click(screen.getByRole("button", { name: "Download evidence PDF" }));
    await waitFor(() => expect(downloadCandidatePdfMock).toHaveBeenCalledOnce());
    expect(downloadCandidatePdfMock.mock.calls[0]?.[4]).toBe("ASO-Compass_Example-disease_GENEA_candidate-evidence_00000000");
    expect(document.querySelector('.print-report[data-print-mode="candidate"]')).toBeInTheDocument();
    expect(document.querySelector('[data-report-section="candidate-evidence"]')).toHaveTextContent("candidate:ENSG1");
    expect(document.querySelector('[data-report-section="candidate-evidence"]')).toHaveTextContent("No AI explanation had been generated");
    await user.click(screen.getByRole("button", { name: "Close gene details" }));

    expect(screen.getByText("No candidate is hidden because a drug or ASO precedent exists.")).toBeVisible();
    expect(screen.getByText("Showing 1–4 of 4")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Research view"), "translational");
    expect(screen.getByText(/Shows candidates with an approved drug/)).toBeVisible();
    const candidateExplorer = screen.getByRole("heading", { name: "Trace every classification" }).closest("article");
    expect(candidateExplorer).not.toBeNull();
    expect(within(candidateExplorer as HTMLElement).getByText("GENEA")).toBeVisible();
    expect(within(candidateExplorer as HTMLElement).queryByText("GENEB")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Research view"), "all");

    await user.type(await screen.findByLabelText("AI access token"), "shared-demo-token");
    await user.click(screen.getByRole("button", { name: "Use token" }));
    expect(screen.getByRole("heading", { name: "AI access token ready" })).toBeVisible();
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) =>
      String(input).endsWith("/ai-summary") && init?.method !== "POST"
    )).toBe(true));

    await user.click(screen.getByRole("button", { name: "View evidence for GENEA" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) =>
      String(input).endsWith("/candidates/GENEA/ai-explanation") && init?.method !== "POST"
    )).toBe(true));
    await user.click(screen.getByRole("button", { name: "Explain saved evidence" }));
    expect(await screen.findByText("GENEA is a modifier based on the saved evidence.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Download evidence PDF + AI" }));
    await waitFor(() => expect(downloadCandidatePdfMock).toHaveBeenCalledTimes(2));
    expect(document.querySelector('[data-report-section="candidate-ai-explanation"]')).toHaveTextContent("Optional AI appendix");
    expect(document.querySelector('[data-report-section="candidate-ai-explanation"]')).toHaveTextContent("candidate:ENSG1");
    await user.click(screen.getByRole("button", { name: "Close gene details" }));
    await user.click(screen.getByRole("button", { name: "View evidence for GENEA" }));
    expect(screen.getByRole("button", { name: "Download evidence PDF + AI" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Download evidence PDF + AI" }));
    await waitFor(() => expect(downloadCandidatePdfMock).toHaveBeenCalledTimes(3));
    expect(document.querySelector('[data-report-section="candidate-ai-explanation"]')).toHaveTextContent("GENEA is a modifier based on the saved evidence.");
    await user.click(screen.getByRole("button", { name: "Close gene details" }));

    await user.click(screen.getByRole("button", { name: "Summarize this run" }));
    expect(await screen.findByText("The saved run contains four candidates and one target-level approved-drug precedent.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Download full PDF + AI" }));
    await waitFor(() => expect(downloadRunPdfMock).toHaveBeenCalledTimes(3));
    const runSummaryAppendix = document.querySelector('[data-report-section="run-ai-summary"]');
    expect(runSummaryAppendix).toHaveTextContent("Optional AI appendix");
    expect(runSummaryAppendix).toHaveTextContent("GENEA has target-level approved-drug precedent.");
    expect(runSummaryAppendix).toHaveTextContent("Validated saved sources: candidate:ENSG1");
    expect(runSummaryAppendix).toHaveTextContent("test-model");

    await user.click(await screen.findByRole("checkbox", { name: "Select GENEA for comparison" }));
    await user.click(screen.getByRole("checkbox", { name: "Select GENEB for comparison" }));
    await user.click(screen.getByRole("checkbox", { name: "Select GENEC for comparison" }));
    expect(screen.getByRole("checkbox", { name: "Select GENED for comparison" })).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: "Select GENEC for comparison" }));
    await user.click(screen.getByRole("button", { name: "Compare selected (2)" }));
    expect(await screen.findByRole("heading", { name: /Evidence comparison: GENEA · GENEB/ })).toBeVisible();
    expect(screen.getByText("Generated · no ranking")).toBeVisible();

    await user.selectOptions(screen.getByLabelText("Candidate evidence context optional, up to 3"), "GENEA");
    await user.type(screen.getByLabelText("Research question"), "Why is GENEA classified as modifier?");
    await user.click(screen.getByRole("button", { name: "Ask saved evidence" }));
    expect(await screen.findByText("GENEA is a modifier because its saved direction is unresolved.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Saved deterministic facts" })).toBeVisible();
    expect(screen.getByText("Server generated · not AI")).toBeVisible();
    expect(screen.getByText("Question premise corrected")).toBeVisible();
    const qaCall = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/ai-question"));
    expect(new Headers(qaCall?.[1]?.headers).get("Authorization")).toBe("Bearer shared-demo-token");
    expect(JSON.parse(String(qaCall?.[1]?.body))).toEqual({
      question: "Why is GENEA classified as modifier?", gene_symbols: ["GENEA"],
    });

    await user.clear(screen.getByLabelText("Research question"));
    await user.type(screen.getByLabelText("Research question"), "What is the weather near the laboratory?");
    await user.click(screen.getByRole("button", { name: "Ask saved evidence" }));
    expect(await screen.findByText("Not supported by this saved run")).toBeVisible();
    expect(screen.getByText("No AI answer was generated.")).toBeVisible();

    await user.clear(screen.getByLabelText("Research question"));
    await user.type(screen.getByLabelText("Research question"), "What dose should the patient take?");
    await user.click(screen.getByRole("button", { name: "Ask saved evidence" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Clinical, treatment, and dosing advice is outside this research tool.");
  });
});
