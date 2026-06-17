# Developer Setup

SignalLoop is organized as a monorepo for three MVP services plus shared packages and assessment packs.

## Required tools

Install these locally before implementation phases that need them:

- Node.js LTS for the Next.js web app.
- Python 3.11 for the FastAPI API, worker, and assessment runtime.
- `uv` for Python environment and dependency management.
- Docker for isolated assessment execution.
- Postgres for local backend persistence.

Local development uses the Docker-based execution worker. Production assessment execution is intended to use AWS ECS/Fargate per-run tasks so deployed services do not depend on Docker-in-Docker or a host Docker socket in a managed web-service container.

## Repository layout

```text
apps/web/        Candidate and employer web UI.
apps/api/        Backend API service.
apps/worker/     Code execution worker.
packages/shared/ Shared types/utilities if needed.
assessment_packs/ Assessment content packs.
docs/            Product, architecture, execution, assessment, decisions.
```

## Environment

Use `.env` for real local credentials and runtime configuration.

Do not commit `.env` or secrets.

Templates:

- `.env.example` - complete reference of supported variables.
- `.env.local.example` - local development template.
- `.env.render-supabase.example` - Render + Supabase + Clerk deployment template.

For Render + Supabase + Clerk pilot deployment, use `docs/deployment/render-supabase-clerk.md`. The app still reads `DATABASE_URL`; for Supabase, set `DATABASE_URL` to the Supabase Postgres direct URL or session pooler URL.

## Local services

Start local Postgres:

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

Build and start the local worker:

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

The API loads the repository root `.env` automatically. Next.js commands in `apps/web` should source `../../.env` when they need `NEXT_PUBLIC_*` values from the root file.

## Python workflow

Use `uv` for Python projects in this repository.

For assessment packs that include a `pyproject.toml`:

```sh
cd assessment_packs/fastapi_task_api_v1/candidate
uv sync
uv run pytest
```

Use `uv run` for one-off commands so future coding agents get consistent dependency resolution without manually activating a virtual environment.

## Phase discipline

Use `CURRENT_STATE.md` to identify the active phase. Read the current phase file before coding and update it, together with `CURRENT_STATE.md`, when the phase is complete.
