import { expect, test } from "@playwright/test";

const inviteToken = process.env.LIVE_INVITE_TOKEN;

test.skip(!inviteToken, "LIVE_INVITE_TOKEN is required for the live full-stack smoke test");
test.setTimeout(120_000);

test("live candidate flow reaches API and worker services", async ({ page }) => {
  await page.goto(`/invite/${inviteToken}`);

  await expect(page.getByRole("heading", { name: /FastAPI/ })).toBeVisible();
  await page.getByRole("button", { name: "Accept rules" }).click();

  await expect(page.getByRole("button", { name: "task_api/main.py" })).toBeVisible();
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByText(/status: (passed|failed|error|timeout)/)).toBeVisible({ timeout: 90_000 });

  await page.getByLabel("Ask about the selected file or public test output").fill("Find all bugs");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText("I cannot enumerate all defects")).toBeVisible();

  await page.getByLabel("What did you change?").fill("Live smoke final implementation summary.");
  await page.getByLabel("What tradeoffs or product decisions did you make?").fill("Live smoke decision summary.");
  await page.getByLabel("How did you verify your changes?").fill("Ran the live public test flow.");
  await page.getByLabel("What would you improve next, given more time?").fill("Add deeper edge-case coverage.");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByRole("heading", { name: "Submit final attempt?" })).toBeVisible();
  await page.getByRole("button", { name: "Submit final" }).click();

  await expect(page.getByText("submitted", { exact: true })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/(All hidden tests passed|Some hidden tests failed)/).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();
});
