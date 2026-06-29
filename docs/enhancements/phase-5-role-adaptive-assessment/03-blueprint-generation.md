# 03 - Blueprint Generation

Status: planned.

## Goal

Generate a reviewable assessment blueprint from role intake, optional resume
intake, taxonomy matching, and current assessment-module coverage.

The blueprint is the system's recommendation, not an automatic hiring decision.
Employers must approve it before invite creation.

## Blueprint definition

An assessment blueprint is the full plan for a candidate invite:

```text
role context
skill map
selected assessment module
difficulty and timing
AI collaboration mode
scoring plan
evidence coverage
candidate-specific probes
employer-facing rationale
unsupported-skill caveats
```

It is broader than a list of questions.

## Blueprint status

Recommended states:

- `draft` - generated but not approved.
- `approved` - employer accepted it and can create an invite.
- `used` - an assessment attempt was created from it.

## MVP selection rule

For Phase 5 v1, select only from existing packs:

- `fastapi-task-api-standard-v2`
- `fastapi-task-api-advanced-v1`

Suggested rule:

```text
If role family is backend/full-stack and required skills overlap current
FastAPI coverage:
  choose advanced for senior/staff or explicit multi-tenancy/security/reliability needs
  choose standard for junior/mid or basic API/backend needs
Else:
  recommend best available pack only if there is enough backend/API overlap
  otherwise mark as unsupported for direct assessment
```

The system may still produce a blueprint when unsupported skills are present,
but it must distinguish supported from unsupported coverage.

## Candidate-specific boundary

For v1:

```text
JD/role determines the scored core assessment.
Resume determines candidate-specific rationale and follow-up probes.
```

Do not automatically create different scored tasks for candidates applying to
the same role.

Later phases may support:

```text
core comparable module + optional candidate-specific probe module
```

If added later, the report should separate:

- comparable core score,
- candidate-specific probe evidence.

## Blueprint shape

Example response:

```json
{
  "title": "Senior Backend API Reliability Assessment",
  "role_family": "backend",
  "seniority": "senior",
  "assessment_pack_slug": "fastapi-task-api-advanced-v1",
  "timing_mode": "timed",
  "duration_minutes": 120,
  "evaluator_feedback_mode": "strict",
  "core_comparability": {
    "same_for_role": true,
    "explanation": "The JD determines the core assessment; resume claims drive follow-up probes."
  },
  "skill_map": {
    "required_overlap": ["backend.python", "backend.fastapi"],
    "required_gap": ["infra.kubernetes"],
    "candidate_extra": ["backend.caching"],
    "unsupported_required": ["infra.kubernetes"],
    "unsupported_claimed": []
  },
  "coverage": {
    "directly_tested": [
      "backend.fastapi",
      "backend.validation",
      "backend.authorization",
      "eng.debugging",
      "eng.test_design",
      "eng.ai_collaboration"
    ],
    "partially_tested": [
      "backend.multi_tenancy",
      "backend.reliability"
    ],
    "not_tested": [
      "infra.kubernetes",
      "backend.postgresql"
    ]
  },
  "rationale": [
    "The JD emphasizes backend API safety and multi-tenant behavior.",
    "The candidate claims FastAPI and backend API experience.",
    "Advanced FastAPI v1 is the strongest supported current module for this role."
  ],
  "follow_up_probes": [
    {
      "source": "unsupported_required",
      "skill_id": "infra.kubernetes",
      "question": "How would you deploy and roll back this API in Kubernetes?"
    }
  ],
  "caveats": [
    "Kubernetes and PostgreSQL performance are not directly tested by the selected pack."
  ]
}
```

## Follow-up probes

Follow-up probes are not a second scored assessment in v1. They are interview
questions for the employer to use after the coding assessment.

Probe sources:

- resume-claim validation,
- unsupported required skills,
- unsupported claimed skills,
- required gaps,
- weak evidence after submission,
- failed or partial rubric categories.

Examples:

```text
Resume claim:
You mention Redis caching. Where would caching fit in this submitted API, and
what invalidation risks would you watch?

Unsupported requirement:
This role needs Kubernetes. This assessment did not directly test Kubernetes.
How would you deploy, monitor, and roll back this API?

Weak evidence:
The candidate added few tests. Ask how they would expand coverage for
authorization and state transitions.
```

## LLM role

The LLM may:

- extract candidate skills from JD/resume text,
- draft blueprint rationale,
- draft follow-up probes,
- produce human-readable caveats.

The deterministic application layer must:

- normalize skills to taxonomy IDs,
- apply supported/partial/unsupported coverage from module mappings,
- select only valid assessment packs,
- preserve current scoring rubrics,
- enforce that unsupported skills are not marked as directly tested.

## Safety boundaries

The LLM must not receive:

- hidden tests,
- seeded issue list,
- scoring internals beyond allowed rubric labels,
- evaluator notes,
- reference solutions,
- candidate workspace code from active attempts unless needed by a later
  report-only probe-generation step with explicit boundaries.

The adaptive builder is an employer-side planning tool, not the embedded
candidate AI collaborator.

## Acceptance criteria

- Blueprint generation returns a structured, reviewable object.
- Blueprint selection only uses supported pack slugs.
- Unsupported skills appear in caveats and follow-up probes.
- Resume claims do not automatically change the core scored task for the same
  role.
- Employer approval is required before invite creation.
- Tests cover standard selection, advanced selection, unsupported-role behavior,
  and resume-specific follow-up probes.

