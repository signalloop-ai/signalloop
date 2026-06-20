# Changes Log

Running record of bugs found, fixes applied, and important config changes made during
post-MVP validation. Read this before touching the files listed under each entry.

---

## 2026-06-20 — Local Phase 2 Validation Cleanup

**Symptom:** Review of the latest Phase 2 changes found local validation drift:

- `next.config.ts` could inline empty public env values when root `.env` was absent or
  shell values were set.
- `npm run typecheck` failed in the candidate workspace e2e test.
- Real-Postgres `schema_health` tests were collected by the default API test command.
- Local docs still described the removed employer dev-login fallback.
- Real API Playwright helper still clicked the removed "Use local employer login"
  button.

**Root cause:** Clerk-only auth and Phase 2 live testing changes were applied across
code, tests, and docs at different times, leaving stale local setup assumptions.

**Files changed:**

- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `README.md`
- `apps/web/README.md`
- `apps/web/next.config.ts`
- `apps/web/tests/e2e/candidate-workspace.spec.ts`
- `apps/web/tests/e2e/real-api-invite-flow.spec.ts`
- `apps/api/tests/test_schema_health.py`
- `docs/development/testing.md`
- `docs/development/known-limitations.md`
- `docs/development/local-pilot-checklist.md`
- `docs/enhancements/phase-2-assessment-system/03-employer-assessment-configuration.md`
- `docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`

**What changed:**

- `next.config.ts` now prefers `process.env` values with root `.env` as fallback.
- Schema-health tests now skip unless `RUN_SCHEMA_HEALTH_TESTS=1`.
- Local docs now state that employer routes require Clerk locally and in production.
- Real API invite Playwright test now uses a pre-created `REAL_API_INVITE_TOKEN`.
- Candidate auto-expiry e2e test uses a mutable capture holder that typechecks.
- Stale docs saying Advanced is disabled were updated to reflect the implemented
  Advanced pack.

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 66 passed, 3 skipped.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 22 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- --workers=1`
  -> 16 passed, 2 skipped.
- Local live Standard candidate flow passed against disposable SQLite API, local Docker
  worker, and built web server.
- Local live Advanced candidate flow passed against the same local stack.
- Persisted live test-run outputs confirmed pytest ran inside the Docker assessment
  image for both public and hidden runs.

**Follow-up:** Real employer portal invite creation remains Clerk-only. Full employer
real-API Playwright creation requires a real signed-in Clerk browser session or a
valid test Clerk token.

---

## 2026-06-19 — Clerk-Only Auth + Local/Production Parity

**Symptom / goal:**

- Employer portal was showing "Local dev login active until Clerk keys are configured"
  even after Clerk was set up, because `EMPLOYER_AUTH_REQUIRED` could be toggled off and
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` was empty in the shell (overriding the root `.env`).
- 10–15 second API latency on employer auth calls because `PyJWKClient` was instantiated
  per-request with no cache.
- Employer page stuck in "Loading employer session" after server restart due to Clerk's
  `getToken` reference changing during initialization causing a cancel-restart loop in
  `useEffect`.
- User requirement: local and production environments must be identical — no dev
  fallback auth paths.

**Root cause:**

- `EMPLOYER_AUTH_REQUIRED` flag allowed bypassing Clerk JWT verification locally via a
  custom `X-Dev-Employer-Id` header and hardcoded employer config values.
- `PyJWKClient` constructed fresh on every request, causing TCP timeout stalls when the
  JWKS endpoint was slow.
- Shell had `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=''` which took precedence over the root
  `.env` value via Next.js's `process.env` auto-inlining.
- `getToken` from `useAuth()` gets a new function reference when Clerk initializes,
  recreating the `useCallback`, triggering the `useEffect` cleanup, and looping.

**Files changed:**

- `apps/api/signalloop_api/auth.py`
- `apps/api/signalloop_api/config.py`
- `apps/api/tests/conftest.py` (new — shared fixtures)
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/api/tests/test_ai_endpoint.py`
- `apps/api/tests/test_cors.py`
- `apps/api/tests/test_employer_isolation.py`
- `apps/api/tests/test_evidence_report.py`
- `apps/api/tests/test_final_submission.py`
- `apps/web/next.config.ts`
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/tests/e2e/employer-portal.spec.ts`

**What changed:**

- Removed `EMPLOYER_AUTH_REQUIRED`, `local_employer_clerk_user_id`, and
  `local_employer_email` from config. Both environments now always require a valid Clerk
  JWT — no dev bypass.
- Removed `local_employer_identity` branch from `auth.py`. `get_current_employer` only
  calls `verify_clerk_token`.
- `PyJWKClient` is now a module-level singleton with `cache_keys=True`, instantiated
  once at import time. Eliminates per-request HTTPS fetches and the 10–15 s stall.
- New `apps/api/tests/conftest.py` with shared `session_factory`, `default_employer`,
  `employer_context`, and `client` fixtures. All test files updated to use
  `app.dependency_overrides[get_current_employer]` instead of relying on dev fallback.
- `EmployerContext` dataclass in conftest lets isolation tests switch authenticated
  employer between requests without two-client contention on `app.dependency_overrides`.
- `apps/web/next.config.ts` injects root `.env` values into `process.env` before the
  config object so that a shell-exported empty variable does not shadow the file value.
- Added `allowedDevOrigins: ["127.0.0.1"]` to `next.config.ts` so HMR works when the
  browser connects via `127.0.0.1`.
- Employer dashboard (`page.tsx`) rewritten to Clerk-only: removed `DevPortal`,
  `ClerkEmployerPortal`, `isDev`, and `localSessionActive`. One code path.
- Added `isClerkLoaded` guard in `useEffect` on both the employer dashboard and the
  evidence report page — prevents the cancel-restart loop caused by `getToken` reference
  churn during Clerk initialization.
- Playwright `employer-portal.spec.ts`: added `mockClerkSignedIn` helper that
  intercepts `**clerk.accounts.dev/v1/client**`, returning a fake authenticated session
  for `GET /v1/client` and `{ object: "token", jwt }` for token refresh endpoints.

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> all passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npx playwright test tests/e2e/employer-portal.spec.ts` -> 5 passed.

---

## 2026-06-19 — Phase 2 Live E2E Findings

**Symptom:** Live local browser testing initially passed through the UI but exposed
several real integration issues:

- Parallel local fallback invite creation could fail with `UNIQUE constraint failed:
  employers.email`.
- Timed attempts could auto-expire immediately in the browser because API responses
  serialized naive timestamps without a UTC marker.
- A non-default web port failed browser fetches until API CORS included that origin.
- Public/hidden worker runs failed before pytest collection when the API used
  `ASSESSMENT_RUNTIME_IMAGE=python:3.11-slim`.
- The live Playwright smoke still asserted old Phase 1 final explanation fields and a
  Standard-only title.

**Root cause:**

- Local employer fallback did not handle unique-email collisions robustly.
- SQLite returns naive datetimes even when the app writes UTC-aware values; browser
  `Date.parse()` interpreted those as local time.
- Local live smoke services were split across `3100` and `8016` without matching CORS.
- `.env.example` still documented a generic Python image instead of the assessment
  runtime image.
- The live smoke test had not been updated for Phase 2 structured Submission Review or
  Advanced assessment titles.

**Files changed:**

- `.env.example`
- `apps/api/signalloop_api/auth.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/api/tests/test_employer_isolation.py`
- `apps/web/tests/e2e/live-full-stack-smoke.spec.ts`
- `docs/development/testing.md`
- `CURRENT_STATE.md`

**What changed:**

- Local fallback employer creation now recovers from unique collisions without merging
  distinct Clerk users by email.
- Candidate/employer attempt timestamps now serialize as UTC ISO strings ending in
  `Z`.
- Live Playwright smoke now uses Phase 2 Submission Review fields, accepts Standard or
  Advanced FastAPI titles, and has a live-worker timeout.
- `.env.example` now points local worker execution at
  `signalloop-python-assessment:3.11`.
- Testing docs now call out CORS/base URL alignment and the required local assessment
  runtime image.

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 57 passed.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 22 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `docker build -f docker/python-assessment.Dockerfile -t signalloop-python-assessment:3.11 .`
  from `apps/worker` -> passed.
- `docker run --rm signalloop-python-assessment:3.11 python -m pytest --version`
  -> `pytest 8.3.4`.
- Live Standard browser smoke passed once against the disposable local API/worker/web,
  then persisted worker output inspection showed the API had used the wrong runtime image.
- Live Advanced browser smoke passed once against the disposable local API/worker/web,
  then persisted worker output inspection showed the API had used the wrong runtime image.

**Follow-up:**

- Re-run fresh Standard and Advanced live Playwright smokes locally with
  `ASSESSMENT_RUNTIME_IMAGE=signalloop-python-assessment:3.11`; the final rerun after
  correcting the runtime image was blocked by the Codex escalation usage limit.
- After those pass, generate reports for the fresh attempts and verify employer report
  pages in the browser.

---

## 2026-06-19 — Playwright E2E Sandbox Fix

**Symptom:** `npm run test:e2e` was unreliable in Codex. Playwright first failed while
trying to bind `127.0.0.1:3000` even though a dev server was already running; direct
browser launch then failed inside the macOS sandbox with a Chromium Mach-port permission
error.

**Root cause:** The Playwright config always tried to manage the web server, and the
Codex sandbox can block both local server binding and Chromium's macOS browser-process
registration. Once run outside the sandbox, the employer report test also had one stale
strict-mode assertion because "Public issue resolution" now appears in both the chart
label and score-card title.

**Files changed:**

- `apps/web/playwright.config.ts`
- `apps/web/tests/e2e/employer-portal.spec.ts`
- `docs/development/testing.md`
- `docs/enhancements/phase-2-assessment-system/05-advanced-assessment-pack.md`
- `CURRENT_STATE.md`

**What changed:**

- Added `PLAYWRIGHT_BASE_URL` for non-default local/hosted targets.
- Added `PLAYWRIGHT_SKIP_WEBSERVER=1` so e2e can reuse an already-running web server.
- Tightened the employer report assertion to avoid duplicate-text strict-mode failure.
- Documented the reusable local command.

**Validation:**

- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- --workers=1`
  -> 2 passed, 1 skipped.

**Follow-up:** The skipped live smoke remains intentional. Run it only with API, worker,
web, and a valid `LIVE_INVITE_TOKEN`.

---

## 2026-06-19 — Phase 2 Task 02 AI Collaborator Policy Tightening

**Symptom:** The AI collaborator policy allowed tradeoff discussion, but the classifier
did not explicitly distinguish "compare tradeoffs" from "choose the answer for me" and
did not tag prompt-injection attempts.

**Root cause:** MVP policy tags focused on all-defects/full-solution/final-explanation
requests and did not encode Phase 2 design-choice ownership or prompt-injection evidence.

**Files changed:**

- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/signalloop_api/ai_provider.py`
- `apps/api/tests/test_ai_policy.py`
- `apps/api/tests/test_ai_endpoint.py`
- `docs/prompts/ai-collaborator-policy.md`
- `docs/enhancements/phase-2-assessment-system/02-ai-collaborator-policy-tightening.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `CURRENT_STATE.md`

**What changed:**

- Added disallowed `choose_design` and `prompt_injection` tags.
- Added a specific redirect for requests asking the assistant to choose an assessment
  design decision.
- Updated the system prompt and local fallback classifier.
- Updated provider fallback behavior to preserve task-specific redirect messages.
- Added AI policy and endpoint tests for tradeoff comparison, design-choice redirect, and
  prompt-injection detection.

**Validation:**

- `cd apps/api && uv run pytest tests/test_ai_policy.py tests/test_ai_endpoint.py tests/test_ai_provider.py`
  -> 11 passed.
- `cd apps/api && uv run pytest` -> 49 passed.

**Follow-up:** AI integrity risk remains report-only and will be surfaced in the reporting
task.

---

## 2026-06-19 — Phase 2 Task 01 Standard v2 Assessment And Rubric

**Symptom:** The MVP assessment and deterministic scoring model were too shallow for the
next phase of human-AI engineering evaluation.

**Root cause:** `fastapi_task_api_v1` was designed as the historical MVP/pilot pack, and
the MVP scoring rubric overweighted simple public/hidden test totals and a generic
written explanation category.

**Files changed:**

- `assessment_packs/fastapi_task_api_standard_v2/`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/reports.py`
- `apps/api/signalloop_api/schemas.py`
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/web/tests/e2e/candidate-workspace.spec.ts`
- `apps/web/tests/e2e/employer-portal.spec.ts`
- `docs/enhancements/phase-2-assessment-system/01-assessment-rubric-and-standard-pack.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `docs/architecture/technical-product-architecture-spec.md`
- `docs/development/known-limitations.md`
- `CURRENT_STATE.md`

**What changed:**

- Created `assessment_packs/fastapi_task_api_standard_v2/` and kept v1 intact.
- Added priority handling as the standard-v2 feature/design dimension.
- Standard v2 starter public tests intentionally pass 2 and fail 4.
- Standard v2 reference solution passes 6 public and 7 hidden tests.
- Default invite pack changed to `fastapi_task_api_standard_v2`.
- Report scoring now uses Phase 2 categories:
  public issue resolution, private issue generalization, feature/design implementation,
  candidate-written tests, AI collaboration, and regression/code quality.
- Candidate-written test scoring now considers test function count, HTTP assertions, and
  edge-case signals instead of only counting touched files.

**Validation:**

- `cd assessment_packs/fastapi_task_api_standard_v2/candidate && uv run pytest`
  -> expected 2 passed, 4 failed.
- `cd assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution && uv run pytest -c pyproject.toml --rootdir=. ../../candidate/tests`
  -> 6 passed.
- `cd assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution && uv run pytest -c pyproject.toml --rootdir=. ../hidden_tests`
  -> 7 passed.
- `cd apps/api && uv run pytest` -> 45 passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run typecheck` -> passed after build regenerated `.next/types`.
- `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.

**Follow-up:** Implement structured submission review and report-only AI integrity risk in
their bounded Phase 2 tasks.

---

## 2026-06-19 — Phase 2 Task 08 Multi-Tenant Employer Isolation

**Symptom:** Employer portal login was a frontend gate only. Backend employer routes could
list all attempts, create attempts with a client-supplied `employer_id`, and generate or
fetch reports by attempt id without ownership checks.

**Root cause:** The MVP shipped with Clerk only on the web surface; the API did not verify
Clerk identity or derive tenant ownership server-side.

**Files changed:**

- `apps/api/pyproject.toml`
- `apps/api/uv.lock`
- `apps/api/signalloop_api/auth.py`
- `apps/api/signalloop_api/config.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/reports.py`
- `apps/api/tests/test_employer_isolation.py`
- `apps/web/src/app/employer/api.ts`
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `docs/deployment/render-supabase-clerk.md`
- `docs/development/known-limitations.md`
- `docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `CURRENT_STATE.md`

**What changed:**

- Added backend Clerk JWT verification with `PyJWT[crypto]`.
- Added `get_current_employer` and local-only dev employer fallback.
- Invite creation now derives `attempt.employer_id` from the authenticated employer and
  ignores client-supplied `employer_id`.
- Attempt listing is scoped to the authenticated employer.
- Evidence-report generation/fetch validates attempt ownership.
- Employer web API calls send Clerk bearer tokens when available.
- Added tenant isolation API tests.

**Validation:**

- `cd apps/api && uv run pytest` -> 45 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.

**Follow-up:** Set `EMPLOYER_AUTH_REQUIRED=true` plus Clerk JWT issuer/JWKS env values in
Render before deploying this change.

---

## 2026-06-19 — Phase 2 Planning Freeze Updates

**Symptom:** Phase 2 scope had open decisions around employer isolation, report
confidence, AI misuse indicators, structured candidate submission evidence, and UI polish.

**Root cause:** The MVP validated the end-to-end flow but left several post-MVP decisions
as conversational context rather than durable implementation guidance.

**Files changed:**

- `CURRENT_STATE.md`
- `docs/architecture/technical-product-architecture-spec.md`
- `docs/enhancements/phase-2-assessment-system/README.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-product-scope.md`
- `docs/enhancements/phase-2-assessment-system/02-ai-collaborator-policy-tightening.md`
- `docs/enhancements/phase-2-assessment-system/06-ui-enhancements.md`
- `docs/enhancements/phase-2-assessment-system/07-reporting-and-favo-updates.md`
- `docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`

**What changed:**

- Added strict Clerk-user-based employer isolation as a Phase 2 task.
- Captured that AI integrity risk is report-only and must not directly affect numeric
  score in Phase 2.
- Captured removal of the generic employer-facing report confidence label.
- Captured structured Submission Review and final-submit confirmation behavior.
- Captured report/candidate UI polish direction, including simple report charts and
  an AI integrity risk panel.

**Follow-up:** Implement one bounded Phase 2 task at a time. Multi-tenant isolation should
be completed before broader external pilot usage.

---

## 2026-06-17 — Hosted Render/Supabase/AWS E2E Smoke Findings

**Why:** First hosted e2e smoke was run against:

- API: `https://signalloop-api.onrender.com`
- Web: `https://signalloop-web.onrender.com`

**What was verified:**

- API `/health` returned 200.
- Web root returned 200.
- API could query the Supabase-backed attempt list.
- Hosted invite creation worked and generated a web invite URL.
- Candidate invite opened against the deployed web app with no browser console errors.
- Candidate workspace loaded assessment files and the rules gate.
- Employer report page rendered a generated report with no browser console errors.

**Findings:**

1. Production execution is blocked by AWS IAM.
   - Public test execution returned `AccessDenied` on `s3:PutObject`.
   - The Render API IAM user `signalloop-render-api` cannot write run payloads to
     `s3://SIGNALLOOP_RUN_BUCKET/runs/...`.
   - ECS did not start because the API failed before `RunTask`.
2. Hosted final submission can leave an attempt submitted without a hidden test run.
   - The UI submit request timed out while waiting for the hidden evaluation status.
   - The API attempt state became `submitted`.
   - Evidence report generation succeeded afterward, but hidden tests showed `missing`.
   - Follow-up: make submission/hidden evaluation atomic enough for MVP, or store a
     pending/error hidden test run if execution fails or the request is interrupted.

**Files changed:**

- `docs/development/changes.md`
- `CURRENT_STATE.md`

**Follow-up items:**

- Add least-privilege S3 permissions for the Render API IAM user.
- Confirm ECS `RunTask`, `DescribeTasks`, and `iam:PassRole` permissions after S3 is fixed.
- Confirm the ECS task role can read/write the same S3 run prefix.
- Re-run hosted public tests, final submission, and report generation.

**Update after S3 input permission fix:**

- A fresh hosted attempt was created and public test execution no longer failed on
  `s3:PutObject`.
- The request waited for the ECS/Fargate task path and then failed with S3 `NoSuchKey`
  while reading the expected `runs/{run_id}/output.json`.
- This means the API can write the input payload and reach the wait/read stage, but the
  runner task did not produce the expected output object.
- Next check CloudWatch logs for `/ecs/signalloop-assessment-runner` and verify the ECS
  task role can read and write `arn:aws:s3:::SIGNALLOOP_RUN_BUCKET/runs/*`.

**Update after linux/amd64 runner image fix:**

- A fresh hosted attempt was created and public test execution returned a real pytest
  result from ECS/Fargate.
- ECS runner output was successfully written to S3 and read by the API.
- The run failed during pytest collection because the Fargate runner image had `pytest`
  and `boto3`, but did not include the assessment runtime dependencies:
  `fastapi`, `httpx`, and `uvicorn`.
- Fixed `apps/runner/Dockerfile` to install the same candidate runtime dependencies used
  by the local Docker assessment image.
- Local Docker smoke with a FastAPI `TestClient` test now passes inside
  `signalloop-assessment-runner:local`.
- Follow-up: rebuild and push the runner image with `--platform linux/amd64`, then rerun
  the hosted public test, final submission, and report flow.

**Update after runner dependency image push:**

- A fresh hosted attempt was created on 2026-06-18.
- Hosted public test execution now works end-to-end through Render API, S3, ECS/Fargate,
  runner output, and API persistence.
- Public test result on unchanged starter code was expected: 2 passed, 2 failed.
- Final submission still returned a generic API 500 while the attempt was marked
  `submitted`, leaving no hidden test run/report for that attempt.
- Local hidden-run reproduction returns a valid failed hidden-test result, so the hosted
  failure is likely an uncaught AWS/runtime exception in the hidden-evaluation path.
- Fixed `apps/api/signalloop_api/submissions.py` to convert any hidden-evaluation
  exception into a persisted hidden test `error` result instead of returning 500 after
  the attempt is submitted.
- Added regression coverage in `apps/api/tests/test_final_submission.py`.
- `cd apps/api && uv run pytest` now reports 36 passed.
- Follow-up: deploy this API fix to Render, then rerun final submission and report
  generation on a fresh hosted attempt.

**Update after Render API redeploy with submission hardening:**

- A fresh hosted attempt was created on 2026-06-18.
- Hosted public execution still works end-to-end and returned the expected unchanged
  starter result: 2 passed, 2 failed.
- Final submission now returns 201 instead of a generic 500.
- A hidden `TestRun` is persisted and linked to the submission.
- Evidence report generation succeeds and renders in the hosted employer report page.
- The hidden run status is currently `error`, not a real hidden pytest `failed` result.
  The report endpoint does not expose hidden stderr, so the next step is checking Render
  API logs or adding an internal diagnostics path to identify the hidden-run exception.

**Update after hidden-test path-resolution deploy:**

- A fresh hosted attempt was created on 2026-06-18 after deploying the fix that resolves
  evaluator hidden tests from the current pack config before falling back to the stored
  DB path.
- Hosted public execution still works end-to-end and returned the expected unchanged
  starter result: 2 passed, 2 failed.
- Final submission returned 201 and persisted a hidden `TestRun`.
- Hidden status still persisted as `error`; evidence report generation succeeded but
  hidden tests still showed `collected: 0`, `passed: 0`, `failed: 0`, `status: error`.
- The path-resolution fix was therefore not sufficient, or the deployed API still cannot
  complete the hidden-run setup for another reason. Need Render API logs or an internal
  diagnostics endpoint/temporary admin check that exposes the hidden-run error for
  attempt 6/test run 9.

**Update after local DB check and hidden logging patch:**

- Local `.env` points at `localhost:5432/signalloop`, not the hosted Supabase database
  used by Render, so querying `test_runs.id = 9` locally did not inspect the hosted
  hidden run. That local row was a public test run.
- Added Render/API-side logging around hidden test loading and hidden evaluation:
  configured vs stored evaluator path fallback, hidden test count, runner start,
  runner completion, and exception traceback before error-result persistence.
- No hidden test source content is logged.
- `cd apps/api && uv run pytest` reports 37 passed.
- Follow-up: deploy this logging patch, submit a fresh hosted attempt, then inspect Render
  API logs around final submission to identify the exact hidden-run exception.

**Update after hidden runner adapter fix:**

- Root cause found from Render/API logs: `submit_final_attempt()` expected the hidden
  runner dependency to expose `.run(...)`, but `get_hidden_test_runner()` was returning
  `ECSFargateExecutionProvider`, which exposes `.run_hidden(...)`.
- Fix deployed: hidden execution now uses an adapter that calls
  `get_execution_provider().run_hidden(...)`.
- Fresh hosted attempt 7 validated the full hosted path:
  - public ECS/Fargate execution returned expected unchanged-starter result: 2 passed,
    2 failed,
  - final submission returned 201 with `hidden_test_status: failed`,
  - hidden ECS/Fargate execution collected 6 tests, passed 1, failed 5,
  - evidence report generation returned 201 with score 26 and recommendation
    `do_not_advance`,
  - hosted employer report page rendered without browser console errors.

**Full validation round before user pilot testing:**

- Local automated checks:
  - `cd apps/api && uv run pytest` -> 38 passed,
  - `cd apps/worker && uv run pytest` -> 22 passed,
  - `cd apps/web && npm run typecheck` -> passed,
  - `cd apps/web && npm run lint` -> passed,
  - `cd apps/web && npm run build` -> passed,
  - `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.
- Updated stale Playwright assertions to match current UI copy and duplicate report text:
  candidate hidden status text and employer report summary assertion.
- Hosted browser-level e2e with fresh attempt 8:
  - candidate invite loaded,
  - public tests ran from hosted web UI through ECS/Fargate,
  - final submission ran hidden tests through ECS/Fargate,
  - evidence report generated with score 26 and recommendation `do_not_advance`,
  - hidden summary was collected 6, passed 1, failed 5,
  - hosted report page rendered without browser console errors.
- Final hosted checks:
  - `https://signalloop-api.onrender.com/health` returned 200,
  - hosted employer portal rendered Clerk sign-in state without browser console errors.

**UX follow-up after user pilot notes:**

- Observed production test and submit latency is expected from the AWS ECS/Fargate
  per-run model: API writes input to S3, starts a fresh isolated Fargate task, waits for
  container startup/test execution, then reads output from S3 and persists the result.
- Added non-blocking inline progress messages while public tests and final submission are
  running so candidates see that the isolated job is still in progress.
- Changed the root web route to redirect directly to `/employer`, removing the extra
  landing screen before Clerk login for employer users. Candidate access remains invite
  URL based.
- Checks after the UX update:
  - `cd apps/web && npm run typecheck` -> passed,
  - `cd apps/web && npm run lint` -> passed,
  - `cd apps/web && npm run build` -> passed,
  - `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.

---

## 2026-06-17 — Hosted Deployment Scaffold: Render, Supabase, and ECS/Fargate

**Why:** Local validation is far enough along to prepare the external deployment path:
Render for web/API, Supabase for Postgres, Clerk for employer auth, and AWS ECS/Fargate
for production execution without Docker-in-Docker.

**What changed:**

- Added root `render.yaml` Blueprint for Render web/API services using root-relative
  monorepo commands.
- Clarified environment split:
  - local root `.env` for local dev,
  - Render environment settings for production/pilot,
  - Supabase dashboard for database credentials,
  - Clerk dashboard for auth keys,
  - AWS resources/env vars for ECS/Fargate execution.
- Removed obsolete `NEXT_PUBLIC_WORKER_URL` from env templates because browser public
  test execution now goes through the API. Also removed stale web README, Playwright
  config, and candidate page references.
- Added `apps/runner` Fargate runner image that runs tests directly in the task and
  reads/writes JSON payloads from local files or S3.
- Added ECS task definition and run-task override templates under `infra/aws/ecs`.
- Added AWS ECS/Fargate deployment guide.
- Added AWS credential/resource placeholders for the future Render API to ECS integration.

**Files changed:**
- `render.yaml`
- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `apps/runner/Dockerfile`
- `apps/runner/signalloop_runner/__init__.py`
- `apps/runner/signalloop_runner/main.py`
- `apps/web/README.md`
- `apps/web/playwright.config.ts`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
- `infra/aws/ecs/task-definition.runner.template.json`
- `infra/aws/ecs/run-task-overrides.example.json`
- `infra/aws/ecs/README.md`
- `docs/deployment/render-supabase-clerk.md`
- `docs/deployment/aws-ecs-fargate-execution.md`
- `CURRENT_STATE.md`

**Follow-up items:**

- Push the repo to GitHub and connect Render to that GitHub repository.
- Create Supabase, Clerk, and Render service env vars from `.env.render-supabase.example`.
- Create AWS ECR/S3/ECS/IAM resources.
- Run hosted integration testing after AWS ECR/S3/ECS/IAM resources are created.

---

## 2026-06-17 — API ECS/Fargate Execution Provider

**Why:** The deployment scaffold needed the API-side execution provider before production
candidate execution can use AWS ECS/Fargate instead of a raw HTTP worker.

**What changed:**

- Added `apps/api/signalloop_api/execution.py` with a shared execution provider boundary.
- Local/staging default remains `EXECUTION_BACKEND=http_worker`.
- Production can use `EXECUTION_BACKEND=ecs_fargate`, which writes run payloads to S3,
  calls ECS `RunTask`, waits for completion, reads runner output JSON from S3, and
  returns the existing public/hidden test result shape.
- Public and hidden test paths now use the shared provider.
- Added AWS ECS env vars to templates and Render Blueprint.
- Added a fake-client unit test for ECS provider behavior.

**Files changed:**
- `apps/api/signalloop_api/execution.py`
- `apps/api/signalloop_api/config.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/submissions.py`
- `apps/api/tests/test_execution.py`
- `apps/api/tests/test_final_submission.py`
- `apps/api/pyproject.toml`
- `apps/api/uv.lock`
- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `render.yaml`
- `docs/deployment/aws-ecs-fargate-execution.md`
- `docs/deployment/render-supabase-clerk.md`
- `CURRENT_STATE.md`

**Validation:**
- `cd apps/api && uv run pytest` — 35 passed.
- `cd apps/web && npm run typecheck` — passed.
- `cd apps/web && npm run lint` — passed.

---

## 2026-06-17 — Candidate Workspace: Final Submission UX Fixes

**Why:** Several submission flow issues found during live testing — 422 errors with unhelpful messages, FINAL_EXPLANATION.md still visible in file tree, seeded hint not visible after test run, and hidden test status message was raw/technical.

**What changed:**

- `final_explanation` is now **required** before Submit is enabled. `decision_log` remains optional. Backend schema enforces `min_length=1` on `final_explanation` only.
- `FINAL_EXPLANATION.md` was already filtered server-side (`IGNORED_FILENAMES`) but requires an API restart to take effect.
- 422 error responses now show the field-level message (e.g. `final_explanation: String should have at least 1 character`) instead of just the HTTP status.
- Seeded hint ("N additional behaviors evaluated beyond these public tests") moved above the `<pre>` output block so it's always visible after running tests. Was previously pushed below the fold by `height: 100%` on the output element.
- `.test-panel` changed from `display: grid` to `display: flex; flex-direction: column`. `.output` changed from `height: 100%` to `flex: 1` so it scrolls internally and doesn't consume all panel space.
- Hidden test result message after submission changed from raw `"failed"/"passed"` status to `"Some hidden tests failed."` / `"All hidden tests passed."` — shown in both topbar and submission panel.
- Seeded issue count (`6`) is static — it is the total count of seeded behaviors, not a live counter of remaining failures. Candidates cannot see hidden test results during the assessment.
- e2e test updated: Submit now asserts disabled before explanation filled, enabled after.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/api/signalloop_api/schemas.py`
- `apps/web/tests/e2e/candidate-workspace.spec.ts`

---

## 2026-06-17 — AI Policy: LLM-based Intent Classification

**Why:** Pattern matching (`"fix all"`, `"find all bugs"`, etc.) is too brittle — slight rephrasing bypasses it entirely. "Can you fix all the errors?" was not caught. The LLM already understands semantic intent; using it to classify is more accurate and adds no extra latency.

**What changed:**

- Single LLM call now handles both classification AND response generation. The system prompt instructs the model to output JSON: `{allowed: bool, policy_tags: [], message: str}`. No separate classification step.
- `ai_policy.py` — updated `SYSTEM_PROMPT` with explicit JSON output format and tag definitions. Old `classify_message()` renamed to `fallback_classify()` (used only when JSON parsing fails).
- `ai_provider.py` — `AIProvider.complete()` replaced by `AIProvider.evaluate()` returning `AIDecision(allowed, policy_tags, message)`. `parse_ai_decision()` handles JSON parsing with fallback to pattern matching on failure.
- `ai.py` — no longer calls `classify_message` separately; calls `provider.evaluate()` directly.
- `LocalGuidanceProvider` (no-OpenAI-key fallback) uses `fallback_classify` internally.
- Tests updated: `FakeProvider.complete()` → `FakeProvider.evaluate()`, `classify_message` → `fallback_classify`, removed `"public_test_output"` hint tag assertion (hint tags only existed in pattern path, not LLM path).

**Files changed:**
- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/signalloop_api/ai_provider.py`
- `apps/api/signalloop_api/ai.py`
- `apps/api/tests/test_ai_policy.py`
- `apps/api/tests/test_ai_endpoint.py`
- `apps/api/tests/test_evidence_report.py`

---

## 2026-06-17 — Public Test Results Persisted to Database

**Why:** Public tests were called directly from the browser to the worker. The result was shown to the candidate but never saved to the DB, so the evidence report had nothing to score — always showed "No public test run recorded" and 0 points for public test coverage.

**What changed:**

- New API endpoint `POST /candidate/invites/{token}/run-public-tests` — saves a snapshot, calls the worker, stores the result as a `TestRun` with `run_type="public"`, and returns the result to the frontend.
- Frontend now calls this API endpoint instead of the worker directly. `NEXT_PUBLIC_WORKER_URL` is no longer needed for public test runs.
- The separate `saveSnapshot("public_test_run")` call before running tests is removed — the new endpoint handles the snapshot internally.

**Files changed:**
- `apps/api/signalloop_api/attempts.py`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

---

## 2026-06-17 — Evidence Report: Dynamic Follow-up Questions + Report UI Rewrite

**Why:** Follow-up questions were hardcoded static strings — same 4 questions for every candidate regardless of what they did. Report UI was using old section names (`favo_analysis`, `functional_correctness`, etc.) that no longer exist after the rubric redesign, leaving sections blank.

**What changed:**

- `build_follow_up_questions()` now generates questions dynamically from the evidence:
  - Names the specific failing hidden test area
  - Asks about 403 vs 404 only if they didn't address it in their explanation
  - Asks about status transitions if not mentioned
  - Asks about test coverage only if no candidate tests were written
  - Asks about AI policy redirects if any occurred
  - Asks about AI code paste or large paste events if detected
  - Asks for elaboration if final explanation is under 80 chars
- Report UI (`employer/reports/[attemptId]/page.tsx`) fully rewritten to use new section names: `public_test_results`, `hidden_test_results`, `candidate_tests`, `ai_collaboration`, `process_evidence`, `explanation_submitted`, `timeline`, `follow_up_questions`
- `employer/types.ts` updated to match new report structure — old types (`favo_analysis`, `seeded_issue_coverage`, etc.) removed
- CSS: added `report-label`, `report-list`, `report-notes`, `report-warn`, `timeline-list` classes
- Scoring fixes: regression gives 0 (not 8) when no public test run recorded; AI collaboration gives 0 (not 5) when no AI messages sent

**Files changed:**
- `apps/api/signalloop_api/reports.py`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/employer/types.ts`
- `apps/web/src/app/globals.css`

---

## 2026-06-17 — Evidence Report: AI Paste Detection (External Code)

**Why:** Candidates could paste large blocks of code from ChatGPT or other external sources without any trace in the AI collaboration panel. This is invisible in the current report.

**Approach:** Option B — snapshot diff analysis. The execution worker already saves snapshots (autosave + before test runs). By comparing consecutive snapshots with `difflib.SequenceMatcher`, we can detect when 8+ consecutive lines appear in a single snapshot interval, which is a strong signal of an external paste.

**What changed:** `ai_collaboration` section in the evidence report now includes:
- `large_paste_events` — list of `{file, lines_added, snapshot_kind, at, code_preview}` for every detected large paste
- `pasted_ai_code` — list of code blocks from AI responses that also appear verbatim in final submitted files (but not in initial files)

**Detection thresholds:**
- `PASTE_LINE_THRESHOLD = 8` — minimum consecutive new lines to flag as a potential external paste
- AI code paste: code block must be 3+ lines and 40+ chars to be worth matching

**Files changed:**
- `apps/api/signalloop_api/reports.py` — added `detect_large_paste_events()`, `detect_pasted_ai_code()`, `extract_code_blocks()`; wired into `build_report`
- `apps/api/tests/test_evidence_report.py` — added 4 unit tests: flags new AI code in final files, ignores existing code quoted by AI, flags big paste between snapshots, ignores small additions

---

## 2026-06-17 — Evidence Report: Full AI Message History

**Why:** The employer could see *that* policy redirects happened and *how many*, but not *what the candidate actually asked*. A candidate who tried to get the full solution multiple times should be visible in the report.

**What changed:** `ai_collaboration` section in the evidence report now includes:
- `policy_redirect_count` — total disallowed prompts
- `flagged_prompts` — list of `{message, policy_tags, at}` for every prompt that triggered a policy redirect (paired with the preceding candidate message)
- `all_candidate_messages` — full list of `{message, at}` for every candidate prompt, so the employer can read the entire AI conversation

**Files changed:**
- `apps/api/signalloop_api/reports.py` — expanded `ai_collaboration` section in `build_report`

---

## 2026-06-17 — E2E Test Update (post UI/scoring changes)

**Context:** Multiple UI and scoring changes were made in this session. Ran full e2e suite to catch regressions.

**Failures found and fixed:**
- `candidate-workspace.spec.ts` line 116: asserted Save button disabled after submission — Save button was removed (auto-snapshot now). Removed assertion.
- `candidate-workspace.spec.ts` mock: missing `seeded_issue_count` in mock `assessment` object. Added `seeded_issue_count: 6`.
- Added new assertions: seeded issue note visible after test run; Submit button enabled before textareas are filled (now optional).

**Files changed:**
- `apps/web/tests/e2e/candidate-workspace.spec.ts`

**Test status after fixes:**

| Check | Result |
|---|---|
| `cd apps/api && uv run pytest` | 30 passed |
| `cd apps/worker && uv run pytest` | 22 passed |
| `cd apps/web && npm run typecheck` | clean |
| `cd apps/web && npm run test:e2e` | 2 passed, 1 skipped |

---

## 2026-06-17 — Scoring Rubric Redesign

**Why:** Original rubric had 9 overlapping categories (100 pts) where seeded issue coverage was only 15 pts despite being the primary signal. Public tests had no separate score. Too complex to explain or maintain.

**New rubric (all weights in `RUBRIC` dict at top of `reports.py` — change there only):**

| Category | Points |
|---|---|
| Public test coverage | 20 |
| Hidden test coverage | 30 |
| Regression | 15 |
| Candidate-written tests | 15 |
| AI collaboration | 10 |
| Explanation and decisions | 10 |
| **Total** | **100** |

**Key design decisions:**
- `RUBRIC` dict is the single source of truth for all point values — rebalancing requires changing one dict only
- Public tests scored from last run pass rate (4 tests × 5 pts each)
- Hidden tests scored from parsed pytest output (6 tests × 5 pts each)
- Regression inferred from public test pass count (can't determine which specific tests ran)
- `parse_pytest_output()` replaces old `hidden_test_summary()` and is used for both public and hidden runs
- `SEEDED_ISSUE_AREAS` updated to list all 6 seeded issues (was missing "unknown actor access" and "idempotent delete")

**Files changed:**
- `apps/api/signalloop_api/reports.py` — full rewrite of scoring section; new `RUBRIC` config dict; new `parse_pytest_output()`; renamed report sections to match new categories; imports `DEFAULT_PACKS` from `attempts` to access `initially_failing_tests`
- `apps/api/signalloop_api/attempts.py` — added `initially_failing_tests` list to `DEFAULT_PACKS` entry
- `apps/api/tests/test_evidence_report.py` — updated section name assertions and key checks to match new report structure
- `assessment_packs/fastapi_task_api_v1/evaluator/SCORING_RUBRIC.md` — rewritten to match new rubric
- `docs/architecture/technical-product-architecture-spec.md` — sections 15 (report structure) and 16 (scoring rubric) updated to reflect new category names and weights

**Key scoring logic:**
- Public test score: `initially_failing_tests` from `DEFAULT_PACKS` defines which tests count. A test is "fixed" if it was in the initially-failing list but is NOT in the final run's failure names. Tests that already pass in the starter code contribute 0 to public test coverage (they go to regression instead).
- Regression score: any test NOT in `initially_failing_tests` that appears in failure names after candidate changes = regression.

---

## 2026-06-17 — E2E Validation Round 1

### Context

First automated e2e pass after Phase 12 completion. All 12 phases were already coded.
Goal: run the test plan from `local-pilot-checklist.md` against the locally running stack
and fix any failures before hosted deployment.

### Environment at the time of testing

| Service | Port | Process |
|---|---|---|
| Next.js web | 3000 | `npm run dev` |
| SignalLoop API | 8015 | `uvicorn signalloop_api.main:app --port 8015` |
| Worker | 9000 | `uvicorn signalloop_worker.main:app --port 9000` |
| Assessment task_api (unrelated) | 8000 | Running from `/signalloop/ass1` |

---

### Bug 1 — API port mismatch in `.env` (critical, broke all live API calls)

**Symptom:** All real API calls from the web UI silently failed. The SignalLoop API was
running on port 8015, but `.env` had `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
Port 8000 was occupied by an unrelated `task_api` process returning 404 for all
SignalLoop routes.

**Files changed:**
- `.env` — `NEXT_PUBLIC_API_URL` changed from `8000` to `8015`

**Note for next agent:** The `.env.example` documents port 8000 as the canonical
default. The mismatch arose because the API was started manually on 8015. If you
restart the API on 8000, revert `.env` accordingly. The `playwright.config.ts` webServer
command already uses 8015 to match the running API. Keep `.env` and the config in sync.

**Action required after this change:** Restart the Next.js dev server so `NEXT_PUBLIC_`
vars are re-read from the updated `.env`.

---

### Bug 2 — Hidden evaluation result not visible after submission (e2e test failure)

**Symptom:** `candidate-workspace.spec.ts` line 115 failed:
```
expect(getByText("Hidden evaluation recorded with status: failed")).toBeVisible()
```
The element was in the DOM but Playwright reported it as `hidden` on every retry (14x
over 5 seconds). Root cause: the `<p>` was inside `.submission-panel` (`overflow: auto`,
240px tall). Filling the textareas scrolls the panel ~106px down. After submission the
paragraph renders near the top (y≈54px), below the scroll viewport (y=106 to y=346).

Multiple scroll recovery approaches were tried and all failed to satisfy Playwright's
visibility check within the 5-second assertion window:
- `window.setTimeout(() => scrollTo({top:0}), 0)` — original code, failed
- `useEffect + scrollIntoView({block:"nearest"})` — failed
- `useLayoutEffect + scrollIntoView({block:"nearest"})` — failed
- `useLayoutEffect + scrollTo({top:0})` — failed

**Fix:** Moved the exact status text to the topbar (always visible, never inside a
scroll container), which is the right UX location for status information. The submission
panel now shows a summary with different text (`"Evaluation complete. Hidden test
status: ..."`) to avoid duplicate Playwright locator matches.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - Added `{submissionResult ? <span>Hidden evaluation recorded with status: ...</span>}` in
    the topbar `<div className="topbar-actions">`, right after the "submitted" status pill
  - Changed panel paragraph text to `"Evaluation complete. Hidden test status: ..."`
  - Removed the failed `window.setTimeout + scrollTo` and the replacement ref/effect code

---

### Bug 3 — Employer portal e2e test blocked by Clerk sign-in (test failure + hidden test bug)

**Symptom:** `employer-portal.spec.ts` timed out at line 117 waiting for
`button[name="Use local employer login"]`. With Clerk keys set in `.env`, the page
rendered only "Sign in with Clerk". After fixing that, it then timed out at line 128
on `getByRole("link", { name: "View" }).nth(1)`.

**Root cause 1:** `EmployerPortal` unconditionally rendered `ClerkEmployerPortal`
whenever `clerkConfigured` was true. `ClerkEmployerPortal` passes `onLocalLogin={() => undefined}`
(a no-op) to `AuthPanel`, so clicking the button did nothing.

**Root cause 2:** `.nth(1)` (second "View" link) was wrong. After creating a new invite,
the list has one "created" attempt (no View link) and one "submitted" attempt (one View
link). Only one View link exists; `.nth(1)` is out of bounds.

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
  - Added `const isDev = process.env.NODE_ENV !== "production"`
  - Changed `EmployerPortal` to use local session flow when `isDev`, even if
    `clerkConfigured` — Clerk sign-in still works in dev because `ClerkProvider` wraps
    the whole app; local bypass just skips `ClerkEmployerPortal`'s gating
  - `AuthPanel` now renders "Use local employer login" when `!clerkConfigured || isDev`
  - `localSessionActive` state initialiser skips false-init when `isDev`

- `apps/web/tests/e2e/employer-portal.spec.ts`
  - Line 128: `.nth(1)` → `.nth(0)` (only one View link exists after invite creation)

**Production safety:** The `isDev` condition uses `process.env.NODE_ENV !== "production"`.
In production builds (`NODE_ENV=production`), Clerk-configured deployments still enforce
Clerk-only sign-in. The local bypass is dev-mode only.

---

### Test status after fixes (2026-06-17)

| Check | Result |
|---|---|
| `cd apps/api && uv run pytest` | 30 passed |
| `cd apps/worker && uv run pytest` | 22 passed |
| `cd apps/web && npm run typecheck` | clean |
| `cd apps/web && npm run lint` | clean |
| `cd apps/web && npm run test:e2e` | 2 passed, 1 skipped |

The skipped test is `live-full-stack-smoke.spec.ts` — requires `LIVE_INVITE_TOKEN` and
live running services.

---

## 2026-06-17 — Candidate UX Round 2

### Change 1 — Auto-snapshot replaces manual Save button

**Why:** The Save button implied code changes needed to be saved to work, which was false. Monaco state is live in the browser. Save was only for evidence capture (snapshots). Removed the button; snapshots now fire automatically 60s after the last keystroke (debounced), plus before every public test run (already existed).

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - Removed `saving` state and `Save` lucide import
  - Added `autoSnapshotTimeoutRef` and cleanup effect
  - Monaco `onChange` now schedules a 60s debounced `saveSnapshot("autosave")`
  - Removed Save button from topbar
  - `saveStatus` initial value changed from "No manual save yet." to `""`; only shown when non-empty
  - `saveSnapshot` messages updated: "Auto-snapshot saved." / "Snapshot saved before test run."

---

### Change 2 — Seeded issue count shown after public test run

**Why:** Candidates had no signal that public tests don't cover all evaluated behaviors. After running tests, they now see "Note: this assessment has N seeded behaviors evaluated beyond these public tests."

**Implementation:** `seeded_issue_count` added to `AssessmentMetadata` schema and to `DEFAULT_PACKS` config (6 for fastapi_task_api_v1). The value is looked up from `DEFAULT_PACKS` at response time — no DB migration needed.

**Files changed:**
- `apps/api/signalloop_api/schemas.py` — added `seeded_issue_count: int = 0` to `AssessmentMetadata`
- `apps/api/signalloop_api/attempts.py` — added `"seeded_issue_count": 6` to `DEFAULT_PACKS`; updated both `AssessmentMetadata(...)` calls to include it
- `apps/web/src/app/invite/[inviteToken]/page.tsx` — added `seeded_issue_count` to frontend type; note rendered below `<pre class="output">` when `testResult` is present

---

### Change 3 — Removed FINAL_EXPLANATION.md; explanation fields are now optional

**Why:** Candidates had to fill a structured file in the editor AND two UI textareas, which was redundant. Removed the file; the UI textareas remain as the single capture point. Textareas are now encouraged but no longer block submission (5 points at stake, not a hard gate).

**Files changed:**
- `apps/api/signalloop_api/assessment_files.py` — added `"FINAL_EXPLANATION.md"` to `IGNORED_FILENAMES` so it is no longer served to candidates
- `apps/api/signalloop_api/schemas.py` — `FinalSubmissionRequest.final_explanation` and `.decision_log` changed from `Field(min_length=1)` to `""` (optional)
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - `canSubmit` simplified to `!submitted` (no textarea content gate)
  - Removed `submitRequirements` list
  - Submission help text updated: "Explanation and decision log are optional but count for 5 points."
  - Sidebar "What to do" step 5 updated to reflect optional nature

---

## 2026-06-17 — UI Polish Round 1

### Fix 1 — Broken text layout in Final Submission panel

**Symptom:** Text content under the "Final Submission" panel was visually overlapping/overflowing. The submission help paragraph and save status text were collapsed and overlapping each other.

**Root cause:** `.test-panel` and `.submission-panel` shared a CSS rule with `grid-template-rows: auto minmax(0, auto)`. The `minmax(0, auto)` second row collapses the help text `<p>` (second DOM child of `.submission-panel`) to zero height under the 240px parent height constraint, causing visual overflow and overlap.

**Fix:** Added a `.submission-panel`-only override after the shared rule:
```css
.submission-panel {
  grid-template-rows: unset;
}
```
This lets all rows in `.submission-panel` size naturally to content while preserving the `minmax(0, auto)` behavior in `.test-panel` (which needs it to constrain the `pre.output` element).

**Files changed:**
- `apps/web/src/app/globals.css` — added `.submission-panel { grid-template-rows: unset; }` after `.test-panel { border-right: ... }` rule

---

### Fix 2 — Copy button after invite creation (employer portal)

**Symptom:** After creating an invite, only a decorative `ClipboardCopy` icon appeared next to the URL — clicking it did nothing.

**Fix:** Replaced the decorative icon with a functional button. Added `copied` state and `copyInviteUrl()` function using `navigator.clipboard.writeText`. Button label toggles "Copy" → "Copied!" for 2 seconds on click.

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
  - Added `const [copied, setCopied] = useState(false)` in `EmployerDashboard`
  - Added `copyInviteUrl()` function
  - Replaced `<ClipboardCopy>` icon-only markup with a `<button className="command-button secondary">` wrapping the icon and label

---

### Fix 3 — AI Collaborator chat scroll broken (outer panel scrolls instead of message list)

**Symptom:** Scrolling in the chat messages area (top portion of the AI Collaborator panel) did nothing. Scroll only worked after clicking inside the textarea at the bottom.

**Root cause:** `.assistant-panel` had `overflow: auto`. `.assistant-chat` inside it had `height: calc(100vh - 113px)` — a fixed height much larger than the actual available height (which is `100vh` minus topbar, resize handle, and bottom panel). So `.assistant-panel` itself overflowed its grid cell. When hovering over the chat messages area, mouse-wheel events were captured by `.assistant-panel` (the outer scroll container), not `.chat-messages` (the inner one). The click-textarea workaround happened to position the scroll viewport such that the inner `.chat-messages` was the topmost scrollable element.

**Fix:**
1. Made `.assistant-panel` a flex column with `overflow: hidden` — it no longer scrolls itself; it now contains its children via flex layout.
2. Replaced `.assistant-chat { height: calc(100vh - 113px) }` with `flex: 1` — the chat container fills the remaining panel space after the header without overflowing.
3. Changed `.chat-messages` grid row from `minmax(220px, 1fr)` to `minmax(0, 1fr)` — avoids a forced 220px minimum that could cause overflow in short viewports now that the parent is properly sized.
4. Also added `chatMessagesRef` with a `useEffect` to auto-scroll to the latest message on each update, so new messages are always visible.

**Files changed:**
- `apps/web/src/app/globals.css`
  - `.assistant-panel`: added `display: flex; flex-direction: column; overflow: hidden`
  - `.assistant-chat`: replaced `height: calc(100vh - 113px)` with `flex: 1`; changed first grid row to `minmax(0, 1fr)`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - Added `chatMessagesRef = useRef<HTMLDivElement | null>(null)`
  - Added `useEffect(() => { el.scrollTop = el.scrollHeight }, [chatMessages])`
  - Added `ref={chatMessagesRef}` on `.chat-messages` div

---

### Other findings (not fixed, recorded for next agent)

- `ASSESSMENT_RUNTIME_IMAGE=python:3.11-slim` in `.env` is a dead variable — no code
  reads it. The worker defaults to `signalloop-python-assessment:3.11` in
  `apps/worker/signalloop_worker/schemas.py`. Both images exist locally. Safe to ignore
  or remove.

- `OPENAI_MODEL=gpt-5` is set in both `.env` and `.env.example`. This uses OpenAI's
  Responses API (`/v1/responses`). Validity depends on OpenAI's current model catalogue.
  If AI chat returns errors in the live smoke test, verify the model name is current.

- Backend-to-worker public test orchestration is still not implemented (known, per
  `CURRENT_STATE.md`). Public tests are called directly from the browser to the worker.

---

## 2026-06-19 — Phase 2 Employer Assessment Configuration

### Change — Invite-level assessment and timing configuration

**Why:** Phase 2 needs employers to choose the standard assessment and timing
expectations per invite before timer enforcement and advanced packs are implemented.

**Implementation:**
- Added `assessment_level`, `timing_mode`, `duration_minutes`, and `expires_at` to
  `assessment_attempts` through Alembic migration `0003_add_attempt_configuration`.
- Extended the attempt creation API with fixed validation for standard/advanced,
  timed/untimed, and 60/90/120/150 minute durations.
- Kept advanced assessment intentionally unavailable until the advanced pack task;
  the employer UI shows it as planned/disabled and the API rejects advanced creation.
- Updated the employer invite form and attempt list to display timing configuration.
- Hardened API validation error serialization so Pydantic validator errors return a
  clean 422 response.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 51 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_config_migration_check_2.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-19 — Phase 2 Advanced FastAPI Pack Implementation

### Change — Advanced pack implemented and enabled

**Why:** Employer invite configuration already exposes assessment difficulty. Leaving
Advanced disabled made the Standard/Advanced choice feel unfinished.

**Implementation:**
- Added `assessment_packs/fastapi_task_api_advanced_v1/`.
- Added candidate starter app, README, public tests, requirements, pyproject, and lock
  file.
- Added evaluator hidden tests, reference solution, reference notes, scoring rubric,
  and manual evaluation form.
- Added `fastapi_task_api_advanced_v1` to API `DEFAULT_PACKS`.
- Mapped `assessment_level=advanced` to the advanced pack and default 120-minute
  duration.
- Enabled the Advanced option in the employer invite form.
- Added API coverage for creating Advanced attempts.
- Made candidate file loading ignore `.uv-cache` generated during local dependency
  attempts.

**Validation:**
- Advanced starter public tests using existing assessment virtualenv:
  `1 passed, 5 failed` on unmodified starter code.
- Advanced reference solution against public tests:
  `6 passed`.
- Advanced reference solution against hidden tests:
  `7 passed`.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 55 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

**Follow-up:**
- External LLM-assisted report review is still not invoked; reports continue to show
  `llm_assisted_review.status=not_run`.

---

## 2026-06-19 — Phase 2 Reporting And FAVO Updates

### Change — Phase 2 report evidence sections

**Why:** Employer reports should evaluate the human-AI engineering process, not only
final code or generic confidence.

**Implementation:**
- Removed the report-level `scores.confidence` field from generated reports.
- Added structured `submission_review` evidence parsed from final submission review
  answers.
- Added deterministic `favo` interpretation for Frame, Ask, Verify, and Own.
- Added report-only `ai_integrity_risk` with low/medium/high/critical labels and
  `score_impact=none_phase_2`.
- Added `feature_design_implementation` as a top-level report section.
- Added `llm_assisted_review` status metadata. External LLM review is not invoked in
  the local deterministic path.
- Updated employer report UI/types to render the backend-provided sections.
- Updated architecture docs to reflect structured Submission Review, FAVO, AI
  integrity risk, and Phase 2 rubric categories.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_evidence_report.py` -> 8 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-19 — Phase 2 UI Enhancements

### Change — Structured submission review, confirmation, and report visuals

**Why:** Phase 2 needs clearer candidate submission expectations and more readable
employer reports without expanding into a dashboard product.

**Implementation:**
- Replaced separate final explanation/decision-log inputs with structured Submission
  Review prompts:
  - What did you change?
  - What tradeoffs or product decisions did you make?
  - How did you verify your changes?
  - What would you improve next, given more time?
  - Optional evaluator notes.
- Submit now opens a confirmation modal and shows public-test, candidate-test, and
  review completion signals before final submission.
- Manual submission no longer requires review text at the API layer; review answers
  remain supporting evidence.
- Employer report page now shows timing metadata, native score bars, public/hidden
  test bars, feature/design summary, FAVO-style interpretation, and AI integrity risk.
- Added modal, chart, and FAVO styling in the shared web CSS.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-19 — Phase 2 Advanced Pack Specification

### Change — Advanced FastAPI pack design documented

**Why:** Phase 2 needs a deeper FastAPI assessment direction, but the advanced pack
implementation should remain separate from standard v2 and timer work.

**Implementation:**
- Added `docs/assessment/fastapi-task-api-advanced-v1.md` with domain, endpoints,
  seeded issue areas, feature/design requirements, public/hidden test direction,
  AI collaboration signal, rubric mapping, and non-goals.
- Marked `05-advanced-assessment-pack.md` as specification completed only.
- Linked the spec from the Phase 2 execution plan and docs index.

**Validation:**
- Confirmed this task is documentation-only.
- Did not create `assessment_packs/fastapi_task_api_advanced_v1/`.

---

## 2026-06-19 — Phase 2 Time-Boxed Assessment Flow

### Change — Timed attempts and expiry enforcement

**Why:** Phase 2 needs employer-selectable timed assessments without trusting only the
browser countdown.

**Implementation:**
- Added `submission_mode` to `assessment_attempts` through Alembic migration
  `0004_add_submission_mode`.
- Added explicit `POST /candidate/invites/{token}/accept`; loading an invite is now
  passive and accepting the rules starts `started_at` plus `expires_at` for timed
  attempts.
- Candidate invite responses now include timing metadata.
- Candidate workspace shows a countdown for timed attempts, warnings at 10/5/1
  minute, and auto-submits current browser files at expiry.
- Backend enforces expiry on snapshots, public test runs, AI messages, and final
  submission.
- Closed/stale-tab expiry records an `auto_expired` final submission from the latest
  persisted snapshot when the next backend action arrives.
- Evidence reports now include timing mode, duration, time used, start, expiry,
  submission timestamp, and submission mode.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_attempt_lifecycle.py tests/test_final_submission.py tests/test_evidence_report.py tests/test_ai_endpoint.py` -> 30 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_timer_migration_check.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.
