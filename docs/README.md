# SignalLoop Documentation

This directory is the source-of-truth documentation set for SignalLoop.

The original MVP Phase 1-12 plan is complete and remains under `execution/` as
historical implementation context. The latest completed post-MVP workstream is
Phase 5: Role-Adaptive Assessment System under
`enhancements/phase-5-role-adaptive-assessment/`.

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
  - `assessment/fastapi-task-api-advanced-v1.md` - advanced FastAPI pack specification.
    Implemented at `assessment_packs/fastapi_task_api_advanced_v1/`.
- `design/` - UI design language. `calibr-design-language.md` is the dark design system
  (tokens, typography, component patterns) shared by the candidate, employer, and admin UIs.
- `decisions/` - architecture decision records.
- `prompts/` - constrained AI collaborator policy.
- `reports/` - Engineering Evidence Report structure.
- `development/` - local setup and development notes.
- `deployment/` - pilot deployment notes for Render, Supabase, Clerk, and execution-runtime
  boundaries, plus the production execution-isolation plan (`production-isolation-plan.md`).
- `retrospectives/` - design-journey write-ups. `ai-collaborator-journey.md` records how the
  AI collaborator evolved into the two-component, progressive-disclosure design (blog-ready).

Work one phase or enhancement task at a time. Do not use planning docs as permission to
implement future scope early.
