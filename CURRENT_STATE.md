# Current State

## Project status

Phase 12 Documentation and Handoff is complete. Local and hosted MVP validation are complete enough for pilot use. Render web/API, Supabase persistence, Clerk-gated employer portal, and AWS ECS/Fargate public/hidden execution have been validated end-to-end, including a hosted browser-level candidate submission and employer report flow.

The active post-MVP workstream is Phase 2: Assessment System Enhancement.

## Current phase

Phase 2 documentation and planning.

## Last completed phase

Phase 12: Documentation and Handoff.

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
  employer-facing generic confidence label, and richer report/candidate UI polish.
- Advanced FastAPI assessment design is specified in
  `docs/assessment/fastapi-task-api-advanced-v1.md` and implemented in
  `assessment_packs/fastapi_task_api_advanced_v1/`.

## What does not exist yet

- External LLM-assisted report review is not invoked yet; reports include
  `llm_assisted_review.status=not_run` until a bounded prompt and safety boundary are
  added.

## Next task

Continue Phase 2 from:

`docs/enhancements/phase-2-assessment-system/`

Recommended next implementation task:

Local Phase 2 implementation is complete except for external LLM-assisted report
review. Local Playwright e2e now passes when run against an already-running dev server
with `PLAYWRIGHT_SKIP_WEBSERVER=1`; decide next whether to implement the bounded LLM
review prompt or proceed to deployment smoke testing.

Strict employer isolation was implemented locally in:

`docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`

Do not mutate `assessment_packs/fastapi_task_api_v1/` into the Phase 2 standard pack.
The versioned standard pack now exists at
`assessment_packs/fastapi_task_api_standard_v2/`; keep v1 as the historical MVP/pilot
reference.

Advanced pack local validation:

- Starter public tests: 1 passed, 5 failed on unmodified candidate code.
- Reference solution public tests: 6 passed.
- Reference solution hidden tests: 7 passed.
- API suite after enabling Advanced: 55 passed.
- Web typecheck/lint/build passed.
- Playwright e2e: 2 passed, 1 skipped by design.
- Live local browser smoke was exercised against Standard and Advanced timed invites
  on a disposable SQLite API at `127.0.0.1:8016`, worker at `127.0.0.1:9000`, and
  built web server at `127.0.0.1:3100`. This found and fixed UTC timestamp
  serialization for timed attempts and local employer fallback collision handling.
- Local Docker assessment runtime must be `signalloop-python-assessment:3.11`; using
  `python:3.11-slim` causes public/hidden runs to fail before pytest collection.
- Final Playwright rerun after forcing the corrected runtime image was blocked by the
  Codex escalation usage limit. Re-run the live smoke locally with fresh invites before
  deployment.

Historical MVP validation notes:

Recent local validation created submitted attempt 11 and generated evidence report 2 with score 40 and recommendation `needs_review`. Candidate submission, hidden evaluation persistence, report generation, and report rendering were verified locally.

A first automated e2e validation round was completed on 2026-06-17. Three bugs were found and fixed (see `docs/development/changes.md` for full details):

1. `.env` had `NEXT_PUBLIC_API_URL` pointing to port 8000; the running API was on port 8015. Fixed in `.env`.
2. Hidden evaluation result was inside a scrollable panel and Playwright consistently reported it hidden. Fixed by surfacing the status text in the topbar (always visible).
3. Employer portal e2e test was blocked by Clerk sign-in gating and a wrong `.nth(1)` link index. Fixed by allowing local dev bypass in `NODE_ENV=development` and correcting the index to `.nth(0)`.

All automated checks now pass per the latest validation notes: API tests, worker tests, web typecheck/lint, and 2 Playwright e2e tests pass (1 skipped by design). A follow-up docs/code review on 2026-06-17 confirmed `cd apps/api && uv run pytest` reports 34 passed and `cd apps/worker && uv run pytest` reports 22 passed.

Hosted deployment work is now in progress using:

`docs/deployment/render-supabase-clerk.md`

ECS/Fargate runner scaffolding exists in `apps/runner` and `infra/aws/ecs`, and the API can switch to it with `EXECUTION_BACKEND=ecs_fargate`. Keep `EXECUTION_BACKEND=http_worker` locally. Do not rely on a raw public worker for production candidate execution.

Hosted smoke on 2026-06-17:

- `https://signalloop-api.onrender.com/health` returned 200.
- `https://signalloop-web.onrender.com` returned 200.
- Supabase-backed attempt listing worked.
- Hosted invite creation and candidate workspace loading worked.
- Public test execution initially failed with AWS `AccessDenied` for `s3:PutObject` by IAM user `signalloop-render-api` on `s3://SIGNALLOOP_RUN_BUCKET/runs/...`.
- After fixing the `runs/*` S3 permission, a fresh public test run waited for ECS/Fargate and then failed with S3 `NoSuchKey` while reading `runs/{run_id}/output.json`; check runner task logs and task-role S3 permissions next.
- After pushing a linux/amd64 image, a fresh public test run returned ECS pytest output but failed with `ModuleNotFoundError: No module named 'fastapi'`; `apps/runner/Dockerfile` now installs `fastapi`, `httpx`, and `uvicorn` to match the local assessment image. Rebuild and push the runner image before the next hosted smoke.
- After pushing the dependency-fixed runner image, hosted public test execution worked end-to-end. Unchanged starter code returned the expected public result: 2 passed, 2 failed.
- A hosted submission attempt was marked `submitted`, but hidden evaluation was not persisted after the UI submit wait timed out; generated report showed hidden tests as `missing`.
- A second hosted submission attempt returned generic 500 after public execution started working. Local hidden runner reproduction returned valid failed hidden-test output, so `apps/api/signalloop_api/submissions.py` now catches all hidden-evaluation exceptions and persists a hidden `error` result instead of leaving submission in a partial state.
- `cd apps/api && uv run pytest` reports 36 passed with the submission hardening.
- After Render API redeploy, hosted final submission returned 201 with `hidden_test_status: error`, report generation returned 201 with score 21 and recommendation `do_not_advance`, and the hosted employer report page rendered without console errors.
- After deploying the hidden-test path-resolution fix, a fresh hosted attempt still returned `hidden_test_status: error`; report generation returned 201 with hidden summary `collected: 0`, `passed: 0`, `failed: 0`, `status: error`.
- Local `.env` currently points at `localhost:5432/signalloop`, so direct local SQL queries do not inspect the hosted Supabase database used by Render.
- Added logging around hidden test path resolution, hidden test count, hidden runner start/completion, and hidden exception tracebacks. Deploy this logging patch and inspect Render API logs on the next fresh hosted submission.
- Root cause was the hidden runner dependency: `submit_final_attempt()` expected `.run(...)`, while `ECSFargateExecutionProvider` exposes `.run_hidden(...)`. After deploying the adapter fix, fresh hosted attempt 7 returned `hidden_test_status: failed` with hidden summary `collected: 6`, `passed: 1`, `failed: 5`.
- Hosted report generation for attempt 7 returned score 26 and recommendation `do_not_advance`; the hosted employer report page rendered without browser console errors.
- Full pre-user-testing validation on 2026-06-18 passed: API tests 38 passed, worker tests 22 passed, web typecheck/lint/build passed, Playwright e2e 2 passed/1 skipped, hosted browser-level attempt 8 completed public tests, final submission, hidden tests, report generation, and hosted report rendering with no browser console errors.
- UX follow-up: public test/final submit latency is expected from the per-run ECS/Fargate task lifecycle. The web app now shows non-blocking inline progress messages while tests/submission are running, and the root route redirects directly to `/employer` to remove the extra landing screen before Clerk login.
- Employer report rendering worked for the generated report.

## Notes for next coding agent

The original MVP phase plan is complete through Phase 12. Use it as historical context, not the active implementation plan.

Current active workstream:

`docs/enhancements/phase-2-assessment-system/`

First Phase 2 task was documentation/planning only. Future implementation must remain
bounded to the specific Phase 2 task file.

Deployment architecture note: use local Docker worker for development/testing. Production execution should target AWS ECS/Fargate per-run assessment runner tasks instead of Docker-in-Docker on Render or another managed web-service runtime. Render remains suitable for web/API, Supabase for Postgres, and Clerk for employer auth.
