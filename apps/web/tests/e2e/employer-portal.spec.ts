import { expect, test, type Page } from "@playwright/test";

// Fake JWT with exp=year 2096 so Clerk won't try to refresh it
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

/**
 * Intercept Clerk's FAPI client endpoint to return a fake authenticated session.
 * This lets mocked Playwright tests reach the employer dashboard without a real
 * Clerk account. The JWT in the session is fake but since all API calls are also
 * mocked via page.route(), the backend never validates it.
 */
async function mockClerkSignedIn(page: Page): Promise<void> {
  // Handle all Clerk client-related requests in one handler.
  // /v1/client → fake authenticated session
  // /v1/client/sessions/*/tokens → fake token refresh response
  await page.route("**clerk.accounts.dev/v1/client**", (route) => {
    const url = route.request().url();
    if (url.includes("/sessions/") && url.includes("/tokens")) {
      void route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ object: "token", jwt: FAKE_JWT }),
      });
    } else {
      void route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(FAKE_CLIENT_RESPONSE),
      });
    }
  });
}

function watchForDuplicateKeyWarnings(page: Page): string[] {
  const duplicateKeyWarnings: string[] = [];
  page.on("console", (message) => {
    const text = message.text();
    if (text.includes("Encountered two children with the same key")) {
      duplicateKeyWarnings.push(text);
    }
  });
  page.on("pageerror", (error) => {
    const text = error.message;
    if (text.includes("Encountered two children with the same key")) {
      duplicateKeyWarnings.push(text);
    }
  });
  return duplicateKeyWarnings;
}

const attempt = {
  attempt_id: 42,
  candidate_email: "candidate@example.com",
  status: "submitted",
  invite_token: "playwright-token",
  invite_url: "http://127.0.0.1:3000/invite/playwright-token",
  assessment: {
    slug: "fastapi_task_api_standard_v2",
    title: "FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment",
    version: "standard_v2",
  },
  assessment_level: "standard",
  timing_mode: "untimed",
  evaluator_feedback_mode: "strict",
  duration_minutes: 90,
  expires_at: null,
  submission_mode: "manual",
  created_at: "2026-06-17T10:00:00+00:00",
  submitted_at: "2026-06-17T10:30:00+00:00",
  report_id: 9,
  recommendation: "advance",
  score_total: 82,
};

const adaptiveBlueprintWithDuplicateUnsupportedSkill = {
  id: 501,
  role_profile_id: 301,
  candidate_profile_id: 401,
  title: "Senior Backend Engineer Adaptive Backend Assessment",
  assessment_pack_slug: "fastapi_task_api_advanced_v1",
  assessment_level: "advanced",
  timing_mode: "timed",
  duration_minutes: 120,
  evaluator_feedback_mode: "strict",
  skill_mapping: {
    role_skill_ids: ["backend.python", "backend.fastapi", "infra.kubernetes"],
    candidate_skill_ids: ["backend.python", "backend.fastapi", "infra.kubernetes"],
    required_overlap: ["backend.python", "backend.fastapi"],
    required_gap: ["infra.kubernetes"],
    extra_claimed: [],
    unsupported_required: ["infra.kubernetes"],
    unsupported_claimed: ["infra.kubernetes"],
    unmapped_terms: [],
  },
  coverage: {
    module_id: "fastapi_task_api_advanced_v1",
    assessment_pack_slug: "fastapi_task_api_advanced_v1",
    label: "Strong backend/API coverage with explicit unsupported caveats",
    directly_tested: ["backend.fastapi", "backend.authorization", "backend.multi_tenancy"],
    partially_tested: ["backend.reliability"],
    not_tested: ["infra.kubernetes"],
  },
  rationale: [
    "Advanced FastAPI is the strongest currently supported executable assessment for the matched backend/API skills.",
  ],
  follow_up_probes: [
    {
      source: "unsupported_required",
      skill_id: "infra.kubernetes",
      question: "Ask the candidate to walk through a real Kubernetes rollout or failure scenario.",
    },
  ],
  caveats: ["Not directly assessed by the selected coding task: Kubernetes."],
  status: "draft",
  approved_at: null,
  used_at: null,
  created_at: "2026-06-29T10:00:00+00:00",
};

const futureFrontendBlueprint = {
  ...adaptiveBlueprintWithDuplicateUnsupportedSkill,
  id: 777,
  title: "Frontend Platform Engineer Frontend Platform Assessment Blueprint",
  assessment_pack_slug: "future_frontend_platform_v1",
  assessment_level: "future_frontend",
  duration_minutes: 90,
  coverage: {
    module_id: "future_frontend_platform_v1",
    assessment_pack_slug: "future_frontend_platform_v1",
    label: "Future Frontend Platform Assessment - planned, not invite-ready",
    directly_tested: [],
    partially_tested: [],
    not_tested: ["frontend.react", "frontend.typescript", "frontend.accessibility"],
  },
  skill_mapping: {
    role_skill_ids: ["frontend.react", "frontend.typescript", "frontend.accessibility"],
    candidate_skill_ids: ["frontend.react", "frontend.typescript", "frontend.accessibility"],
    required_overlap: ["frontend.react", "frontend.typescript", "frontend.accessibility"],
    required_gap: [],
    candidate_extra: [],
    unsupported_required: ["frontend.react", "frontend.typescript", "frontend.accessibility"],
    unsupported_claimed: ["frontend.react", "frontend.typescript", "frontend.accessibility"],
    unmapped_terms: [],
  },
  rationale: [
    "The JD maps primarily to a frontend platform assessment.",
    "This is a valid assessment blueprint, but the executable module is on the roadmap.",
  ],
  follow_up_probes: [
    {
      source: "future_assessment_scope",
      skill_id: "frontend.react",
      question: "The future assessment should test React with a realistic UI work sample.",
    },
  ],
  caveats: ["Future assessment planned: Future Frontend Platform Assessment."],
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
      evaluator_feedback_mode: "strict",
      timing: {
        timing_mode: "untimed",
        duration_minutes: 90,
        time_used_minutes: 30,
        started_at: "2026-06-17T10:00:00+00:00",
        submitted_at: "2026-06-17T10:30:00+00:00",
        expires_at: null,
        submission_mode: "manual",
      },
    },
    executive_summary: {
      summary: "Candidate fixed core validation and ownership issues with clear verification.",
      evidence_limits: ["Scores are deterministic estimates from captured process evidence."],
    },
    overall_recommendation: "advance",
    scores: {
      total: 82,
      max_points: 100,
      categories: [
        { category: "Public issue resolution", points: 15, max_points: 15, evidence: "All initially failing public tests now pass." },
        { category: "Private issue generalization", points: 16, max_points: 20, evidence: "Hidden tests: 4/5 passed." },
        { category: "Feature/design implementation", points: 18, max_points: 20, evidence: "Most feature/design checks passed." },
        { category: "Candidate-written tests", points: 11, max_points: 15, evidence: "1 test file added, 2 test functions." },
        { category: "AI collaboration", points: 20, max_points: 20, evidence: "1 candidate prompts, no policy redirects." },
        { category: "Regression/code quality", points: 10, max_points: 10, evidence: "No regression detected in previously-passing tests." },
      ],
    },
    rubric_weights: {
      public_issue_resolution: 15,
      private_issue_generalization: 20,
      feature_design_implementation: 20,
      candidate_tests: 15,
      ai_collaboration: 20,
      regression_code_quality: 10,
    },
    public_test_results: {
      run_count: 2,
      initially_failing_tests: ["test_duplicate_user_email_is_rejected", "test_blank_task_title_is_rejected"],
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
    feature_design_implementation: {
      category: "Feature/design implementation",
      points: 18,
      max_points: 20,
      evidence: "Most feature/design checks passed.",
    },
    candidate_tests: {
      added_test_files: ["tests/test_candidate_validation.py"],
      modified_test_files: [],
      candidate_test_file_count: 1,
      functions_added: 3,
      functions_modified: 0,
    },
    ai_collaboration: {
      message_count: 2,
      candidate_prompt_count: 1,
      policy_redirect_count: 0,
      pasted_ai_code: { pasted_ai_code_count: 0, matches: [] },
      large_paste_events: { large_paste_count: 0, events: [] },
      flagged_prompts: [],
      all_candidate_messages: [
        { message: "This ownership public test failed. How should I debug it?", at: "2026-06-17T10:20:00+00:00" },
      ],
    },
    ai_integrity_risk: {
      label: "low",
      signals: {
        policy_redirect_count: 0,
        severe_redirect_count: 0,
        prompt_injection_count: 0,
        pasted_ai_code_count: 0,
        large_paste_event_count: 0,
        weak_submission_review: false,
      },
      score_impact: "none_phase_2",
    },
    favo: {
      frame: { label: "strong", evidence: "Most feature/design checks passed." },
      ask: { label: "present", evidence: "1 candidate prompt(s) captured." },
      verify: { label: "strong", evidence: "2 public run(s), 1 candidate test file(s), hidden status failed." },
      own: { label: "present", evidence: "4/4 submission-review questions answered." },
    },
    llm_assisted_review: {
      status: "not_run",
      reason: "LLM-assisted report review is disabled in local deterministic tests.",
      provider_configured: false,
    },
    process_evidence: {
      snapshot_count: 4,
      test_run_count: 3,
      test_runs: [
        { id: 1, type: "public", status: "passed", duration_ms: 120, timings: { api_total_ms: 1500, worker_pytest_ms: 500 } },
        { id: 2, type: "hidden", status: "failed", duration_ms: 180, timings: { api_total_ms: 2500, ecs_wait_stopped_ms: 1700 } },
      ],
    },
    explanation_submitted: {
      final_explanation: "Candidate fixed core validation and ownership issues with clear verification.",
      decision_log: "Chose explicit authorization behavior and documented the status transition policy.",
    },
    submission_review: {
      what_changed: "Candidate fixed core validation and ownership issues.",
      tradeoffs_or_product_decisions: "Chose explicit authorization behavior.",
      verification: "Ran public tests and added focused candidate tests.",
      improvements_with_more_time: "Add more hidden-edge coverage.",
      additional_notes: "",
      required_answer_count: 4,
      required_question_count: 4,
    },
    timeline: [
      { at: "2026-06-17T10:00:00+00:00", type: "attempt_started", summary: "Candidate opened invite" },
      { at: "2026-06-17T10:30:00+00:00", type: "attempt_submitted", summary: "Candidate submitted final solution" },
    ],
    follow_up_questions: [
      "How did you choose the authorization response behavior?",
      "Walk through the status transition policy you enforced.",
    ],
  },
};

test("employer can sign in with Clerk, create an invite, and view a report", async ({ page }) => {
  let attempts: Array<Record<string, unknown>> = [attempt];
  let createPayload: Record<string, unknown> | null = null;

  await page.route("**/assessment-attempts", async (route) => {
    if (route.request().method() === "POST") {
      createPayload = (await route.request().postDataJSON()) as Record<string, unknown>;
      attempts = [
        {
          ...attempt,
          attempt_id: 43,
          candidate_email: "new-candidate@example.com",
          status: "created",
          assessment: {
            slug: "fastapi_task_api_advanced_v1",
            title: "FastAPI Team Task API Deep Debugging, Authorization & Product Judgment Assessment",
            version: "advanced_v1",
          },
          assessment_level: "advanced",
          timing_mode: "timed",
          evaluator_feedback_mode: "guided",
          duration_minutes: 120,
          expires_at: null,
          submission_mode: null,
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

  await mockClerkSignedIn(page);
  await page.goto("/employer");

  await expect(page.getByRole("heading", { name: "SignalLoop" })).toBeVisible({ timeout: 10_000 });
  // Overview is the landing view; recent activity lists the existing candidate.
  await expect(page.getByRole("heading", { name: "Assessment creation paths" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Direct coding challenge" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Adaptive builder" })).toBeVisible();
  await expect(page.getByText("candidate@example.com")).toBeVisible();

  // Candidates view shows the attempt table with the recommendation.
  await page.getByRole("button", { name: "Candidates" }).click();
  await expect(page.locator(".attempt-recommendation").filter({ hasText: "advance" })).toBeVisible();

  // Build and send an invite from the Assessments view.
  await page.getByRole("button", { name: "Assessments" }).click();
  await page.getByLabel("Candidate email").fill("new-candidate@example.com");
  await page.getByRole("group", { name: "Assessment level" }).getByRole("button", { name: "Advanced" }).click();
  await page.getByRole("group", { name: "Timing enforcement" }).getByRole("button", { name: "Strict" }).click();
  await page.getByRole("group", { name: "Evaluator feedback" }).getByRole("button", { name: "Guided" }).click();
  await page.getByRole("button", { name: "Send invite" }).click();
  await expect(page.locator("input.invite-url-input")).toHaveValue("http://127.0.0.1:3000/invite/new-token");
  expect(createPayload).not.toBeNull();
  const submittedPayload = createPayload as unknown as Record<string, unknown>;
  expect(submittedPayload.evaluator_feedback_mode).toBe("guided");

  // The new candidate appears in the Candidates view.
  await page.getByRole("button", { name: "Candidates" }).click();
  await expect(page.getByText("new-candidate@example.com")).toBeVisible();
  await expect(page.getByText("Timed 120 min · guided")).toBeVisible();

  await page.getByRole("link", { name: "View" }).nth(0).click();
  await expect(page.getByRole("heading", { name: "Evidence Report" })).toBeVisible();
  await expect(page.getByText("Candidate fixed core validation").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Score breakdown" })).toBeVisible();
  await expect(page.locator(".chart-bar-label").filter({ hasText: "Public tests" }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Public tests" })).toBeVisible();
  await expect(page.getByText("Evaluator mode")).toBeVisible();
  await expect(page.getByText("strict")).toBeVisible();
  await expect(page.getByText("How did you choose the authorization response behavior?")).toBeVisible();
});

test("adaptive builder renders overlapping unsupported skills without duplicate-key warnings", async ({ page }) => {
  const duplicateKeyWarnings = watchForDuplicateKeyWarnings(page);
  let attempts: Array<Record<string, unknown>> = [attempt];

  await page.route("**/assessment-attempts", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(attempts) });
  });
  await page.route("**/employer/adaptive/role-profiles", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify({ id: adaptiveBlueprintWithDuplicateUnsupportedSkill.role_profile_id }),
    });
  });
  await page.route("**/employer/adaptive/candidate-profiles", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify({ id: adaptiveBlueprintWithDuplicateUnsupportedSkill.candidate_profile_id }),
    });
  });
  await page.route("**/employer/adaptive/blueprints", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify([]),
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      status: 201,
      body: JSON.stringify(adaptiveBlueprintWithDuplicateUnsupportedSkill),
    });
  });
  await page.route("**/employer/adaptive/blueprints/*/approve", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ...adaptiveBlueprintWithDuplicateUnsupportedSkill, status: "approved" }),
    });
  });
  await page.route("**/employer/adaptive/blueprints/*/invites", async (route) => {
    attempts = [
      {
        ...attempt,
        attempt_id: 88,
        candidate_email: "candidate.phase5@example.com",
        status: "created",
        invite_token: "adaptive-token",
        invite_url: "http://127.0.0.1:3000/invite/adaptive-token",
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
        attempt_id: 88,
        invite_token: "adaptive-token",
        invite_url: "http://127.0.0.1:3000/invite/adaptive-token",
        status: "created",
      }),
    });
  });
  await page.route("**/employer/adaptive/extract-document-text", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        filename: route.request().headers()["x-filename"] ?? "jd.txt",
        text: "We need Python, FastAPI, authorization, multi-tenant APIs, Kubernetes basics, and reliability.",
      }),
    });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer");
  await page.getByRole("button", { name: "Assessments" }).click();
  await expect(page.getByRole("group", { name: "Assessment creation path" }).getByRole("button", { name: "Direct coding challenge" })).toHaveClass(/active/);
  await expect(page.getByRole("button", { name: "Send invite" })).toBeVisible();

  await page.getByRole("group", { name: "Assessment creation path" }).getByRole("button", { name: "Adaptive builder" }).click();
  await expect(page.getByRole("button", { name: "Send invite" })).not.toBeVisible();
  const adaptiveBuilder = page.locator(".mod-card").filter({ hasText: "Adaptive builder" });
  await adaptiveBuilder.getByPlaceholder("candidate@company.com").fill("candidate.phase5@example.com");
  await adaptiveBuilder.getByLabel("Upload JD").setInputFiles({
    name: "jd.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("backend role"),
  });
  await expect(adaptiveBuilder.getByPlaceholder("Paste the job description or role requirements.")).toHaveValue(/Kubernetes basics/);
  await adaptiveBuilder.getByPlaceholder("Optional for blueprint generation; recommended for follow-up probes.").fill(
    "Backend engineer with Python, FastAPI, and Kubernetes collaboration experience.",
  );
  await adaptiveBuilder.getByRole("button", { name: "Generate adaptive blueprint" }).click();

  const notDirectlyTested = page.locator(".assessment-section").filter({ hasText: "Not directly tested" });
  await expect(notDirectlyTested.getByText("infra / kubernetes")).toHaveCount(1);
  await expect(page.getByText("Ask the candidate to walk through a real Kubernetes rollout or failure scenario.")).toBeVisible();
  expect(duplicateKeyWarnings).toEqual([]);

  await page.getByRole("button", { name: "Approve and send invite" }).click();
  await expect(page.getByLabel("Adaptive invite URL")).toHaveValue("http://127.0.0.1:3000/invite/adaptive-token");
});

test("adaptive builder shows future assessment blueprint without invite-ready actions", async ({ page }) => {
  await page.route("**/assessment-attempts", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify([attempt]) });
  });
  await page.route("**/employer/adaptive/role-profiles", async (route) => {
    await route.fulfill({ contentType: "application/json", status: 201, body: JSON.stringify({ id: 701 }) });
  });
  await page.route("**/employer/adaptive/candidate-profiles", async (route) => {
    await route.fulfill({ contentType: "application/json", status: 201, body: JSON.stringify({ id: 702 }) });
  });
  await page.route("**/employer/adaptive/blueprints", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify([futureFrontendBlueprint]) });
      return;
    }
    await route.fulfill({ contentType: "application/json", status: 201, body: JSON.stringify(futureFrontendBlueprint) });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer");
  await page.getByRole("button", { name: "Assessments" }).click();
  await page.getByRole("group", { name: "Assessment creation path" }).getByRole("button", { name: "Adaptive builder" }).click();
  await page.getByRole("button", { name: /Frontend Platform Engineer Frontend Platform Assessment Blueprint/ }).click();

  await expect(page.getByText("Future Frontend Platform Assessment - planned, not invite-ready")).toBeVisible();
  await expect(page.getByText("Planned assessment", { exact: true })).toBeVisible();
  await expect(page.getByText("Invite sending is disabled because this assessment is planned for a future module.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve and send invite" })).toBeDisabled();
});

test("evidence report renders all Phase 2 sections", async ({ page }) => {
  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(report),
    });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.getByRole("heading", { name: "Evidence Report" })).toBeVisible();

  // === Top metrics row ===
  // Recommendation shown in .rec-value, assessment version in .rec-label
  await expect(page.locator(".rec-value").filter({ hasText: /advance/ })).toBeVisible();
  await expect(page.getByText("standard_v2")).toBeVisible();

  // === Timing metadata row ===
  await expect(page.getByText("untimed", { exact: true })).toBeVisible();
  // Untimed: shows "Time used" with value only (no duration / used split)
  await expect(page.getByText("30 min")).toBeVisible();
  await expect(page.getByText("Manual")).toBeVisible();
  await expect(page.getByText("Evaluator mode")).toBeVisible();
  await expect(page.getByText("strict")).toBeVisible();

  // === Executive summary ===
  await expect(page.getByRole("heading", { name: "Executive summary" })).toBeVisible();
  await expect(page.getByText("Candidate fixed core validation and ownership issues with clear verification.")).toBeVisible();
  // Evidence limits are inside a collapsed Disclosure — open it first
  await page.getByText("Evidence limits").click();
  await expect(page.getByText("Scores are deterministic estimates from captured process evidence.")).toBeVisible();

  // === Score breakdown — all 6 rubric categories ===
  await expect(page.getByRole("heading", { name: "Score breakdown" })).toBeVisible();
  for (const label of [
    "Public issue resolution",
    "Private issue generalization",
    "Feature/design implementation",
    "Candidate-written tests",
    "AI collaboration",
    "Regression/code quality",
  ]) {
    await expect(page.locator(".chart-bar-label").filter({ hasText: label })).toBeVisible();
  }

  // === Public test results ===
  await expect(page.getByRole("heading", { name: "Public tests" })).toBeVisible();
  await expect(page.getByText(/ran 2 time\(s\)/)).toBeVisible();
  // Initially failing tests are inside a collapsed Disclosure — open it first
  await page.getByText("Initially failing tests").click();
  await expect(page.getByText("test_duplicate_user_email_is_rejected")).toBeVisible();
  await expect(page.getByText("test_blank_task_title_is_rejected")).toBeVisible();

  // === Hidden test results ===
  await expect(page.getByRole("heading", { name: "Hidden tests" })).toBeVisible();
  // Failure names and seeded areas are inside collapsed Disclosures — open them
  await page.getByText("1 failure(s)").click();
  await expect(page.getByText("test_status_transition_requires_in_progress")).toBeVisible();
  await page.getByText("Seeded issue areas").click();
  await expect(page.getByText("duplicate email handling")).toBeVisible();
  await expect(page.getByText("ownership/access behavior")).toBeVisible();

  // === Enhancements (Feature/design implementation) ===
  await expect(page.getByRole("heading", { name: "Enhancements" })).toBeVisible();
  await expect(page.getByText("18/20: Most feature/design checks passed.")).toBeVisible();

  // === FAVO interpretation ===
  await expect(page.getByText("FAVO interpretation")).toBeVisible();
  // FAVO area keys rendered as <strong> inside the favo-grid (capitalized)
  const favoGrid = page.locator(".favo-grid");
  await expect(favoGrid.getByText("Frame", { exact: true })).toBeVisible();
  await expect(favoGrid.getByText("Ask", { exact: true })).toBeVisible();
  await expect(favoGrid.getByText("Verify", { exact: true })).toBeVisible();
  await expect(favoGrid.getByText("Own", { exact: true })).toBeVisible();
  // FAVO labels and evidence snippets
  await expect(favoGrid.getByText(/strong.*Most feature\/design checks passed/)).toBeVisible();
  await expect(favoGrid.getByText(/present.*1 candidate prompt/)).toBeVisible();

  // === Candidate-written tests ===
  await expect(page.getByRole("heading", { name: "Candidate-written tests" })).toBeVisible();
  // Format: "N functions added" (functions_added=3 in mock)
  await expect(page.getByText("3 functions added")).toBeVisible();
  // File name is inside collapsed "Files changed" Disclosure — open it
  await page.getByText("Files changed").click();
  await expect(page.getByText("tests/test_candidate_validation.py")).toBeVisible();

  // === AI collaboration ===
  await expect(page.getByRole("heading", { name: "AI collaboration" })).toBeVisible();
  // Format: "N prompt(s) · M redirect(s) · integrity risk: label"
  await expect(page.getByText(/1 prompt\(s\).*0 redirect\(s\)/)).toBeVisible();
  await expect(page.getByText("integrity risk:")).toBeVisible();
  // No paste warnings (counts are 0)
  await expect(page.getByText(/AI code block.*found verbatim/)).not.toBeVisible();
  await expect(page.getByText(/large paste event/)).not.toBeVisible();
  // Signals inside collapsed "Integrity signals" Disclosure
  await page.getByText("Integrity signals").click();
  for (const signal of [
    "policy_redirect_count",
    "severe_redirect_count",
    "prompt_injection_count",
    "pasted_ai_code_count",
    "large_paste_event_count",
    "weak_submission_review",
  ]) {
    await expect(page.getByText(new RegExp(signal))).toBeVisible();
  }

  // === Submission review ===
  await expect(page.getByRole("heading", { name: "Submission review" })).toBeVisible();
  await expect(page.getByText("Candidate fixed core validation and ownership issues.")).toBeVisible();
  await expect(page.getByText("Chose explicit authorization behavior.")).toBeVisible();
  await expect(page.getByText("Ran public tests and added focused candidate tests.")).toBeVisible();
  await expect(page.getByText("Add more hidden-edge coverage.")).toBeVisible();

  // === Process evidence (summary always visible; runs inside collapsed Disclosure) ===
  await expect(page.getByRole("heading", { name: "Process evidence" })).toBeVisible();
  await expect(page.locator(".process-mini-metric").filter({ hasText: "Snapshots" })).toContainText("4");
  await expect(page.locator(".process-mini-metric").filter({ hasText: "Test runs" })).toContainText("3");
  // Open the runs disclosure to check individual run entries
  await page.getByText("Test run details").click();
  await expect(page.getByText(/public — passed/)).toBeVisible();
  await expect(page.getByText(/hidden — failed/)).toBeVisible();
  // api_total_ms for run 1 is 1500ms → "1.5s"
  await expect(page.getByText(/1\.5s/)).toBeVisible();

  // === Suggested follow-up questions ===
  await expect(page.getByRole("heading", { name: "Suggested interview follow-ups" })).toBeVisible();
  await expect(page.getByText("How did you choose the authorization response behavior?")).toBeVisible();
  await expect(page.getByText("Walk through the status transition policy you enforced.")).toBeVisible();

  // === Timeline ===
  await expect(page.getByRole("heading", { name: "Timeline" })).toBeVisible();
  await page.getByText("Show timeline").click();
  await expect(page.getByText("attempt_started")).toBeVisible();
  await expect(page.getByText("attempt_submitted")).toBeVisible();
  await expect(page.getByText("Candidate opened invite")).toBeVisible();
  await expect(page.getByText("Candidate submitted final solution")).toBeVisible();
});

test("adaptive evidence report renders overlapping unsupported skills without duplicate-key warnings", async ({ page }) => {
  const duplicateKeyWarnings = watchForDuplicateKeyWarnings(page);
  const adaptiveReport = {
    ...report,
    report: {
      ...report.report,
      adaptive_context: {
        blueprint_id: adaptiveBlueprintWithDuplicateUnsupportedSkill.id,
        role: {
          title: "Senior Backend Engineer",
          seniority: "senior",
          role_family: "backend",
        },
        selected_assessment: {
          assessment_pack_slug: "fastapi_task_api_advanced_v1",
          assessment_level: "advanced",
          duration_minutes: 120,
          evaluator_feedback_mode: "strict",
        },
        skill_mapping: adaptiveBlueprintWithDuplicateUnsupportedSkill.skill_mapping,
        coverage: adaptiveBlueprintWithDuplicateUnsupportedSkill.coverage,
        rationale: adaptiveBlueprintWithDuplicateUnsupportedSkill.rationale,
        caveats: adaptiveBlueprintWithDuplicateUnsupportedSkill.caveats,
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(adaptiveReport) });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  await expect(page.getByRole("heading", { name: "Role-adaptive context" })).toBeVisible();
  const notDirectlyTested = page.locator(".report-grid").filter({ hasText: "Not directly tested" });
  await expect(notDirectlyTested.getByText("infra / kubernetes")).toHaveCount(1);
  expect(duplicateKeyWarnings).toEqual([]);
});

test("evidence report with AI integrity risk medium shows warning style", async ({ page }) => {
  const mediumRiskReport = {
    ...report,
    report: {
      ...report.report,
      ai_integrity_risk: {
        label: "medium",
        signals: {
          policy_redirect_count: 1,
          severe_redirect_count: 0,
          prompt_injection_count: 0,
          pasted_ai_code_count: 0,
          large_paste_event_count: 0,
          weak_submission_review: false,
        },
        score_impact: "none_phase_2",
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(mediumRiskReport) });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");
  // Integrity risk banner appears as a status pill at the top of the report
  await expect(page.locator(".status-pill.warn").filter({ hasText: /Integrity risk/i })).toBeVisible();
  // The risk label itself uses report-warn class for non-low values
  await expect(page.locator(".report-warn").filter({ hasText: "medium" })).toBeVisible();
});

test("evidence report shows paste warnings when AI code or large paste detected", async ({ page }) => {
  const pasteReport = {
    ...report,
    report: {
      ...report.report,
      ai_collaboration: {
        ...report.report.ai_collaboration,
        pasted_ai_code: {
          pasted_ai_code_count: 2,
          matches: [
            { code_preview: "def check_owner(task, actor_id):\n    ...", found_in_files: ["task_api/main.py"] },
          ],
        },
        large_paste_events: {
          large_paste_count: 1,
          events: [
            { file: "task_api/main.py", lines_added: 14, snapshot_kind: "autosave", at: "2026-06-17T10:15:00+00:00", code_preview: "..." },
          ],
        },
      },
    },
  };

  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(pasteReport) });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");
  await expect(page.getByText(/2 AI code block\(s\) found verbatim in submission/)).toBeVisible();
  await expect(page.getByText(/1 large paste event\(s\) detected/)).toBeVisible();
});

test("evidence report shows hidden test failure names and seeded issue areas", async ({ page }) => {
  await page.route("**/assessment-attempts/42/evidence-report", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(report) });
  });

  await mockClerkSignedIn(page);
  await page.goto("/employer/reports/42");

  // Failure names inside collapsed Disclosure — open it first
  await page.getByText("1 failure(s)").click();
  await expect(page.getByText("test_status_transition_requires_in_progress")).toBeVisible();

  // Seeded issue areas inside collapsed "Seeded issue areas" Disclosure — open it
  await page.getByText("Seeded issue areas").click();
  for (const area of [
    "duplicate email handling",
    "empty or whitespace-only task title",
    "invalid status transitions",
    "ownership/access behavior",
    "unknown actor access",
    "idempotent delete",
  ]) {
    await expect(page.getByText(area)).toBeVisible();
  }
});
