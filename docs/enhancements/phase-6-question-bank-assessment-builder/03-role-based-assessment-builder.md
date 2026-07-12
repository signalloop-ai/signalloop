# 03 - Role-Based Assessment Builder

Status: deferred future work.

## Goal

Generate role-level assessment blueprints from approved questions.

The builder should adapt to the role and cognitive goals while preserving comparability across
candidates for the same role.

## Builder inputs

Inputs:

- company name,
- company website optional,
- engineering team size,
- India/global context,
- hiring area,
- years of experience,
- JD / role requirements,
- cognitive areas,
- target duration.

Candidate resume is optional context for gap analysis and follow-up probes, but not scored
question selection.

## Blueprint assembly

High-level process:

```text
normalize role criteria
-> extract role skills from JD
-> classify cognitive requirements
-> determine required question slots
-> query approved question bank
-> choose best-fit questions
-> validate total time and coverage
-> generate reviewable blueprint
```

Blueprint contents:

- selected questions,
- question type for each slot,
- estimated time per question,
- total estimated duration,
- role coverage,
- skill coverage,
- cognitive coverage,
- difficulty mix,
- seniority fit,
- rationale,
- future / unsupported coverage gaps,
- resume-driven follow-up probes if resume is provided.

## Slot model

The builder should produce required slots before selecting concrete questions.

Example:

```text
Backend Engineer, 5-7 years, 60 minutes
```

Slots:

```text
coding/debugging - 35 minutes
system design/trade-off - 15 minutes
communication/final explanation - 10 minutes
```

Question selection fills those slots from approved questions.

## Employer review

Employer can:

- approve blueprint,
- regenerate blueprint,
- change role criteria,
- swap a question within a required slot.

Employer cannot:

- remove a required slot,
- use an unapproved question,
- reduce coverage without regenerating from changed criteria,
- create candidate-specific scored blueprints from resumes.

## Swap rules

Same-slot swaps must preserve:

- question type,
- approximate estimated time,
- required role/hiring area fit,
- required cognitive coverage,
- supported status,
- seniority/difficulty band.

If no valid replacement exists, the UI should explain the coverage constraint rather than offer
invalid alternatives.

## Resume boundary

Resume can affect:

- required-vs-claimed skill map,
- resume gaps,
- candidate extra skills,
- follow-up probes,
- interviewer notes,
- report context.

Resume must not affect:

- selected scored questions,
- required slots,
- scoring rubric,
- timing,
- allowed AI-helper behavior.

## Assessment creation

After employer approval:

```text
approved blueprint
-> candidate invite
-> candidate receives the selected questions
-> attempt references immutable question versions
```

All candidates invited to the same role assessment should use the same approved blueprint unless
the employer explicitly creates a new role assessment version.

## Supported candidate experience

Phase 6 can support question types without custom runtimes:

- coding uses the existing coding workspace,
- system design uses structured written response,
- communication/final explanation uses structured written response,
- trade-off judgment uses structured written response.

The assessment may be presented as a sequence of questions. Evidence capture should record:

- question start,
- answer drafts or snapshots where useful,
- AI interactions,
- final answer,
- submission timestamp,
- scoring output and evaluator overrides.

## Future extensions

- assessment formats such as coding-heavy, interview-only, screening-lite,
- employer-selectable optional slots,
- richer company research,
- specialized runtimes for data, frontend, or ML tasks,
- question effectiveness analytics.
