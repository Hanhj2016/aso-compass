import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
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
