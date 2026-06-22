# 05 - Advanced Assessment Pack

Status: completed locally.

## Goal

Define a deeper FastAPI assessment that requires stronger human-AI collaboration,
multi-step debugging, and product judgment.

Do not implement this pack until standard v2 and timer foundations are planned and/or
started.

## Pack Path

Planned implementation path:

```text
assessment_packs/fastapi_task_api_advanced_v1/
```

Detailed design spec:

```text
docs/assessment/fastapi-task-api-advanced-v1.md
```

## Domain

Same broad FastAPI task-management domain, with deeper behavior.

Potential entities:

- User,
- Team,
- TeamMembership,
- Task,
- TaskComment,
- TaskEvent / AuditEvent.

Potential endpoints:

- `POST /users`,
- `POST /teams`,
- `POST /teams/{team_id}/members`,
- `POST /tasks`,
- `GET /tasks/{task_id}`,
- `PATCH /tasks/{task_id}`,
- `PATCH /tasks/{task_id}/status`,
- `POST /tasks/{task_id}/comments`,
- `GET /users/{user_id}/tasks`,
- `GET /teams/{team_id}/tasks`,
- `DELETE /tasks/{task_id}`,
- `GET /tasks/{task_id}/events`.

## Advanced Characteristics

- 8-10 seeded issue areas,
- 3-5 feature/design requirements,
- more ambiguous product tradeoffs,
- more multi-step debugging,
- stronger candidate judgment,
- stronger AI collaboration signal,
- default recommended duration: 120 minutes.

## Potential Issue Areas

- duplicate email normalization,
- team membership duplicate/invalid role,
- team lead access too broad,
- PATCH task overwrites omitted fields with null,
- status transition and completion-context behavior,
- audit events missing/inaccurate,
- deleted/archived tasks leak through list endpoints,
- pagination/sorting unstable,
- error behavior inconsistent across endpoints,
- comment actor or ownership issue.

## Potential Feature/Design Requirements

- team lead permissions,
- delete/archive semantics,
- unauthorized response behavior,
- audit behavior,
- partial update behavior.

## Implementation Notes

Implemented locally:

- candidate starter app,
- candidate README,
- public tests,
- evaluator hidden tests,
- reference solution,
- reference notes,
- scoring rubric,
- manual evaluation form,
- API pack registry and employer invite selection.

## Local Validation

- Advanced starter public tests using the existing assessment virtualenv:
  `1 passed, 5 failed` on unmodified starter code.
- Advanced reference solution against public tests:
  `6 passed`.
- Advanced reference solution against hidden tests:
  `7 passed`.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 55 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- --workers=1`
  -> 2 passed, 1 skipped.
