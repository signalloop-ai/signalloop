# 04 - AI Helper and Scoring

Status: deferred future work.

## Goal

Apply one shared constrained AI-helper model across all Phase 6 question types, then add
question-type-specific boundaries as needed.

## Base AI rule

The AI helper is a constrained collaborator, not an answer generator.

This applies to:

- coding,
- debugging,
- technical concept,
- system design,
- trade-off judgment,
- communication,
- AI collaboration,
- data reasoning or other future types.

## Common allowed behavior

The assistant may:

- explain concepts,
- clarify candidate-visible instructions,
- explain public test output,
- discuss one candidate-identified issue,
- suggest general debugging or reasoning approaches,
- compare trade-offs after the candidate frames the choice,
- provide small generic examples that are not the full answer.

## Common disallowed behavior

The assistant must not:

- provide the full answer,
- write the final response,
- enumerate all defects or all expected points,
- reveal scoring internals, rubrics, hidden tests, or evaluator notes,
- rewrite complete files,
- generate the complete missing test suite,
- choose the candidate's final design or judgment,
- allow decomposition that produces the full solution through smaller prompts.

## Type-specific examples

### Coding

Allowed:

```text
Explain what this public test failure says.
Suggest where I should inspect for this one behavior.
```

Disallowed:

```text
Rewrite the whole implementation.
List every bug in the codebase.
```

### System design

Allowed:

```text
Compare cache invalidation trade-offs for the approach I proposed.
```

Disallowed:

```text
Write the complete final architecture answer.
```

### Trade-off judgment

Allowed:

```text
What dimensions should I consider for choosing between strict and permissive behavior?
```

Disallowed:

```text
Pick the final decision and write my rationale.
```

### Communication

Allowed:

```text
Give feedback on whether my explanation is clear.
```

Disallowed:

```text
Write the final employer-facing explanation for me.
```

## Protected artifacts

The AI helper must not receive:

- hidden tests,
- scoring internals,
- evaluator-only rubrics unless transformed into candidate-safe guidance,
- expected answer keys,
- seeded issue lists,
- reference solutions,
- private source-ingestion metadata,
- super-admin review notes.

## AI-assisted scoring

Phase 6 should score all supported question types with AI-assisted draft scoring and evaluator
review.

Scoring model:

```text
candidate answer + allowed evidence + approved rubric
-> AI draft score and evidence notes
-> evaluator/employer review or override
-> final report
```

AI scoring should cite evidence from:

- candidate code,
- public/hidden test results where applicable,
- written answer,
- final explanation,
- AI interaction log,
- captured snapshots/events.

AI scoring must not cite:

- facts not present in the candidate evidence,
- private evaluator-only notes as if the candidate demonstrated them,
- unsupported resume claims as scored evidence.

## Report language

Reports should distinguish:

- directly tested evidence,
- partially tested evidence,
- AI-scored written evidence,
- follow-up probes,
- unsupported or future coverage.

Do not imply that a candidate was scored on a skill that was only mentioned in their resume or
JD and not tested by the assessment.

## Human review

AI scoring is not final truth. The report should preserve:

- AI draft score,
- cited evidence,
- reviewer override if any,
- override reason,
- final score used for recommendation.
