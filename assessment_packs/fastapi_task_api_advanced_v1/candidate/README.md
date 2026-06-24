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

The embedded assistant is a constrained collaborator: it coaches you toward the answer and gives you code once you show you understand the approach. It is not an answer machine — but used well, it is genuinely helpful.

### How to get the most from it

- **Found a bug?** Say what's wrong and where ("`patch_task` overwrites every field, not just the ones I sent"). It confirms and shows you the small change to make.
- **Adding an enhancement or writing a test?** It asks a guiding question first. Answer it — once you describe your approach (the route and what to filter/validate; or what a test should send and assert), it gives you the code. Engage with the question instead of asking it to "just do it."
- **Syntax or concept question?** Ask directly ("how do I raise a 409 in FastAPI?", "what does `model_dump(exclude_unset=True)` do?") — you get a straight answer.
- It can see the files you're working on, so refer to functions by name.
- If it replies with a question, that's the path forward — answering it is what unlocks the code. Don't give up after one Socratic question.

### Prompts that work vs. prompts that stall

| Instead of this… | Try this… |
| --- | --- |
| "What's wrong with my code?" / "Find all the bugs" | "I think `is_team_lead` isn't scoped to a team — how do I fix that?" |
| "Give me the complete solution" / "Write all the tests" | "How do I raise a 409 in FastAPI?" — or, after describing your plan, "ok give me the code for that" |
| "Just write the dependency feature for me" | "For task dependencies I'd add a blocker list and reject cycles with DFS — does that sound right?" |
| Pasting a test and asking "make this pass" | "The archived-task test expects it hidden but I still see it — what should I check?" |
| "Should I return 403 or 404? You decide." | "What are the tradeoffs between 403 and 404 for a non-member?" |

It will not enumerate every defect, write the whole solution, rewrite whole files, write your full test suite, reveal hidden tests, or make design decisions for you — those are the parts being assessed.

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
