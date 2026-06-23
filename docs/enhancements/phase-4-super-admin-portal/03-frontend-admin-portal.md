# 03 - Frontend Admin Portal

Status: not started.

## Goal

Build the super admin frontend at `/admin` with three pages: roster, employer
detail, and report drill-through. Add role-based redirect logic so admins go
to `/admin` and employers go to `/employer`.

## Pages

### 1. Admin roster: `/admin`

Main landing page. Shows a table of all employers with Tier 1 + Tier 2
summary data.

**Table columns:**

| Column | Source |
|---|---|
| Email | `email` |
| Company | `company_name` |
| Role | `role` (badge: "Admin" or blank) |
| Created | `created_at` (formatted) |
| Last activity | `last_activity_at` (relative: "2h ago") |
| Invites | `invite_count` |
| Attempts | `attempt_count` |
| Submitted | `submitted_count` |
| Reports | `report_count` |
| Avg score | (from score_distribution if available, else "—") |

**Interactions:**
- Click any row → navigate to `/admin/employers/[id]`
- Auto-refresh every 60s (lighter than employer portal's 30s)
- Loading state while fetching
- Empty state if no employers

**Layout:** Full-width table, SignalLoop logo in header, "Super Admin" label
in top bar. No invite creation button (admin is view-only).

### 2. Employer detail: `/admin/employers/[id]`

Per-employer drill-down. Shows all Tier 2 signals + the full attempt list.

**Sections:**

1. **Header**: employer email, company name, created date, role badge
2. **Summary cards** (metric cards, same style as evidence report):
   - Invites sent, Attempts created, Submitted, Reports generated
   - Avg score, Median score, Score range
   - AI messages, AI violations
   - Failed test runs, Missing reports
3. **Status breakdown**: mini bar showing in_progress / submitted / expired
   counts
4. **Assessment pack breakdown**: list with counts
5. **Attempt table**: same columns as the employer portal's attempt list
   (candidate email, pack, status, submitted date, score, report link)
   - Click any row → navigate to `/admin/reports/[attemptId]`

**Back button** to return to `/admin`.

### 3. Admin report: `/admin/reports/[attemptId]`

Reuses the existing evidence report component from the employer portal.

**Implementation:** Extract the report rendering logic from
`apps/web/src/app/employer/reports/[attemptId]/page.tsx` into a shared
component (e.g., `apps/web/src/app/components/EvidenceReport.tsx`). Both
the employer report page and the admin report page render this component.

The only difference is the data fetch URL:
- Employer: `GET /employer/attempts/{id}/report`
- Admin: `GET /admin/attempts/{id}/report`

**Back button** returns to the employer detail page (not the employer
portal).

## Role-based redirect

### On `/employer` load

1. Fetch `GET /employer/me` (or `/admin/me`)
2. If `role === 'super_admin'` → redirect to `/admin`
3. Else → render employer portal as normal

### On `/admin` load

1. Fetch `GET /admin/me`
2. If 403 (not admin) → redirect to `/employer`
3. If 200 → render admin portal
4. If 401 → show Clerk sign-in

### Clerk protection

Both `/employer` and `/admin` are behind Clerk auth. The Clerk `<SignedIn>`
wrapper handles the authentication gate. The role check happens after
authentication.

No separate Clerk instance, no separate sign-in page. The same
`<SignIn>` component is used.

## File structure

```
apps/web/src/app/admin/
  layout.tsx          # Clerk auth wrapper + role check
  page.tsx            # Roster page (Tier 1 + Tier 2)
  employers/
    [id]/
      page.tsx        # Employer detail (Tier 2 + attempt list)
  reports/
    [attemptId]/
      page.tsx        # Report drill-through (reuses EvidenceReport component)
```

New shared component:
```
apps/web/src/app/components/
  EvidenceReport.tsx  # Extracted from employer report page
```

## Styling

- Reuse the existing employer portal design language (SignalLoop logo, metric
  cards, tables, badges)
- Admin pages use the same CSS classes and color palette
- "Super Admin" label in the top bar distinguishes admin from employer
- No new CSS framework or design system

## Acceptance criteria

- `/admin` renders the employer roster with correct counts.
- Clicking an employer row navigates to `/admin/employers/[id]`.
- Employer detail page shows all Tier 2 signals + attempt list.
- Clicking an attempt navigates to `/admin/reports/[attemptId]`.
- Admin report page renders the same evidence report as the employer portal.
- Admin visiting `/employer` is redirected to `/admin`.
- Regular employer visiting `/admin` is redirected to `/employer`.
- Unauthenticated user sees Clerk sign-in on both routes.
- No invite creation controls visible on admin pages.
- Typecheck and build pass.
