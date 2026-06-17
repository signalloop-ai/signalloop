import { expect, test } from "@playwright/test";

const attempt = {
  attempt_id: 42,
  candidate_email: "candidate@example.com",
  status: "submitted",
  invite_token: "playwright-token",
  invite_url: "http://127.0.0.1:3000/invite/playwright-token",
  assessment: {
    slug: "fastapi_task_api_v1",
    title: "FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment",
    version: "v1",
  },
  created_at: "2026-06-17T10:00:00+00:00",
  submitted_at: "2026-06-17T10:30:00+00:00",
  report_id: 9,
  recommendation: "advance",
  score_total: 82,
};

const report = {
  attempt_id: 42,
  report_id: 9,
  recommendation: "advance",
  score_total: 82,
  report: {
    metadata: {
      candidate_email: "candidate@example.com",
      submitted_at: "2026-06-17T10:30:00+00:00",
      assessment: attempt.assessment,
    },
    executive_summary: {
      summary: "Candidate fixed core validation and ownership issues with clear verification.",
      evidence_limits: [],
    },
    overall_recommendation: "advance",
    scores: {
      total: 82,
      max_points: 100,
      confidence: "medium",
      categories: [
        {
          category: "Public test coverage",
          points: 20,
          max_points: 20,
          evidence: "All initially failing public tests now pass.",
        },
      ],
    },
    rubric_weights: {
      public_test_coverage: 20,
      hidden_test_coverage: 30,
      regression: 15,
      candidate_written_tests: 15,
      ai_collaboration: 10,
      explanation_and_decisions: 10,
    },
    public_test_results: {
      run_count: 2,
      initially_failing_tests: [
        "test_duplicate_user_email_is_rejected",
        "test_blank_task_title_is_rejected",
      ],
      last_run_summary: {
        collected: 4,
        passed: 4,
        failed: 0,
        failure_names: [],
        status: "passed",
      },
    },
    hidden_test_results: {
      seeded_issue_areas: [
        "duplicate email handling",
        "empty or whitespace-only task title",
        "invalid status transitions",
        "ownership/access behavior",
        "unknown actor access",
        "idempotent delete",
      ],
      summary: {
        collected: 6,
        passed: 5,
        failed: 1,
        failure_names: ["test_status_transition_requires_in_progress"],
        status: "failed",
      },
    },
    candidate_tests: {
      added_test_files: ["tests/test_candidate_validation.py"],
      modified_test_files: [],
      candidate_test_file_count: 1,
    },
    ai_collaboration: {
      message_count: 2,
      candidate_prompt_count: 1,
      policy_redirect_count: 0,
      pasted_ai_code: { pasted_ai_code_count: 0, matches: [] },
      large_paste_events: { large_paste_count: 0, events: [] },
      flagged_prompts: [],
      all_candidate_messages: [
        {
          message: "This ownership public test failed. How should I debug it?",
          at: "2026-06-17T10:20:00+00:00",
        },
      ],
    },
    process_evidence: {
      snapshot_count: 4,
      test_run_count: 3,
      test_runs: [
        { id: 1, type: "public", status: "passed", duration_ms: 120 },
        { id: 2, type: "hidden", status: "failed", duration_ms: 180 },
      ],
    },
    explanation_submitted: {
      final_explanation: "Candidate fixed core validation and ownership issues with clear verification.",
      decision_log: "Chose explicit authorization behavior and documented the status transition policy.",
    },
    timeline: [{ at: "2026-06-17T10:30:00+00:00", type: "submission", summary: "Submitted" }],
    follow_up_questions: ["How did you choose the authorization response behavior?"],
  },
};

test("employer can log in locally, create an invite, and view a report", async ({ page }) => {
  let attempts: Array<Record<string, unknown>> = [attempt];

  await page.route("**/assessment-attempts", async (route) => {
    if (route.request().method() === "POST") {
      attempts = [
        {
          ...attempt,
          attempt_id: 43,
          candidate_email: "new-candidate@example.com",
          status: "created",
          invite_token: "new-token",
          invite_url: "http://127.0.0.1:3000/invite/new-token",
          submitted_at: null,
          report_id: null,
          recommendation: null,
          score_total: null,
        },
        ...attempts,
      ];
      await route.fulfill({
        contentType: "application/json",
        status: 201,
        body: JSON.stringify({
          attempt_id: 43,
          invite_token: "new-token",
          invite_url: "http://127.0.0.1:3000/invite/new-token",
          status: "created",
        }),
      });
      return;
    }

    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(attempts),
    });
  });

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(report),
    });
  });

  await page.goto("/employer");

  await expect(page.getByRole("heading", { name: "SignalLoop Employer Portal" })).toBeVisible();
  await page.getByRole("button", { name: "Use local employer login" }).click();

  await expect(page.getByRole("heading", { name: "Employer Review" })).toBeVisible();
  await expect(page.getByText("candidate@example.com")).toBeVisible();
  await expect(page.getByText("82 · advance")).toBeVisible();

  await page.getByLabel("Candidate email").fill("new-candidate@example.com");
  await page.getByRole("button", { name: "Create invite" }).click();
  await expect(page.getByText("http://127.0.0.1:3000/invite/new-token")).toBeVisible();
  await expect(page.getByText("new-candidate@example.com")).toBeVisible();

  await page.getByRole("link", { name: "View" }).nth(0).click();
  await expect(page.getByRole("heading", { name: "Evidence Report" })).toBeVisible();
  await expect(page.getByText("Candidate fixed core validation")).toBeVisible();
  await expect(page.getByText("Public test coverage")).toBeVisible();
  await expect(page.getByText("Public test results")).toBeVisible();
  await expect(page.getByText("How did you choose the authorization response behavior?")).toBeVisible();
});
