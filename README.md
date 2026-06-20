# SignalLoop

SignalLoop is an AI-native candidate evaluator for software engineering hiring.

The MVP evaluates whether candidates can solve a realistic backend engineering task while using a constrained AI collaborator. It captures evidence of framing, AI usage, verification behavior, design judgment, and final ownership, then generates an Engineering Evidence Report for employer review.

## Status

Phases 1 through 12 of the original MVP plan are complete and should be treated as historical implementation context.

The active workstream is:

```text
docs/enhancements/phase-2-assessment-system/
```

Phase 2 is currently documentation/planning first. Do not implement scoring, timer, assessment-pack, or UI changes until the relevant Phase 2 task is explicitly started.

Current capabilities:

- Candidate invite links and browser workspace.
- Monaco editor-backed file editing.
- Public test runs through the local Docker worker.
- Constrained AI collaborator with OpenAI provider and local fallback.
- Final submission with hidden-test execution through the worker.
- Deterministic Engineering Evidence Report generation.
- Employer portal with Clerk login.
- Pilot hardening: audit events, validation/fallback error responses, retry-bounded hidden worker calls, basic rate limiting, and deployment env templates.
- Hosted Render/Supabase/Clerk deployment with AWS ECS/Fargate public/hidden execution validated for pilot use.

Next product direction: assessment system enhancement, including a stronger standard assessment, optional timed assessments, LLM-assisted report scoring, and a planned advanced FastAPI assessment.

## Coding Agent Reading Order

Start every new coding-agent session with:

1. `AGENTS.md`
2. `CURRENT_STATE.md`
3. `docs/README.md`
4. `docs/architecture/technical-product-architecture-spec.md`
5. `docs/execution/coding-agent-execution-plan.md`
6. The active workstream file named in `CURRENT_STATE.md`

Work one phase or enhancement task at a time. Do not implement future-scope features without an explicit architecture decision.

## Repository Layout

```text
apps/web/          Candidate and employer Next.js UI.
apps/api/          FastAPI backend, SQLAlchemy models, Alembic migrations.
apps/worker/       Docker-based local execution worker.
assessment_packs/  Candidate/evaluator assessment content.
docs/              Product, architecture, execution, deployment, and handoff docs.
packages/shared/   Placeholder for shared code if needed later.
```

## Local Environment

Use `.env` for real local secrets and configuration. Do not commit it.

Templates:

- `.env.example` - complete reference of supported env vars.
- `.env.local.example` - local development template.
- `.env.render-supabase.example` - Render + Supabase + Clerk pilot deployment template.

The API loads the repo-root `.env` automatically. The web app does not automatically load the root `.env`; source it before running web commands when you need Clerk/API/worker values:

```sh
set -a && source ../../.env && set +a
```

## Local Run Sequence

Start Postgres locally, for example with Docker:

```sh
docker run --name signalloop-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=signalloop \
  -p 5432:5432 \
  -d postgres:16
```

Run API migrations:

```sh
cd apps/api
uv sync
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/signalloop uv run alembic upgrade head
```

Build the local assessment runtime and start the worker:

```sh
cd apps/worker
uv sync
docker build -f docker/python-assessment.Dockerfile -t signalloop-python-assessment:3.11 .
uv run uvicorn signalloop_worker.main:app --reload --port 9000
```

Start the API:

```sh
cd apps/api
uv run uvicorn signalloop_api.main:app --reload --port 8000
```

Start the web app:

```sh
cd apps/web
npm install
set -a && source ../../.env && set +a
npm run dev -- -H 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000/employer
```

Create an invite, open the candidate link, run tests, submit, then generate/view the report from the employer portal.

## Test Commands

```sh
cd apps/api && uv run pytest
cd apps/worker && uv run pytest
cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_migration_check.db uv run alembic upgrade head
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm run build
cd apps/web && npm run test:e2e
```

The live full-stack Playwright smoke test is skipped by default. Enable it only when API, worker, web, and a valid invite token are running:

```sh
LIVE_INVITE_TOKEN=... npm run test:e2e
```

## Deployment Direction

Pilot deployment target:

- Render for web/API.
- Supabase for Postgres.
- Clerk for employer auth.
- Local Docker worker for local testing.
- AWS ECS/Fargate per-run tasks for hosted candidate execution.

See `docs/deployment/render-supabase-clerk.md`.

## Known Limits

See `docs/development/known-limitations.md`.
