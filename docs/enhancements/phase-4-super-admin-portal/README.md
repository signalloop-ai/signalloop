# Phase 4: Super Admin Portal

Status: planning complete, implementation in progress.

## Purpose

Phase 4 adds a super admin portal that gives the SignalLoop operator complete
visibility into all employers and their assessment activity. The admin can see
who is using the platform, how much they are using it, and drill into any
employer's attempts and evidence reports — without logging in as that employer.

The admin portal is **view-only**. The admin cannot create invites, regenerate
reports, or modify any data. It is an observation surface, not a management
surface.

## Auth model

The super admin uses the same Clerk application as employers. There is no
separate login screen. The admin signs in with their Google account via Clerk,
same as any employer.

At login time, the backend checks the authenticated email against
`SUPER_ADMIN_EMAILS` (comma-separated env var). If the email matches, the
`Employer` row is marked `role = 'super_admin'`. The frontend then redirects
the user to `/admin` instead of `/employer`.

Clean separation: an admin account cannot access the employer portal
(`/employer`), and a regular employer cannot access `/admin`. The role is
checked on both frontend routes and backend endpoints.

## What Phase 4 delivers

### 1. Employer roster (Tier 1)

A single-page view at `/admin` listing every employer in the system:

- Email
- Company name (if set)
- Created date
- Last activity timestamp
- Invite count
- Attempt count (created)
- Attempt count (submitted)
- Report count (generated)

### 2. Per-employer operational summary (Tier 2)

Each employer row in the roster links to a detail page at
`/admin/employers/[id]` showing:

- All Tier 1 fields
- Attempt status breakdown (in_progress / submitted / expired)
- Score distribution (average, median, min, max across submitted attempts)
- AI usage (total AI messages across all attempts)
- Assessment pack breakdown (which packs this employer uses)
- Error/stuck signals (attempts with failed test runs, error status, or no
  report generated)
- Full attempt list for that employer (same data the employer sees, minus
  invite creation controls)

### 3. Drill-through to evidence reports (Tier 3)

From the per-employer detail page, the admin can click any attempt to view the
full evidence report at `/admin/reports/[attemptId]`. This reuses the existing
report rendering component used by the employer portal — no new report UI is
built.

### 4. Role-based access control

- New `role` column on `employers` table (nullable string, default NULL =
  regular employer)
- `SUPER_ADMIN_EMAILS` env var drives role assignment at login
- `get_current_super_admin` FastAPI dependency protects all admin API endpoints
- Frontend `/admin` routes check role and redirect non-admins to `/employer`
- Frontend `/employer` routes check role and redirect admins to `/admin`

## Non-goals

- Admin cannot create, modify, or delete employers
- Admin cannot create invites or regenerate reports
- Admin cannot modify assessment packs or scoring rules
- Admin cannot impersonate an employer
- No admin settings or configuration UI
- No audit log of admin views (admin is trusted, not audited)

## Planned task order

1. `01-backend-auth-and-schema.md` — migration, model, config, role
   assignment, super admin dependency
2. `02-backend-admin-api.md` — admin endpoints for roster, employer detail,
   attempt detail
3. `03-frontend-admin-portal.md` — `/admin` routes, role redirect, roster page,
   employer detail page, report reuse

## Deployment notes

- `SUPER_ADMIN_EMAILS` must be set in the Render environment (and locally in
  `.env`). Example: `SUPER_ADMIN_EMAILS=redacted-personal-email@example.com`
- Migration `0008_add_employer_role` is additive (nullable column) and safe to
  run on a live database without downtime.
- No new infrastructure, no new external services.
