# FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment - Standard v2

## Scenario

The team used an AI assistant to generate a first version of an internal task-management API. The API is being prepared for a limited beta with internal employees and team leads.

The product manager wants the beta to be safe, predictable, and easy to debug. Public tests are incomplete. Some behavior is intentionally under-specified. Where requirements are ambiguous, make a reasonable decision and implement it consistently.

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

Debug and harden the API in `task_api/`.

You should:

- Run the public tests.
- Inspect the implementation.
- Fix behavior you believe is unsafe, invalid, or inconsistent.
- Add or update candidate tests for the behavior you change.
- Be ready to summarize what you changed, what tradeoffs you chose, and how you verified it in the SignalLoop submission review.

Two areas intentionally require judgment:

- Unauthorized access behavior: choose whether inaccessible resources should return `403` or `404`.
- Status transition policy: choose whether tasks can move directly from `TODO` to `DONE` or must move through `IN_PROGRESS`.
- Priority handling: decide how to normalize and validate task priority values while preserving a simple API.

Priority is part of the beta triage workflow. Tasks should expose a `priority` field using `LOW`, `MEDIUM`, or `HIGH`. If no priority is supplied, use a safe default.

## AI collaborator policy

The embedded assistant is a constrained collaborator. You may ask it to explain selected code, explain public test output, discuss one candidate-identified issue, or suggest general debugging approaches.

Do not ask it to enumerate every defect, provide a full solution, rewrite whole files, generate your final explanation, infer hidden tests, or provide issue-by-issue patches.

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
- `POST /tasks` creates a task from `title`, `owner_id`, and optional `priority`.
- `GET /tasks/{task_id}?actor_user_id=...` returns a task for an actor.
- `PATCH /tasks/{task_id}/status` updates a task status.
- `DELETE /tasks/{task_id}?actor_user_id=...` deletes a task for an actor.

Keep the API small and explicit. If you change behavior, explain why.
