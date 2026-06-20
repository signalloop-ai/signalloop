# SignalLoop Documentation

This directory is the source-of-truth documentation set for SignalLoop.

The original MVP Phase 1-12 plan is complete and remains under `execution/` as
historical implementation context. The active post-MVP workstream is Phase 2:
Assessment System Enhancement under `enhancements/phase-2-assessment-system/`.

## Reading order for coding agents

Before making implementation changes, read:

1. `AGENTS.md`
2. `CURRENT_STATE.md`
3. `docs/README.md`
4. `docs/architecture/technical-product-architecture-spec.md`
5. `docs/execution/coding-agent-execution-plan.md`
6. The active workstream file named in `CURRENT_STATE.md`

## Directory map

- `product/` - product requirements and scope.
- `architecture/` - MVP technical architecture and system boundaries.
- `execution/` - phase-by-phase implementation plan.
- `enhancements/` - active post-MVP enhancement workstreams.
- `assessment/` - assessment design and evaluation documentation.
  - `assessment/fastapi-task-api-advanced-v1.md` - planned advanced FastAPI pack
    specification; not implemented yet.
- `decisions/` - architecture decision records.
- `prompts/` - constrained AI collaborator policy.
- `reports/` - Engineering Evidence Report structure.
- `development/` - local setup and development notes.
- `deployment/` - pilot deployment notes for Render, Supabase, Clerk, and execution-runtime boundaries.

Work one phase or enhancement task at a time. Do not use planning docs as permission to
implement future scope early.
