# Phase 6 Execution Plan

Status: Phase 6A governance foundation complete; Tasks 4-9 are deferred future work.

## Objective

Implement the Question Bank Assessment Builder as an additive post-MVP workstream.

Phase 6 should introduce:

```text
approved question bank
-> role-based blueprint assembly
-> employer review and same-slot swaps
-> mixed coding/written assessment delivery
-> AI-assisted scoring with review
```

## Task 1 - Question taxonomy and data model

Status: complete for Phase 6A foundation.

Deliverables:

- question type enum,
- role/hiring area taxonomy,
- cognitive area taxonomy,
- question status enum,
- database models for questions, versions, sources, rubrics, and tags,
- migration,
- API schemas.

Validation:

- migration `0010_add_question_bank` adds `question_sources` and `question_bank_questions`,
- approved questions cannot be edited in place through the admin API,
- question responses include source/provenance metadata.

## Task 2 - Super admin question bank UI

Status: complete for Phase 6A foundation.

Deliverables:

- question list/filter UI,
- create/edit question form,
- AI-generate draft action,
- approve/reject/deprecate actions,
- metadata editor for role, cognitive tags, difficulty, time, and rubric,
- source/provenance display.

Validation:

- non-admin employers cannot access question-bank admin routes,
- unapproved questions do not appear in employer builder results,
- approve/reject actions persist reviewer and timestamp,
- coding questions expose separate package status and package approval controls,
- Super Admin can delete questions from any status during Phase 6A inventory cleanup,
- web typecheck passes.

## Task 3 - Controlled public-source ingestion

Status: complete for the Phase 6A boundary.

Deliverables:

- curated source allowlist based on `05-source-allowlist.md`,
- seed endpoint creates initial draft records with source/provenance metadata,
- admin-operated approved-source import endpoint,
- extraction into reviewable draft question records,
- metadata classification,
- duplicate detection,
- license/provenance capture.

Validation:

- arbitrary URL scraping is not exposed to employers,
- imported/seeded questions remain `needs_review`,
- imported questions require human approval.

## Task 4 - Role-based blueprint assembly

Status: deferred.

Deliverables:

- role criteria intake model,
- required slot generation,
- approved-question matching,
- duration balancing,
- cognitive and skill coverage summary,
- future/unsupported coverage caveats,
- resume-driven follow-up probes without scored-question selection.

Validation:

- same role criteria produce reusable role-level blueprints,
- candidate resume does not change scored question selection,
- unsupported coverage is visible and not scored.

## Task 5 - Employer builder UX

Status: deferred.

Deliverables:

- employer role criteria form,
- generated blueprint review,
- selected question list,
- coverage summary,
- same-slot swap UI,
- approve and send invite flow.

Validation:

- employer can swap only within valid required slots,
- employer cannot remove required slots in MVP,
- existing direct coding invite path remains available unless explicitly retired later.

## Task 6 - Candidate mixed assessment experience

Status: deferred.

Deliverables:

- question sequence UI,
- reuse existing coding workspace for coding questions,
- written-response UI for system design, communication, and trade-off questions,
- per-question evidence capture,
- final submission across all questions.

Validation:

- coding question protected artifacts remain hidden,
- written-response answers are persisted,
- AI interactions are linked to the active question.

## Task 7 - AI helper policy generalization

Status: deferred.

Deliverables:

- base AI policy reused across all question types,
- type-specific allowed/disallowed examples,
- protected artifact boundaries per question,
- anti-decomposition guard across mixed assessments.

Validation:

- AI cannot write full written answers,
- AI cannot reveal scoring/rubric internals,
- AI cannot enumerate all expected points or all defects.

## Task 8 - AI-assisted scoring and reviewer overrides

Status: deferred.

Deliverables:

- AI draft scoring for coding and written-response questions,
- rubric evidence citations,
- reviewer override fields,
- report section showing directly tested, AI-scored, and follow-up-only evidence.

Validation:

- scoring cites candidate evidence only,
- resume claims are not scored unless tested,
- evaluator overrides are preserved.

## Task 9 - Documentation, testing, and handoff

Status: deferred.

Deliverables:

- update `CURRENT_STATE.md`,
- update architecture spec after implementation decisions settle,
- update `docs/development/changes.md`,
- add ADRs for question bank source/provenance and AI-assisted scoring if implemented,
- API, web, and e2e tests for the new workflows.

## Future composition completion criteria

- Super admin can create or generate draft questions and approve them.
- Controlled public-source ingestion can create reviewable draft questions.
- Employer can generate a role-based blueprint from approved questions.
- Employer can swap questions within required slots and approve the blueprint.
- Candidate can complete coding and written-response questions.
- AI helper stays constrained across all question types.
- Reports include AI-assisted scores with evidence and reviewer override support.

## Explicit non-goals

- Fully automatic company research.
- Employer-facing arbitrary web scraping.
- Candidate-specific scored assessments.
- Unreviewed generated questions in scored assessments.
- Specialized runtimes for every future question type.
- ATS integration.
