/**
 * Phase 3 — Proctoring e2e tests
 *
 * Covers:
 *   - Employer report Proctoring Signals section rendering
 *   - Unified IntegrityBanner (low/medium/high)
 *   - Candidate workspace webcam consent prompt
 *   - Proctoring event batch endpoint called on submission
 */

import { expect, test, type Page } from "@playwright/test";

// ── Shared Clerk mock ──────────────────────────────────────────────────────────

const FAKE_JWT =
  "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" +
  ".eyJzdWIiOiJ0ZXN0LWVtcGxveWVyLXVzZXIiLCJleHAiOjQwMDAwMDAwMDAsImlhdCI6MTcwMDAwMDAwMCwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIn0" +
  ".fake_sig_for_playwright_tests";

const FAKE_CLIENT_RESPONSE = {
  response: {
    object: "client",
    id: "client_test",
    sessions: [
      {
        object: "session",
        id: "sess_test",
        status: "active",
        expire_at: 4000000000000,
        abandon_at: 4000000000000,
        last_active_at: 1700000000000,
        last_active_token: { jwt: FAKE_JWT },
        last_active_organization_id: null,
        actor: null,
        user: {
          object: "user",
          id: "user_test",
          created_at: 1700000000000,
          updated_at: 1700000000000,
          first_name: "Test",
          last_name: "Employer",
          image_url: "",
          has_image: false,
          primary_email_address_id: "idn_test",
          email_addresses: [
            {
              id: "idn_test",
              object: "email_address",
              email_address: "test@example.com",
              verification: { status: "verified", strategy: "ticket" },
              linked_to: [],
            },
          ],
          phone_numbers: [],
          web3_wallets: [],
          passkeys: [],
          external_accounts: [],
          public_metadata: {},
        },
        public_user_data: {
          first_name: "Test",
          last_name: "Employer",
          image_url: "",
          has_image: false,
          identifier: "test@example.com",
          user_id: "user_test",
        },
        created_at: 1700000000000,
        updated_at: 1700000000000,
      },
    ],
    sign_in: null,
    sign_up: null,
    last_active_session_id: "sess_test",
    last_authentication_strategy: null,
    cookie_expires_at: null,
    captcha_bypass: false,
    created_at: 1700000000000,
    updated_at: 1700000000000,
  },
  client: null,
};

async function mockClerkSignedIn(page: Page): Promise<void> {
  await page.route("**clerk.accounts.dev/v1/client**", (route) => {
    const url = route.request().url();
    if (url.includes("/sessions/") && url.includes("/tokens")) {
      void route.fulfill({ contentType: "application/json", body: JSON.stringify({ object: "token", jwt: FAKE_JWT }) });
    } else {
      void route.fulfill({ contentType: "application/json", body: JSON.stringify(FAKE_CLIENT_RESPONSE) });
    }
  });
}

// ── Shared report fixture ─────────────────────────────────────────────────────

const baseReport = {
  attempt_id: 42,
  report_id: 9,
  recommendation: "advance",
  score_total: 78,
  report: {
    metadata: {
      candidate_email: "candidate@example.com",
      submitted_at: "2026-06-20T11:30:00+00:00",
      assessment: { slug: "fastapi_task_api_standard_v2", title: "FastAPI Assessment", version: "standard_v2" },
      evaluator_feedback_mode: "strict",
      timing: {
        timing_mode: "untimed",
        duration_minutes: 90,
        time_used_minutes: 30,
        started_at: "2026-06-20T11:00:00+00:00",
        submitted_at: "2026-06-20T11:30:00+00:00",
        expires_at: null,
        submission_mode: "manual",
      },
    },
    executive_summary: { summary: "Candidate submitted a solid fix.", evidence_limits: [] },
    overall_recommendation: "advance",
    scores: {
      total: 78,
      max_points: 100,
      categories: [
        { category: "public_issue_resolution", points: 12, max_points: 15, evidence: "ok" },
      ],
    },
    rubric_weights: { public_issue_resolution: 15 },
    public_test_results: {
      run_count: 1,
      initially_failing_tests: [],
      last_run_summary: { collected: 4, passed: 4, failed: 0, failure_names: [], status: "passed" },
    },
    hidden_test_results: {
      seeded_issue_areas: ["edge case"],
      summary: { collected: 5, passed: 4, failed: 1, failure_names: ["test_edge"], status: "failed" },
    },
    feature_design_implementation: null,
    candidate_tests: {
      added_test_files: [],
      modified_test_files: [],
      candidate_test_file_count: 0,
      functions_added: 0,
      functions_modified: 0,
    },
    ai_collaboration: {
      message_count: 1,
      candidate_prompt_count: 1,
      policy_redirect_count: 0,
      pasted_ai_code: { pasted_ai_code_count: 0, matches: [] },
      large_paste_events: { large_paste_count: 0, events: [] },
      flagged_prompts: [],
      all_candidate_messages: [],
    },
    ai_integrity_risk: {
      label: "low",
      signals: { policy_redirect_count: 0, severe_redirect_count: 0, prompt_injection_count: 0, pasted_ai_code_count: 0, large_paste_event_count: 0, weak_submission_review: false },
      score_impact: "none",
    },
    integrity_score: {
      label: "low",
      contributing_factors: [
        { signal: "focus_loss_count", value: 0, weight: "none" },
        { signal: "focus_loss_duration_seconds", value: 0, weight: "none" },
        { signal: "fullscreen_exits", value: 0, weight: "none" },
        { signal: "large_paste_count", value: 0, weight: "none" },
        { signal: "ai_violation_count", value: 0, weight: "none" },
        { signal: "prompt_injection_count", value: 0, weight: "none" },
      ],
      total_weight_points: 0,
    },
    favo: {
      frame: { label: "present", evidence: "ok" },
      ask: { label: "present", evidence: "ok" },
      verify: { label: "present", evidence: "ok" },
      own: { label: "present", evidence: "ok" },
    },
    llm_assisted_review: { status: "not_run", reason: "disabled", provider_configured: false },
    process_evidence: { snapshot_count: 2, test_run_count: 1, test_runs: [] },
    explanation_submitted: { final_explanation: "", decision_log: "" },
    submission_review: { what_changed: "Fixed bug.", tradeoffs_or_product_decisions: "", verification: "", improvements_with_more_time: "", additional_notes: "", required_answer_count: 1, required_question_count: 1 },
    timeline: [],
    follow_up_questions: [],
  },
};

// ── Employer report — Proctoring Signals section ──────────────────────────────

test("proctoring signals section shows 'No proctoring data' for pre-Phase-3 attempt", async ({ page }) => {
  const reportWithoutProctoring = {
    ...baseReport,
    report: { ...baseReport.report, proctoring_signals: undefined },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(reportWithoutProctoring) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.getByRole("heading", { name: "Proctoring Signals" })).toBeVisible();
  await expect(page.getByText("No proctoring data available for this attempt.")).toBeVisible();
});

test("proctoring signals section renders webcam enabled chip and event table", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      proctoring_signals: {
        webcam_consented: true,
        focus_loss_count: 3,
        focus_loss_duration_seconds: 145,
        fullscreen_exit_count: 1,
        large_paste_count: 0,
        focus_events: [
          { occurred_at: "2026-06-20T11:05:00+00:00", duration_seconds: 45 },
          { occurred_at: "2026-06-20T11:15:00+00:00", duration_seconds: 60 },
          { occurred_at: "2026-06-20T11:25:00+00:00", duration_seconds: 40 },
        ],
        snapshots: [],
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.getByRole("heading", { name: "Proctoring Signals" })).toBeVisible();
  await expect(page.locator(".status-pill.ready").filter({ hasText: "Webcam enabled" })).toBeVisible();

  // Event table values
  await expect(page.getByText("Focus-loss events")).toBeVisible();
  await expect(page.locator(".proctoring-table").getByText("3")).toBeVisible();
  await expect(page.getByText("Fullscreen exits")).toBeVisible();
  await expect(page.locator(".proctoring-table").getByText("1")).toBeVisible();
  // 145 seconds = 2m 25s
  await expect(page.getByText("2m 25s")).toBeVisible();
});

test("proctoring signals section renders webcam declined chip", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      proctoring_signals: {
        webcam_consented: false,
        focus_loss_count: 0,
        focus_loss_duration_seconds: 0,
        fullscreen_exit_count: 0,
        large_paste_count: 0,
        focus_events: [],
        snapshots: [],
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.locator(".status-pill").filter({ hasText: "Webcam declined" })).toBeVisible();
  await expect(page.getByText("Candidate did not enable webcam for this assessment.")).toBeVisible();
});

test("proctoring signals section renders 'Webcam not requested' for null consent", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      proctoring_signals: {
        webcam_consented: null,
        focus_loss_count: 0,
        focus_loss_duration_seconds: 0,
        fullscreen_exit_count: 0,
        large_paste_count: 0,
        focus_events: [],
        snapshots: [],
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.locator(".status-pill").filter({ hasText: "Webcam not requested" })).toBeVisible();
});

test("focus-loss timeline is collapsed by default and expands on click", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      proctoring_signals: {
        webcam_consented: false,
        focus_loss_count: 2,
        focus_loss_duration_seconds: 90,
        fullscreen_exit_count: 0,
        large_paste_count: 0,
        focus_events: [
          { occurred_at: "2026-06-20T11:05:00+00:00", duration_seconds: 30 },
          { occurred_at: "2026-06-20T11:20:00+00:00", duration_seconds: 60 },
        ],
        snapshots: [],
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  // Timeline summary is visible but individual events are hidden in <details>
  await expect(page.getByText("Focus-loss timeline (2 events)")).toBeVisible();
  // Individual events are not visible until expanded
  await expect(page.getByText(/away for 30s/)).not.toBeVisible();

  // Expand the timeline
  await page.getByText("Focus-loss timeline (2 events)").click();
  await expect(page.getByText(/away for 30s/)).toBeVisible();
  await expect(page.getByText(/away for 1m/)).toBeVisible();
});

test("snapshot thumbnails render for webcam-consented attempt", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      proctoring_signals: {
        webcam_consented: true,
        focus_loss_count: 0,
        focus_loss_duration_seconds: 0,
        fullscreen_exit_count: 0,
        large_paste_count: 0,
        focus_events: [],
        snapshots: [
          { timestamp: "2026-06-20T11:05:00+00:00", trigger: "periodic", url: "https://example.com/snapshot1.jpg" },
          { timestamp: "2026-06-20T11:29:00+00:00", trigger: "submission", url: "https://example.com/snapshot2.jpg" },
        ],
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  // Mock the snapshot images so they don't 404
  await page.route("https://example.com/snapshot*.jpg", async (route) => {
    await route.fulfill({ contentType: "image/jpeg", body: Buffer.alloc(0) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  const strip = page.locator(".snapshot-strip");
  await expect(strip).toBeVisible();
  const thumbs = strip.locator(".snapshot-thumb-link");
  await expect(thumbs).toHaveCount(2);
  // Both thumbnails link to presigned URLs
  await expect(thumbs.nth(0)).toHaveAttribute("href", "https://example.com/snapshot1.jpg");
  await expect(thumbs.nth(1)).toHaveAttribute("href", "https://example.com/snapshot2.jpg");
  // Trigger labels visible
  await expect(strip.getByTitle(/periodic/)).toBeVisible();
  await expect(strip.getByTitle(/submission/)).toBeVisible();
});

// ── Integrity banner ──────────────────────────────────────────────────────────

test("no integrity banner shown for low integrity score", async ({ page }) => {
  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(baseReport) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.locator(".integrity-banner")).not.toBeVisible();
});

test("amber integrity banner shown for medium integrity score", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      integrity_score: {
        label: "medium",
        contributing_factors: [
          { signal: "focus_loss_count", value: 1, weight: "low" },
          { signal: "focus_loss_duration_seconds", value: 45, weight: "low" },
          { signal: "fullscreen_exits", value: 0, weight: "none" },
          { signal: "large_paste_count", value: 0, weight: "none" },
          { signal: "ai_violation_count", value: 0, weight: "none" },
          { signal: "prompt_injection_count", value: 0, weight: "none" },
        ],
        total_weight_points: 2,
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  const banner = page.locator(".integrity-banner.warn");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("Moderate integrity signals");
  await expect(banner).toContainText("Proctoring Signals");
});

test("red integrity banner shown for high integrity score with contributing factor summary", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      integrity_score: {
        label: "high",
        contributing_factors: [
          { signal: "focus_loss_count", value: 5, weight: "high" },
          { signal: "focus_loss_duration_seconds", value: 320, weight: "high" },
          { signal: "fullscreen_exits", value: 2, weight: "medium" },
          { signal: "large_paste_count", value: 1, weight: "low" },
          { signal: "ai_violation_count", value: 0, weight: "none" },
          { signal: "prompt_injection_count", value: 0, weight: "none" },
        ],
        total_weight_points: 8,
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  const banner = page.locator(".integrity-banner.error");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("High integrity risk");
  // Contributing factor summary should name the signals
  await expect(banner).toContainText("5 focus-loss events");
  await expect(banner).toContainText("2 fullscreen exits");
  await expect(banner).toContainText("1 large paste");
  await expect(banner).toContainText("Review proctoring signals");
});

test("red integrity banner for critical score lists all signals", async ({ page }) => {
  const report = {
    ...baseReport,
    report: {
      ...baseReport.report,
      integrity_score: {
        label: "critical",
        contributing_factors: [
          { signal: "focus_loss_count", value: 7, weight: "high" },
          { signal: "focus_loss_duration_seconds", value: 500, weight: "high" },
          { signal: "fullscreen_exits", value: 4, weight: "high" },
          { signal: "large_paste_count", value: 3, weight: "high" },
          { signal: "ai_violation_count", value: 3, weight: "high" },
          { signal: "prompt_injection_count", value: 1, weight: "high" },
        ],
        total_weight_points: 18,
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });
  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  const banner = page.locator(".integrity-banner.error");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("High integrity risk");
  await expect(banner).toContainText("1 prompt injection attempt");
});

// ── Candidate workspace — proctoring ─────────────────────────────────────────

const assessmentFiles = {
  "README.md": "# Assessment\n\nRules and scenario.",
  "task_api/main.py": "def hello():\n    return 'world'\n",
  "tests/test_public_api.py": "def test_public():\n    assert True\n",
};

const startedAttempt = {
  attempt_id: 42,
  status: "in_progress",
  candidate_email: "candidate@example.com",
  assessment: {
    slug: "fastapi_task_api_standard_v2",
    title: "FastAPI Assessment",
    version: "standard_v2",
    seeded_issue_count: 6,
  },
  timing_mode: "untimed",
  duration_minutes: 90,
  started_at: "2026-06-20T11:00:00Z",
  expires_at: null,
  submitted_at: null,
  submission_mode: null,
  files: assessmentFiles,
};

test("webcam consent prompt appears for started attempt", async ({ page }) => {
  await page.route("**/candidate/invites/playwright-token", async (route) => {
    if (route.request().method() !== "GET") { await route.continue(); return; }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(startedAttempt) });
  });
  // Route autosave snapshots
  await page.route("**/candidate/invites/playwright-token/snapshots", async (route) => {
    await route.fulfill({ contentType: "application/json", status: 201, body: JSON.stringify({ snapshot_id: 1, attempt_id: 42, kind: "autosave", status: "in_progress" }) });
  });

  await page.goto("/invite/playwright-token");

  await expect(page.getByRole("heading", { name: "Optional webcam" })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("button", { name: "Allow camera" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Skip" })).toBeVisible();
  await expect(page.getByText("One image every 5 minutes and at submission.")).toBeVisible();
  await expect(page.getByText("No audio is recorded.")).toBeVisible();
  await expect(page.getByText("You can decline — this does not affect your assessment.")).toBeVisible();
});

test("declining webcam consent posts to API and shows workspace", async ({ page }) => {
  let consentPayload: Record<string, unknown> | null = null;

  await page.route("**/candidate/invites/playwright-token", async (route) => {
    if (route.request().method() !== "GET") { await route.continue(); return; }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(startedAttempt) });
  });
  await page.route("**/candidate/invites/playwright-token/snapshots", async (route) => {
    await route.fulfill({ contentType: "application/json", status: 201, body: JSON.stringify({ snapshot_id: 1, attempt_id: 42, kind: "autosave", status: "in_progress" }) });
  });
  await page.route("**/candidate/invites/playwright-token/webcam-consent", async (route) => {
    consentPayload = (await route.request().postDataJSON()) as Record<string, unknown>;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ attempt_id: 42, webcam_consent: false }) });
  });

  await page.goto("/invite/playwright-token");

  await expect(page.getByRole("heading", { name: "Optional webcam" })).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Skip" }).click();

  // After declining, workspace should appear
  await expect(page.locator(".workspace-shell")).toBeVisible({ timeout: 5_000 });

  // Consent endpoint was called with consented: false
  expect(consentPayload).not.toBeNull();
  expect((consentPayload as Record<string, unknown>).consented).toBe(false);
});

test("proctoring events batch endpoint is called when focus is lost and submission happens", async ({ page }) => {
  const proctoringBatches: unknown[] = [];

  await page.route("**/candidate/invites/playwright-token", async (route) => {
    if (route.request().method() !== "GET") { await route.continue(); return; }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(startedAttempt) });
  });
  await page.route("**/candidate/invites/playwright-token/snapshots", async (route) => {
    await route.fulfill({ contentType: "application/json", status: 201, body: JSON.stringify({ snapshot_id: 1, attempt_id: 42, kind: "autosave", status: "in_progress" }) });
  });
  await page.route("**/candidate/invites/playwright-token/webcam-consent", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ attempt_id: 42, webcam_consent: false }) });
  });
  await page.route("**/candidate/invites/playwright-token/proctoring-events/batch", async (route) => {
    proctoringBatches.push(await route.request().postDataJSON());
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ accepted: 1 }) });
  });
  await page.route("**/candidate/invites/playwright-token/submit", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ attempt_id: 42, status: "submitted" }) });
  });

  await page.goto("/invite/playwright-token");
  await expect(page.getByRole("heading", { name: "Optional webcam" })).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page.locator(".workspace-shell")).toBeVisible({ timeout: 5_000 });

  // Simulate focus lost then returned (triggers queued events)
  await page.evaluate(() => {
    window.dispatchEvent(new Event("blur"));
  });
  // Brief pause so blurredAt is recorded
  await page.waitForTimeout(100);
  await page.evaluate(() => {
    window.dispatchEvent(new Event("focus"));
  });

  // Open submit modal and confirm (notes are optional, no pre-fill needed)
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByRole("heading", { name: "Submit final attempt?" })).toBeVisible();
  await page.getByRole("button", { name: "Submit final" }).click();

  // Allow time for async flush + submit
  await page.waitForTimeout(1_500);

  // At least one batch call was made (the flush before submit)
  expect(proctoringBatches.length).toBeGreaterThan(0);
  // Each batch has an "events" array
  const firstBatch = proctoringBatches[0] as { events: unknown[] };
  expect(Array.isArray(firstBatch.events)).toBe(true);
});
