# Evaluator Guide

## Assessment test philosophy

**Public tests** — signal known issues. These tests fail on the unmodified starter code
and are visible to the candidate from the moment they open the workspace. They tell the
candidate "these behaviors are broken, fix them." Passing them drives the
`public_issue_resolution` score.

**Hidden tests — two roles:**

1. **Edge-case / quality tests** — the candidate knows the behavior area (e.g., "fix
   status transitions") but does not see the specific edge cases being checked (e.g.,
   DONE→TODO rejected, invalid status name returns 422). The candidate is expected to
   reason about correctness and implement robustly. These drive `private_issue_generalization`.

2. **Enhancement tests** — the candidate designs and builds the feature. The hidden
   test suite checks whether the implementation meets the design constraints (correct
   status codes, access control, cycle detection, pagination, etc.). Basic enhancement
   tests verify the feature exists; quality enhancement tests verify correctness.
   Together they drive `feature_design_implementation`.

**Enhancement tests must not appear in the public test file.** Putting an enhancement
test in the public file hands the candidate the endpoint shape, request body, and
response contract — defeating the design exercise. Enhancement tests belong exclusively
in the hidden test file.

**Candidate-written tests** are scored independently via proving tests: a candidate
test that fails on the original starter code AND passes on the candidate's submitted
code counts as a proving test. Candidates get credit for writing tests for both bug
fixes and enhancements. This score is completely separate from the hidden test score.

## Scoring summary

| Category | Driven by |
|---|---|
| Public issue resolution | Evaluator public tests passing |
| Private issue generalization | Evaluator hidden edge-case tests passing |
| Feature/design implementation | Evaluator named enhancement tests passing (hidden) |
| Candidate-written tests | Candidate's own proving tests (fail on starter, pass on submission) |
| AI collaboration | Policy violations / clean use pattern |
| Regression/code quality | Previously-passing public tests still passing |

## Pack test structure (current)

### Standard v2 — public tests (3 initial failures)
- `test_duplicate_user_email_is_rejected`
- `test_blank_task_title_is_rejected`
- `test_non_owner_cannot_read_task`

### Standard v2 — hidden tests (7 total)
- Enhancement basic: `test_due_date_is_optional_and_returned`, `test_tasks_can_be_listed_by_owner`
- Edge cases: `test_duplicate_email_is_case_insensitive_and_trimmed`, `test_status_transition_chain_is_enforced`, `test_unknown_actor_returns_404_not_403`
- Enhancement quality: `test_due_date_rejects_invalid_format`, `test_task_listing_is_filtered_and_ordered_by_id`

### Advanced v1 — public tests (4 initial failures)
- `test_patch_task_preserves_omitted_fields`
- `test_team_lead_cannot_access_unrelated_team_task`
- `test_archived_tasks_are_excluded_from_team_lists`
- `test_comment_requires_task_access`

### Advanced v1 — hidden tests (8 total)
- Enhancement basic: `test_task_can_block_another_task`, `test_team_activity_feed_returns_events`
- Edge cases: `test_non_owner_non_assignee_cannot_patch_task`, `test_invalid_role_is_rejected`, `test_status_transition_enforcement`
- Enhancement quality: `test_blocker_prevents_in_progress_transition`, `test_dependency_cycle_is_rejected`, `test_activity_feed_is_paginated_and_team_scoped`

## Red flags during evaluation

- Perfect solution with no process evidence (no snapshots, no test runs)
- No candidate tests added at all
- Generic final explanation not tied to specific decisions made
- AI history shows full-solution requests or enumerate-all-bugs attempts
- Candidate cannot explain design decisions in follow-up questions
