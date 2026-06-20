# Phase 2 Product Scope

## Objective

Improve SignalLoop from a validated MVP flow into a stronger assessment system for
engineering hiring.

## Product Thesis

SignalLoop evaluates the human-AI engineering process, not just final code.

The report should help employers understand whether a candidate can:

- frame a realistic engineering task,
- use AI without over-delegating,
- verify output with tests and inspection,
- make safe and consistent design decisions,
- own the final implementation.

## Scope

Phase 2 includes:

- a common rubric for standard and advanced assessments,
- a versioned standard FastAPI assessment plan,
- a planned advanced FastAPI assessment,
- tighter AI collaborator policy,
- employer assessment configuration,
- optional time-boxed assessment flow,
- strict multi-tenant employer isolation based on Clerk user identity,
- candidate and employer UI enhancements,
- reporting updates with FAVO interpretation,
- LLM-assisted report scoring/review where deterministic checks are insufficient.

## Out Of Scope

Do not add:

- Kubernetes,
- enterprise SSO,
- ATS integration,
- video proctoring,
- marketplace,
- production billing,
- multi-language assessment support,
- broad analytics dashboards.

## Current MVP Baseline

The current pack remains:

```text
assessment_packs/fastapi_task_api_v1/
```

It should be treated as the MVP/pilot reference pack. Phase 2 standard implementation
should use a new versioned pack rather than mutating v1 after pilot usage.

## Priority Order

1. Assessment depth.
2. Strict employer isolation.
3. Timer.
4. Render/pilot UI polish.
5. Advanced pack documentation.
6. Advanced pack implementation later.
