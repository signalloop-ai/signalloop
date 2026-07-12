# 01 - Product Requirements

Status: Phase 6A governance requirements implemented; composition requirements deferred.

## Objective

Create a dynamic assessment builder that assembles role-level assessments from approved
questions.

Phase 6 should make SignalLoop feel adaptive without giving each candidate for the same role a
different scored assessment.

## Employer inputs

The employer defines the role assessment using fields that map naturally to hiring decisions:

- company name,
- company website optional,
- engineering team size,
- India/global hiring context,
- hiring area,
- years of experience expected,
- JD / role requirement text or upload,
- cognitive areas to emphasize,
- target duration.

Initial hiring areas:

- Backend,
- Frontend,
- Full stack,
- ML/AI,
- Data engineering,
- DevOps,
- Security,
- Tech support.

Initial cognitive areas:

- logical reasoning,
- chaos tolerance,
- debugging,
- systems thinking,
- trade-off judgment,
- communication quality,
- critical AI usage,
- critical thinking,
- creative problem solving.

## Role-based assessment rule

The scored assessment is determined by the role definition:

```text
company context + hiring area + JD + years of experience + cognitive areas + target duration
```

Candidate resume is not an input to scored question selection.

The same role assessment blueprint should be reusable across candidates so employers can compare
candidates against the same evidence surface.

## Candidate resume use

Candidate resume may be attached for:

- JD/resume skill overlap,
- missing required skills,
- candidate extra skills,
- follow-up interview probes,
- report caveats,
- interviewer notes.

Candidate resume must not:

- select or remove scored questions,
- change the scoring rubric,
- change time allocation for a candidate,
- cause different candidates for the same role to receive different scored assessments by
  default.

## Question types

Question type is primarily a system planning dimension, not a required employer input.

Initial supported types:

- coding,
- technical concept,
- system design,
- communication / final explanation,
- trade-off judgment.

Future types:

- data reasoning,
- security review,
- ML/AI design,
- standalone debugging.

Role and question type are separate concepts. For example, an ML/AI role can use:

```text
question type: system design
role tag: ML/AI
prompt: Design a batch inference pipeline with monitoring and rollback.
```

## Coding question behavior

A coding question is one approved question that may contain a full coding package:

- prompt,
- starter files,
- public tests,
- optional hidden tests,
- seeded issues,
- enhancements,
- rubric,
- expected evidence.

The existing candidate coding interface should be reused for coding questions. Phase 6 does not
require hidden tests for every coding question; public tests plus rubric evidence are acceptable
for simpler coding questions.

Coding questions have two review states:

```text
content review: draft / needs_review / approved / rejected
package review: missing / draft / ready_for_review / package_approved / rejected
```

For non-coding questions, content approval is enough for assessment readiness. For coding
questions, assessment readiness requires both approved content and an approved coding package.

Coding packages can come from:

- an existing SignalLoop assessment pack,
- source-imported starter code/tests when the source license and quality allow it,
- human-authored starter code/tests,
- AI-drafted starter code/tests that are human reviewed and validated.

Phase 6A treats the current FastAPI Standard and Advanced packs as two separate coding
questions with existing package references. New Node.js/TypeScript and other coding questions
may be content-approved before they are assessment-ready, but they must remain unavailable to
the employer builder until their package is approved.

## Employer review and control

The system generates a role-level assessment blueprint. The employer can:

- review selected questions,
- review coverage by role, skill, cognitive area, difficulty, and time,
- swap a question for another approved question in the same required slot,
- regenerate the blueprint,
- change upstream criteria and regenerate.

The employer cannot silently remove a required slot from the generated blueprint.

Example:

```text
Required slots:
- coding/debugging - 35 minutes
- system design/trade-off - 15 minutes
- communication/final explanation - 10 minutes
```

Allowed:

```text
replace coding question A with coding question B
replace system design question A with system design question B
```

Not allowed in Phase 6 MVP:

```text
delete coding and create a 60-minute communication-only assessment
```

## Super admin product requirements

Super admin manages the approved question bank:

- create a question manually,
- generate an AI draft question,
- edit prompt, metadata, time, difficulty, and rubric,
- review imported public-source questions,
- approve, reject, deprecate, or revise questions.

Only approved questions can be selected by employer-facing assessment builders.

## Public-source ingestion

Phase 6 should support controlled public-source ingestion from a curated allowlist.

This is not an employer feature and not arbitrary web scraping. Product/engineering agrees on
safe reusable sources, then an offline/admin-operated ingestion pipeline extracts candidate
questions, classifies metadata, and stores them as reviewable drafts.

All imported questions require provenance and review before activation.

## Non-goals

- Fully automatic company research.
- Free-form scraping from arbitrary sources.
- Unreviewed AI-generated scored assessments.
- Candidate-specific scored assessments.
- ATS integration.
- Marketplace-style assessment publishing.
- A separate custom runtime engine for every question type.
