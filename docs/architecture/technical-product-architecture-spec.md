# SignalLoop Technical Product & Architecture Specification

Version: 1.0 Markdown scaffold
Status: MVP source of truth

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
8. Candidate submits final code, explanation, and decision log.
9. System runs hidden tests.
10. System generates Engineering Evidence Report.
11. Employer reviews report and follow-up questions.

## 3. Architecture components

### Web app

Candidate onboarding, workspace UI, Monaco editor, file tree, test output panel, AI assistant panel, final explanation, decision log, employer report UI.

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

Evaluator-only issue areas:

1. Duplicate email handling.
2. Empty or whitespace-only task title.
3. Invalid status transitions.
4. Ownership/access behavior.
5. Delete behavior.

## 11. Candidate workspace

Layout:

```text
Top: assessment title, timer, run tests, submit
Left: file tree
Center: Monaco editor
Right: constrained AI assistant
Bottom: test output panel
Final: final explanation (required) + decision log (optional)
```

## 12. Constrained AI collaborator

Allowed:

- explain selected code,
- explain public test output,
- explain concepts,
- suggest debugging approaches,
- discuss tradeoffs for candidate-identified decisions,
- provide small generic code examples.

Disallowed:

- enumerate all defects,
- list all hidden issues,
- provide full solution,
- rewrite whole files,
- provide issue-by-issue patches,
- generate final explanation,
- list all missing tests,
- infer hidden tests,
- access evaluator-only artifacts.

## 13. Anti-decomposition rule

The assistant must treat a multi-turn sequence as disallowed if the combined effect is to produce the full solution.

Example disallowed sequence:

1. “Explain all problems in the code.”
2. “For each problem, give me the code.”
3. “For each problem, give me tests.”

Expected redirect:

```text
I cannot enumerate all defects or provide issue-by-issue fixes for the assessment. I can help you reason through one candidate-identified issue or one failing behavior at a time.
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
- final explanation,
- decision log,
- hidden test results.

## 15. Engineering Evidence Report

Inputs:

- final code,
- code snapshots,
- public tests,
- hidden tests,
- candidate-created tests,
- AI interaction history,
- final explanation,
- decision log,
- timeline.

Sections:

1. Executive summary
2. Overall recommendation
3. Scores and rubric weights
4. Public test results
5. Hidden test results (seeded issue coverage)
6. Candidate-written tests
7. AI collaboration
8. Process evidence (snapshots, test runs)
9. Explanation submitted
10. Timeline
11. Follow-up questions

## 16. Scoring rubric

All weights are stored in the `RUBRIC` dict at the top of `apps/api/signalloop_api/reports.py`.
Change values there to rebalance — nothing else needs to change.

| Category | Points | Notes |
|---|---:|---|
| Public test coverage | 20 | Only tests that start failing in the unmodified starter code count. Tests that already pass go to regression instead. |
| Hidden test coverage | 30 | 6 hidden tests × 5 pts each. Automated after submission. |
| Regression | 15 | Previously-passing tests that fail after candidate changes. |
| Candidate-written tests | 15 | Test files added or modified vs initial snapshot. |
| AI collaboration | 10 | Disciplined use; no enumerate-all redirects. |
| Explanation and decisions | 10 | Notes on changes, 403 vs 404 choice, status transition policy. |

Which tests are initially failing is configured per assessment pack in `DEFAULT_PACKS` inside
`apps/api/signalloop_api/attempts.py` under the key `initially_failing_tests`.

Recommendation thresholds: ≥80 → strong_advance, ≥60 → advance_with_followups, ≥40 → needs_review, &lt;40 → do_not_advance.

## 17. Integrity roadmap

MVP has no video proctoring. Use process evidence and low-process-evidence flags.

Later phases may add browser focus events, tab-switch signals, copy/paste telemetry, optional screen recording, proctored mode, and candidate-specific variants.

## 18. Code boundary

This spec does not include complete candidate/evaluator source code. Full code belongs under `assessment_packs/fastapi_task_api_v1/` and is generated/maintained during implementation.

## 19. Manual trial learnings

A manual trial showed that prompt-only restriction is insufficient. Candidates can decompose full-solution requests into smaller requests. The assessment must include judgment, tradeoffs, and stricter assistant anti-decomposition rules.
