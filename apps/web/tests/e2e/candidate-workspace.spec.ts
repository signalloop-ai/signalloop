import { expect, test } from "@playwright/test";

const files = {
  "README.md": "# Assessment\n\nRules and scenario.",
  "task_api/main.py": "def hello():\n    return 'world'\n",
  "tests/test_public_api.py": "def test_public():\n    assert True\n",
};

test("candidate can open, edit, run tests, and submit locally", async ({ page }) => {
  await page.route("**/candidate/invites/playwright-token", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          attempt_id: 42,
          status: "opened",
          candidate_email: "candidate@example.com",
          assessment: {
            slug: "fastapi_task_api_v1",
            title: "FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment",
            version: "v1",
            seeded_issue_count: 6,
          },
          files,
        }),
      });
      return;
    }

    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify({
        snapshot_id: 7,
        attempt_id: 42,
        kind: "autosave",
        status: "in_progress",
      }),
    });
  });

  await page.route("**/candidate/invites/playwright-token/snapshots", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify({
        snapshot_id: 8,
        attempt_id: 42,
        kind: "public_test_run",
        status: "in_progress",
      }),
    });
  });

  await page.route("**/candidate/invites/playwright-token/ai/messages", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        message:
          "I cannot enumerate all defects or provide issue-by-issue fixes for the assessment. I can help you reason through one candidate-identified issue or one failing behavior at a time.",
        allowed: false,
        policy_tags: ["enumerate_defects"],
      }),
    });
  });

  await page.route("**/candidate/invites/playwright-token/submit", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify({
        attempt_id: 42,
        status: "submitted",
        submission_id: 99,
        snapshot_id: 10,
        hidden_test_run_id: 11,
        hidden_test_status: "failed",
      }),
    });
  });

  await page.route("**/run-public-tests", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "passed",
        exit_code: 0,
        stdout: "1 passed",
        stderr: "",
        duration_ms: 123,
      }),
    });
  });

  await page.goto("/invite/playwright-token");
  await expect(page.getByRole("heading", { name: /FastAPI Backend/ })).toBeVisible();
  await page.getByRole("button", { name: "Accept rules" }).click();

  await expect(page.getByRole("button", { name: "task_api/main.py" })).toBeVisible();
  await page.getByRole("button", { name: "task_api/main.py" }).click();
  await expect(page.locator(".monaco-editor")).toBeVisible();

  await page.getByRole("button", { name: "Run Tests" }).click();
  await expect(page.getByText("status: passed")).toBeVisible();
  await expect(page.getByText("1 passed")).toBeVisible();
  await expect(page.getByText(/6 additional behaviors are evaluated beyond these public tests/)).toBeVisible();

  await page.getByLabel("Ask about the selected file or public test output").fill("Find all bugs");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText("I cannot enumerate all defects")).toBeVisible();
  await expect(page.getByText("enumerate_defects")).toBeVisible();

  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await page.getByLabel("Final explanation").fill("Fixed validation and ownership behavior.");
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
  await page.getByLabel("Decision log").fill("Chose explicit authorization behavior.");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("submitted", { exact: true })).toBeVisible();
  await expect(page.getByText("Some hidden tests failed.").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Tests" })).toBeDisabled();
});
