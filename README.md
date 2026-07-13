# SignalLoop

SignalLoop is an AI-native candidate evaluator for software engineering hiring.

The MVP evaluates whether candidates can solve a realistic backend engineering task while using a constrained AI collaborator. It captures evidence of framing, AI usage, verification behavior, design judgment, and final ownership, then generates an Engineering Evidence Report for employer review.

SignalLoop is open-sourced under Apache-2.0. Assessment and question-bank content may carry
additional source-license and attribution metadata; see `THIRD_PARTY_NOTICES.md`.

## Status

Phases 1 through 12 of the original MVP plan are complete and should be treated as historical implementation context.

Post-MVP Phases 2-5 are implemented. Phase 6A question-bank governance is complete as an
experimental foundation. The current workstream is project closeout and open-source release
preparation; question-level adaptive assessment composition is deferred future work.

The repository has been transferred to the joint GitHub organization
`signalloop-ai/signalloop` and should remain private until hosted smoke testing, secret/history
cleanup, and final demo/README review are complete.

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
- Guided role matching from role/JD requirements to the closest registered Standard or Advanced
  FastAPI assessment, with explicit unsupported-coverage results.
- Super-admin question-bank provenance, draft import/generation, review, and approval workflows.

Guided role matching does not assemble new questions. Phase 6A questions are not connected to
employer blueprint composition, mixed-question candidate delivery, or report scoring.

Future problem: compose comparable role-level assessments from an approved, calibrated question
bank without resume-driven scored-question selection or unreviewed AI-generated content.

## For Readers

SignalLoop explores a simple product thesis: when candidates can use AI, coding assessments
should measure framing, verification, judgment, collaboration, and ownership instead of only
measuring whether code appears at the end.

The current release is intentionally narrow. It demonstrates a constrained AI collaborator,
evidence capture, deterministic reports, and role-guided matching to existing FastAPI assessment
packs. It does not yet generate mixed question-level assessments from the Phase 6A question bank.

## For Developers

Use this repository as a runnable reference implementation. The fastest path is:

1. Start Postgres.
2. Run API migrations.
3. Start the worker.
4. Start the API.
5. Start the web app.
6. Create an employer invite and run a candidate attempt.

The detailed command sequence is below.

## Open-Source Boundary

This repository is intended as a reference implementation and demo foundation.

- Original SignalLoop application code, docs, and internally authored assessment material are
  Apache-2.0 unless a file states otherwise.
- Imported or adapted question-bank material retains its upstream license and attribution
  requirements.
- Included FastAPI assessment packs are public demo/reference content. Because hidden tests,
  scoring rubrics, and evaluator notes are public in this repository, they should not be reused
  as secure production hiring inventory.
- Included role/JD upload fixtures under
  `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/` are public demo
  fixtures for guided role matching, including text-based PDFs and DOCX files.
- Production adopters should author and calibrate private assessment packs before using
  SignalLoop for real hiring decisions.

See `AUTHORS.md`, `CITATION.cff`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, and
`docs/release/open-source-release-plan.md`.

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
