import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

afterEach(() => { cleanup(); localStorage.clear(); sessionStorage.clear(); vi.restoreAllMocks(); });

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

  it("explains the deterministic workflow", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Learn" }));
    expect(screen.getByRole("heading", { name: /transparent map/i })).toBeVisible();
    expect(screen.getByText(/not a clinical answer/i)).toBeVisible();
    expect(screen.getByRole("heading", { name: "The five research tracks" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "简体中文" })).not.toBeInTheDocument();
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
      drug_status: "None found", has_approved_drug: false, n_drugs: 0, drug_max_stage: null,
      approved_drugs: "", oligo_drug: null, oligo_names: "", aso_drug: null, aso_names: "",
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
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const requestBody = init?.body ? JSON.parse(String(init.body)) as { question?: string } : null;
      if (url.endsWith("/ai-question") && requestBody?.question?.includes("dose")) {
        return new Response(JSON.stringify({ detail: { code: "CLINICAL_ADVICE", message: "Clinical, treatment, and dosing advice is outside this research tool." } }), { status: 422, headers: { "Content-Type": "application/json" } });
      }
      const body = url.endsWith("/config/public") ? { ai_enabled: true, ai_access_required: true }
        : url.endsWith(`/runs/${run.id}`) ? run
        : url.endsWith("/events") ? []
        : url.includes("/candidates?limit=500") ? candidates
        : url.endsWith("/ai-compare") && init?.method === "POST" ? comparison
        : url.endsWith("/ai-question") && requestBody?.question?.includes("weather") ? unsupportedAnswer
        : url.endsWith("/ai-question") && init?.method === "POST" ? questionAnswer
        : {};
      return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("aso-compass-run", run.id);
    const user = userEvent.setup();
    const printSpy = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Print report" }));
    expect(printSpy).toHaveBeenCalledOnce();

    await user.type(await screen.findByLabelText("AI access token"), "shared-demo-token");
    await user.click(screen.getByRole("button", { name: "Use token" }));
    expect(screen.getByRole("heading", { name: "AI access token ready" })).toBeVisible();

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
