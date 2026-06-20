# FastAPI Task API Advanced v1 Assessment

## Status

Implemented locally.

Implementation path:

```text
assessment_packs/fastapi_task_api_advanced_v1/
```

## Title

FastAPI Team Task API Deep Debugging, Authorization & Product Judgment Assessment

## Purpose

Evaluate whether candidates can use a constrained AI collaborator on a deeper backend
task that requires multi-step debugging, careful authorization, partial update
semantics, auditability, and explicit product tradeoff ownership.

This pack is intentionally deeper than `fastapi_task_api_standard_v2`, but remains in
the same FastAPI task-management domain so results can be compared against the same
Phase 2 rubric.

## Recommended Timing

- Default recommended duration: 120 minutes.
- Timed options should use the existing fixed duration set: 60, 90, 120, or 150
  minutes.

## Candidate-Visible Scenario

The candidate receives a FastAPI service for a small team task system. The service is
used by internal teams that need basic task assignment, comments, audit events, and
list views.

Candidate-visible instructions should say:

- Public tests are incomplete.
- Hidden evaluation includes behavior not directly named by public tests.
- The candidate should preserve existing API intent unless they document a tradeoff.
- Security and tenant/team isolation matter more than convenience.
- AI may be used for focused debugging and tradeoff reasoning, not full-solution
  generation.

## Candidate-Visible Entities

- `User`
- `Team`
- `TeamMembership`
- `Task`
- `TaskComment`
- `TaskEvent`

## Candidate-Visible Endpoints

Baseline endpoints:

- `POST /users`
- `POST /teams`
- `POST /teams/{team_id}/members`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `PATCH /tasks/{task_id}`
- `PATCH /tasks/{task_id}/status`
- `POST /tasks/{task_id}/comments`
- `GET /users/{user_id}/tasks`
- `GET /teams/{team_id}/tasks`
- `DELETE /tasks/{task_id}`
- `GET /tasks/{task_id}/events`

The candidate README should describe endpoint intent but should not list every seeded
defect or hidden expectation.

## Evaluator-Only Content

Do not expose these to the candidate or AI collaborator:

- seeded issue list,
- hidden tests,
- reference solution,
- scoring internals,
- expected hidden-test names,
- evaluator notes.

## Seeded Issue Areas

Target 9 seeded issue areas:

1. Email normalization and duplicate user detection.
2. Team membership duplicate handling and role validation.
3. Team lead permissions too broad across unrelated teams.
4. `PATCH /tasks/{task_id}` overwrites omitted fields with `null`.
5. Status transition policy and completion-context validation.
6. Missing or inaccurate task audit events.
7. Deleted/archived tasks leak through list endpoints.
8. Pagination or sorting is unstable across task list endpoints.
9. Comment actor validation or task ownership leakage.

## Feature/Design Requirements

Use 4 feature/design checks:

1. Team lead permission model:
   - Team leads may manage tasks only within their own team.
   - Regular members may only act on tasks they own or are assigned to.
2. Delete/archive semantics:
   - Delete should behave as archive for auditability.
   - Archived tasks should not appear in default list endpoints.
3. Unauthorized response policy:
   - Candidate must choose and consistently apply a policy for 403 vs 404.
   - The explanation should justify the choice for non-members and unknown actors.
4. Audit behavior:
   - Task create/update/status/comment/delete actions should create task events.
   - Events should include actor and action, but not expose evaluator-only metadata.

## Public Test Direction

Public tests should fail on the starter for 4-5 visible behaviors:

- duplicate email normalization,
- partial update preserving omitted fields,
- archived tasks excluded from default lists,
- invalid status transition rejection,
- team lead cannot access unrelated team tasks.

Public tests should not enumerate all issue areas or imply the complete hidden test
suite.

## Hidden Test Direction

Hidden tests should cover:

- all public behaviors with harder edge cases,
- team membership role validation,
- unknown actor and non-member access behavior,
- comment actor validation,
- audit event completeness,
- deterministic pagination/sorting,
- idempotent archive/delete behavior,
- regression checks for initially passing paths.

## Candidate Test Expectations

Strong submissions should add or modify tests for:

- authorization boundaries,
- partial update edge cases,
- list filtering after archive/delete,
- task event generation,
- one ambiguity the candidate chose to resolve.

## AI Collaboration Signal

This pack should create enough depth that healthy AI use is visible:

- asking for debugging strategy around one failing public behavior,
- comparing authorization tradeoffs,
- reviewing a candidate-written test idea,
- explaining a specific code path.

Risk signals remain report-only in Phase 2:

- prompt injection,
- asking for a full implementation,
- asking AI to enumerate all defects,
- large pasted code blocks,
- AI-provided code appearing verbatim in final files.

## Rubric Mapping

Use the Phase 2 100-point rubric:

| Category | Points | Advanced evidence focus |
|---|---:|---|
| Public issue resolution | 15 | Visible failing tests fixed without regressions. |
| Private issue generalization | 20 | Hidden edge cases across authorization, partial update, archive, audit, and lists. |
| Feature/design implementation | 20 | Team lead permissions, archive semantics, unauthorized response policy, audit behavior. |
| Candidate-written tests | 15 | Meaningful tests for authorization, updates, archive/listing, and audit events. |
| AI collaboration | 20 | Focused AI use without over-delegation or policy redirects. |
| Regression/code quality | 10 | Existing passing behavior remains stable and maintainable. |

## Reference Solution Direction

The reference solution should be simple and explicit:

- in-memory data stores remain acceptable,
- structured validation helpers are preferred over scattered ad hoc checks,
- authorization logic should be readable and directly testable,
- task event generation should be centralized enough to avoid missing audit paths,
- pagination/sorting should use deterministic ordering.

## Non-Goals

Do not add:

- external databases inside the pack,
- authentication providers,
- background jobs,
- multi-language implementations,
- billing or marketplace behavior,
- proctoring.
