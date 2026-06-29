# SignalLoop Technical Product & Architecture Specification

Version: 3.1
Status: Phase 5 MVP implemented locally — updated 2026-06-29

## 1. Purpose

This document combines product-technical architecture, assessment design, candidate workspace design, AI collaborator rules, evidence capture, and report-generation pipeline.

## 2. System overview

SignalLoop consists of:

```text
Candidate Browser
  -> Web App
  -> Backend API
  -> Execution Worker
  -> Assessment Pack Store
  -> Database
  -> AI Provider
  -> S3 (test payloads + webcam snapshots)
  -> Employer Report UI
```

Core flow:

1. Employer creates candidate invite.
   Employer may choose assessment level, timing mode, and evaluator feedback mode.
2. Candidate opens unique invite link.
3. Candidate reads onboarding and assessment rules.
4. Candidate edits code in browser.
5. Candidate runs public tests.
6. Candidate asks constrained AI assistant questions.
7. System captures snapshots and events.
8. Candidate submits final code and structured Submission Review.
9. System runs hidden tests.
10. System generates Engineering Evidence Report.
11. Employer reviews report and follow-up questions.

## 3. Architecture components

### Web app

Candidate onboarding, workspace UI, Monaco editor, file tree, test output panel, AI assistant panel, structured Submission Review, employer report UI.

The UI uses a single dark design language derived from the Calibr reference — see
`docs/design/calibr-design-language.md` for tokens, typography, and component patterns. The
design tokens live in `apps/web/src/app/globals.css` `:root` (dark surfaces `--bg0..bg4`,
borders `--b0..b2`, text `--t0..t2`, and semantic accent pairs), with legacy aliases so every
class resolves to the dark palette. The employer portal (`/employer`) is an app shell with a
left sidebar (Overview / Assessments / Candidates / Reports + Settings / Help & docs) and
client-side view switching. The Assessments view shows the single live coding module plus a
"Coming soon" roadmap of unsupported assessment types (preview only — coding is the only
supported module). The admin portal and evidence report reuse the same tokens; Monaco runs in
`vs-dark`. The Clerk sign-in modal and UserButton keep Clerk's default readable surface with
only the primary action tinted to the brand blue.

Candidate IDE enhancements may include syntax diagnostics, public-test-output links,
color-coded public test output, and file indicators. These features must use only
candidate-visible files and public test output; hidden tests and evaluator artifacts must
not drive candidate IDE hints.

### Backend API

Employer auth integration, invite creation, assessment attempt lifecycle, file/session state, test-run orchestration, AI assistant proxy, event logging, final submission, report generation.

### Execution worker

Receives code snapshots, runs tests in Docker, enforces timeouts/resource limits, returns structured test results, separates public and hidden test execution.

Local development uses the Docker-based worker directly. Production execution targets AWS ECS/Fargate per-run tasks rather than Docker-in-Docker inside a hosted web service. In production, the API or execution orchestrator starts an isolated assessment runner task for each public or hidden test run, and the runner returns structured results through a defined handoff path. The API-to-execution boundary should stay stable so the product flow does not depend on the runtime backend.

### Database

Stores employers, assessment packs, attempts, snapshots, test runs, AI interactions, final submissions, and evidence reports.

### AI provider abstraction

OpenAI initially. Provider abstraction required.

The AI provider must never receive hidden tests, seeded issue list, scoring internals, evaluator notes, or reference solution.

## 4. MVP architecture decision

Use modular monolith plus worker:

```text
apps/web      Next.js UI
apps/api      FastAPI API
apps/worker   Docker execution worker
```

Use HTTP async-style execution for MVP. Add queue later if needed.

Deployment target split:

- Web/API: managed web service such as Render.
- Database: hosted Postgres such as Supabase.
- Employer auth: Clerk.
- Local execution: existing Docker worker.
- Production execution: AWS ECS/Fargate per-run assessment runner tasks.

## 5. Assessment design model

First assessment:

```text
FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment
```

It tests debugging, validation, authorization/ownership, state transitions, error handling, product tradeoff decisions, test design, AI collaboration, and final explanation.

## 6. Assessment pack contract

Full candidate/evaluator code lives in the implementation repo, not inline in this spec.

Required structure:

```text
assessment_packs/
  fastapi_task_api_v1/
    candidate/
      README.md
      requirements.txt
      FINAL_EXPLANATION.md  (evaluator reference only — excluded from candidate file tree)
      task_api/
      tests/
    evaluator/
      hidden_tests/
      REFERENCE_SOLUTION_NOTES.md
      SCORING_RUBRIC.md
      MANUAL_EVALUATION_FORM.md
```

## 7. Enhanced assessment scenario

Candidate-visible scenario:

The team used an AI assistant to generate a first version of an internal task-management API. The API is being prepared for a limited beta with internal employees and team leads. The product manager wants the beta to be safe, predictable, and easy to debug. Public tests are incomplete. Some behavior is intentionally under-specified. Where requirements are ambiguous, candidates must make a reasonable decision, implement it consistently, and explain their reasoning.

## 8. Organizational constraints

1. Internal beta, not public consumer product.
2. Security and data isolation are more important than convenience.
3. Avoid large new frameworks or persistence layers.
4. Keep implementation simple.
5. Do not change public API shape unless justified.
6. Prefer explicit error behavior over silent success.
7. Add tests for changed behavior.

## 9. Design decisions required

Candidate must decide:

1. Unauthorized access behavior: 403 vs 404.
2. Status transition policy: allow TODO -> DONE directly or require TODO -> IN_PROGRESS -> DONE.

## 10. Seeded issue areas

Evaluator-only issue areas (7 total, configured per pack):

1. Duplicate email (case-insensitive + whitespace trimming).
2. Blank or whitespace-only task title (with title trimming).
3. Task priority defaulting, normalization, and validation.
4. Owner-only read and delete access.
5. Unknown actor access (resource existence leakage).
6. Status transition enforcement (TODO → IN_PROGRESS → DONE).
7. Idempotent owner delete (second delete returns 404).

## 11. Candidate workspace

Layout:

```text
Top: assessment title, timer, run tests, submit
Left: file tree
Center: Monaco editor
Right: constrained AI assistant
Bottom: test output panel
Final: structured Submission Review with final confirmation
```

## 12. Constrained AI collaborator

The AI collaborator is a **coach, not a solution generator**. It guides the candidate toward
the answer and hands over code only once they demonstrate they understand the approach
(*progressive disclosure*). It runs as **two LLM components, one responsibility each**, plus a
deterministic pre-gate and an availability-only fallback. Full rationale and the design history
are in `docs/retrospectives/ai-collaborator-journey.md` and ADR 0007.

### Allowed

- Explain Python, FastAPI, pytest, or httpx mechanics not specific to the assessment code
  (e.g. how parametrize works, what a 422 status code means) — answered directly.
- Interpret test failure output the candidate shares — describe what the output says.
- Help implement a bug the candidate has diagnosed (minimal changed lines, not whole functions).
- Coach an enhancement or a test the candidate is building (guide first; give code once they
  articulate the approach).
- Compare candidate-identified tradeoffs on a design decision they have already framed.

### Blocking policy tags (classifier)

| Tag | Trigger |
|---|---|
| `enumerate_defects` | Asks to list/explain ALL bugs/defects/issues (a whole-codebase sweep) |
| `full_solution` | Asks for the complete/whole solution or whole-file rewrite |
| `issue_by_issue_patch` | Asks for a fix for EACH problem |
| `missing_tests` | Asks to write the complete/whole test suite |
| `final_explanation` | Asks the AI to write the final explanation or decision log |
| `hidden_tests` | Asks about hidden tests, evaluator artifacts, or scoring internals |
| `choose_design` | Asks the AI to pick the design choice (it may compare; candidate must choose) |
| `prompt_injection` | Asks AI to ignore policy, change roles, or reveal protected information |
| `anti_decomposition` | A single message asking to sweep the whole assessment at once |
| `test_paste_derivation` | Pastes actual test function code to reverse the fix out of it |

`no_issue_identified` is **no longer a blocking tag.** A vague "what's wrong with my code?" is
*allowed* and coached Socratically by the generator — it is normal coaching, not a scored
violation.

### Behavior — guide first, give code once earned (progressive disclosure)

For any implement/fix/write request the generator decides from what the candidate has shown
**in the conversation**:

- **Not yet shown the approach** (first ask, "just do it for me", named the goal but not the
  how, vague fishing, pasted failure with no diagnosis) → one pointed Socratic question, a
  conceptual hint, or a pointer to a similar pattern in their code. No code yet.
- **Has shown the approach** (articulated the change, answered the guiding question, identified
  the exact behavior and why) → give the code, tight: a **bug fix is only the minimal changed
  lines**, never the whole function; an enhancement/test is the focused implementation.
- The gate is *demonstrated understanding*, not a turn count: give code the moment it's shown;
  keep guiding indefinitely if the candidate only deflects.

### Architecture

- **Deterministic pre-gate:** pasted test function code is blocked structurally (reliable,
  no LLM needed).
- **Classifier (LLM, single source of truth for blocking):** judges the CURRENT message alone
  — no conversation history, which avoids context-bleed false blocks — leans allow, and emits
  only the blocking tags above.
- **Generator (LLM, owns the response):** workspace-grounded (reads the candidate's
  candidate-visible files), receives the recent transcript for reference resolution, and
  applies progressive disclosure. Its output is returned verbatim — there is no second keyword
  pass re-judging it.
- **Fallback (`fallback_classify`):** availability-only; runs solely when the LLM call or parse
  fails; leans allow and never overrides a working LLM.
- Context boundaries prevent the AI (classifier and generator) from seeing hidden tests,
  evaluator notes, or scoring internals.
- Validated by a live regression net (`tests/test_live_ai_policy.py`) that runs the real model
  against scenarios grounded in the packs' actual seeded issues.

## 13. Anti-decomposition rule

The assistant must treat a multi-turn sequence as disallowed if the combined effect is to
produce the full solution.

Example disallowed sequence:

1. “Explain all problems in the code.”
2. “For each problem, give me the code.”
3. “For each problem, give me tests.”

Expected redirect:

```text
I cannot enumerate all defects or provide issue-by-issue fixes for the assessment. I can help you reason through one candidate-identified issue or one failing behavior at a time.
```

`no_issue_identified` redirects use a different message:

```text
Before I help further, what behavior did you observe, and what did you expect? Tell me what you've already tried or noticed, and I'll help you reason through it.
```

## 14. Evidence capture

Capture:

- assessment opened,
- onboarding accepted,
- code snapshots,
- public test results,
- AI messages,
- selected code context,
- final submission,
- structured submission-review answers,
- hidden test results,
- evaluator feedback mode,
- execution timing breakdown where available,
- browser proctoring events (fullscreen exits, focus loss/return with duration),
- webcam consent decision,
- periodic webcam JPEG snapshots (if consented), stored in S3.

## 15. Engineering Evidence Report

Inputs:

- final code,
- code snapshots,
- public tests,
- hidden tests,
- candidate-created tests,
- AI interaction history,
- structured submission-review answers,
- timeline.

Sections:

1. Executive summary
2. Overall recommendation
3. Scores and rubric weights
4. Timing metadata (mode, duration, time used, submission mode)
5. Follow-up interview questions
6. Public test results
7. Hidden test results (seeded issue coverage)
8. Enhancements
9. Candidate-written tests
10. AI collaboration (flagged prompts, paste detection, large paste events)
11. Unified integrity score (low/medium/high/critical — combines AI signals + proctoring signals)
12. FAVO interpretation (Frame/Ask/Verify/Own derived from evidence)
13. LLM-assisted review status (`not_run` until bounded prompt is added)
14. Process evidence (snapshots, test runs)
15. Proctoring Signals (focus-loss events, fullscreen exits, webcam snapshot strip)
16. Submission Review
17. Timeline

## 16. Scoring rubric

Weights are defined in two places:
- Global `RUBRIC` in `apps/api/signalloop_api/reports.py` — standard v2 default.
- Per-pack `"rubric"` key in `DEFAULT_PACKS` (`attempts.py`) — overrides global for advanced packs.

### Standard v2 weights (default)

| Category | Points | Notes |
|---|---:|---|
| Public issue resolution | 15 | Initially failing public tests now pass. |
| Private issue generalization | 20 | Hidden tests covering undiscovered behaviors. |
| Feature/design implementation | 20 | Configured feature/design checks. |
| Candidate-written tests | 15 | Test files added or modified vs initial snapshot. |
| AI collaboration | 15 | Disciplined use and policy evidence. |
| Regression/code quality | 15 | Previously passing behavior remains stable. |

### Advanced v1 weights

| Category | Points |
|---|---:|
| Public issue resolution | 15 |
| Private issue generalization | 15 |
| Feature/design implementation | 25 |
| Candidate-written tests | 15 |
| AI collaboration | 15 |
| Regression/code quality | 15 |

### Quality as a modifier

Quality is embedded within each category rather than scored separately. For each public
issue, hidden issue, and enhancement, the authored rubric defines full vs partial credit
based on implementation approach. Tests encode quality where possible; the evaluator rubric
specifies quality signals for cases tests cannot differentiate.

Which tests are initially failing is configured per assessment pack in `DEFAULT_PACKS` inside
`apps/api/signalloop_api/attempts.py` under the key `initially_failing_tests`.

Recommendation thresholds: ≥80 → strong_advance, ≥60 → advance_with_followups, ≥40 → needs_review, &lt;40 → do_not_advance.

## 17. Integrity roadmap

### Phase 2 (implemented)

- AI policy redirect logging (all tags persisted per interaction).
- Paste detection: verbatim AI code block matching against final submission.
- Large paste event detection: snapshot-to-snapshot diff flagging sudden large additions.
- AI integrity risk label (low/medium/high/critical) derived from signals above.
  (The `no_issue_identified` redirect from this phase has since been superseded — vague
  fishing is now coached by the generator, not blocked; see section 12.)

### Phase 3 (implemented — proctoring; see `docs/enhancements/phase-3-proctoring/`)

- Browser event logging: fullscreen exit, focus loss, focus return (with duration).
- Webcam consent screen (opt-in, never mandatory). If consented: periodic JPEG
  snapshots every 5 minutes + on focus return > 30s + at submission.
- Snapshots stored in S3 at `snapshots/{attempt_id}/{timestamp}.jpg`, with an inline
  data-URL fallback when S3 is unavailable (local dev or upload failure) so snapshots are
  never silently lost.
- Unified integrity score replacing the Phase 2 `ai_integrity_risk` field.
  Combines AI collaboration signals + proctoring signals. All thresholds are
  configurable in `INTEGRITY_THRESHOLDS` (`integrity_config.py`).
- Employer report: "Proctoring Signals" section with event summary, focus-loss
  timeline, and webcam snapshot thumbnail strip.

### Phase 4 (implemented — super admin portal; see `docs/enhancements/phase-4-super-admin-portal/`)

- Operator-facing, view-only portal at `/admin`: employer roster (with invite/submitted/
  report counts and average score), per-employer drill-down (status/score distribution, AI
  usage, pack breakdown, stuck signals, attempt list), and read-only access to any employer's
  evidence report — without logging in as that employer.
- Same Clerk app as employers. `SUPER_ADMIN_EMAILS` drives role assignment at login; a
  nullable `role` column on `employers` stores `super_admin`. Role is re-evaluated every login.
  Because the Clerk session token has no email claim, the API resolves the user's email via the
  Clerk Backend API to match `SUPER_ADMIN_EMAILS`.
- `get_current_super_admin` protects all `/admin/*` routes (401 unauth, 403 non-admin). Admin
  is strictly view-only — no invite creation, no report regeneration.

### Explicitly out of scope (all phases)

- Continuous video recording or streaming
- Screen recording
- Paste blocking
- Dev tools detection (unreliable, produces false positives)
- OS-level window switch interception
- Face analysis or biometric processing
- Mandatory webcam

## 18. Code boundary

This spec does not include complete candidate/evaluator source code. Full code belongs under `assessment_packs/fastapi_task_api_v1/` and is generated/maintained during implementation.

## 19. Manual trial learnings

A manual trial showed that prompt-only restriction is insufficient. Candidates can decompose full-solution requests into smaller requests. The assessment must include judgment, tradeoffs, and stricter assistant anti-decomposition rules.

## 20. Phase 2 Assessment System Enhancement

Status: implemented locally. Hosted deployment not yet smoke-tested for Phase 2 features.

The MVP architecture was validated locally and in hosted pilot infrastructure. Phase 2
improves the assessment system while preserving the existing deployment stack.

### Assessment pack versioning

MVP pack kept as historical/pilot reference (do not mutate):

```text
assessment_packs/fastapi_task_api_v1/
```

Phase 2 packs:

```text
assessment_packs/fastapi_task_api_standard_v2/   (standard — default for new invites)
assessment_packs/fastapi_task_api_advanced_v1/   (advanced — optional per invite)
```

### Rubric

Implemented in `apps/api/signalloop_api/reports.py` (`RUBRIC` dict, standard v2 default).
Per-pack overrides live in `DEFAULT_PACKS["rubric"]` in `attempts.py`.

| Category | Standard v2 | Advanced v1 | Evaluation mode |
|---|---:|---:|---|
| Public issue resolution | 15 | 15 | Automated public tests |
| Private issue generalization | 20 | 15 | Automated hidden tests |
| Feature/design implementation | 20 | 25 | Configured feature/design checks |
| Candidate-written tests | 15 | 15 | Automated heuristics |
| AI collaboration | 15 | 15 | AI logs and policy classifier |
| Regression/code quality | 15 | 15 | Automated regression check |

Quality is a modifier within each category — full vs partial credit per issue/enhancement,
defined in per-pack `SCORING_RUBRIC.md`. Tests encode quality where possible; the evaluator
rubric specifies quality signals for cases tests alone cannot differentiate.

### AI collaboration scoring tiers

| Scenario | Score (of 15) |
|---|---:|
| No AI use | 8 (neutral floor — no signal, not penalised) |
| Used AI, zero policy violations | 15 (full credit) |
| Used AI, 1 policy violation | 6 (below floor) |
| Used AI, 2–3 policy violations | 3 (heavy penalty) |
| Used AI, 4+ policy violations | 0 (systematic abuse) |

`no_issue_identified` redirects do not reduce the AI collaboration score. `enumerate_defects`,
`full_solution`, and `final_explanation` redirects do (they count toward `disallowed_count` in
`calculate_scores`).

### Timer model

Timed assessments are optional per invite. Employer selects mode and duration at invite creation.

- Timer starts when the candidate accepts onboarding.
- Standard v2 default: 60 minutes. Advanced v1 default: 120 minutes.
- Fixed duration options: 60, 90, 120, 150 minutes.
- Countdown shown in candidate workspace topbar with warnings at 10 min, 5 min, 1 min.
- On expiry with open tab: frontend auto-submits current in-browser files with
  `submission_mode: "auto_expired"`.
- Backend enforces expiry on all candidate endpoints (snapshots, public tests, AI, submit)
  and returns 409 after expiry regardless of browser state.

### Evaluator feedback mode

Each attempt should record an employer-selected evaluator feedback mode:

- `strict` — default for hiring. During active work, candidates see public test results
  only. A static "Hidden checks — additional behaviors evaluated at submission" row is
  always shown so candidates know edge-case testing exists, but no counts are revealed.
  Enhancement feedback (which of the `feature_design_tests` pass) is always shown
  regardless of mode. Full hidden/evaluator counts are available in employer reports after
  final submission.
- `guided` — candidates additionally see live hidden check counts split into two rows:
  "Hidden checks" (edge-case/quality tests only, excluding enhancement tests) and
  "Enhancements built" (named `feature_design_tests` subset). Hidden test names, failure
  messages, tracebacks, file paths, and line numbers must remain hidden in both modes.

Reports must display which mode was used. Guided mode improves candidate feedback but
weakens hidden-test purity because candidates can iterate against aggregate evaluator
signal.

### Execution timing breakdown

Public and hidden/evaluator execution should record timing buckets where available:

- API preflight and snapshot persistence,
- payload upload/handoff,
- execution-provider startup,
- runner/container startup,
- workspace materialization,
- pytest execution,
- output upload/download handoff,
- DB persistence,
- total elapsed time.

Candidate UI should show simple running/completed/duration feedback. Detailed timing is
primarily for debugging latency and deciding where optimization gives the highest return.

### LLM-assisted review

Not yet invoked. Reports include `llm_assisted_review.status = "not_run"` until a bounded
review prompt and ADR-approved safety boundary are added. The LLM reviewer must not receive
hidden test source, reference solutions, evaluator notes, or scoring internals beyond the
bounded evidence needed for the review task.

### Submission review

Replaces the separate final explanation and decision log with a structured 4-question form
captured at final submission:

1. What changed?
2. Tradeoffs or product decisions?
3. How did you verify?
4. What would you improve next?

Optional: additional evaluator notes. The Submit button opens a confirmation modal showing
public-test status, whether candidate tests were added, and how many required questions
were answered. Incomplete answers warn but do not block submission.

### FAVO report interpretation

Derived automatically from evidence. Candidates do not write FAVO.

| FAVO area | Derived from |
|---|---|
| Frame | feature/design score |
| Ask | candidate AI prompt count |
| Verify | public test run count, candidate test files, hidden test status |
| Own | submission-review required questions answered |

### AI integrity risk

Report-only label (low/medium/high/critical) derived from:

- `policy_redirect_count` — all assistant interactions with any policy tag.
- `severe_redirect_count` — `full_solution`, `final_explanation`, `anti_decomposition`, `prompt_injection`.
- `prompt_injection_count` — `prompt_injection` tag specifically.
- `pasted_ai_code_count` — verbatim AI code blocks found in final submission.
- `large_paste_event_count` — snapshot-to-snapshot diffs with ≥8 lines added at once.
- `weak_submission_review` — fewer than 2 required questions answered.

Does not change the numeric score. Guides employer review attention and follow-up questions.
Must not state plagiarism as a fact.

Severe redirects (`full_solution`, `final_explanation`, `anti_decomposition`,
`prompt_injection`) count toward `severe_redirect_count`, which drives the AI-collaboration
score tiers. Ordinary coaching (a vague "what's wrong?") is not a redirect and does not count.

### Key collaborator rule enforcement (progressive disclosure)

Candidates can attempt to extract answers by asking for an enhancement, a test, or a fix
outright. The generator handles this by guiding first and giving code only once the candidate
articulates the approach — see section 12. Vague fishing is coached Socratically rather than
blocked, so `no_issue_identified` is no longer emitted as a blocking tag; the integrity signal
comes from the *severe* redirect tags above, not from coaching.

### Employer isolation

Strict Clerk-user-based isolation implemented:

- Web sends Clerk session token on all employer API calls.
- Backend employer routes verify Clerk identity via `get_current_employer()`.
- `Employer` row keyed by Clerk user id.
- Invite creation derives `attempt.employer_id` from the authenticated employer.
- Attempt lists and evidence-report routes are scoped to the authenticated employer.
- Clerk JWT is always required — both local and production. No dev bypass exists.
- Candidate invite routes remain bearer-link based and do not expose employer-wide data.

### Deployment architecture

Phase 2 switched hosted execution to `EXECUTION_BACKEND=direct` — pytest runs
inline in the API process via subprocess (no ECS cold start, ~7s vs ~50s).
This is pilot-only; switch to `ecs_fargate` for production to restore isolation.

- Web/API: Render.
- Database: Supabase (Postgres).
- Employer auth: Clerk.
- Local execution: Docker worker (`http_worker` backend) or `direct`.
- Hosted candidate execution: `direct` (pilot); `ecs_fargate` (production path).
- File storage: AWS S3 (`signalloop-runner-payloads` bucket).
  - `runs/` prefix: ECS runner test payloads and outputs.
  - `snapshots/` prefix: Phase 3 webcam snapshots.
- Backend switches via `EXECUTION_BACKEND` env var (`apps/api/signalloop_api/execution.py`).

## 21. Phase 3: Evidence-Based Proctoring

Status: implemented.
Full detail: `docs/enhancements/phase-3-proctoring/`.

### What Phase 3 adds

**Browser event logging** — candidate workspace emits structured events to the backend:
- `fullscreen_exit` / `fullscreen_enter` — tracked via Fullscreen API
- `focus_lost` / `focus_returned` (with duration in seconds) — tracked via
  `visibilitychange` and `window.blur/focus`

Events are buffered client-side and flushed in batches every 30 seconds, on
page unload, and before final submission. Stored in new `proctoring_events` table.

**Webcam consent and snapshots** — optional, never mandatory:
- Consent screen shown once at workspace load, before assessment begins.
- If granted: JPEG snapshot (640px wide) captured every 5 min, on focus return
  > 30s, and at submission. Uploaded via S3 presigned PUT URL.
- S3 path: `snapshots/{attempt_id}/{unix_timestamp}.jpg`.
- Employer report shows thumbnail strip with timestamps and trigger labels.

**Unified integrity score** — replaces `ai_integrity_risk` field:
- Combines Phase 2 AI signals (violations, pastes, prompt injection) with
  Phase 3 proctoring signals (focus loss, fullscreen exits).
- Label: `low / medium / high / critical`.
- All thresholds in `INTEGRITY_THRESHOLDS` dict (`integrity_config.py`) — no
  magic numbers in logic.
- Old `ai_integrity_risk` field kept for backwards compatibility, derived from
  `integrity_score.label`.

**Employer report: Proctoring Signals section** — new section after Process Evidence:
- Webcam consent chip, event summary table, focus-loss timeline (collapsed),
  snapshot thumbnail strip.
- Unified integrity banner replaces the Phase 2 AI risk banner.

### What Phase 3 explicitly does not do

- Block paste, fullscreen exit, tab switching, or any candidate action.
- Record audio, continuous video, or screen content.
- Perform face detection or biometric analysis.
- Make webcam mandatory.

## 22. Phase 5: Role-Adaptive Assessment System

Status: MVP implemented locally.
Full detail: `docs/enhancements/phase-5-role-adaptive-assessment/`.

Phase 5 adds an adaptive planning layer before invite creation:

```text
pasted JD/resume -> skill map -> assessment blueprint -> employer approval -> invite
```

The MVP boundary is deliberately narrow:

- The employer can paste role/JD requirements and optional candidate resume text.
- SignalLoop maps both inputs into a versioned skill taxonomy.
- The system recommends a reviewable assessment blueprint.
- The employer approves the blueprint before creating an invite.
- Current executable support remains Standard FastAPI v2 and Advanced FastAPI v1.
- Unsupported skills are shown as caveats and follow-up areas, not scored evidence.
- The existing candidate workspace, AI collaborator boundaries, hidden-test handling, and
  scoring rubrics remain unchanged.

For v1, the role/JD determines the comparable core assessment. Resume data may influence
blueprint rationale, resume claims to validate, caveats, report interpretation, and follow-up
probes, but should not automatically give different candidates for the same role different
scored coding tasks.

Implemented additive concepts:

- `RoleProfile` for employer JD/team-context intake.
- `CandidateProfile` for optional pasted resume context.
- `AssessmentBlueprint` for the reviewable recommendation.
- Nullable `assessment_attempts.blueprint_id` to connect completed attempts back to the
  approved blueprint.
- Static taxonomy and module-coverage files under the API package.
- Optional adaptive builder in the employer Assessments view.
- `adaptive_context` section in blueprint-backed evidence reports.

Regular quick assessment invites remain supported and should not show adaptive report sections.
