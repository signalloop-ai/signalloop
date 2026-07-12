# 02 - Approved Question Bank

Status: Phase 6A governance model implemented; future blueprint references deferred.

## Goal

Use question-level approval as the primitive for Phase 6.

An assessment is assembled from approved questions. A question can be small, such as a short
trade-off prompt, or large, such as a coding task with files and tests.

## Question record

Recommended fields:

```text
id
version
status
title
question_type
prompt
role_tags
skill_tags
cognitive_tags
difficulty
seniority_band
experience_min_years
experience_max_years
estimated_minutes
rubric
expected_evidence
source_type
source_url
source_license
source_attribution
source_notes
package_status
coding_package_kind
coding_package_ref
coding_package_notes
created_by
reviewed_by
approved_at
deprecated_at
```

Question types:

```text
coding
technical_concept
system_design
communication
tradeoff_judgment
```

`technical_concept` is for focused technical explanation questions such as React synthetic
events, JavaScript event-loop behavior, or framework semantics. These are not communication
questions by type, even though the rubric can still evaluate communication quality.

Future question types:

```text
data_reasoning
security_review
ml_ai_design
standalone_debugging
```

Statuses:

```text
draft
needs_review
approved
rejected
deprecated
```

Selection rule:

```text
Only approved questions are selectable for employer-facing scored assessments.
```

For coding questions, this rule is stricter:

```text
content status must be approved
package_status must be package_approved
```

Non-coding questions use `package_status = not_required`.

## Coding question payload

Coding questions may include a structured package:

```text
runtime
starter_files
public_tests
hidden_tests optional
seeded_issues optional
enhancements optional
entrypoint
test_command
candidate_visible_files
protected_evaluator_files
```

Hidden tests are optional in Phase 6. Simpler coding questions can rely on public tests, code
diff, final explanation, AI collaboration evidence, and rubric-based scoring.

Package statuses:

```text
missing
draft
ready_for_review
package_approved
rejected
```

For the Phase 6A foundation, Super Admin may delete questions in any status because the
question bank is not yet referenced by live assessments. Once employer blueprints reference
approved questions, deletion should become deprecation/archive to preserve historical attempts.

## Rubric requirements

Every approved question needs a rubric before activation.

Minimum rubric fields:

- scoring dimensions,
- point allocation or rating scale,
- evidence expected for strong / acceptable / weak responses,
- disallowed shortcuts,
- AI-helper boundaries specific to the question if needed.

For written-response questions, the rubric should describe what the AI scorer should cite as
evidence. The scorer must not invent facts beyond the candidate answer and allowed context.

## Source paths

Questions can enter the system from four paths:

### Internal authored

SignalLoop-authored questions created directly by the product or assessment team.

### Super-admin AI draft

Super admin chooses:

- role tags,
- question type,
- cognitive tags,
- difficulty,
- expected time,
- optional source context.

The system generates a draft question, metadata, and rubric. The draft must be reviewed before
activation.

### System-curated public-source import

Engineering/product maintains a curated allowlist of reusable public sources.

The ingestion pipeline:

```text
allowlisted source
-> extract candidate questions
-> normalize into SignalLoop question shape
-> classify tags/difficulty/time
-> store as needs_review
```

The super admin reviews imported questions before approval.

### Customer-specific custom

A customer may provide custom questions. These should be isolated to that customer unless
explicitly approved for the global bank.

## Public-source licensing rules

Every imported question needs:

- source URL,
- source name,
- license,
- commercial-use status,
- modification status,
- attribution requirement,
- import date,
- reviewer.

If reuse rights are unclear, the question must not become approved.

Do not directly copy from:

- paid assessment platforms,
- prep sites without reuse permissions,
- company interview dumps,
- books/blogs without compatible license,
- repositories without a clear license.

## Classification

AI can suggest metadata:

- role tags,
- skill tags,
- cognitive tags,
- difficulty,
- estimated time,
- seniority band,
- likely question type.

Human review remains required before approval.

## Versioning

Approved questions should be immutable for completed assessments.

If the question prompt, files, tests, rubric, or scoring dimensions change, create a new version.
Existing attempts should continue to reference the version used at invite creation.
