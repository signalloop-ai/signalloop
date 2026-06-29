# 01 - Product Requirements

Status: planned.

## Goal

Allow an employer to create a role-adaptive assessment blueprint from pasted job
requirements and optional pasted resume text, then approve that blueprint before
sending a candidate invite.

The MVP should make SignalLoop feel adaptive without weakening fairness,
comparability, or evidence integrity.

## User stories

### Employer creates a role profile

As an employer, I can paste a JD and provide role context so SignalLoop can
understand what the hiring team needs.

Required fields:

- role title,
- role family,
- seniority,
- JD / job requirement text.

Optional fields:

- team or product context,
- expected AI usage,
- hiring market,
- notes about must-have or nice-to-have skills.

### Employer adds candidate context

As an employer, I can paste a candidate resume so SignalLoop can compare the
candidate's claims against the role needs.

The resume is treated as a set of claims to validate, not as proof of ability.

### Employer reviews a skill map

As an employer, I can see how SignalLoop classified skills:

- required overlap: required by JD and claimed by candidate,
- required gap: required by JD but not clearly claimed,
- candidate extra: claimed but not required,
- unsupported required: required but not directly assessable now,
- unsupported claimed: claimed but not directly assessable now.

### Employer reviews an assessment blueprint

As an employer, I can review the recommended assessment before creating an
invite.

The blueprint must clearly show:

- what will be tested,
- what will not be tested,
- which current assessment pack will be used,
- why that pack was selected,
- which follow-up probes should be asked outside the scored coding task.

### Employer sends an invite from a blueprint

As an employer, I can approve a blueprint and create a candidate invite from it.

The invite uses the existing candidate assessment flow. The candidate does not
need to know the employer's JD/resume analysis or taxonomy mapping.

### Employer reads adaptive report context

As an employer, I can see the blueprint context in the final report so I know
how to interpret the score against the role and resume.

## MVP behavior

For a given role/JD, the core assessment should remain stable across candidates:

```text
same assessment pack
same task
same rubric
same duration
same scoring model
```

Candidate resume data may influence:

- resume claims to validate,
- follow-up probes,
- report interpretation,
- unsupported-skill caveats.

Candidate resume data should not automatically change the scored coding task
for the same role in v1.

## Example

JD:

```text
Senior Backend Engineer for an AI infrastructure company. Needs Python,
FastAPI, PostgreSQL, Kubernetes basics, multi-tenant APIs, observability,
distributed systems, and AI-tool fluency.
```

Resume:

```text
5 years backend experience. Python, FastAPI, Django, PostgreSQL, Redis, AWS,
internal APIs, background jobs, and LLM tooling.
```

Blueprint:

```text
Selected pack:
fastapi_task_api_advanced_v1

Directly tested:
Python/FastAPI implementation, API debugging, validation, ownership,
authorization, tests, tradeoff judgment, AI collaboration.

Partially tested:
multi-tenant safety judgment, product/security edge cases.

Not directly tested:
Kubernetes, GPU orchestration, PostgreSQL performance, observability tooling.

Follow-up probes:
- How would you enforce this behavior with database constraints and migrations?
- Where would Redis help or hurt this API?
- How would you monitor and roll back this service in Kubernetes?
```

## Acceptance criteria

- Employer can create a role-adaptive blueprint from pasted JD text.
- Employer can optionally include pasted resume text.
- System displays a skill map with supported and unsupported skills.
- System recommends Standard FastAPI v2 or Advanced FastAPI v1.
- Employer must approve the blueprint before invite creation.
- Invite created from a blueprint uses the existing candidate flow.
- Evidence report shows adaptive context only for blueprint-backed attempts.
- Existing quick assessment flow continues to work unchanged.

## Out of scope

- Resume file upload or document parsing.
- Fully generated coding tasks.
- New assessment packs.
- Dynamic scoring weights.
- Candidate-specific core task selection for the same role.
- Taxonomy editing UI.
- ATS or HRIS integrations.

