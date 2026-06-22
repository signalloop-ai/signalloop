# FastAPI Team Task API — Advanced v1

You are working on an internal team task API generated from an early AI-assisted prototype. The service is being prepared for a limited beta with employees, team members, and team leads.

Public tests are intentionally incomplete. Some behaviors are not surfaced by any test — you are expected to find and fix them by reading the code. Where requirements are ambiguous, choose a policy and apply it consistently.

## Time limit

{{DURATION_MINUTES}} minutes{{TIMING_NOTE}}.

## Product constraints

- Security and team isolation matter more than convenience.
- Team leads should not gain access across unrelated teams.
- Partial updates should not erase omitted fields.
- Where 403 vs 404 is ambiguous, choose a policy and apply it consistently.
- Keep the in-memory implementation simple; do not add a database or auth provider.

## Your task

Debug and harden the API in `task_api/`. Then implement two enhancements described below.

You should:

- Run the public tests to find initially-failing behaviors.
- Inspect the implementation for additional issues not surfaced by any test.
- Fix behavior you believe is unsafe, invalid, or inconsistent.
- Implement the enhancements below.
- Add or update candidate tests for the behavior you change or add.
- Be ready to summarize what you changed, what tradeoffs you chose, and how you verified it.

## Enhancements

### 1. Task dependencies

Tasks should support a blocking relationship. A task that has unresolved blockers should not be allowed to move to `IN_PROGRESS`. The API should reject dependency relationships that would create a cycle. Design the endpoint shape and the exact rules — the what is required, the how is up to you.

### 2. Team activity feed

The API should expose a team-level activity feed via `GET /teams/{team_id}/activity`. The feed should aggregate events across all tasks in the team. Only team members should be able to access it. Decide how to handle ordering, pagination, and whether archived task events are included.

## How your submission is evaluated

Your score reflects not just whether tests pass, but the quality of your implementation:

- **Authorization correctness**: Which status code for a non-owner vs. an unknown actor? Partial update authorization? These are evaluated on correctness, not just presence.
- **Input and role validation**: Invalid roles, bad inputs, and edge cases are tested beyond the public test suite.
- **Enhancement correctness**: Task dependencies are evaluated on blocker enforcement and cycle detection. The activity feed is evaluated on pagination, ordering, and access scoping — not just that events appear.
- **Consistency**: If you choose an access control policy or status transition rule, apply it uniformly. Inconsistent enforcement is a signal.

You will not see the exact hidden checks during the attempt. Read the code and the constraints, reason about what correct behavior should be, and implement it thoroughly.

## AI collaborator policy

Once you have identified a specific issue, you may ask the assistant to help you implement the fix. You may also ask it to explain Python, FastAPI, or pytest mechanics, interpret test output, or discuss tradeoffs for a design decision you have already made.

Do not ask it to enumerate every defect, provide a full solution, or generate your final explanation.

## Useful commands

```bash
uv run pytest
uv run uvicorn task_api.main:app --reload
```

## API summary (current)

- `POST /users` — create user
- `POST /teams` — create team
- `POST /teams/{team_id}/members` — add member (role: member or lead)
- `POST /tasks` — create task (team_id, owner_id, assignee_id, description)
- `GET /tasks/{task_id}?actor_user_id=...` — get task
- `PATCH /tasks/{task_id}?actor_user_id=...` — partial update
- `PATCH /tasks/{task_id}/status?actor_user_id=...` — update status
- `DELETE /tasks/{task_id}?actor_user_id=...` — soft archive
- `POST /tasks/{task_id}/comments` — add comment
- `GET /tasks/{task_id}/events` — audit trail
- `GET /users/{user_id}/tasks` — tasks for a user
- `GET /teams/{team_id}/tasks?actor_user_id=...` — team task list (limit/offset)
