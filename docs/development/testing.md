# Testing Guide

Run these checks before handing off local MVP changes.

## API

```sh
cd apps/api
uv run pytest
```

Expected current result:

```text
297 passed, 51 skipped
```

Run the Alembic migration chain against a disposable SQLite database:

```sh
cd apps/api
DATABASE_URL=sqlite:////tmp/signalloop_migration_check.db uv run alembic upgrade head
```

The migration chain should apply through `0012_concept_question_types`.

## Worker

```sh
cd apps/worker
uv run pytest
```

Expected current result:

```text
23 passed
```

The worker tests validate path filtering, public and hidden test endpoints, structured results, and configurable CORS origins.

## Web

```sh
cd apps/web
npm run typecheck
npm run lint
npm run build
npm run test:e2e
```

If a dev server is already running on `127.0.0.1:3000`, reuse it instead of asking
Playwright to start another server:

```sh
PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- --workers=1
```

Expected current Playwright result:

```text
35 passed, 2 skipped
```

The skipped tests are live-service tests. They require real local services and invite tokens:

- `live-full-stack-smoke.spec.ts` requires `LIVE_INVITE_TOKEN`.
- `real-api-invite-flow.spec.ts` requires `RUN_REAL_API_TESTS=1` and `REAL_API_INVITE_TOKEN`.

The employer Playwright test mocks Clerk's browser session and mocks employer API calls.
The real employer portal requires Clerk locally and in production; there is no local
employer-login fallback.

The API suite includes deterministic submission-scenario coverage for unchanged,
public-only, strong, weak-review, AI-risk, standard, and advanced assessment outcomes.

Live OpenAI policy validation is opt-in because it makes real network calls and can be
slower/flakier than deterministic tests:

```sh
cd apps/api
RUN_LIVE_AI_TESTS=1 uv run pytest tests/test_live_ai_policy.py -q
```

Expected latest live result:

```text
48 passed
```

Real Postgres schema health checks are opt-in:

```sh
cd apps/api
RUN_SCHEMA_HEALTH_TESTS=1 uv run pytest tests/test_schema_health.py -v
```

## Live Local Smoke

For a full manual local smoke:

1. Start Postgres and run API migrations.
2. Confirm `cd apps/api && uv run alembic current` shows the latest head revision.
3. Build the worker runtime image.
4. Start worker on `127.0.0.1:9000`.
5. Start API on the port configured in `NEXT_PUBLIC_API_URL` and `playwright.config.ts`
   (`127.0.0.1:8015` in the current local validation setup).
6. Start web on `127.0.0.1:3000`.
7. Open `/employer`.
8. Sign in with Clerk.
9. Create an invite.
10. Open the candidate invite.
11. Run public tests.
12. Ask the AI collaborator a bounded question.
13. Submit final code and structured Submission Review.
14. Generate and view the evidence report in the employer portal.

To run the live Playwright smoke after creating an invite:

```sh
cd apps/web
LIVE_INVITE_TOKEN=... npm run test:e2e
```

When running the live smoke on a non-default web port, keep these values aligned:

- API `PUBLIC_BASE_URL`
- API `CORS_ORIGINS`
- web `NEXT_PUBLIC_API_URL`
- Playwright `PLAYWRIGHT_BASE_URL`

For local Docker worker execution, the API must use:

```sh
ASSESSMENT_RUNTIME_IMAGE=signalloop-python-assessment:3.11
```

The generic `python:3.11-slim` image does not include pytest or FastAPI assessment
dependencies and will make public/hidden runs fail before tests are collected.

## Hosted Smoke

Render/Supabase/Clerk hosted smoke has covered both execution configurations used during the
pilot:

- Attempt 8 on 2026-06-18 confirmed public execution through ECS/Fargate, final submission,
  hidden evaluation, report generation, and employer report rendering.
- Attempt 34 on 2026-07-13 confirmed the current `direct` pilot path after the GitHub organization
  transfer and Render runtime repair: workspace load, public tests, AI policy redirect, final
  submission, hidden evaluation status, and persisted webcam decline.

Before changing repository visibility, perform one final Clerk-authenticated employer report and
guided-role review from a browser-capable session. Use
`docs/deployment/render-supabase-clerk.md` for deployment reference.
