# Current State

## Project status

Phase 12 Documentation and Handoff is complete. The MVP is ready for local end-to-end validation using the handoff docs before moving to hosted Render/Supabase/Clerk deployment and AWS ECS/Fargate execution work.

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

- Hosted Render/Supabase/Clerk integration test.
- API-side AWS ECS/Fargate execution provider that uploads payloads to S3, starts ECS tasks, waits for completion, and reads runner output.

## Next task

Continue local pilot validation first:

`docs/development/local-pilot-checklist.md`

Recent local validation created submitted attempt 11 and generated evidence report 2 with score 40 and recommendation `needs_review`. Candidate submission, hidden evaluation persistence, report generation, and report rendering were verified locally.

A first automated e2e validation round was completed on 2026-06-17. Three bugs were found and fixed (see `docs/development/changes.md` for full details):

1. `.env` had `NEXT_PUBLIC_API_URL` pointing to port 8000; the running API was on port 8015. Fixed in `.env`.
2. Hidden evaluation result was inside a scrollable panel and Playwright consistently reported it hidden. Fixed by surfacing the status text in the topbar (always visible).
3. Employer portal e2e test was blocked by Clerk sign-in gating and a wrong `.nth(1)` link index. Fixed by allowing local dev bypass in `NODE_ENV=development` and correcting the index to `.nth(0)`.

All automated checks now pass per the latest validation notes: API tests, worker tests, web typecheck/lint, and 2 Playwright e2e tests pass (1 skipped by design). A follow-up docs/code review on 2026-06-17 confirmed `cd apps/api && uv run pytest` reports 34 passed and `cd apps/worker && uv run pytest` reports 22 passed.

After local validation, continue with hosted deployment work using:

`docs/deployment/render-supabase-clerk.md`

ECS/Fargate runner scaffolding exists in `apps/runner` and `infra/aws/ecs`, but the API still defaults to `EXECUTION_WORKER_URL`. Do not rely on a raw public worker for production candidate execution; add the API-side ECS provider before production pilots with real candidates.

## Notes for next coding agent

The phase plan is complete through Phase 12. Next work should validate the full MVP locally, then proceed to hosted Render/Supabase/Clerk setup and the ECS/Fargate execution backend as separate, explicit follow-up work.

Deployment architecture note: use local Docker worker for development/testing. Production execution should target AWS ECS/Fargate per-run assessment runner tasks instead of Docker-in-Docker on Render or another managed web-service runtime. Render remains suitable for web/API, Supabase for Postgres, and Clerk for employer auth.
