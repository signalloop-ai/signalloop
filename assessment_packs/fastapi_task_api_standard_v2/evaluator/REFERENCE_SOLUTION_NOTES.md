# Reference Solution Notes

Evaluator-only. Do not expose to candidates or the AI collaborator.

The reference solution uses the same public API shape as the starter code and keeps the in-memory implementation. It does not add persistence, auth frameworks, or external services.

## Behavioral choices

- **Email normalization:** `email.strip().lower()` at model level via `field_validator`. Stored email is canonical. Duplicate check compares normalized values → 409.
- **Title validation:** `title.strip()` in `field_validator`. Stored title is trimmed. Blank-after-strip → 422.
- **Priority:** Optional field, default `MEDIUM`. `field_validator` strips and uppercases. Invalid values → 422. Valid: `LOW`, `MEDIUM`, `HIGH`.
- **Authorization policy:** Known non-owner → 403. Unknown actor (not in users) → 404. Shared `_ensure_actor_can_access` helper used on GET and DELETE.
- **Status transitions:** `ALLOWED_TRANSITIONS` dict: `TODO → IN_PROGRESS → DONE`. Direct `TODO → DONE` → 409. Reopening `DONE` → 409. Invalid status string → 422 via `field_validator`.
- **Delete:** Owner-only. Task removed from dict. Repeat delete → 404.
- **Due date:** Optional ISO date string (`YYYY-MM-DD`). Invalid format → 422. Past date → 422. Null for missing.
- **Task listing:** `GET /tasks?owner_id=...`. Filtered by owner_id, ordered by task id ascending. Unknown owner or no tasks → empty list `[]`.

## Quality signals to look for

| Area | Full-quality signal | Sloppy signal |
|---|---|---|
| Email | `field_validator`, stored normalized | Route-level check, raw email stored |
| Title | `field_validator`, stored trimmed | Route-level `len(title) == 0` |
| Priority | `field_validator`, `strip().upper()` | Hardcoded `if priority == "HIGH"` |
| Auth | Shared helper, actor-then-owner order | Inline check, owner-only |
| Transitions | `ALLOWED_TRANSITIONS` map | Hardcoded per-case conditionals |
| Due date | `date.fromisoformat()`, past-date check | Raw string stored |
| Listing | Sorted by id, empty list for unknown | Unfiltered or 404 for unknown |

## Verification

From `assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution`, run:

```sh
uv run pytest -c pyproject.toml --rootdir=. ../hidden_tests
uv run pytest -c pyproject.toml --rootdir=. ../../candidate/tests
```

From `assessment_packs/fastapi_task_api_standard_v2/candidate`, run:

```sh
uv run pytest
```

The starter code is expected to fail the 3 public issue tests and the 2 enhancement tests. A correct solution passes all public and hidden tests.
