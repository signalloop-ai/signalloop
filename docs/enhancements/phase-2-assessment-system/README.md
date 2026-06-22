# Phase 2: Assessment System Enhancement

Status: **complete** — all 8 planned tasks implemented, validated locally and on Render.

## Purpose

Phase 2 improves the assessment system quality now that the MVP product flow has been
validated locally and in hosted pilot infrastructure.

The goal is to make SignalLoop better at evaluating human-AI engineering work:

- stronger assessment depth,
- a shared rubric for standard and advanced assessments,
- tighter AI collaborator boundaries,
- employer assessment configuration,
- optional timed assessments,
- strict Clerk-user employer isolation,
- better candidate/employer UI,
- report updates with FAVO interpretation and richer collaboration evidence.

## Non-Goals For The First Phase 2 Task

The first task is documentation and planning only. Do not implement:

- scoring changes,
- timer behavior,
- new assessment packs,
- standard pack changes,
- advanced pack code,
- UI changes,
- report-generation code changes.

## Planned Task Order

1. `01-assessment-rubric-and-standard-pack.md`
2. `02-ai-collaborator-policy-tightening.md`
3. `03-employer-assessment-configuration.md`
4. `04-time-boxed-assessment-flow.md`
5. `08-multi-tenant-employer-isolation.md`
6. `05-advanced-assessment-pack.md`
7. `06-ui-enhancements.md`
8. `07-reporting-and-favo-updates.md`

## Assessment Pack Versioning Decision

Keep `assessment_packs/fastapi_task_api_v1/` as the historical MVP/pilot reference.

When Phase 2 implementation changes the standard assessment content, create a new pack
instead of mutating v1 in place:

```text
assessment_packs/fastapi_task_api_standard_v2/
```

Use v1 as source material, but keep v2 distinct so already-run pilot results remain
comparable and auditable.

Later, create the advanced pack as:

```text
assessment_packs/fastapi_task_api_advanced_v1/
```

Do not implement either pack in the documentation-only task.
