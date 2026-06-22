# FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment - Standard v2

## Scenario

The team used an AI assistant to generate a first version of an internal task-management API. The API is being prepared for a limited beta with internal employees and team leads.

The product manager wants the beta to be safe, predictable, and easy to debug. Public tests are incomplete. Some behavior is intentionally under-specified. Where requirements are ambiguous, make a reasonable decision and implement it consistently.

## Time limit

{{DURATION_MINUTES}} minutes{{TIMING_NOTE}}.

## Constraints

1. Internal beta, not a public consumer product.
2. Security and data isolation are more important than convenience.
3. Avoid large new frameworks or persistence layers.
4. Keep implementation simple.
5. Do not change the public API shape unless justified.
6. Prefer explicit error behavior over silent success.
7. Add tests for changed behavior.
8. Keep the implementation small enough for an internal beta.

## Your task

Debug and harden the API in `task_api/`. Then implement two small enhancements described below.

You should:

- Run the public tests to find the initially-failing behaviors.
- Inspect the implementation for additional issues not surfaced by public tests.
- Fix behavior you believe is unsafe, invalid, or inconsistent.
- Implement the enhancements below.
- Add or update candidate tests for the behavior you change or add.
- Be ready to summarize what you changed, what tradeoffs you chose, and how you verified it in the SignalLoop submission review.

Two areas intentionally require judgment:

- Unauthorized access behavior: choose whether inaccessible resources should return `403` or `404`.
- Status transition policy: choose whether tasks can move directly from `TODO` to `DONE` or must move through `IN_PROGRESS`.

## Enhancements

### 1. Task due date

Tasks should support an optional `due_date` field for the beta triage workflow. A task with a due date should expose it in the response. The API should reject dates that do not make sense for a task management system. The exact validation rules are up to you — make a reasonable decision and implement it consistently.

### 2. Task listing

The API should support listing tasks for a given owner via `GET /tasks?owner_id=...`. The response should be a list of tasks. Decide how to handle ordering and what happens when the owner does not exist or has no tasks.

## How your submission is evaluated

Your score reflects not just whether tests pass, but the quality of your implementation:

- **Design decisions**: For example, should an unknown actor receive a `403` or a `404`? The correct choice is evaluated, not just that you handled it at all.
- **Input handling**: Normalization (e.g., case-insensitive email, whitespace trimming) and validation (e.g., rejecting bad date formats) are tested beyond the basic happy path.
- **Enhancement correctness**: Enhancements are evaluated on edge cases — ordering, empty results, invalid inputs — not just the core feature working once.
- **Consistency**: If you choose a policy (e.g., status transitions, access control), apply it consistently. Partial or inconsistent enforcement is a signal.

You will not see the exact hidden checks during the attempt. Read the code and the constraints, reason about what correct behavior should be, and implement it thoroughly.

## AI collaborator policy

The embedded assistant is a constrained collaborator. Once you have identified a specific issue, you may ask it to help you implement the fix. You may also ask it to explain Python, FastAPI, or pytest mechanics, interpret test output, or discuss tradeoffs for a design decision you have already made.

Do not ask it to enumerate every defect, provide a full solution, rewrite whole files, or generate your final explanation.

## Local setup

Use `uv` and Python 3.11 for the assessment runtime.

```sh
uv sync
uv run pytest
```

The API is exercised through tests. You do not need to run a server, but you can start one for manual inspection:

```sh
uv run uvicorn task_api.main:app --reload
```

## API summary

- `POST /users` creates a user from `email` and optional `name`.
- `GET /users/{user_id}` returns a user.
- `POST /tasks` creates a task from `title`, `owner_id`, and optional `due_date`.
- `GET /tasks/{task_id}?actor_user_id=...` returns a task for an actor.
- `GET /tasks?owner_id=...` lists tasks for an owner.
- `PATCH /tasks/{task_id}/status` updates a task status.
- `DELETE /tasks/{task_id}?actor_user_id=...` deletes a task for an actor.

Keep the API small and explicit. If you change behavior, explain why.
