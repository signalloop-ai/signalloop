# Scoring Rubric

Phase 2 deterministic rubric. Source of truth is `RUBRIC` in `apps/api/signalloop_api/reports.py`
and pack-specific overrides in `DEFAULT_PACKS` in `apps/api/signalloop_api/attempts.py`.

## Standard v2 (fastapi_task_api_standard_v2)

| Category | Points | Evaluation basis |
|---|---:|---|
| Public issue resolution | 15 | Fraction of initially-failing public tests now passing |
| Private issue generalization | 20 | Hidden test pass ratio |
| Feature/design implementation | 20 | Named feature/design tests passing (hidden test file only, via `feature_design_tests` pack config) |
| Candidate-written tests | 15 | Proving-test count (candidate tests that fail on starter code AND pass on submitted code) |
| AI collaboration | 15 | Usage and policy violation tiers (see below) |
| Regression/code quality | 15 | No regressions in previously-passing public tests |
| **Total** | **100** | |

## Advanced v1 (fastapi_task_api_advanced_v1)

| Category | Points | Evaluation basis |
|---|---:|---|
| Public issue resolution | 15 | Fraction of initially-failing public tests now passing |
| Private issue generalization | 15 | Hidden test pass ratio |
| Feature/design implementation | 25 | Named feature/design tests passing (hidden test file only, via `feature_design_tests` pack config) |
| Candidate-written tests | 15 | Proving-test count (candidate tests that fail on starter code AND pass on submitted code) |
| AI collaboration | 15 | Usage and policy violation tiers (see below) |
| Regression/code quality | 15 | No regressions in previously-passing public tests |
| **Total** | **100** | |

## AI collaboration scoring tiers

| Scenario | Score (of 15) |
|---|---:|
| No AI use | 8 (neutral floor — no signal, not penalised) |
| Used AI, zero policy violations | 15 (full credit) |
| Used AI, 1 policy violation | 6 (below floor) |
| Used AI, 2–3 policy violations | 3 (heavy penalty) |
| Used AI, 4+ policy violations | 0 (systematic abuse) |

## Quality embedding

Quality is evaluated through the test suite, not as a separate rubric dimension:

- Hidden tests check design decisions (e.g., 403 vs 404 for unknown actors, status
  transition correctness, input normalization) — not just basic correctness.
- Enhancement quality tests check edge cases (cycle detection, blocker enforcement,
  ordering, pagination, format validation).
- Passing these tests requires making the correct design choice and implementing
  it thoroughly. Partial or inconsistent enforcement reduces the hidden/feature score.

## Candidate-written tests scoring (proving tests)

Candidate tests are scored by running the candidate's submitted test files against the
original starter code (via the `/run-candidate-verification` worker endpoint). A
"proving test" is one that:

1. **Fails** on the original unmodified starter code (proves it caught a real bug), AND
2. **Passes** on the candidate's submitted code (proves the candidate fixed it).

| Proving tests found | Points awarded |
|---:|---:|
| 0 | 0 |
| 1 | 6 (40%) |
| 2 | 11 (75%) |
| 3+ | 15 (full) |

Candidate verification runs at report-generation time. If the worker is unreachable the
category falls back to 0 rather than blocking report generation.

## Notes

- All scores are deterministic estimates from captured evidence.
- Manual evaluator review remains required before hiring decisions.
- The `regression_code_quality` category measures no-regression, not code style.
  Style signals are captured through follow-up questions.
