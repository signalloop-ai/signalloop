# Phase 5: Role-Adaptive Assessment System

Status: MVP implementation complete locally.

## Purpose

Phase 5 adds an adaptive planning layer before invite creation. Employers can
paste a job requirement and, optionally, a candidate resume. SignalLoop maps both
inputs into a standard skill taxonomy, recommends an assessment blueprint, and
asks the employer to review and approve it before sending the invite.

The Phase 5 MVP changes **how SignalLoop selects and explains an assessment**.
It does not change the candidate workspace, AI collaborator safety boundaries,
assessment scoring rules, hidden-test handling, or evidence-capture model.

## Product principle

For the MVP, the role/JD determines the comparable core assessment. Candidate
resume data influences the skill map, rationale, report interpretation, and
follow-up probes, but it does not give different candidates for the same role a
different scored coding task by default.

```text
Role/JD -> core assessment blueprint
Resume  -> claims to validate, caveats, follow-up probes
```

This preserves comparability while still making the report candidate-aware.

## What Phase 5 delivers

### 1. Paste-based intake

Employers can create an adaptive blueprint from:

- role title,
- role family,
- seniority,
- pasted JD / job requirements,
- pasted team or domain context,
- expected AI usage,
- optional pasted candidate resume.

File upload and resume parsing from PDF/DOCX are out of scope for v1.

### 2. Standard skill taxonomy

SignalLoop keeps a versioned taxonomy of engineering skills and maps both JD
requirements and resume claims into it. The taxonomy is broad enough to support
the roadmap, but only a subset is assessable by current packs.

Skills are classified as:

- required overlap,
- required gap,
- candidate extra,
- unsupported required,
- unsupported claimed.

### 3. Assessment blueprint recommendation

The system recommends the best supported assessment from the current pack
registry. For v1, this means Standard FastAPI v2 or Advanced FastAPI v1.

The blueprint shows:

- selected assessment pack,
- difficulty and timing,
- evaluator feedback mode,
- directly tested skills,
- partially tested skills,
- unsupported/not-tested skills,
- rationale,
- follow-up probes.

Unsupported areas remain visible as caveats and follow-up interview prompts. The
system must not imply those skills were evaluated by the coding score.

## Implementation status

- Static taxonomy and module coverage live in `apps/api/signalloop_api/assessment_taxonomy/`.
- Adaptive persistence is implemented with role profiles, candidate profiles,
  assessment blueprints, and nullable attempt blueprint links.
- Deterministic skill extraction/matching and blueprint recommendation are implemented.
- Employer adaptive API endpoints are available under `/employer/adaptive/*`.
- Employer UI includes an optional adaptive builder beside the quick assessment flow.
- Blueprint-backed reports include role-adaptive context, coverage, caveats, and
  follow-up probes.
- Realistic JD/resume API e2e coverage is in `apps/api/tests/test_adaptive_assessment.py`.
- Manual copy-paste fixtures for product QA live in `manual-test-fixtures.md`.

### 4. Employer approval

The adaptive builder is an optional path beside the existing quick assessment
flow. Employers review the skill map and blueprint before creating an invite.

The existing quick assessment flow remains available.

### 5. Report additions

Attempts created from an adaptive blueprint add a report section covering:

- role context,
- skill map,
- blueprint rationale,
- directly tested skills,
- partially tested skills,
- unsupported skills,
- resume claims probed,
- suggested follow-up questions.

Regular invites without a blueprint continue to use the existing report UI.

## Non-goals

- No arbitrary LLM-generated scored assessments.
- No dynamic hidden-test generation.
- No scoring-rule changes.
- No AI collaborator boundary changes.
- No PDF/DOCX resume parsing.
- No ATS integration.
- No new external services.
- No candidate-specific core assessment variation for the same role.
- No admin-managed taxonomy UI.
- No support for frontend, infra, data, ML, or system-design assessments beyond
  taxonomy and roadmap representation.

## Planned task order

1. `01-product-requirements.md` - adaptive builder requirements and MVP scope.
2. `02-skill-taxonomy-and-matching.md` - taxonomy shape, skill classification,
   and initial skill set.
3. `03-blueprint-generation.md` - blueprint object, selection rules, LLM role,
   and examples.
4. `04-architecture-and-data-model.md` - new backend concepts, persistence, and
   API direction.
5. `05-employer-ux-and-reporting.md` - employer flow and adaptive report
   additions.
6. `phase-5-execution-plan.md` - completed implementation order and validation.

## Deployment notes

Phase 5 should be additive. Existing invite creation, assessment attempts,
reports, and candidate links must continue to work when no blueprint is present.
