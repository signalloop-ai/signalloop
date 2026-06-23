# 02 - Backend Admin API

Status: not started.

## Goal

Add read-only API endpoints that the super admin frontend uses to render the
roster, per-employer detail, and drill-through report views.

All endpoints are protected by `get_current_super_admin` (from task 01).
Regular employers get 403.

## Endpoints

### 1. Admin roster: `GET /admin/employers`

Returns all employers with aggregate counts.

```json
[
  {
    "id": 11,
    "email": "local-employer@signalloop.dev",
    "company_name": null,
    "role": null,
    "created_at": "2026-06-19T13:40:39Z",
    "last_activity_at": "2026-06-22T10:15:00Z",
    "invite_count": 5,
    "attempt_count": 5,
    "submitted_count": 3,
    "report_count": 3
  }
]
```

`last_activity_at` = most recent timestamp across: employer `created_at`,
latest `AssessmentAttempt.created_at`, latest `CodeSnapshot.created_at`,
latest `TestRun.created_at`, latest `AIInteraction.created_at` for that
employer's attempts. Falls back to `created_at` if no activity.

Implementation: single query with joins/aggregates, or one query for employers
+ one for counts. Avoid N+1.

### 2. Admin employer detail: `GET /admin/employers/{employer_id}`

Returns Tier 2 operational signals for a single employer.

```json
{
  "id": 11,
  "email": "local-employer@signalloop.dev",
  "company_name": null,
  "role": null,
  "created_at": "2026-06-19T13:40:39Z",
  "invite_count": 5,
  "attempt_count": 5,
  "submitted_count": 3,
  "report_count": 3,
  "status_breakdown": {
    "in_progress": 1,
    "submitted": 3,
    "expired": 1
  },
  "score_distribution": {
    "average": 62.5,
    "median": 65,
    "min": 40,
    "max": 85
  },
  "ai_usage": {
    "total_messages": 42,
    "total_violations": 2
  },
  "pack_breakdown": {
    "fastapi-task-api-standard-v2": 3,
    "fastapi-task-api-advanced-v1": 2
  },
  "stuck_signals": {
    "failed_test_runs": 0,
    "error_attempts": 0,
    "missing_reports": 1
  },
  "attempts": [
    {
      "id": 45,
      "candidate_email": "candidate@example.com",
      "assessment_pack_slug": "fastapi-task-api-standard-v2",
      "status": "submitted",
      "submitted_at": "2026-06-21T14:00:00Z",
      "score_total": 65
    }
  ]
}
```

`attempts` is the full list for this employer (same fields as the existing
`EmployerAttemptSummary`, plus `score_total` from the evidence report if
generated).

### 3. Admin attempt report: `GET /admin/attempts/{attempt_id}/report`

Returns the same evidence report JSON as the existing employer endpoint
`GET /employer/attempts/{attempt_id}/report`. The only difference is the auth
dependency: `get_current_super_admin` instead of `get_current_employer` +
`ensure_employer_owns_attempt`.

This means the admin can view any employer's report without the ownership
check.

If the report has not been generated yet, returns 404 with the same message
as the employer endpoint.

### 4. Admin me: `GET /admin/me`

Returns the current admin's identity for frontend routing.

```json
{
  "id": 17,
  "email": "redacted-personal-email@example.com",
  "role": "super_admin"
}
```

This is the same as `GET /employer/me` but protected by
`get_current_super_admin` (403 for non-admins). The frontend can call either;
the admin endpoint gives a clean 403 signal.

## Implementation notes

- New router module: `apps/api/signalloop_api/admin.py`
- Registered in `main.py` alongside existing routers
- All endpoints use `get_current_super_admin` dependency
- No write operations — every endpoint is GET
- Reuse existing report generation/fetch logic from `reports.py` for the
  admin report endpoint (call the same function, just skip the ownership
  check)
- `score_distribution` computed from `EvidenceReport` rows for that
  employer's submitted attempts
- `stuck_signals`: `failed_test_runs` = TestRuns with `status = 'error'`,
  `error_attempts` = AssessmentAttempts with `status = 'error'` (if any),
  `missing_reports` = submitted attempts without an EvidenceReport

## Acceptance criteria

- `GET /admin/employers` returns all employers with correct counts.
- `GET /admin/employers/{id}` returns Tier 2 signals + attempt list.
- `GET /admin/attempts/{id}/report` returns the same JSON as the employer
  report endpoint.
- `GET /admin/me` returns admin identity with `role = 'super_admin'`.
- Regular employers get 403 on all `/admin/*` endpoints.
- Unauthenticated requests get 401.
- No N+1 queries on the roster endpoint.
