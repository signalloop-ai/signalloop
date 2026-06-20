# Phase 2 Execution Plan

Status: planning active.

## Global Rule

Work one task at a time. Do not implement later task scope early.

## Task 1: Documentation And Navigation

Create Phase 2 enhancement docs and update navigation files:

- `AGENTS.md`
- `CURRENT_STATE.md`
- `README.md`
- `docs/README.md`
- `docs/architecture/technical-product-architecture-spec.md`

No product code changes.

## Task 2: Rubric And Standard Pack Specification

Status: completed locally.

Defined the new common rubric and created:

```text
assessment_packs/fastapi_task_api_standard_v2/
```

Do not modify `fastapi_task_api_v1` as the canonical Phase 2 standard pack.

## Task 3: AI Collaborator Policy Tightening

Status: completed locally.

Updated policy docs and implementation so the AI can compare tradeoffs but cannot
choose the assessment design for the candidate.

## Task 4: Employer Assessment Configuration

Status: completed locally.

Add employer configuration fields for:

- assessment type: Standard or Advanced,
- timing mode: untimed or timed,
- duration: fixed options.

Advanced is implemented and available for invite creation.

## Task 5: Time-Boxed Assessment Flow

Status: completed locally.

Implement timer persistence, candidate countdown, expiry behavior, backend enforcement,
and report time metadata.

Timed attempts start only when the candidate accepts the rules. Manual submissions are
recorded as `manual`; expired attempts are recorded as `auto_expired`.

## Task 6: Multi-Tenant Employer Isolation

Status: completed locally.

Implemented strict employer data isolation before expanding external pilot usage:

- web sends Clerk session token to the API,
- API verifies Clerk identity,
- API maps attempts to the current Clerk user,
- attempt lists and reports are scoped to the current employer,
- tests prove employer A cannot access employer B attempts or reports.

Use Clerk user identity for Phase 2. Do not introduce Clerk organizations unless
explicitly requested later.

## Task 7: Advanced Assessment Pack Specification

Status: completed locally.

Document the advanced FastAPI pack in detail before implementation.

Implementation later should create:

```text
assessment_packs/fastapi_task_api_advanced_v1/
```

The current design spec is `docs/assessment/fastapi-task-api-advanced-v1.md`.
The implementation exists at `assessment_packs/fastapi_task_api_advanced_v1/`, and
employers can select Standard or Advanced during invite creation.

## Task 8: UI Enhancements

Status: completed locally.

Improve employer and candidate surfaces for assessment selection, timer state, progress
feedback, and report readability.

The candidate workspace now uses structured Submission Review prompts and a final
confirmation modal. The report page renders timing metadata, native score/test bars,
FAVO-style interpretation, feature/design summary, and AI integrity risk.

## Task 9: Reporting And FAVO Updates

Status: completed locally, except external LLM-assisted review execution.

Update report generation with:

- new score categories,
- LLM-assisted review where needed,
- FAVO interpretation,
- richer AI collaboration evidence,
- feature/design implementation section.

The report generator now emits deterministic Phase 2 sections for structured
Submission Review, FAVO, AI integrity risk, feature/design implementation, and LLM
review status. External LLM-assisted review remains disabled until a bounded prompt and
safety boundary are added.

## Completion Protocol

After each task:

1. Run relevant checks.
2. Update `CURRENT_STATE.md`.
3. Append non-trivial findings to `docs/development/changes.md`.
4. Update architecture docs or ADRs if decisions changed.
5. Summarize files changed and next task.
