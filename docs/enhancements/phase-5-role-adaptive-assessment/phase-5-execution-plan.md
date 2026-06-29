# Phase 5 Execution Plan

Status: MVP implementation complete locally.

## Objective

Implement the Role-Adaptive Assessment System as an additive MVP workstream.

The first implementation should prove the adaptive planning loop without
expanding assessment content or changing scoring:

```text
pasted JD/resume -> skill map -> blueprint -> employer approval -> invite ->
existing assessment flow -> adaptive report context
```

## Task 1 - Taxonomy and module coverage

Status: complete.

Create static taxonomy files and loader utilities.

Deliverables:

- `skills.json`
- `module_coverage.json`
- taxonomy loader/validator,
- tests that module coverage references valid skill IDs,
- explicit coverage for Standard FastAPI v2 and Advanced FastAPI v1.

Validation:

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py`
  -> 6 passed,
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 267 passed, 51 skipped,
- malformed taxonomy fixtures fail loudly.

## Task 2 - Adaptive data model

Status: complete.

Add persistence for role profiles, candidate profiles, assessment blueprints,
and attempt-blueprint links.

Deliverables:

- SQLAlchemy models,
- Alembic migration,
- Pydantic schemas,
- employer-scoped CRUD helpers,
- tests for employer isolation.

Validation:

- `DATABASE_URL=sqlite:////tmp/signalloop_phase5_adaptive_migration_2.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head`
  -> passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 272 passed, 51 skipped.
- adaptive records cannot cross employer boundaries.

## Task 3 - Skill extraction and matching

Status: complete.

Implement the first matching pipeline.

Deliverables:

- JD extraction from pasted text,
- resume extraction from pasted text,
- taxonomy normalization using aliases,
- classification into overlap/gap/extra/unsupported/unmapped,
- deterministic fallback when LLM is unavailable.

Validation:

- realistic JD/resume API e2e test covers overlap, unsupported required skills,
  and follow-up probe generation.
- manual fixture sweep covers current FastAPI, future planned assessment, and
  out-of-scope role classification.
- no unsupported skill is marked directly assessed.

## Task 4 - Blueprint generation

Status: complete.

Generate draft blueprints from role/candidate profiles and module coverage.

Deliverables:

- pack selection rules for Standard vs Advanced FastAPI,
- rationale generation,
- follow-up probe generation,
- caveat generation,
- `draft` / `approved` / `used` status transitions,
- tests for standard selection, advanced selection, unsupported-heavy roles,
  and resume-specific probes.

Validation:

- blueprint references valid Standard/Advanced FastAPI pack slugs.
- future assessment blueprints are saved but not invite-ready.
- non-roadmap roles fail with a clear out-of-scope response.
- resume claims do not change the core scored assessment for the same role.

## Task 5 - Employer adaptive API

Status: complete.

Add employer endpoints for the adaptive builder.

Deliverables:

- create/read role profile,
- create/read candidate profile,
- generate blueprint,
- approve blueprint,
- create invite from approved blueprint.

Validation:

- Clerk employer auth enforced through the existing employer dependency.
- existing quick invite API unchanged.
- invite from blueprint creates an attempt with `blueprint_id`.
- candidate endpoints do not expose role/resume/blueprint details.

## Task 6 - Employer adaptive UI

Status: complete.

Add an optional adaptive builder path beside the quick assessment flow.

Deliverables:

- entry point in Assessments view,
- JD/team context step,
- candidate email/resume step,
- skill map review,
- blueprint review,
- approve and send invite.

Validation:

- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed with 4 known warnings.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e -- --workers=1` -> 33 passed, 2 skipped.

## Task 7 - Report adaptive context

Status: complete.

Extend report generation and report UI for blueprint-backed attempts.

Deliverables:

- adaptive context in persisted report JSON,
- report UI section shown only when blueprint exists,
- follow-up probes included in report,
- caveats for unsupported skills.

Validation:

- existing non-blueprint reports remain supported.
- blueprint-backed reports show role context and skill coverage.
- unsupported skills are caveated, not scored.

## Task 8 - Documentation and handoff

Status: complete for MVP implementation.

Update current state and operational docs after implementation.

Deliverables:

- `CURRENT_STATE.md` updated,
- `docs/development/changes.md` entry,
- architecture spec updated if implementation changes source-of-truth behavior,
- tests/commands recorded.

Validation commands are recorded below and in `docs/development/changes.md`.

Final validation before commit:

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 288 passed, 51 skipped.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q` -> 27 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run test:e2e -- --workers=1` -> 33 passed, 2 skipped.

## MVP completion criteria

- Employer can paste JD and optional resume, or upload TXT/MD, DOCX, or
  text-based PDF files for extraction.
- System extracts and classifies skills.
- System recommends Standard or Advanced FastAPI with clear rationale.
- Employer approves a blueprint and sends an invite.
- Candidate completes the normal SignalLoop assessment.
- Employer report includes adaptive context.
- Quick assessment path remains unchanged.
- API and web test suites pass for affected areas.

## Explicit non-goals

- New assessment packs.
- Generated hidden tests.
- Dynamic scoring weights.
- Full document parsing parity for every PDF/DOCX variant. MVP upload support is
  text extraction only; scanned PDFs/OCR are out of scope.
- Candidate-specific scored core tasks for the same role.
- Taxonomy admin UI.
- ATS integration.
