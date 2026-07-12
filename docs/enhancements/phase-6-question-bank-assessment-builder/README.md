# Phase 6 - Question Bank Assessment Builder

Status: Phase 6A governance foundation complete; question-level adaptive composition is future work.

## Completed boundary

Phase 6A implements the governance foundation for future question-level composition:

- curated source and provenance metadata,
- reviewable question records,
- AI-assisted and imported draft creation,
- content and coding-package approval states,
- Super Admin review and inventory management.

The question bank is not connected to employer assessment creation, candidate delivery, or
evidence-report scoring. It should not be presented as a usable question-level adaptive builder.

## Future problem statement

Future work may turn Phase 5 guided role matching into a role-based assessment composer backed by
an approved, calibrated question bank.

The core product shift:

```text
role/company/JD/cognitive areas/duration
-> approved question bank
-> role-level assessment blueprint
-> employer review and same-slot swaps
-> candidate assessment
-> AI-assisted evidence report
```

## Product principles

- The scored assessment is role-adaptive, not candidate-resume-adaptive.
- Candidate resume text must not select scored questions for a role.
- Resume text may drive skill gaps, follow-up probes, interviewer notes, and report context.
- Only approved questions can be used in real scored assessments.
- Employers can swap questions within required slots; they cannot silently remove required
  coverage from a generated blueprint.
- The same constrained AI helper model applies across coding, design, judgment, and
  communication questions.
- AI scoring is evaluator assistance. It should produce rubric-based draft scores and evidence
  notes that can be reviewed or overridden.

## Phase 6 documents

- `01-product-requirements.md` - product scope, inputs, non-goals, and user flows.
- `02-approved-question-bank.md` - question schema, statuses, source paths, and review rules.
- `03-role-based-assessment-builder.md` - blueprint assembly, employer review, swap rules, and
  resume boundary.
- `04-ai-helper-and-scoring.md` - shared AI safety model and AI-assisted scoring rules.
- `05-source-allowlist.md` - draft external source approval list for public-source ingestion.
- `phase-6-execution-plan.md` - implementation tasks and validation plan.

## Release boundary

Phase 6A complete:

- Approved source allowlist captured in docs and seed metadata.
- Question bank data model and migration.
- Seed draft endpoint for initial reviewable questions.
- Super Admin question-bank review page.
- Super Admin can edit metadata, approve, and reject draft questions.

Deferred question-level adaptive scope:

- Role-based assessment blueprint generation from approved questions.
- Employer review with same-slot question swaps.
- Candidate experience for coding and written-response question types.
- AI-assisted draft scoring for every supported question type.

Not included:

- Fully automatic company research.
- Free-form web scraping from arbitrary URLs.
- Candidate-specific scored assessments.
- A separate execution engine for every question type.
- Employer removal of required blueprint slots.
- Unreviewed AI-generated scored questions.

## Relationship to Phase 5

Phase 5 proved:

```text
JD/resume -> skill map -> Standard/Advanced FastAPI blueprint -> invite
```

Phase 6 generalizes this into:

```text
role/company/JD/cognitive requirements -> approved questions -> assessment blueprint
```

The Phase 5 resume boundary remains: resume is context for gaps and follow-ups, not the source
of per-candidate scored task variation.
