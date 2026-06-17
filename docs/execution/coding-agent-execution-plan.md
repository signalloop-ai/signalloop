# SignalLoop Coding Agent Execution Plan

Version: 0.1
Status: Draft implementation playbook

## Purpose

This document tells coding agents how to implement SignalLoop MVP phase by phase.

Use this together with:

- `AGENTS.md`
- `CURRENT_STATE.md`
- `docs/architecture/technical-product-architecture-spec.md`
- the current phase file under `docs/execution/phases/`

## Global rule

Work one phase at a time. Do not skip ahead.

## Phase list

1. Phase 01 — Repository setup
2. Phase 02 — Assessment pack
3. Phase 03 — Backend core data model
4. Phase 04 — Candidate attempt lifecycle
5. Phase 05 — Execution worker
6. Phase 06 — Candidate workspace UI
7. Phase 07 — AI collaborator
8. Phase 08 — Final submission and hidden evaluation
9. Phase 09 — Engineering Evidence Report
10. Phase 10 — Employer portal
11. Phase 11 — Pilot hardening
12. Phase 12 — Documentation and handoff

## Completion protocol

After each phase:

1. Update `CURRENT_STATE.md`.
2. Mark completed tasks in the phase file.
3. Run tests.
4. Summarize files changed.
5. Record new architecture decisions as ADRs where needed.

## Do not implement yet

Unless explicitly requested, do not build video proctoring, ATS integration, Kubernetes deployment, enterprise SSO, billing, or multi-assessment marketplace.
