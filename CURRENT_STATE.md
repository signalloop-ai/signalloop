# Current State

## Project status

Phase 12 Documentation and Handoff is complete. Local and hosted MVP validation are complete enough for pilot use. Render web/API, Supabase persistence, Clerk-gated employer portal, and AWS ECS/Fargate public/hidden execution have been validated end-to-end, including a hosted browser-level candidate submission and employer report flow.

## Current phase

Post-MVP local validation and hosted deployment preparation.

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
- Root `.gitignore` and `.env.example`.
- Candidate assessment README, starter FastAPI app, public tests, and final explanation template.
- Evaluator-only hidden tests, reference solution notes, scoring rubric, manual evaluation form, and reference solution.
- `uv` documented as the Python dependency and command runner for assessment development.
- Backend API project in `apps/api` with FastAPI app, SQLAlchemy models, Alembic migrations, database session setup, health endpoint, and tests.
- Candidate attempt lifecycle API endpoints for creating invites, opening candidate invite links, returning candidate-safe assessment metadata/files, and saving snapshots.
- Worker service in `apps/worker` with public test-run API, Docker runtime image definition, workspace materialization, hidden/evaluator file rejection, timeout/resource controls, and tests.
- Web app in `apps/web` with candidate invite workspace UI, Monaco editor, direct public test execution through the worker, and final explanation/decision-log form.
- Candidate workspace polish from local validation: visible candidate instructions, resizable file/AI/submission panels, independent scroll containers, Enter-to-send chat, explicit save status, and visible submission requirements.
- Backend-to-worker public test-run orchestration through `POST /candidate/invites/{token}/run-public-tests`, with public test snapshots and `TestRun` records persisted for evidence reports.
- Constrained AI collaborator endpoint with provider abstraction, OpenAI provider, local fallback provider, system prompt, guardrail classifier, context boundary checks, AI message logging, policy tags, and workspace chat UI.
- Final submission endpoint with immutable final code snapshot, final explanation, decision log, attempt locking, backend-orchestrated hidden worker run, hidden `TestRun` persistence, and candidate-safe submission response.
- Worker hidden-test endpoint for backend-supplied evaluator tests.
- Skipped-by-default live full-stack Playwright smoke test enabled with `LIVE_INVITE_TOKEN`.
- Engineering Evidence Report generation and fetch endpoints, with persisted report JSON, recommendation, score total, scoring categories, FAVO analysis, timeline, and follow-up questions.
- Employer attempt list API endpoint with invite URLs and evidence report summary metadata.
- Employer web portal at `/employer` with Clerk login when configured, local development login fallback, invite creation, candidate attempt list, and report detail pages.
- API audit events persisted in `audit_events` through Alembic migration `0002_create_audit_events`.
- API request validation/fallback error handlers and basic in-memory rate limiting.
- Retry-bounded hidden worker calls with configurable timeout/retry settings.
- Worker CORS origins configurable through `WORKER_CORS_ORIGINS`.
- Local and hosted environment templates: `.env.local.example` and `.env.render-supabase.example`.
- Render + Supabase + Clerk pilot deployment guide at `docs/deployment/render-supabase-clerk.md`.
- AWS ECS/Fargate execution deployment guide at `docs/deployment/aws-ecs-fargate-execution.md`.
- Root README updated with current MVP status, local run sequence, test commands, deployment direction, and known-limits pointer.
- Development handoff docs: `docs/development/testing.md`, `docs/development/known-limitations.md`, and `docs/development/local-pilot-checklist.md`.

## What does not exist yet

- Production hardening beyond pilot scope: hosted public execution, final submission, hidden execution, report generation, and employer report rendering now work end-to-end. Remaining work is polish/hardening rather than unblocking the MVP flow.

## Next task

Continue local pilot validation first:

`docs/development/local-pilot-checklist.md`

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

The phase plan is complete through Phase 12. Next work should validate the full MVP locally, then proceed to hosted Render/Supabase/Clerk setup and the ECS/Fargate execution backend as separate, explicit follow-up work.

Deployment architecture note: use local Docker worker for development/testing. Production execution should target AWS ECS/Fargate per-run assessment runner tasks instead of Docker-in-Docker on Render or another managed web-service runtime. Render remains suitable for web/API, Supabase for Postgres, and Clerk for employer auth.
