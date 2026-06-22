# 04 - Time-Boxed Assessment Flow

Status: completed locally.

## Goal

Support optional timed assessments while preserving candidate evidence.

## Timer Semantics

The timer starts when the candidate accepts onboarding, not when the invite is created.

Server stores:

- `started_at`,
- `expires_at`,
- `submitted_at`,
- `submission_mode`.

Submission modes:

- `manual`,
- `auto_expired`.

## Candidate Behavior

If timed:

- show countdown in the candidate workspace,
- show warnings at 10, 5, and 1 minute,
- allow manual submission before expiry,
- at expiry, auto-submit latest work.

If the tab is open at expiry:

1. frontend saves the current in-browser files,
2. frontend submits that snapshot,
3. UI shows expired/submitted state.

If the tab is closed or disconnected:

1. backend still enforces expiry,
2. backend submits or records the latest persisted snapshot according to the implementation design.

## Backend Enforcement

Backend must enforce expiry for:

- snapshots,
- public test runs,
- AI messages if required by product decision,
- final submission.

Implementation should avoid trusting only the browser countdown.

## Report Fields

Report should include:

- assessment timing mode,
- duration_minutes,
- time_used_minutes,
- started_at,
- submitted_at,
- expires_at,
- submission_mode.

## Implementation Notes

Implemented locally with:

- explicit candidate accept endpoint that starts the timer,
- candidate countdown and 10/5/1 minute warnings,
- open-tab auto-submit of current browser files at expiry,
- backend expiry enforcement for snapshots, public tests, AI messages, and final
  submission,
- auto-expired persisted submission from the latest saved snapshot when a closed or
  stale tab makes a later backend request,
- report timing metadata.

Manual submissions before expiry are recorded with `submission_mode=manual`.
Submissions at or after expiry are recorded with `submission_mode=auto_expired`.

## Local Validation

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_attempt_lifecycle.py tests/test_final_submission.py tests/test_evidence_report.py tests/test_ai_endpoint.py` -> 30 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_timer_migration_check.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.

Playwright e2e was attempted, but this Codex sandbox could not bind
`127.0.0.1:3000`. Run `cd apps/web && npm run test:e2e` locally before deployment.
