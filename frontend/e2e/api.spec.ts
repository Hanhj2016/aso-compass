import { expect, test } from "@playwright/test";

test("backend accepts a bounded run and exposes safe public configuration", async ({ request }) => {
  const configResponse = await request.get("http://127.0.0.1:8100/api/v1/config/public");
  const runResponse = await request.post("http://127.0.0.1:8100/api/v1/runs", {
    headers: {
      Origin: "http://127.0.0.1:5173",
      "Content-Type": "application/json",
      "Idempotency-Key": "playwright-e2e-run",
    },
    data: { disease_id: "MONDO:0004976", parameters: { run_mode: "quick" } },
  });
  const config = await configResponse.json();
  const run = await runResponse.json();
  expect(configResponse.status()).toBe(200);
  expect(config.ai_enabled).toBe(false);
  expect(runResponse.status()).toBe(202);
  expect(run.disease_id).toBe("MONDO_0004976");
  expect(run.warnings[0]).toContain("incomplete");
  expect(runResponse.headers()["access-control-allow-origin"]).toBe("http://127.0.0.1:5173");
  expect(runResponse.headers()["x-request-id"]).toBeTruthy();
});
