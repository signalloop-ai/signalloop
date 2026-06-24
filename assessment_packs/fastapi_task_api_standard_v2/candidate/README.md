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

The embedded assistant is a constrained collaborator: it coaches you toward the answer and gives you code once you show you understand the approach. It is not an answer machine — but used well, it is genuinely helpful.

### How to get the most from it

- **Found a bug?** Say what's wrong and where ("delete_task never checks the task owner"). It confirms and shows you the small change to make.
- **Adding an enhancement or writing a test?** It asks a guiding question first. Answer it — once you describe your approach (the route and what to filter; or what a test should send and assert), it gives you the code. Engage with the question instead of asking it to "just do it."
- **Syntax or concept question?** Ask directly ("how do I raise a 409 in FastAPI?", "what does `model_dump(exclude_unset=True)` do?") — you get a straight answer.
- It can see the files you're working on, so refer to functions by name.
- If it replies with a question, that's the path forward — answering it is what unlocks the code. Don't give up after one Socratic question.

### Prompts that work vs. prompts that stall

| Instead of this… | Try this… |
| --- | --- |
| "What's wrong with my code?" / "Find all the bugs" | "I think `delete_task` doesn't check the owner — how do I block non-owners?" |
| "Give me the complete solution" / "Write all the tests" | "How do I raise a 409 in FastAPI?" — or, after describing your plan, "ok give me the code for that" |
| "Just write the due-date enhancement for me" | "For due dates I'd add a `due_date` field and reject past dates in `create_task` — does that sound right?" |
| Pasting a test and asking "make this pass" | "The duplicate-email test expects 409 but I get 201 — what should I check?" |
| "Should I return 403 or 404? You decide." | "What are the tradeoffs between 403 and 404 for a non-owner?" |

It will not enumerate every defect, write the whole solution, rewrite whole files, write your full test suite, reveal hidden tests, or make design decisions for you — those are the parts being assessed.

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
