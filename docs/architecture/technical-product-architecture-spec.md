# SignalLoop Technical Product & Architecture Specification

Version: 2.0
Status: Phase 2 source of truth — updated 2026-06-19

## 1. Purpose

This document combines product-technical architecture, assessment design, candidate workspace design, AI collaborator rules, evidence capture, and report-generation pipeline.

## 2. System overview

SignalLoop MVP consists of:

```text
Candidate Browser
  -> Web App
  -> Backend API
  -> Execution Worker
  -> Assessment Pack Store
  -> Database
  -> AI Provider
  -> Employer Report UI
```

Core flow:

1. Employer creates candidate invite.
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

The AI collaborator operates as a **Socratic tutor**, not a solution generator. Classification
uses an LLM-based `evaluate()` call that returns structured JSON `{allowed, policy_tags, message}`.
A pattern-based fallback (`fallback_classify`) runs only if the LLM call fails.

### Allowed

- Explain Python, FastAPI, pytest, or httpx mechanics not specific to the assessment code
  (e.g. how parametrize works, what a 422 status code means).
- Interpret test failure output the candidate shares — describe what the output says, not the fix.
- Confirm or redirect a hypothesis the candidate has already stated and committed to.
- Compare candidate-identified tradeoffs on a design decision they have already made.
- Ask one focused question that leads the candidate to discover the issue themselves.

### Disallowed policy tags

| Tag | Trigger | Response |
|---|---|---|
| `direct_diagnosis` | Asks AI to identify what is wrong with specific code, confirm implementation correctness, or suggest a test to catch a bug | Socratic redirect — a question back, not a flat block |
| `enumerate_defects` | Asks to list or explain all bugs/defects/issues | Block with redirect message |
| `full_solution` | Asks to fix everything or provide a complete solution | Block |
| `issue_by_issue_patch` | Asks for a patch for each problem | Block |
| `missing_tests` | Asks to write all missing tests or the complete test suite | Block |
| `final_explanation` | Asks to write or generate the final explanation or decision log | Block |
| `hidden_tests` | Asks about hidden tests, evaluator artifacts, or scoring internals | Block |
| `choose_design` | Asks the AI to pick the assessment design choice for the candidate | Tradeoff redirect — AI may compare, candidate must choose |
| `prompt_injection` | Asks AI to ignore policy, change roles, bypass rules, or reveal protected information | Block |
| `anti_decomposition` | Multi-turn session is cumulatively producing a full solution | Block |

### Socratic tutor rule

When a candidate asks the AI to diagnose their code or suggest a test for a specific behavior,
the AI must respond with one question about what the candidate has already observed:

- “What behavior did you see when you ran this?”
- “What input would trigger the case you're worried about?”
- “What does the test output tell you about where it's failing?”

If the candidate has already stated a hypothesis, the AI may confirm or redirect it — but
must not provide the implementation or the exact fix.

### Classification architecture

- **LLM path (primary):** `OpenAIProvider.evaluate()` sends the system prompt plus the candidate
  message to OpenAI and parses structured JSON. Context boundaries prevent the AI from seeing
  hidden tests, evaluator notes, or scoring internals.
- **Fallback (on LLM failure):** `fallback_classify()` uses keyword patterns for unambiguous
  bulk-bypass requests (`enumerate_defects`, `full_solution`, etc.). `direct_diagnosis` is
  intentionally excluded from the fallback — it requires context the pattern matcher cannot judge.
- **Message routing:** `direct_diagnosis` responses use `SOCRATIC_REDIRECT_MESSAGE` (a question
  back). All other disallowed tags use `REDIRECT_MESSAGE` (a flat block).

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

`direct_diagnosis` redirects use a different message:

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
- hidden test results.

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
5. Public test results
6. Hidden test results (seeded issue coverage)
7. Feature/design implementation
8. Candidate-written tests
9. AI collaboration (flagged prompts, paste detection, large paste events)
10. AI integrity risk (low/medium/high/critical label with signals)
11. FAVO interpretation (Frame/Ask/Verify/Own derived from evidence)
12. LLM-assisted review status (`not_run` until bounded prompt is added)
13. Process evidence (snapshots, test runs)
14. Submission Review
15. Timeline
16. Follow-up questions (candidate-specific, generated from evidence)

## 16. Scoring rubric

All weights are stored in the `RUBRIC` dict at the top of `apps/api/signalloop_api/reports.py`.
Change values there to rebalance — nothing else needs to change.

| Category | Points | Notes |
|---|---:|---|
| Public issue resolution | 15 | Initially failing public tests now pass. |
| Private issue generalization | 20 | Hidden tests and private seeded behavior coverage. |
| Feature/design implementation | 20 | Configured feature/design checks plus supporting review evidence. |
| Candidate-written tests | 15 | Test files added or modified vs initial snapshot. |
| AI collaboration | 20 | Disciplined use and policy evidence. |
| Regression/code quality | 10 | Previously passing behavior remains stable. |

Which tests are initially failing is configured per assessment pack in `DEFAULT_PACKS` inside
`apps/api/signalloop_api/attempts.py` under the key `initially_failing_tests`.

Recommendation thresholds: ≥80 → strong_advance, ≥60 → advance_with_followups, ≥40 → needs_review, &lt;40 → do_not_advance.

## 17. Integrity roadmap

MVP has no video proctoring. Phase 2 uses process evidence and the AI integrity risk label.

Implemented in Phase 2:
- AI policy redirect logging (all tags persisted per interaction).
- Paste detection: verbatim AI code block matching against final submission.
- Large paste event detection: snapshot-to-snapshot diff flagging sudden large additions.
- AI integrity risk label (low/medium/high/critical) derived from signals above.
- `direct_diagnosis` Socratic redirect — logged and visible in employer report.

Later phases may add browser focus events, tab-switch signals, optional screen recording,
proctored mode, and candidate-specific assessment variants.

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

Implemented in `apps/api/signalloop_api/reports.py` (`RUBRIC` dict). Change values there
to rebalance — nothing else needs to change.

| Category | Points | Evaluation mode |
|---|---:|---|
| Public issue resolution | 15 | Automated public tests |
| Private issue generalization | 20 | Automated hidden tests |
| Feature/design implementation | 20 | Configured feature/design checks |
| Candidate-written tests | 15 | Automated heuristics (test file count, function count, edge-case signals) |
| AI collaboration | 20 | AI logs, policy classifier, verification behavior |
| Regression/code quality | 10 | Automated regression check |

`direct_diagnosis` redirects do not reduce the AI collaboration score. `enumerate_defects`,
`full_solution`, and `final_explanation` redirects do.

### Timer model

Timed assessments are optional per invite. Employer selects mode and duration at invite creation.

- Timer starts when the candidate accepts onboarding.
- Standard default: 90 minutes. Advanced default: 120 minutes.
- Fixed duration options: 60, 90, 120, 150 minutes.
- Countdown shown in candidate workspace topbar with warnings at 10 min, 5 min, 1 min.
- On expiry with open tab: frontend auto-submits current in-browser files with
  `submission_mode: "auto_expired"`.
- Backend enforces expiry on all candidate endpoints (snapshots, public tests, AI, submit)
  and returns 409 after expiry regardless of browser state.

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

`direct_diagnosis` redirects appear in `flagged_prompts` and count toward
`policy_redirect_count` but not `severe_redirect_count`.

### Socratic AI tutor (direct_diagnosis)

Candidates can bypass diagnosis by asking the AI about one function at a time. The
`direct_diagnosis` policy tag handles this: instead of blocking, the AI responds with
a Socratic question about what the candidate has already observed. See section 12 for
the full classification architecture and response routing.

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

No deployment stack changes in Phase 2.

- Web/API: Render.
- Database: Supabase (Postgres).
- Employer auth: Clerk.
- Local execution: Docker worker (`http_worker` backend).
- Hosted candidate execution: AWS ECS/Fargate per-run tasks (`ecs_fargate` backend).
- Backend switches via `EXECUTION_BACKEND` env var (`apps/api/signalloop_api/execution.py`).
