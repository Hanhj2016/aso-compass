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
