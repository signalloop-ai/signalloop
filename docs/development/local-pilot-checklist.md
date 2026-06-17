# Local Pilot Checklist

Use this checklist before moving to hosted Render/Supabase/Clerk testing.

## Setup

- [ ] `.env` exists at the repository root.
- [ ] `DATABASE_URL` points to local Postgres.
- [ ] `OPENAI_API_KEY` is set, or local fallback AI behavior is acceptable.
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` are set if testing real Clerk login.
- [ ] Web/API ports match `.env`, `playwright.config.ts`, and the running services.
- [ ] Docker is running.
- [ ] Local Postgres is running.

## Services

- [ ] API migrations applied with Alembic.
- [ ] Worker runtime image built as `signalloop-python-assessment:3.11`.
- [ ] Worker is running on port `9000`.
- [ ] API is running on the port configured by `NEXT_PUBLIC_API_URL`.
- [ ] Web app is running on port `3000`.

## Automated Checks

- [ ] `cd apps/api && uv run pytest`
- [ ] `cd apps/worker && uv run pytest`
- [ ] `cd apps/web && npm run typecheck`
- [ ] `cd apps/web && npm run lint`
- [ ] `cd apps/web && npm run build`
- [ ] `cd apps/web && npm run test:e2e`

## Manual Flow

- [ ] Open `/employer`.
- [ ] Sign in with Clerk, or use local development login while running the dev server.
- [ ] Create a candidate invite.
- [ ] Open the invite link.
- [ ] Accept candidate rules.
- [ ] Edit a file.
- [ ] Run public tests.
- [ ] Ask one bounded AI question.
- [ ] Submit final explanation and decision log.
- [ ] Generate evidence report.
- [ ] Confirm employer report view shows score, recommendation, FAVO, and follow-up questions.

## Stop Before Hosted Deployment

Do not begin Render/Supabase/ECS work until the local checklist is complete.
