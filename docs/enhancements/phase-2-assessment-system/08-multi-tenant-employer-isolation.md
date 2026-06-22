# 08 - Multi-Tenant Employer Isolation

Status: completed locally.

## Goal

Make the employer portal and employer API routes strict multi-tenant surfaces before
broader external pilot usage.

Employer A must not be able to list, fetch, generate, or infer Employer B attempts or
reports.

## Identity Decision

Use Clerk user identity for Phase 2.

Do not introduce Clerk organizations in this task unless explicitly requested later.
Organization/team support can be revisited after the pilot flow needs shared company
accounts.

## Current MVP Gap

The MVP web app uses Clerk as a frontend gate, but backend Clerk authorization is not
enforced yet.

Known gaps to close:

- employer API calls do not send a Clerk session token,
- API routes do not verify the current Clerk user,
- `POST /assessment-attempts` accepts optional client-provided `employer_id`,
- `GET /assessment-attempts` returns all attempts,
- report generate/fetch routes load by attempt id without employer ownership checks.

## Required Behavior

Employer routes must require a verified Clerk user:

- create invite,
- list attempts,
- generate evidence report,
- fetch evidence report.

Candidate invite routes remain bearer-link based:

- open invite,
- save snapshots,
- run public tests,
- send AI messages,
- final submit.

Candidate routes must not expose employer-wide data.

## Implementation Direction

Add an API dependency such as `get_current_employer`.

It should:

1. Read `Authorization: Bearer <token>`.
2. Verify the Clerk token.
3. Use Clerk user id as the stable tenant identity.
4. Create or fetch a local `Employer` row for the Clerk user.
5. Return the local employer for route ownership checks.

Create invite should ignore any client-supplied `employer_id` and set:

```text
attempt.employer_id = current_employer.id
```

Attempt listing should filter:

```text
WHERE assessment_attempts.employer_id = current_employer.id
```

Report generation and fetch should verify that the report attempt belongs to the current
employer before returning data.

## Local Development

Local development uses the same Clerk-backed employer authentication path as production.
There is no local employer-login fallback. API tests use FastAPI dependency overrides for
`get_current_employer` so tenant behavior can be tested without relying on external Clerk
network calls.

## Tests

Added API tests proving:

- unauthenticated employer routes are rejected in production-like mode,
- invite creation assigns the current employer,
- employer A only sees employer A attempts,
- employer A cannot generate employer B report,
- employer A cannot fetch employer B report,
- candidate invite routes still work with only the invite token.

Web checks:

- employer API helper sends Clerk authorization when Clerk is active,
- local Playwright employer flow mocks Clerk browser session state and mocked employer
  API responses; real employer API tests require a Clerk-authenticated browser/session.

## Local Validation

- `cd apps/api && uv run pytest`
- `cd apps/web && npm run typecheck`
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`
- `cd apps/web && npm run test:e2e`

## Out Of Scope

Do not add:

- Clerk organizations,
- employer team management,
- enterprise SSO,
- billing,
- admin cross-tenant dashboard.
