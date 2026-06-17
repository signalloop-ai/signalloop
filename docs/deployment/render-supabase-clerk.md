# Render, Supabase, and Clerk Pilot Deployment

## Scope

This document covers the Phase 11 pilot deployment shape:

- Render hosts the web app and API.
- Supabase provides Postgres.
- Clerk provides employer login.
- Local Docker remains the development execution worker.
- Production execution is planned for AWS ECS/Fargate per-run tasks and is not implemented in Phase 11.

Render is not used for the execution worker because the worker architecture must not depend on Docker-in-Docker or a host Docker socket in a managed web-service container.

## Environment Files

Use provider-neutral names in the application:

- `DATABASE_URL` points to local Postgres or Supabase Postgres.
- `PUBLIC_BASE_URL` is the web URL used when generating candidate invite links.
- `NEXT_PUBLIC_API_URL` is the browser-visible API URL.
- `CORS_ORIGINS` lists web origins allowed to call the API.

Templates:

- `.env.local.example` for local development.
- `.env.render-supabase.example` for Render + Supabase + Clerk.

Use separate environment stores:

- Local development: root `.env`, loaded by the API and optionally sourced before starting web.
- Render production/pilot: Render service environment variables or environment groups.
- Supabase: database password and connection string in Supabase dashboard.
- Clerk: publishable/secret keys in Clerk dashboard and Render env vars.
- AWS: IAM/ECR/ECS/S3 resource identifiers and credentials in AWS/Render env vars.

Do not commit a production `.env` file. Add the keys from `.env.render-supabase.example`
in each Render service's Environment tab or environment group.

Render deploys from a Git provider repository. Push this repo to GitHub, connect the
GitHub repository in Render, then either create services manually or use the root
`render.yaml` Blueprint.

## Supabase

Create a Supabase project and copy a Postgres connection string from the project dashboard.

For Render-hosted API traffic, prefer the Supabase shared pooler session-mode URL if the direct database endpoint is not reachable over IPv4 from the deployment environment. Supabase documents:

- direct connection on `db.[project-id].supabase.co:5432`,
- shared pooler session mode on `aws-[region].pooler.supabase.com:5432`,
- shared pooler transaction mode on `aws-[region].pooler.supabase.com:6543`.

SignalLoop's API is a long-running service with SQLAlchemy's application-side pool, so use direct connection when reachable, or session pooler when IPv4 reachability is needed. Avoid transaction mode unless the SQLAlchemy connection behavior is explicitly tested with prepared statements disabled.

Set the API service environment variable:

```env
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres
```

Then run migrations against the same URL:

```sh
cd apps/api
DATABASE_URL='postgresql://...' uv run alembic upgrade head
```

## Clerk

Create or use a Clerk application and set allowed origins/callbacks to the Render web URL.

Set these values:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_or_pk_test_...
CLERK_SECRET_KEY=sk_live_or_sk_test_...
```

The web app needs `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`. The backend keeps `CLERK_SECRET_KEY` available for server-side auth hardening.

## Render API Service

Create a Render web service for the API from the repository root. The committed
`render.yaml` Blueprint uses root-relative commands so the API can still read
assessment packs from the repository.

Recommended commands:

```sh
cd apps/api && pip install uv && uv sync --frozen
```

Start command:

```sh
cd apps/api && uv run uvicorn signalloop_api.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```env
SIGNALLOOP_ENV=pilot
DATABASE_URL=postgresql://...
PUBLIC_BASE_URL=https://YOUR-WEB-SERVICE.onrender.com
CORS_ORIGINS=https://YOUR-WEB-SERVICE.onrender.com
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5
CLERK_SECRET_KEY=...
EXECUTION_BACKEND=http_worker
EXECUTION_WORKER_URL=https://YOUR-EXECUTION-RUNTIME
ASSESSMENT_RUNTIME_IMAGE=signalloop-python-assessment:3.11
WORKER_REQUEST_TIMEOUT_SECONDS=90
WORKER_REQUEST_RETRIES=1
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=120
```

For a controlled hosted smoke before AWS resources are ready, keep
`EXECUTION_BACKEND=http_worker` and point `EXECUTION_WORKER_URL` to a trusted staging
worker. Do not expose a raw worker as the long-term production candidate execution path.
For production execution, set `EXECUTION_BACKEND=ecs_fargate` and use the ECS/Fargate
runner path described in `docs/deployment/aws-ecs-fargate-execution.md`.

## Render Web Service

Create a Render web service for the web app from the repository root. The committed
`render.yaml` Blueprint uses root-relative commands for the monorepo.

Recommended commands:

```sh
cd apps/web && npm ci && npm run build
```

Start command:

```sh
cd apps/web && npm run start -- -H 0.0.0.0 -p $PORT
```

Environment variables:

```env
NEXT_PUBLIC_API_URL=https://YOUR-API-SERVICE.onrender.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
```

The browser no longer calls the worker directly for public tests. Public test execution
goes through the API so results can be persisted for evidence reports.

## Smoke Checks

After deploy:

1. API health:

```sh
curl https://YOUR-API-SERVICE.onrender.com/health
```

2. Web loads:

```text
https://YOUR-WEB-SERVICE.onrender.com
```

3. Employer portal loads and Clerk sign-in opens:

```text
https://YOUR-WEB-SERVICE.onrender.com/employer
```

4. API migrations are current:

```sh
cd apps/api
DATABASE_URL='postgresql://...' uv run alembic upgrade head
```

5. Controlled end-to-end pilot only:

- create an invite in `/employer`,
- open the candidate invite,
- run public tests against the configured execution runtime,
- submit,
- generate and view the report.

## Official References

- Render environment variables: https://render.com/docs/configure-environment-variables
- Supabase Postgres connection modes: https://supabase.com/docs/guides/database/connecting-to-postgres
- Clerk environment variables: https://clerk.com/docs/guides/development/clerk-environment-variables
