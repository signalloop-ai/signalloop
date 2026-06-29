# 05 - Employer UX and Reporting

Status: planned.

## Goal

Add an optional adaptive builder to the employer portal while preserving the
current quick assessment flow.

The UX should make the adaptive recommendation understandable and reviewable. It
must clearly show what SignalLoop can assess now and what remains a follow-up
or unsupported area.

## Employer entry points

The Assessments view should offer two paths:

### Quick assessment

Existing flow:

```text
choose Basic/Advanced
choose timing
choose evaluator feedback mode
enter candidate email
send invite
```

This remains the fastest path and should not require JD/resume input.

### Adaptive builder

New flow:

```text
paste JD
paste optional resume
review skill map
review blueprint
approve
send invite
```

For Phase 5 v1, the adaptive builder still selects Standard or Advanced FastAPI
under the hood.

## Adaptive builder steps

### Step 1 - Role intake

Fields:

- role title,
- role family,
- seniority,
- JD / job requirement text,
- team context,
- expected AI usage.

The UI should avoid implying that company website scraping or external lookup is
required for MVP.

### Step 2 - Candidate context

Fields:

- candidate email,
- pasted resume text optional.

The UI should state that resume text is used to identify claims and follow-up
probes, not to give the candidate a different scored task by default.

### Step 3 - Skill map

Show grouped skills:

- Required and claimed,
- Required but not claimed,
- Candidate extras,
- Not directly assessed,
- Unmapped text.

Each group should be concise and editable later if needed. For MVP, employer
editing can be deferred if generated mapping is visibly reviewable.

### Step 4 - Blueprint review

Show:

- recommended assessment pack,
- level,
- duration,
- timing mode,
- evaluator feedback mode,
- directly tested skills,
- partially tested skills,
- not tested skills,
- rationale,
- caveats,
- follow-up probes.

Primary action:

```text
Approve and send invite
```

Secondary action:

```text
Back / adjust inputs
```

## Copy direction

Prefer:

```text
Recommended assessment blueprint ready.
Review what will be tested and what will not be tested.
```

Avoid:

```text
AI generated the perfect interview.
Every candidate gets a unique test.
All skills are verified.
```

## Adaptive report section

Only show this section when the attempt has a blueprint.

Suggested section title:

```text
Role-Adaptive Context
```

Suggested subsections:

### Role summary

- role title,
- role family,
- seniority,
- assessment pack selected.

### Skill coverage

Show:

- directly tested,
- partially tested,
- not directly tested.

### Resume claims probed

Show candidate claims that were relevant to the selected assessment and report
evidence.

### Blueprint rationale

Brief explanation of why this pack was selected.

### Follow-up interview probes

Questions for the employer to ask after reviewing the report.

### Caveats

Explicitly state unsupported or weakly supported areas.

Example:

```text
This assessment did not directly test Kubernetes operations, PostgreSQL query
performance, or GPU orchestration. Use the follow-up probes below if those are
critical for the role.
```

## Report interpretation rule

The adaptive report must not imply unsupported skills were scored.

Good:

```text
Kubernetes was required by the JD but not directly tested by this assessment.
```

Bad:

```text
The candidate is weak in Kubernetes.
```

## Candidate workspace impact

None for v1.

Candidates should see the same candidate-safe assessment metadata and files as
today. The embedded assistant should not receive JD/resume text or blueprint
rationale.

## Acceptance criteria

- Quick assessment remains available.
- Adaptive builder is an optional path.
- Employer can review supported and unsupported coverage before sending.
- Blueprint-backed reports show adaptive context.
- Non-blueprint reports do not show empty adaptive sections.
- Candidate workspace behavior is unchanged.

