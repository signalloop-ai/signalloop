# Changes Log

Running record of bugs found, fixes applied, and important config changes made during
post-MVP validation. Read this before touching the files listed under each entry.

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
- Implement the API-side ECS execution provider before using Fargate for production
  candidate execution.

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
