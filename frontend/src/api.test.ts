import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.resetModules();
  delete window.huggingface;
});

describe("API deployment configuration", () => {
  it("uses the Hugging Face runtime variable when no build-time URL is supplied", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    window.huggingface = {
      variables: { VITE_API_BASE_URL: "https://aso-compass-api.onrender.com/" },
    };

    const { API_BASE } = await import("./api");

    expect(API_BASE).toBe("https://aso-compass-api.onrender.com");
  });

  it("retries a transient configuration failure before disabling AI", async () => {
    vi.useFakeTimers();
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("temporary network failure"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ai_enabled: true, ai_access_required: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    const { getPublicConfig } = await import("./api");

    const configPromise = getPublicConfig();
    await vi.advanceTimersByTimeAsync(1_000);

    await expect(configPromise).resolves.toMatchObject({ ai_enabled: true, ai_access_required: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});

describe("candidate retrieval", () => {
  it("drains backend pages before returning candidates", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const firstPage = Array.from({ length: 500 }, (_, index) => ({ id: `candidate-${index}` }));
    const secondPage = [{ id: "candidate-500" }];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify(firstPage), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(secondPage), { status: 200 }));

    const { getCandidates } = await import("./api");
    const candidates = await getCandidates("run-1");

    expect(candidates).toHaveLength(501);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "https://api.example.test/api/v1/runs/run-1/candidates?limit=500&offset=0",
      undefined,
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "https://api.example.test/api/v1/runs/run-1/candidates?limit=500&offset=500",
      undefined,
    );

    fetchMock.mockRestore();
  });
});

describe("offline example AI routing", () => {
  it("uses the allow-listed example endpoint and keeps the bearer token server-bound", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ output: {} }), { status: 200 }),
    );
    const { explainCandidate } = await import("./api");

    await explainCandidate("example-als-2026-10", "TARDBP", "shared-token", true);

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/v1/examples/example-als-2026-10/candidates/TARDBP/ai-explanation",
      expect.objectContaining({ method: "POST" }),
    );
    const headers = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer shared-token");
  });

  it("retrieves saved example AI without generating and treats current and legacy cache misses as empty", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ cached: true, output: {} }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { code: "AI_INSIGHT_NOT_FOUND" } }), { status: 404 }));
    const { getSavedCandidateExplanation, getSavedRunSummary } = await import("./api");

    await expect(getSavedRunSummary("example-als-2026-10", "shared-token", true)).resolves.toMatchObject({ cached: true });
    await expect(getSavedCandidateExplanation("example-als-2026-10", "TARDBP", "shared-token", true)).resolves.toBeNull();
    await expect(getSavedCandidateExplanation("example-als-2026-10", "TARDBP", "shared-token", true)).resolves.toBeNull();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "https://api.example.test/api/v1/examples/example-als-2026-10/ai-summary",
      expect.not.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "https://api.example.test/api/v1/examples/example-als-2026-10/candidates/TARDBP/ai-explanation",
      expect.not.objectContaining({ method: "POST" }),
    );
  });
});
