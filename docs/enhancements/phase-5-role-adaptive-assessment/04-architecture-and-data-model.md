# 04 - Architecture and Data Model

Status: planned.

## Goal

Add role-adaptive assessment planning without disrupting the existing invite,
candidate attempt, execution, AI collaborator, or report flows.

The implementation should be additive. Existing quick assessment invites should
continue to work when no blueprint is present.

## New backend concepts

### RoleProfile

Represents the employer's role/JD intake.

Suggested fields:

```text
id
employer_id
title
role_family
seniority
jd_text
team_context
expected_ai_usage
required_skills_json
nice_to_have_skills_json
extracted_skills_json
created_at
updated_at
```

### CandidateProfile

Represents optional candidate resume/context for blueprint generation.

Suggested fields:

```text
id
employer_id
candidate_email
resume_text
extracted_skills_json
extracted_experience_json
created_at
updated_at
```

For v1, resume text is pasted. File upload and document parsing are out of
scope.

### AssessmentBlueprint

Represents the reviewable recommendation.

Suggested fields:

```text
id
employer_id
role_profile_id
candidate_profile_id nullable
title
assessment_pack_slug
assessment_level
timing_mode
duration_minutes
evaluator_feedback_mode
skill_mapping_json
coverage_json
rationale_json
follow_up_probes_json
caveats_json
status
approved_at nullable
used_at nullable
created_at
updated_at
```

`status` values:

- `draft`
- `approved`
- `used`

### AssessmentAttempt link

Add a nullable blueprint link to existing attempts:

```text
assessment_attempts.blueprint_id nullable
```

This allows report generation to include adaptive context when present while
preserving existing attempt behavior.

## Static configuration

Add versioned taxonomy and module coverage files:

```text
apps/api/signalloop_api/assessment_taxonomy/
  skills.json
  module_coverage.json
```

The backend should load these files at startup or on demand. Tests should verify
that all skill IDs referenced by module coverage exist in `skills.json`.

## API direction

Suggested employer endpoints:

### Create role profile

```text
POST /employer/adaptive/role-profiles
```

Creates or updates role intake from pasted JD/team context.

### Create candidate profile

```text
POST /employer/adaptive/candidate-profiles
```

Creates optional candidate context from pasted resume text.

### Generate blueprint

```text
POST /employer/adaptive/blueprints
```

Inputs:

- role profile ID,
- optional candidate profile ID,
- requested timing/feedback preferences if any.

Returns a draft blueprint.

### Approve blueprint

```text
POST /employer/adaptive/blueprints/{blueprint_id}/approve
```

Marks the blueprint as approved.

### Create invite from blueprint

```text
POST /employer/adaptive/blueprints/{blueprint_id}/invites
```

Creates an `AssessmentAttempt` using the approved blueprint's pack, level,
timing, duration, and feedback mode.

## Invite creation behavior

Creating an invite from a blueprint should reuse the same internal logic as the
existing employer invite endpoint wherever possible.

Blueprint-derived fields:

- `assessment_pack_slug`
- `assessment_level`
- `timing_mode`
- `duration_minutes`
- `evaluator_feedback_mode`
- `blueprint_id`

The candidate invite link remains bearer-link based. Candidate endpoints should
not expose the employer's JD or resume text.

## Report generation behavior

When `assessment_attempt.blueprint_id` is present, report generation should add
an adaptive context section to the persisted report JSON.

When absent, report generation should behave exactly as it does today.

## Privacy and retention

JD and resume text are sensitive employer data.

MVP policy:

- Store role and candidate profile data scoped to the authenticated employer.
- Do not expose JD/resume text to candidate endpoints.
- Do not send JD/resume text to the embedded candidate AI collaborator.
- Do not use candidate resume text to alter hidden tests or scoring.
- Keep deletion/retention controls as a future enhancement unless explicitly
  requested.

## LLM integration

Use the existing provider abstraction direction where possible. The adaptive
builder may use an LLM for extraction/rationale, but deterministic code must own
taxonomy normalization, module coverage, and pack selection.

If the LLM is unavailable, the MVP should degrade to:

- simple keyword/alias extraction,
- visible lower-confidence caveats,
- no automatic unsupported-skill claims.

## Migration direction

Likely additive migrations:

```text
create role_profiles
create candidate_profiles
create assessment_blueprints
add nullable assessment_attempts.blueprint_id
```

No destructive migration should be required.

## Acceptance criteria

- Existing quick invite creation works unchanged.
- Adaptive blueprint data is employer-scoped.
- Blueprint-backed attempts retain a link to the blueprint.
- Candidate endpoints do not expose JD/resume/profile data.
- Report generation includes adaptive context only when `blueprint_id` exists.
- Tests cover employer isolation for role profiles, candidate profiles, and
  blueprints.

