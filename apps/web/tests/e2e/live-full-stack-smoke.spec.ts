import { expect, test } from "@playwright/test";

const inviteToken = process.env.LIVE_INVITE_TOKEN;

test.skip(!inviteToken, "LIVE_INVITE_TOKEN is required for the live full-stack smoke test");

test("live candidate flow reaches API and worker services", async ({ page }) => {
  await page.goto(`/invite/${inviteToken}`);

  await expect(page.getByRole("heading", { name: /FastAPI Backend/ })).toBeVisible();
  await page.getByRole("button", { name: "Accept rules" }).click();

  await expect(page.getByRole("button", { name: "task_api/main.py" })).toBeVisible();
  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByText(/status: (passed|failed|error|timeout)/)).toBeVisible({ timeout: 30_000 });

  await page.getByLabel("Ask about the selected file or public test output").fill("Find all bugs");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText("I cannot enumerate all defects")).toBeVisible();

  await page.getByLabel("Final explanation").fill("Live smoke final explanation.");
  await page.getByLabel("Decision log").fill("Live smoke decision log.");
  await page.getByRole("button", { name: "Submit" }).click();

  await expect(page.getByText("submitted", { exact: true })).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText(/Hidden evaluation recorded with status: (passed|failed|error|timeout)/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Save" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();
});
