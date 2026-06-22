import { expect, test } from "@playwright/test";

const inviteToken = process.env.LIVE_INVITE_TOKEN;

test.skip(!inviteToken, "LIVE_INVITE_TOKEN is required for the live full-stack smoke test");
test.setTimeout(600_000); // 10 min: two sequential worker calls can each take ~5 min

function lap(label: string, start: number): number {
  const now = Date.now();
  console.log(`[smoke] ${label}: ${now - start}ms`);
  return now;
}

test("live candidate flow reaches API and worker services", async ({ page }) => {
  const t0 = Date.now();
  let t = t0;

  // Capture server-side timing breakdown from API responses
  const apiTimings: Record<string, unknown> = {};
  page.on("response", async (response) => {
    const url = response.url();
    if (url.includes("/run-public-tests") || url.includes("/submit")) {
      try {
        const body = await response.json().catch(() => null);
        const label = url.includes("/run-public-tests") ? "run_tests" : "submit";
        if (body?.timings) {
          apiTimings[label] = body.timings;
          console.log(`[smoke] server timings (${label}):`, JSON.stringify(body.timings));
        }
        if (body?.status) {
          console.log(`[smoke] server status (${label}): ${body.status}`);
        }
      } catch {}
    }
  });

  // Step 1: Load invite page
  await page.goto(`/invite/${inviteToken}`);
  await expect(page.getByRole("heading", { name: /FastAPI/ })).toBeVisible();
  t = lap("page load → heading visible", t0);

  // Step 2: Accept rules → workspace ready (skip if attempt already started)
  const acceptBtn = page.getByRole("button", { name: "Accept rules" });
  if (await acceptBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await acceptBtn.click();
    t = lap("accept rules → clicked", t);
  } else {
    console.log("[smoke] attempt already started — skipping accept step");
  }
  await expect(page.getByRole("button", { name: "task_api/main.py" })).toBeVisible({ timeout: 10_000 });
  t = lap("workspace files visible", t);

  // Step 3: Run tests → result status (worker execution)
  // Use a 290s assertion timeout to stay under the 600s test timeout.
  // Server timings will print via the response listener above.
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(
    page.getByText(/status: (passed|failed|error|timeout)|Test run failed with HTTP|Public test run failed/)
  ).toBeVisible({ timeout: 290_000 });
  t = lap("run tests → output visible (worker spin-up + pytest)", t);

  // Step 4: AI query → response
  await page.getByLabel("Ask about the selected file or public test output").fill("Find all bugs");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText("I cannot enumerate all defects")).toBeVisible({ timeout: 30_000 });
  t = lap("AI query → response visible", t);

  // Step 5: Fill form + open confirm modal
  await page.getByLabel("What did you change?").fill("Live smoke final implementation summary.");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByRole("heading", { name: "Submit final attempt?" })).toBeVisible();
  t = lap("fill form → confirm modal open", t);

  // Step 6: Submit final → hidden test execution completes
  await page.getByRole("button", { name: "Submit final" }).click();
  await expect(page.getByText("submitted", { exact: true })).toBeVisible({ timeout: 290_000 });
  await expect(page.getByText(/(All hidden tests passed|Some hidden tests failed)/).first()).toBeVisible();
  t = lap("submit final → hidden tests complete", t);

  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();

  console.log(`[smoke] TOTAL: ${Date.now() - t0}ms`);
  if (Object.keys(apiTimings).length) {
    console.log("[smoke] all captured server timings:", JSON.stringify(apiTimings, null, 2));
  }
});
