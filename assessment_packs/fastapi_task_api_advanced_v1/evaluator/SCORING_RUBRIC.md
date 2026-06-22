# Advanced v1 Scoring Rubric

Evaluator-only. Do not expose to candidates or the AI collaborator.

## Point weights

| Category | Points |
|---|---:|
| Public issue resolution | 15 |
| Hidden issue generalization | 15 |
| Enhancements | 25 |
| Candidate-written tests | 15 |
| AI collaboration | 15 |
| Regression | 15 |
| **Total** | **100** |

## Quality principle

Quality is a modifier within each category. For each issue and enhancement, the reference implementation defines full points. Tests encode quality where possible; the LLM evaluator applies the authored rubric below where test results alone cannot differentiate.

---

## Public issue resolution — 15 pts

4 public tests, ~4 pts each. Only initially-failing tests count.

### Issue 1: Partial update overwrites omitted fields (4 pts)

- **Full (4):** `payload.model_dump(exclude_unset=True)` — only provided fields updated
- **Partial (2):** Manual `if payload.title is not None` per field — works but brittle, breaks when new fields added

### Issue 2: Team lead access is global (4 pts)

- **Full (4):** `is_team_lead(team_id, user_id)` scoped to the task's team — single membership check
- **Partial (2):** Check scoped to GET but not to other endpoints (status, patch, delete)

### Issue 3: Archived tasks visible in team list (4 pts)

- **Full (4):** `not task["archived"]` filter applied on both `GET /teams/{id}/tasks` and `GET /users/{id}/tasks`
- **Partial (2):** Filter on team list only, missed on user task list

### Issue 4: Comment has no access check (3 pts)

- **Full (3):** Reuses `ensure_task_access` helper — single source of truth for access logic
- **Partial (1):** Inline duplicate check — works but diverges from `get_task` access logic if either changes

---

## Hidden issue generalization — 15 pts

3 hidden tests, 5 pts each. Candidate must discover these by reading the code.

### Hidden 1: Partial update authorization (5 pts)

Non-owner, non-assignee, non-lead can patch a task.

- **Full (5):** `ensure_task_access` applied consistently on PATCH, status update, and delete
- **Partial (3):** Applied only on PATCH, missed on status update or delete

### Hidden 2: Role validation (5 pts)

`"admin"` accepted as a valid role, should be 422.

- **Full (5):** `field_validator` at model level — `Literal` type or explicit set check
- **Partial (3):** Route-level `if role not in valid_roles` check — works but bypassed by model inheritance

### Hidden 3: Status transition not enforced (5 pts)

`TODO → DONE` direct allowed, invalid statuses accepted.

- **Full (5):** `ALLOWED_TRANSITIONS` dict + `field_validator` for status string — extensible
- **Partial (3):** Hardcoded conditionals for specific failing cases only

---

## Enhancements — 25 pts

2 enhancements, split as described below.

### Enhancement 1: Task dependencies (13 pts)

README specifies: blocking relationship, cycle rejection. Endpoint shape left open.

**Correctness (public test) — 4 pts**
- Dependency endpoint exists and returns the relationship → 4 pts
- Endpoint missing → 0 pts

**Quality — 9 pts**
- **Full (9):** Blocker enforced on IN_PROGRESS transition, cycle detection via graph traversal (DFS/BFS), self-dependency rejected, archived blocker treated as resolved
- **Partial (5):** Blocker enforced on transition, no cycle detection — circular deps silently allowed
- **Minimal (2):** Dependency stored but not enforced on any transition

### Enhancement 2: Team activity feed (12 pts)

README specifies: `GET /teams/{id}/activity`, team-scoped, only members can access. Pagination and ordering left open.

**Correctness (public test) — 4 pts**
- Endpoint exists, returns events for team member → 4 pts
- Endpoint missing → 0 pts

**Quality — 8 pts**
- **Full (8):** Deterministic ordering, limit/offset pagination, non-member → 403, archived task events excluded
- **Partial (4):** Endpoint exists, some events returned, but no pagination or unordered or archived events included
- **Minimal (1):** Endpoint exists but returns all events from all teams

---

## Candidate-written tests — 15 pts

- **3+ test functions covering auth, partial update, dependency, or activity behavior** → 15 pts
- **1–2 test functions with meaningful assertions** → 9 pts
- **Tests added but shallow** → 4 pts
- **No tests** → 0 pts

---

## AI collaboration — 15 pts

- **Used AI, no policy redirects** → 15 pts
- **Used AI, some policy redirects** → 9 pts
- **Never used AI** → 7 pts

---

## Regression — 15 pts

- **No regressions** → 15 pts
- **1 regression** → 6 pts
- **2+ regressions** → 0 pts
- **No test run recorded** → 8 pts

---

## Recommendation thresholds

| Score | Recommendation |
|---|---|
| 80–100 | strong_advance |
| 60–79 | advance_with_followups |
| 40–59 | needs_review |
| 0–39 | do_not_advance |
