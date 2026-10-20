import type { AIQuestionAnswer, Candidate, CandidateComparison, CandidateExplanation, PublicConfig, RunEvent, RunRecord, RunSummary } from "./types";

const buildTimeApiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
const spaceApiBase = window.huggingface?.variables?.VITE_API_BASE_URL?.trim();
export const API_BASE = (buildTimeApiBase || spaceApiBase || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: { message?: string }; message?: string } | null;
    throw new Error(body?.detail?.message ?? body?.message ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function createRun(payload: Record<string, unknown>): Promise<RunRecord> {
  return request("/api/v1/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(payload),
  });
}

export const getRun = (id: string) => request<RunRecord>(`/api/v1/runs/${id}`);
export const getPublicConfig = () => request<PublicConfig>("/api/v1/config/public");
export const getEvents = (id: string) => request<RunEvent[]>(`/api/v1/runs/${id}/events`);
export const getCandidates = (id: string) => request<Candidate[]>(`/api/v1/runs/${id}/candidates?limit=500`);
export const explainCandidate = (runId: string, geneSymbol: string) => request<CandidateExplanation>(`/api/v1/runs/${runId}/candidates/${encodeURIComponent(geneSymbol)}/ai-explanation`, { method: "POST" });
export const summarizeRun = (runId: string) => request<RunSummary>(`/api/v1/runs/${runId}/ai-summary`, { method: "POST" });
export const compareCandidates = (runId: string, geneSymbols: string[]) => request<CandidateComparison>(`/api/v1/runs/${runId}/ai-compare`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ gene_symbols: geneSymbols }),
});
export const askSavedEvidenceQuestion = (runId: string, question: string, geneSymbols: string[]) => request<AIQuestionAnswer>(`/api/v1/runs/${runId}/ai-question`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question, gene_symbols: geneSymbols }),
});
export const exportUrl = (id: string, format: "csv" | "json") => `${API_BASE}/api/v1/runs/${id}/exports/${format}`;
