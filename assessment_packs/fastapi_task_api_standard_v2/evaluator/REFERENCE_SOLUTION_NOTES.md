# Reference Solution Notes

These notes are evaluator-only. Do not expose them to candidates or the AI collaborator.

The included reference solution uses the same public API shape as the starter code and keeps the in-memory implementation. It intentionally avoids adding persistence, authentication frameworks, or external services.

## Behavioral choices

- Duplicate email handling: emails are stripped, lowercased, and unique. Duplicate creates return `409`.
- Task title validation: titles are stripped and blank titles fail request validation with `422`.
- Status policy: tasks must move `TODO -> IN_PROGRESS -> DONE`; direct `TODO -> DONE` and reopening `DONE -> TODO` return `409`.
- Priority handling: task priority defaults to `MEDIUM`, strips whitespace, uppercases valid values, and rejects unknown values with `422`.
- Unauthorized access policy: known users who do not own a task receive `403`; unknown actors receive `404`.
- Delete policy: only the owner can delete a task. Deleted tasks are no longer readable and repeat deletes return `404`.

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

The starter code is expected to fail selected public tests. A correct solution should pass public tests and hidden evaluator tests.
