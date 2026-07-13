# 01 - Backend Auth and Schema

Status: not started.

## Goal

Add the database column, configuration, and auth dependency that distinguish a
super admin from a regular employer. This is the foundation for all admin API
endpoints and frontend routing.

## Schema change

### Migration: `0008_add_employer_role`

Add a nullable `role` column to `employers`:

```sql
ALTER TABLE employers ADD COLUMN role VARCHAR(50);
```

- `NULL` = regular employer (default for all existing rows)
- `'super_admin'` = super admin

Nullable + no default means this migration is safe on a live database — no
backfill, no table rewrite, no lock.

### Model update (`apps/api/signalloop_api/models.py`)

```python
class Employer(TimestampMixin, Base):
    __tablename__ = "employers"
    # ... existing fields ...
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

## Configuration

### Env var: `SUPER_ADMIN_EMAILS`

Add to `apps/api/signalloop_api/config.py`:

```python
self.super_admin_emails = [
    e.strip().lower()
    for e in getenv("SUPER_ADMIN_EMAILS", "").split(",")
    if e.strip()
]
```

Comma-separated list of email addresses. Case-insensitive (lowercased on load
and on comparison). Example:

```
SUPER_ADMIN_EMAILS=admin@example.com
```

### `.env.example` and `.env.render-supabase.example`

Add the env var to both templates with a placeholder.

## Role assignment at login

Update `get_or_create_employer` in `apps/api/signalloop_api/auth.py`:

When creating or updating an employer, check if the identity email matches a
super admin email:

```python
def get_or_create_employer(session: Session, identity: EmployerIdentity) -> Employer:
    employer = session.scalar(select(Employer).where(Employer.clerk_user_id == identity.clerk_user_id))
    # ... existing create/update logic ...

    # Assign role based on env var. Checked on every login so removing an
    # email from SUPER_ADMIN_EMAILS downgrades the role on next login.
    is_admin = identity.email.lower() in settings.super_admin_emails
    if employer.role != ("super_admin" if is_admin else None):
        employer.role = "super_admin" if is_admin else None
    return employer
```

This means:
- Admin email in env var → `role = 'super_admin'` on every login
- Admin email removed from env var → `role = NULL` on next login (downgrade)
- Non-admin email → `role = NULL` always

## Super admin auth dependency

New function in `apps/api/signalloop_api/auth.py`:

```python
def get_current_super_admin(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Employer:
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Super admin authentication required")
    identity = verify_clerk_token(token)
    employer = get_or_create_employer(session, identity)
    if employer.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return employer
```

- 401 if no token / invalid token (same as employer auth)
- 403 if authenticated but not a super admin (the key difference from
  `get_current_employer`, which never 403s)

## API response: include role

The employer auth response (if any endpoint returns the current employer
info) should include `role` so the frontend can redirect. At minimum, the
`/employer` page load should be able to detect the role.

Options:
1. Add `role` to `EmployerAttemptSummary` or a new `EmployerInfoResponse`
   schema returned by a lightweight `/me` endpoint.
2. Add a dedicated `GET /admin/me` endpoint that returns `{ role: "super_admin" }`
   or 403.

Recommended: add `GET /employer/me` returning `{ id, email, role }`. The
frontend calls this on load and redirects based on role. This endpoint is
already auth-gated by `get_current_employer` (works for both admin and
regular employer).

## Acceptance criteria

- Migration `0008_add_employer_role` runs cleanly on a database with existing
  employers.
- `Employer.role` column exists in the model.
- `SUPER_ADMIN_EMAILS` env var is read and lowercased.
- `get_or_create_employer` sets `role = 'super_admin'` when the email matches.
- `get_current_super_admin` returns 403 for non-admin employers.
- `GET /employer/me` returns `{ id, email, role }`.
- Existing employer endpoints are unaffected (no behavior change for
  non-admin employers).
