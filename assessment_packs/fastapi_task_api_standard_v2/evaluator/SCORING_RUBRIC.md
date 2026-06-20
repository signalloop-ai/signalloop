# Standard v2 Scoring Rubric

Evaluator-only scoring internals. Do not expose this file to candidates or the AI collaborator.

All weights live in `apps/api/signalloop_api/reports.py` under the `RUBRIC` dict.
Change values there to rebalance without touching any other code.

| Category | Points | Measured by |
|---|---:|---|
| Public issue resolution | 15 | Initially failing public tests fixed |
| Private issue generalization | 20 | Hidden seeded behaviors fixed |
| Feature/design implementation | 20 | Priority behavior, design consistency, edge-case handling |
| Candidate-written tests | 15 | Meaningful candidate tests added or modified |
| AI collaboration | 20 | Focused, candidate-owned AI use and verification behavior |
| Regression/code quality | 10 | Existing behavior preserved and implementation remains simple |
| **Total** | **100** | |

## Public issue resolution, 15 pts

6 public tests. Only initially failing tests count toward this category.

- `test_can_create_user_and_task` — happy-path baseline (should already pass)
- `test_duplicate_user_email_is_rejected` — seeded issue hint (409)
- `test_blank_task_title_is_rejected` — seeded issue hint (422)
- `test_task_priority_defaults_and_accepts_high` — product/design hint
- `test_non_owner_cannot_read_task` — ownership hint
- `test_missing_task_returns_404` — basic 404 baseline (should already pass)

## Private issue generalization, 20 pts

7 hidden tests. Automated after submission.

1. Duplicate email: case-insensitive + whitespace-trimmed conflict → 409
2. Blank/whitespace title rejected + non-blank titles trimmed → 422 / trimmed title
3. Priority defaulting, normalization, and validation → `MEDIUM` / `HIGH` / 422
4. Owner-only read and delete (known non-owner) → 403
5. Unknown actor access (resource existence leakage) → 404
6. Status transitions enforced: invalid → 422, TODO→DONE direct → 409, TODO→IN_PROGRESS→DONE → 200
7. Idempotent owner delete: first → 200 `{deleted: true}`, second → 404

Note: public tests are easier versions of selected hidden tests. A candidate who only
fixes the exact public cases may still fail stricter hidden versions.

## Regression, 15 pts

Did existing working behavior survive the candidate's changes?

- All public tests pass → 15 pts
- 2–3 public tests pass → 12 pts (minor regression possible)
- 1 public test passes → 6 pts (likely regression)
- 0 public tests pass → 0 pts
- No test run recorded → 8 pts (benefit of doubt)

## Candidate-written tests, 15 pts

Test files in `tests/` that the candidate added or modified (compared against initial snapshot).

- 2+ test files touched → 15 pts
- 1 test file touched → 9 pts
- 0 test files touched → 0 pts

## AI collaboration, 10 pts

Based on logged AI messages (automatic evidence capture).

- Used AI, no policy redirects → 10 pts
- Used AI, some policy redirects → 6 pts
- Never used AI → 5 pts

## Explanation and decisions, 10 pts

Based on the candidate's submission notes (final_explanation + decision_log fields).

- Mentions design decisions (403/404, status transitions) AND has ≥80 chars → 10 pts
- Mentions decisions OR has length, but not both → 6 pts
- Very brief or absent → 2 pts

## Recommendation thresholds

| Score | Recommendation |
|---|---|
| 80–100 | strong_advance |
| 60–79 | advance_with_followups |
| 40–59 | needs_review |
| 0–39 | do_not_advance |
