# Current State

## Project status

Phase 12 Documentation and Handoff is complete. Local and hosted MVP validation are complete enough for pilot use. Render web/API, Supabase persistence, Clerk-gated employer portal, and AWS ECS/Fargate public/hidden execution have been validated end-to-end, including a hosted browser-level candidate submission and employer report flow.

The active post-MVP workstream is Phase 2: Assessment System Enhancement.

## Current phase

**Phase 2 is complete.** All 11 planned Phase 2 tasks are implemented, locally validated,
and deployed to Render. The current state reflects the June 2026 UI polish session which
also switched hosted execution to `DirectExecutionProvider` (`EXECUTION_BACKEND=direct`).

## Last completed phase

Phase 2: Assessment System Enhancement (all tasks, including hosted deployment and
UX polish close-out).

## What exists

- Portable Markdown documentation structure.
- Technical Product & Architecture Spec.
- Coding Agent Execution Plan.
- Phase-by-phase execution files.
- Phase index and developer setup notes.
- Initial ADRs.
- ADR 0006 documenting local Docker execution for development and AWS ECS/Fargate per-run tasks for production execution.
- ADR 0007 documenting LLM-based AI policy evaluation with fallback classification.
- ADR 0008 documenting the deterministic six-category MVP scoring rubric.
- Render Blueprint scaffold for web/API deployment.
- AWS ECS/Fargate runner scaffold for future production execution.
- API-side execution provider switch with `EXECUTION_BACKEND=http_worker` for local/staging and `EXECUTION_BACKEND=ecs_fargate` for AWS ECS/Fargate.
- Assessment design documentation.
- Prompt policy documentation.
- Report structure documentation.
- Placeholder app folders: `apps/web`, `apps/api`, `apps/worker`.
- Shared package placeholder: `packages/shared`.
- Assessment pack implementation: `assessment_packs/fastapi_task_api_v1`.
- Phase 2 standard assessment pack implementation:
  `assessment_packs/fastapi_task_api_standard_v2`.
- Phase 2 advanced assessment pack implementation:
  `assessment_packs/fastapi_task_api_advanced_v1`.
- Root `.gitignore` and `.env.example`.
- Candidate assessment README, starter FastAPI app, public tests, and historical final explanation template for the MVP pack.
- Evaluator-only hidden tests, reference solution notes, scoring rubric, manual evaluation form, and reference solution.
- `uv` documented as the Python dependency and command runner for assessment development.
- Backend API project in `apps/api` with FastAPI app, SQLAlchemy models, Alembic migrations, database session setup, health endpoint, and tests.
- Candidate attempt lifecycle API endpoints for creating invites, opening candidate invite links, returning candidate-safe assessment metadata/files, and saving snapshots.
- Worker service in `apps/worker` with public test-run API, Docker runtime image definition, workspace materialization, hidden/evaluator file rejection, timeout/resource controls, and tests.
- Web app in `apps/web` with candidate invite workspace UI, Monaco editor, direct public test execution through the worker, and structured Submission Review form.
- Candidate workspace polish from local validation: visible candidate instructions, resizable file/AI/submission panels, independent scroll containers, Enter-to-send chat, explicit save status, and visible submission requirements.
- Backend-to-worker public test-run orchestration through `POST /candidate/invites/{token}/run-public-tests`, with public test snapshots and `TestRun` records persisted for evidence reports.
- Constrained AI collaborator endpoint with provider abstraction, OpenAI provider, local fallback provider, system prompt, guardrail classifier, context boundary checks, AI message logging, policy tags, and workspace chat UI.
- Phase 2 AI policy tightening is implemented locally: the assistant may compare
  tradeoffs but must not choose the candidate's design, and prompt-injection attempts
  are classified as disallowed evidence.
- Final submission endpoint with immutable final code snapshot, structured Submission Review evidence, attempt locking, backend-orchestrated hidden worker run, hidden `TestRun` persistence, and candidate-safe submission response.
- Worker hidden-test endpoint for backend-supplied evaluator tests.
- Skipped-by-default live full-stack Playwright smoke test enabled with `LIVE_INVITE_TOKEN`.
- Engineering Evidence Report generation and fetch endpoints, with persisted report JSON, recommendation, score total, scoring categories, FAVO analysis, timeline, and follow-up questions.
- Phase 2 deterministic scoring rubric is implemented in the report generator for
  public issue resolution, private issue generalization, feature/design implementation,
  candidate-written tests, AI collaboration, and regression/code quality.
- Employer attempt list API endpoint with invite URLs and evidence report summary metadata.
- Employer web portal at `/employer` with Clerk login (always required), invite creation, candidate attempt list, and report detail pages.
- Employer invite creation now supports Phase 2 assessment configuration fields:
  standard assessment, timed/untimed mode, and fixed duration options of 60, 90,
  120, and 150 minutes. Employers can select Standard FastAPI v2 or Advanced
  FastAPI v1.
- Time-boxed assessment flow is implemented locally: candidate accept starts the
  server timer, timed attempts show a countdown with warnings, expiry auto-submits
  the current browser files when the tab is open, backend expiry is enforced on
  snapshots/public tests/AI/final submission, and reports include timing metadata.
- Phase 2 UI enhancements are implemented locally: candidate Submission Review uses
  structured prompts plus a final confirmation modal, and employer reports show
  timing metadata, native score/test bars, feature/design summary, FAVO-style
  interpretation, and AI integrity risk.
- Phase 2 report generation is implemented locally with deterministic score sections,
  structured Submission Review evidence, FAVO, AI integrity risk, feature/design
  implementation, and explicit LLM-assisted review status.
- Backend employer routes enforce Clerk-user employer ownership for invite creation,
  attempt listing, and evidence-report generate/fetch. Both local and production
  environments always require a valid Clerk JWT — no dev-fallback bypass exists.
  `EMPLOYER_AUTH_REQUIRED` and the local employer identity config have been removed.
- API audit events persisted in `audit_events` through Alembic migration `0002_create_audit_events`.
- API request validation/fallback error handlers and basic in-memory rate limiting.
- Retry-bounded hidden worker calls with configurable timeout/retry settings.
- Worker CORS origins configurable through `WORKER_CORS_ORIGINS`.
- Local and hosted environment templates: `.env.local.example` and `.env.render-supabase.example`.
- Render + Supabase + Clerk pilot deployment guide at `docs/deployment/render-supabase-clerk.md`.
- AWS ECS/Fargate execution deployment guide at `docs/deployment/aws-ecs-fargate-execution.md`.
- Root README updated with current MVP status, local run sequence, test commands, deployment direction, and known-limits pointer.
- Development handoff docs: `docs/development/testing.md`, `docs/development/known-limitations.md`, and `docs/development/local-pilot-checklist.md`.
- Phase 2 enhancement documentation under `docs/enhancements/phase-2-assessment-system/`.
- Phase 2 planning decisions include Clerk-user-based strict employer isolation,
  structured Submission Review, report-only AI integrity risk, removal of the
  employer-facing generic confidence label, richer report/candidate UI polish, and
  a planned configurable evaluator feedback mode.
- Evaluator feedback mode is implemented locally. Strict mode remains the default:
  public test feedback during active work, with hidden/evaluator counts employer-report-only.
  Guided mode shows aggregate evaluator pass/fail counts during active work while still
  hiding hidden test names, tracebacks, failure messages, file paths, and line numbers.
- Execution timing breakdown is implemented locally for API/worker public runs, guided
  evaluator runs, and final hidden evaluation so latency can be measured before changing
  ECS/Fargate architecture.
- Candidate IDE ergonomics are implemented locally: lightweight Python syntax diagnostics,
  clickable public-test file/line output, color-coded public test output, and file
  indicators based only on candidate-visible files and public test output.
- Deterministic API scenario tests cover representative candidate submission outcomes:
  unchanged starter code, public-only fixes, strong submissions, weak submission review,
  AI-risk evidence, standard rubric, and advanced rubric/guided mode metadata.
- Opt-in live OpenAI policy validation exists and passed locally for the real
  OpenAI-backed AI collaborator prompt across allowed and blocked candidate question types.
- Advanced FastAPI assessment design is specified in
  `docs/assessment/fastapi-task-api-advanced-v1.md` and implemented in
  `assessment_packs/fastapi_task_api_advanced_v1/`.

## Settled state after June 2026 redesign

- Standard v2 rubric: 15/20/20/15/15/15 (public/private/feature/tests/ai/regression), 60 min default.
- Advanced v1 rubric: 15/15/25/15/15/15 (feature gets 25 pts), 120 min default.
- AI collaboration scoring tiers: 0 use = 8/15 (floor), clean use = 15/15, 1 violation = 6/15, 2–3 = 3/15, 4+ = 0/15.
- LLM-assisted review section hidden from employer report UI (field still present in JSON payload).
- Assessment pack READMEs include "How your submission is evaluated" section covering quality expectations.
- API test suite: 76 passed / 11 skipped.

## Settled state after June 2026 proving-tests + AI policy session

- **Candidate test scoring** uses proving tests, not keyword heuristics. A proving test
  fails on the original starter code AND passes on the candidate's submitted code.
  Scoring: 0→0, 1→6, 2→11, 3+→15. Verification runs at report-generation time via the
  new worker endpoint `POST /run-candidate-verification`.
- **Standard v2** `seeded_issue_count` is now 5 (priority test removed — priority had
  no public test signal and was unfair to candidates).
- **AI policy** system prompt leads with "Default: answer the question." The
  `no_issue_identified` tag fires only for vague "find my bugs" requests with no specific
  issue, code, or test named. Post-implementation review and conceptual questions are
  always answered. Code responses must give only the changed lines, not whole functions.
  Prompt-injection patterns expanded.
- **Assessment READMEs** use `{{DURATION_MINUTES}}` placeholder substituted at serve
  time; no more hardcoded time limits in pack files.
- **Submitted code viewer** appears in the employer report page (tab-based, defaults to
  `task_api/main.py`, max-height 520 px). The `submitted_code` field is present in the
  report JSON sorted as: `task_api/` first, `tests/` second, config files last.
- AI policy test suite: 59 tests (was 10), including 9 prompt-injection cases.

## Settled state after June 2026 progress checklist + enhancement feedback session

- **Enhancement feedback** is always computed and returned on every public test run,
  regardless of guided/strict mode. The evaluator's hidden tests always run; the
  `feature_design_tests` list in the pack config determines which hidden tests count as
  enhancement tests. Applies to standard_v2 and advanced_v1.
- **`enhancement_summary()` error guard**: if the evaluator Docker run fails,
  `enhancement_feedback` returns all-zeros rather than incorrectly reporting all tests as
  passing.
- **Hidden checks progress item** (guided mode) now shows only the non-enhancement hidden
  tests (edge-case/quality), so counts are non-overlapping with "Enhancements built".
  In strict mode, a static row "additional behaviors evaluated at submission" is always
  shown so candidates know edge-case testing exists.
- **Candidate test count** correctly shows tests added beyond the original starter.
  Root cause fixed: `initial_files` is now a separate API field (original starter from
  pack path, never overwritten by a snapshot). Previously both `files` and `initialFiles`
  were set to the current snapshot on load, making the diff always zero.
- **Evaluator notes removed from test output panel**: the "Notes: additional behaviors
  evaluated…" and "Evaluator checks: N passed…" paragraphs are removed. The progress
  checklist is now the single source for all evaluator feedback.
- **Test count**: `initial_files: dict[str, str]` added to `CandidateAttemptResponse`
  schema.

## Settled state after June 2026 UX polish + DirectExecution session

- **DirectExecutionProvider**: `EXECUTION_BACKEND=direct` runs pytest inline in the API
  process via subprocess. ~7s vs ~50s ECS cold start. Used on Render for pilot only — no
  container isolation. Switch to `ecs_fargate` for production. Both
  `.env.example` and `.env.render-supabase.example` updated to `direct`.
- **Candidate workspace** fully redesigned as an IDE-style layout: left file explorer,
  top bar with logo + status chips + progress pills + Run/Submit buttons, right panel
  with "What to do" (resizable) + AI Collaborator sections, collapsible bottom test
  output drawer.
- **Status chips** conditionally render: Public tests, Edge cases, Enhancements, My tests
  chips only appear when real data exists. Divider hidden when no chips are visible.
  Status label "started" → "In progress". Duration: "Recommended 90 min".
- **Chip labels finalized**: "Public" → "Public tests", "Hidden" → "Edge cases",
  "Enhanced" / "Feature/design" → "Enhancements", "Tests" → "My tests".
- **Elapsed timer** shown during test run and submission ("Running tests… 3s").
- **Employer portal** professionally redesigned: SignalLoop logo, auto-poll every 30s
  (no Refresh button), inline Create invite button next to email field, inline Details
  button next to assessment select, colored score badge, `timeAgo` helper for sent-at
  display, assessment detail modal sourced from evaluator rubric MD files, flat table
  header (no border/card on header row).
- **Evidence report** professionally redesigned: logo in header, amber Regenerate button
  with confirm dialog, CSS `data-tooltip` metric card tooltips, follow-up interview
  questions promoted above score breakdown, FAVO section subtitle, process evidence as
  mini metric cards, score breakdown bar chart with jump-link labels, "Enhancements"
  label throughout (was "Feature/design implementation").
- **Score breakdown**: bar chart labels are anchor `<a>` tags that scroll to the
  corresponding detail section. Score chip list removed — bar chart is the only
  summary element.
- **Web typecheck/build**: passing. All changes pushed to `main` and deployed to Render.

## Settled state after June 2026 report polish + scoring fixes session

- **Evidence report redesigned**: score summaries always visible; verbose lists
  (failure names, seeded areas, file diffs, AI prompts, timeline) collapsed behind
  `<details>/<summary>` Disclosure components. Page is crisp at a glance and detailed
  on demand.
- **Regression scoring proportional**: `reg_score = rubric_weight × (1 - regressed/originally_passing)`.
  A candidate who regresses 1 of 10 tests loses 10% of the regression category, not all of
  it. Candidate-added tests are excluded from regression detection via `original_test_names`
  set built from initial files.
- **Candidate test display**: employer report now shows "N functions added · M modified"
  instead of file/function/assertion counts. Backend `candidate_test_evidence()` does a
  name-level function diff — `functions_added` = new test names, `functions_modified` =
  existing names whose body changed. HTTP assertion count removed from display (kept for
  scoring heuristic).
- **Large paste threshold**: `PASTE_LINE_THRESHOLD` raised from 8 → 25 lines. Prevents
  single test functions from being flagged as suspicious pastes.
- **Integrity risk thresholds updated**: `large_paste_count >= 3` (was ≥2) triggers
  "high"; 1–2 large pastes → "medium". Prevents two legitimate large test writes from
  producing a "high" integrity label.
- **Submission review format**: employer report now shows only non-empty fields
  dynamically. Old 4-field form and new 2-field form both display correctly. Candidates
  who filled only "What changed" see just that field; no empty label/dash rows.
- **Weak submission review threshold**: `required_question_count` now comes from the
  form format. New 2-field form has 1 required field (what changed); only an empty
  submission triggers `weak_review = true`.
- **`flag_modified` for JSON persistence**: `flag_modified(evidence_report, "report")`
  added before commit in the report generate endpoint so SQLAlchemy flushes JSON column
  updates on regenerate.
- **API test suite**: 127 passed, 11 skipped.

## What does not exist yet

- External LLM-assisted report review is not invoked yet; reports include
  `llm_assisted_review.status=not_run` until a bounded prompt and safety boundary are
  added.

## Next task

**Phase 2 is complete. Begin Phase 3.**

Phase 3 has not yet been defined. Brainstorm with the team on scope before creating
phase documentation. Likely candidate themes based on Phase 2 learnings:

- Candidate experience improvements (richer test feedback, better error messages)
- Employer experience improvements (bulk invite, candidate comparison, export)
- Scoring accuracy improvements (LLM-assisted review section currently `not_run`)
- Operational hardening (production-grade execution backend, monitoring, alerts)
- New assessment packs

Do not start Phase 3 implementation until a phase document exists under
`docs/enhancements/phase-3-*/`.

Phase 2 historical reference: see `docs/development/changes.md` for the full session-by-session log. Phase 2 final hosted validation (2026-06-18) passed with API tests 38 passed, worker tests 22 passed, web typecheck/lint/build passed, Playwright e2e 2 passed/1 skipped, and a full browser-level attempt (public tests → submission → hidden evaluation → report generation → report rendering) working on Render without browser console errors.

## Notes for next coding agent

The original MVP phase plan is complete through Phase 12. Use it as historical context, not the active implementation plan.

Current active workstream:

`docs/enhancements/phase-2-assessment-system/`

First Phase 2 task was documentation/planning only. Future implementation must remain
bounded to the specific Phase 2 task file.

Deployment architecture note: use local Docker worker for development/testing. Production execution should target AWS ECS/Fargate per-run assessment runner tasks instead of Docker-in-Docker on Render or another managed web-service runtime. Render remains suitable for web/API, Supabase for Postgres, and Clerk for employer auth.
