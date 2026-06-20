/**
 * Real-API invite flow tests — NO page.route() mocking.
 *
 * These tests hit the real running API and real database for candidate invite loading.
 * They are skipped unless RUN_REAL_API_TESTS=1 and REAL_API_INVITE_TOKEN are set.
 *
 * Prerequisites before running:
 *   - API running on NEXT_PUBLIC_API_URL (default: http://127.0.0.1:8015)
 *   - Postgres DB running and fully migrated (alembic upgrade head)
 *   - Web dev server running (or PLAYWRIGHT_SKIP_WEBSERVER=1 with server already up)
 *
 * Run with:
 *   RUN_REAL_API_TESTS=1 REAL_API_INVITE_TOKEN=... npx playwright test real-api-invite-flow
 */

import { expect, test } from "@playwright/test";

const inviteToken = process.env.REAL_API_INVITE_TOKEN;

// Guard: skip the entire file if real-API tests are not opted in
test.skip(!process.env.RUN_REAL_API_TESTS, "Set RUN_REAL_API_TESTS=1 to run against the real API");
test.skip(!inviteToken, "Set REAL_API_INVITE_TOKEN to a candidate invite token created through the Clerk-authenticated employer portal or API");

test("invite link navigates to real candidate workspace", async ({ page }) => {
  await page.goto(`/invite/${inviteToken}`);

  // The assessment title heading must appear — proves the real candidate workspace loaded
  // and GET /candidate/invites/{token} returned 200 from the real API
  await expect(page.getByRole("heading", { name: /FastAPI/ })).toBeVisible({ timeout: 15_000 });

  // The Monaco editor area must be present (it loads after the invite metadata is fetched)
  // Wait for the accept button first, then accept to enter the workspace
  await page.getByRole("button", { name: "Accept rules" }).click();

  // After accepting, the editor panel must be visible
  await expect(page.locator(".monaco-editor")).toBeVisible({ timeout: 15_000 });

  // Verify no error messages appeared
  await expect(page.getByText(/error/i)).not.toBeVisible();
  await expect(page.getByText(/not found/i)).not.toBeVisible();
  await expect(page.getByText(/500/)).not.toBeVisible();
});
