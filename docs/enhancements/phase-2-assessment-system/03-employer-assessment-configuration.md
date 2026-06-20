# 03 - Employer Assessment Configuration

Status: completed locally.

## Goal

Allow employers to configure the assessment type and timing for each invite.

## Configuration Options

Assessment type:

- Standard,
- Advanced.

Timing mode:

- Untimed / recommended time only,
- Timed.

Duration options:

- 60 minutes,
- 90 minutes,
- 120 minutes,
- 150 minutes.

Defaults:

- Standard: 90 minutes,
- Advanced: 120 minutes.

For Phase 2, use fixed duration options. Do not add arbitrary custom duration unless
explicitly requested later.

## Data Model Direction

Add per-attempt/invite fields later:

- `assessment_level` or assessment pack slug,
- `timing_mode`,
- `duration_minutes`,
- `started_at`,
- `expires_at`.

Exact schema should be designed during implementation.

## Employer UI Direction

Invite creation should show:

- assessment selector,
- recommended duration,
- timed/untimed selector,
- duration dropdown when timed.

## Implementation Notes

Implemented locally with:

- schema migration `0003_add_attempt_configuration`,
- API schema changes for fixed assessment level, timing mode, and duration options,
- employer portal invite form changes,
- tests for defaults and validation.

Advanced assessment is now available because the bounded advanced-pack task has been
implemented. The employer UI can create Standard or Advanced invites.

## Local Validation

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 51 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_config_migration_check_2.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.

Playwright e2e was attempted, but this Codex sandbox could not bind
`127.0.0.1:3000` and approval escalation was unavailable because the session hit the
Codex approval usage limit. Run `cd apps/web && npm run test:e2e` locally after this
change.
