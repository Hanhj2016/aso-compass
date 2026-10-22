import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

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

test("guided tutorial leads into the offline evidence example", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Learn" }).click();
  await expect(page.getByRole("heading", { name: /transparent map/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "The five research tracks" })).toBeVisible();

  await page.getByRole("button", { name: /open the guided ALS example/i }).first().click();
  await expect(page.getByRole("heading", { name: /amyotrophic lateral sclerosis/i })).toBeVisible();
  await expect(page.getByText(/offline-ready example/i)).toBeVisible();
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

test("full print report uses bounded independent candidate tables", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "PDF layout is verified once in desktop Chromium");
  const exampleUrl = new URL("../public/examples/als-v4.1.json", import.meta.url);
  const bundle = JSON.parse(await readFile(exampleUrl, "utf8"));
  const seeds = bundle.candidates as Array<Record<string, unknown>>;
  bundle.run.engine_version = "4.2-guided";
  bundle.run.warnings = ["Quick mode caps variant enrichment at 25 genes; results are incomplete."];
  bundle.candidates = Array.from({ length: 40 }, (_, index) => {
    const seed = seeds[index % seeds.length];
    const enriched = index < 25;
    return {
      ...seed,
      ensembl_id: `ENSGPRINT${String(index).padStart(5, "0")}`,
      gene_symbol: `GENE${String(index + 1).padStart(2, "0")}`,
      gene_name: `Print layout candidate ${index + 1}`,
      final_call: index < 9 ? "knockdown" : index < 17 ? "splice/upregulation" : index < 20 ? "ambiguous" : "insufficient data",
      shortlist_position: index < 17 ? index + 1 : null,
      evidence_truncated: enriched && index % 7 === 0,
      n_evidence: enriched ? 50 + index : null,
      n_evidence_returned: enriched ? (index % 7 === 0 ? 50 : 50 + index) : null,
      has_approved_drug: enriched ? index % 11 === 0 : null,
      drug_status: enriched ? (index % 11 === 0 ? "Approved: EXAMPLE" : "None found") : "not checked",
      aso_precedent: index % 13 === 0 ? "ASO / trial example requiring review" : "",
    };
  });

  await page.route("**/examples/als-v4.1.json", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(bundle),
  }));
  await page.addInitScript(() => { window.print = () => undefined; });
  await page.goto("/");
  await page.getByRole("button", { name: /precomputed ALS example/i }).click();
  await expect(page.getByRole("heading", { name: /amyotrophic lateral sclerosis/i })).toBeVisible();
  await page.getByRole("button", { name: "Print full report" }).click();
  await expect(page.locator('.print-report[data-print-mode="full"]')).toHaveCount(1);

  const appendixPages = page.locator('[data-report-section="appendix"]');
  await expect(appendixPages).toHaveCount(4);
  await expect(page.locator('[data-report-section="appendix"] .print-candidate-row')).toHaveCount(40);
  for (const reportPage of await page.locator(".print-table-page").all()) {
    expect(await reportPage.locator(".print-candidate-row").count()).toBeLessThanOrEqual(12);
    await expect(reportPage.locator('[role="columnheader"]')).toHaveCount(8);
  }

  await page.emulateMedia({ media: "print" });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  });
  const pdf = await page.pdf({
    path: testInfo.outputPath("full-report.pdf"),
    format: "Letter",
    landscape: true,
    printBackground: true,
    preferCSSPageSize: true,
  });
  expect(pdf.subarray(0, 4).toString()).toBe("%PDF");
  expect(pdf.byteLength).toBeGreaterThan(20_000);

  await page.emulateMedia({ media: "screen" });
  await page.getByRole("button", { name: "View evidence for GENE01" }).click();
  await expect(page.getByRole("dialog", { name: "GENE01" })).toBeVisible();
  await page.getByRole("button", { name: "Print evidence" }).click();
  await expect(page.locator('.print-report[data-print-mode="candidate"]')).toHaveCount(1);
  await expect(page.locator('[data-report-section="candidate-evidence"]')).toContainText("Optional AI explanations are excluded");
  await page.emulateMedia({ media: "print" });
  const candidatePdf = await page.pdf({
    path: testInfo.outputPath("candidate-evidence.pdf"),
    format: "Letter",
    landscape: true,
    printBackground: true,
    preferCSSPageSize: true,
  });
  expect(candidatePdf.subarray(0, 4).toString()).toBe("%PDF");
  expect(candidatePdf.byteLength).toBeGreaterThan(10_000);
});
