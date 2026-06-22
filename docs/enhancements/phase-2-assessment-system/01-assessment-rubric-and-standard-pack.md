# 01 - Assessment Rubric And Standard Pack

Status: completed locally.

## Goal

Replace the MVP scoring model with a common Phase 2 rubric that works for both standard
and advanced assessments.

## Common Rubric

| Category | Points (standard v2) | Points (advanced v1) | Evaluation mode |
|---|---:|---:|---|
| Public issue resolution | 15 | 15 | Automated public tests |
| Private issue generalization | 20 | 15 | Automated hidden tests |
| Feature/design implementation | 20 | 25 | Automated tests (combined public + hidden) |
| Candidate-written tests | 15 | 15 | Automated heuristics |
| AI collaboration | 15 | 15 | AI logs, policy classifier, violation tiers |
| Regression/code quality | 15 | 15 | Automated regression |
| Total | 100 | 100 | |

Note: weights were rebalanced in the June 2026 redesign. AI collaboration decreased from
the originally planned 20 to 15; regression/code quality increased from 10 to 15.
Pack-specific overrides are in `DEFAULT_PACKS` in `attempts.py`.

## Changes From MVP Rubric

- Public issue score decreases from 20 to 15.
- Hidden/private score decreases from 30 to 20.
- AI collaboration increases from 10 to 20.
- Markdown-heavy explanation score is replaced by feature/design implementation.
- Regression/code quality becomes 10 points:
  - 5 automated regression,
  - 5 evaluator/LLM-assisted code quality.

## Standard Pack Versioning

Do not mutate `fastapi_task_api_v1` into the Phase 2 standard pack.

Created a new standard pack:

```text
assessment_packs/fastapi_task_api_standard_v2/
```

Used v1 as baseline/source material. Keep v1 as historical MVP/pilot reference.

## Standard Pack Design Direction

The standard pack should remain approachable but require judgment:

- realistic FastAPI internal task API,
- 5-7 seeded issue areas,
- explicit ambiguity in authorization/status policy,
- candidate-written tests encouraged,
- AI collaboration useful but not sufficient,
- default recommended duration: 60 minutes.

## Feature/Design Implementation Principle

Do not require long Markdown explanations.

Candidate-facing guidance should say:

> Some requirements intentionally require engineering judgment. You will be evaluated not
> only on whether the feature works, but also on whether your design is safe,
> consistent, simple, maintainable, and well-tested. You do not need to write a long
> design document. Your implementation and tests should make your choices clear.

Evaluation should infer design choices from:

- code behavior,
- endpoint consistency,
- edge-case handling,
- tests added,
- hidden test results,
- optional short notes only if present.

## Candidate-Written Test Heuristics

Improve scoring beyond "test files touched."

Signals:

- number of added test functions,
- meaningful HTTP assertions,
- negative and edge-case tests,
- multi-user/authorization tests,
- status transition tests,
- delete/idempotency tests,
- tests covering feature/design behavior,
- tests that would catch regressions.

Positive examples:

- `assert response.status_code`,
- 400/403/404/409/422 checks,
- `actor_user_id` or multiple users,
- duplicate, blank, and invalid inputs,
- status transition flows,
- delete/idempotency behavior.

## Implementation Notes

Completed local implementation updated:

- assessment pack files,
- `DEFAULT_PACKS`,
- scoring/report code,
- tests for rubric scoring,
- evaluator docs.

## Local Validation

- `cd assessment_packs/fastapi_task_api_standard_v2/candidate && uv run pytest`
  - expected starter result: 2 passed, 4 failed.
- `cd assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution && uv run pytest -c pyproject.toml --rootdir=. ../../candidate/tests`
  - 6 passed.
- `cd assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution && uv run pytest -c pyproject.toml --rootdir=. ../hidden_tests`
  - 7 passed.
- `cd apps/api && uv run pytest`
  - 45 passed.
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`
- `cd apps/web && npm run typecheck`
- `cd apps/web && npm run test:e2e`
