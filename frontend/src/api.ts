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

async function requestOptional<T>(path: string, init?: RequestInit): Promise<T | null> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (response.status === 404) return null;
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
export async function getPublicConfig(): Promise<PublicConfig> {
  const retryDelays = [0, 1_000, 2_500, 5_000, 10_000, 20_000];
  let lastError: unknown;
  for (const delay of retryDelays) {
    if (delay) await new Promise(resolve => window.setTimeout(resolve, delay));
    try {
      return await request<PublicConfig>("/api/v1/config/public");
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("The API configuration is unavailable.");
}
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

const aiResource = (runId: string, isExample: boolean) => `/api/v1/${isExample ? "examples" : "runs"}/${runId}`;

export const explainCandidate = (runId: string, geneSymbol: string, accessToken: string, isExample = false) => request<CandidateExplanation>(`${aiResource(runId, isExample)}/candidates/${encodeURIComponent(geneSymbol)}/ai-explanation`, { method: "POST", headers: aiHeaders(accessToken) });
export const summarizeRun = (runId: string, accessToken: string, isExample = false) => request<RunSummary>(`${aiResource(runId, isExample)}/ai-summary`, { method: "POST", headers: aiHeaders(accessToken) });
export const getSavedCandidateExplanation = (runId: string, geneSymbol: string, accessToken: string, isExample = false) => requestOptional<CandidateExplanation>(`${aiResource(runId, isExample)}/candidates/${encodeURIComponent(geneSymbol)}/ai-explanation`, { headers: aiHeaders(accessToken) });
export const getSavedRunSummary = (runId: string, accessToken: string, isExample = false) => requestOptional<RunSummary>(`${aiResource(runId, isExample)}/ai-summary`, { headers: aiHeaders(accessToken) });
export const compareCandidates = (runId: string, geneSymbols: string[], accessToken: string, isExample = false) => request<CandidateComparison>(`${aiResource(runId, isExample)}/ai-compare`, {
  method: "POST",
  headers: aiHeaders(accessToken, true),
  body: JSON.stringify({ gene_symbols: geneSymbols }),
});
export const askSavedEvidenceQuestion = (runId: string, question: string, geneSymbols: string[], accessToken: string, isExample = false) => request<AIQuestionAnswer>(`${aiResource(runId, isExample)}/ai-question`, {
  method: "POST",
  headers: aiHeaders(accessToken, true),
  body: JSON.stringify({ question, gene_symbols: geneSymbols }),
});
export const exportUrl = (id: string, format: "csv" | "json") => `${API_BASE}/api/v1/runs/${id}/exports/${format}`;
