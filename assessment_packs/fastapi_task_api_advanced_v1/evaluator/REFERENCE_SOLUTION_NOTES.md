# Advanced v1 Reference Solution Notes

Evaluator-only. Do not expose to candidates or the AI collaborator.

## Behavioral choices

- **Email normalization:** `field_validator` strips and lowercases. Stored email is canonical.
- **Role validation:** `field_validator` on `MemberCreate` — only `"member"` and `"lead"` accepted, case-normalized.
- **Membership deduplication:** `membership_for` check before insert → 409 if already a member.
- **Partial update:** `payload.model_dump(exclude_unset=True)` — only provided fields written. `title` is validated if present.
- **Team lead scoping:** `is_team_lead(team_id, user_id)` checks the specific team's memberships only.
- **Access control:** Shared `ensure_task_access` helper used on GET, PATCH, status update, delete, and comment. Checks actor exists, is a team member, and is owner/assignee/lead.
- **Status transitions:** `ALLOWED_TRANSITIONS` dict: `TODO → IN_PROGRESS → DONE`. Invalid status string → 422 via `field_validator`. Invalid transition → 409.
- **Archive:** Soft delete — sets `archived=True`. Archived tasks return 404 on GET. Hidden from team and user task lists.
- **Task dependencies:** `POST /tasks/{id}/dependencies` with `{"blocker_task_id": int}`. Blocker must be DONE for blocked task to move to IN_PROGRESS. Cycle detection via DFS — `_is_reachable(blocker_task_id, task_id)` checks if adding the edge would create a cycle. Self-dependency rejected.
- **Team activity feed:** `GET /teams/{id}/activity?limit=&offset=`. Returns events from all non-archived tasks in the team, ordered by `(task_id, event_index)`. Non-member → 403. Paginated with limit/offset.

## Quality signals to look for

| Area | Full-quality signal | Sloppy signal |
|---|---|---|
| Partial update | `model_dump(exclude_unset=True)` | Per-field `if payload.x is not None` |
| Lead scoping | `membership_for(team_id, user_id)` | Global scan across all memberships |
| Archive filter | Applied on both team and user task lists | Only on team list |
| Comment access | Reuses `ensure_task_access` | Inline duplicate check |
| Patch auth | `ensure_task_access` on PATCH and status | Only on GET |
| Role validation | `field_validator` at model level | Route-level if check |
| Status transitions | `ALLOWED_TRANSITIONS` map | Hardcoded per-case conditionals |
| Dependencies | DFS cycle detection + transition enforcement | Stores relationship, no enforcement |
| Activity feed | Pagination + auth + deterministic order | Returns all events, no auth |

## Verification

From `assessment_packs/fastapi_task_api_advanced_v1/evaluator/reference_solution`, run:

```sh
uv run pytest -c pyproject.toml --rootdir=. ../hidden_tests
uv run pytest -c pyproject.toml --rootdir=. ../../candidate/tests
```

From `assessment_packs/fastapi_task_api_advanced_v1/candidate`, run:

```sh
uv run pytest
```

The starter is expected to fail 4 public issue tests and 2 enhancement tests. A correct solution passes all public and hidden tests.
