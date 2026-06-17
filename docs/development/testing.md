# Testing Guide

Run these checks before handing off local MVP changes.

## API

```sh
cd apps/api
uv run pytest
```

Expected current result:

```text
34 passed
```

Run the Alembic migration chain against a disposable SQLite database:

```sh
cd apps/api
DATABASE_URL=sqlite:////tmp/signalloop_migration_check.db uv run alembic upgrade head
```

The migration chain should apply through `0002_create_audit_events`.

## Worker

```sh
cd apps/worker
uv run pytest
```

Expected current result:

```text
22 passed
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

Expected current Playwright result:

```text
2 passed, 1 skipped
```

The skipped test is `live-full-stack-smoke.spec.ts`. It requires real local services and `LIVE_INVITE_TOKEN`.

The employer Playwright test uses the local development login fallback. In development
(`NODE_ENV=development`), the "Use local employer login" button is always shown, even
when `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is set. This means the Playwright test passes
against the dev server regardless of Clerk configuration. In a production build the
Clerk-only path is enforced.

## Live Local Smoke

For a full manual local smoke:

1. Start Postgres and run API migrations.
2. Build the worker runtime image.
3. Start worker on `127.0.0.1:9000`.
4. Start API on the port configured in `NEXT_PUBLIC_API_URL` and `playwright.config.ts`
   (`127.0.0.1:8015` in the current local validation setup).
5. Start web on `127.0.0.1:3000`.
6. Open `/employer`.
7. Sign in with Clerk, or use local development login if Clerk keys are not configured.
8. Create an invite.
9. Open the candidate invite.
10. Run public tests.
11. Ask the AI collaborator a bounded question.
12. Submit final code/explanation/decision log.
13. Generate and view the evidence report in the employer portal.

To run the live Playwright smoke after creating an invite:

```sh
cd apps/web
LIVE_INVITE_TOKEN=... npm run test:e2e
```

## Hosted Smoke

Render/Supabase/Clerk hosted testing has not been completed yet. Use `docs/deployment/render-supabase-clerk.md` when moving beyond local validation.
