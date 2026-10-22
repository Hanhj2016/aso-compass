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
export async function getCandidates(id: string): Promise<Candidate[]> {
  const candidates: Candidate[] = [];
  const limit = 500;
  for (let offset = 0; ; offset += limit) {
    const page = await request<Candidate[]>(`/api/v1/runs/${id}/candidates?limit=${limit}&offset=${offset}`);
    candidates.push(...page);
    if (page.length < limit) return candidates;
  }
}
const aiHeaders = (accessToken: string, includeJson = false): HeadersInit => ({
  ...(includeJson ? { "Content-Type": "application/json" } : {}),
  ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
});

export const explainCandidate = (runId: string, geneSymbol: string, accessToken: string) => request<CandidateExplanation>(`/api/v1/runs/${runId}/candidates/${encodeURIComponent(geneSymbol)}/ai-explanation`, { method: "POST", headers: aiHeaders(accessToken) });
export const summarizeRun = (runId: string, accessToken: string) => request<RunSummary>(`/api/v1/runs/${runId}/ai-summary`, { method: "POST", headers: aiHeaders(accessToken) });
export const compareCandidates = (runId: string, geneSymbols: string[], accessToken: string) => request<CandidateComparison>(`/api/v1/runs/${runId}/ai-compare`, {
  method: "POST",
  headers: aiHeaders(accessToken, true),
  body: JSON.stringify({ gene_symbols: geneSymbols }),
});
export const askSavedEvidenceQuestion = (runId: string, question: string, geneSymbols: string[], accessToken: string) => request<AIQuestionAnswer>(`/api/v1/runs/${runId}/ai-question`, {
  method: "POST",
  headers: aiHeaders(accessToken, true),
  body: JSON.stringify({ question, gene_symbols: geneSymbols }),
});
export const exportUrl = (id: string, format: "csv" | "json") => `${API_BASE}/api/v1/runs/${id}/exports/${format}`;
