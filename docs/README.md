# SignalLoop Documentation

This directory is the source-of-truth documentation set for the SignalLoop MVP.

## Reading order for coding agents

Before making implementation changes, read:

1. `AGENTS.md`
2. `CURRENT_STATE.md`
3. `docs/README.md`
4. `docs/architecture/technical-product-architecture-spec.md`
5. `docs/execution/coding-agent-execution-plan.md`
6. `docs/execution/phases/README.md`
7. The current phase file under `docs/execution/phases/`

## Directory map

- `product/` - product requirements and scope.
- `architecture/` - MVP technical architecture and system boundaries.
- `execution/` - phase-by-phase implementation plan.
- `assessment/` - assessment design and evaluation documentation.
- `decisions/` - architecture decision records.
- `prompts/` - constrained AI collaborator policy.
- `reports/` - Engineering Evidence Report structure.
- `development/` - local setup and development notes.
- `deployment/` - pilot deployment notes for Render, Supabase, Clerk, and execution-runtime boundaries.

Work one phase at a time. Do not use later-phase docs as permission to implement future scope early.
