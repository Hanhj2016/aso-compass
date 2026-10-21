import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("guided form and offline evidence example are usable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /clearer path through target evidence/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /deployed automatically from github/i })).toHaveAttribute(
    "href",
    "https://github.com/Hanhj2016/aso-compass",
  );
  await expect(page.getByRole("button", { name: /begin evidence analysis/i })).toBeDisabled();
  await page.getByRole("checkbox").check();
  await expect(page.getByRole("button", { name: /begin evidence analysis/i })).toBeEnabled();

  const formAudit = await new AxeBuilder({ page }).analyze();
  expect(
    formAudit.violations.filter((item) => item.impact === "critical" || item.impact === "serious"),
  ).toEqual([]);

  await page.getByRole("button", { name: /precomputed ALS example/i }).click();
  await expect(page.getByRole("heading", { name: /amyotrophic lateral sclerosis/i })).toBeVisible();
  await expect(page.getByText(/offline-ready example/i)).toBeVisible();
  await expect(page.getByText(/AI questions are unavailable for the bundled example/i)).toBeVisible();
  await page.getByRole("button", { name: "View evidence for SOD1" }).click();
  await expect(page.getByRole("dialog", { name: "SOD1" })).toBeVisible();
  await expect(page.getByText(/AI explanations are unavailable for the bundled example/i)).toBeVisible();
  await expect(page.getByText(/not for clinical decision-making/i).last()).toBeVisible();
});

test("a failed scientific run offers a safe offline fallback", async ({ page }) => {
  const run = {
    id: "11111111-1111-4111-8111-111111111111",
    environment: "test",
    disease_id: "MONDO_0004976",
    disease_label: "Amyotrophic lateral sclerosis (ALS)",
    status: "queued",
    parameters: {},
    warnings: [],
    validation: {},
    upstream_metadata: {},
    engine_version: "4.1-guided",
    error_code: null,
    error_message: null,
  };

  await page.route("http://127.0.0.1:8000/api/v1/runs", async (route) => {
    await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify(run) });
  });
  await page.route(`http://127.0.0.1:8000/api/v1/runs/${run.id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...run,
        status: "failed",
        error_code: "RUN_FAILED",
        error_message: "Upstream evidence remained unavailable; no negative inference was made.",
      }),
    });
  });
  await page.route(`http://127.0.0.1:8000/api/v1/runs/${run.id}/events`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.goto("/");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: /begin evidence analysis/i }).click();
  await expect(page.getByRole("heading", { name: /run could not be completed/i })).toBeVisible();
  await expect(page.getByText(/no negative inference/i)).toBeVisible();
  await page.getByRole("button", { name: /open the example instead/i }).click();
  await expect(page.getByText(/offline-ready example/i)).toBeVisible();
});
