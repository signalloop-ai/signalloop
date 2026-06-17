# ADR: Use Deterministic Six-Category MVP Scoring Rubric

## Status

Accepted

## Context

SignalLoop's Engineering Evidence Report needs a clear MVP scoring model that is explainable, testable, and stable across candidates.

The original rubric had more overlapping categories and gave seeded issue coverage relatively little weight despite functional/debugging evidence being the primary assessment signal. Local validation also showed that public test results needed to be persisted and scored explicitly, because public verification behavior is part of the candidate evidence trail.

For the MVP, scores should be deterministic estimates from captured evidence. Manual evaluator review remains required before any hiring decision.

## Decision

Use a deterministic six-category scoring rubric totaling 100 points:

| Category | Points |
|---|---:|
| Public test coverage | 20 |
| Hidden test coverage | 30 |
| Regression | 15 |
| Candidate-written tests | 15 |
| AI collaboration | 10 |
| Explanation and decisions | 10 |

The `RUBRIC` dict in `apps/api/signalloop_api/reports.py` is the implementation source of truth for the point values.

Public test coverage is scored from the final public test run and the assessment pack's `initially_failing_tests` configuration. Regression scoring treats failures outside that initially failing list as possible regressions. Hidden test coverage is scored from parsed hidden pytest output. Candidate tests, AI collaboration, and explanation quality use deterministic evidence heuristics.

## Consequences

- The report is easier to explain to employers and future coding agents.
- Rebalancing rubric weights should happen in one place: `RUBRIC`.
- Assessment packs must declare which public tests are expected to fail in starter code if public test coverage is scored.
- Public test runs must be persisted as `TestRun` records, not only shown in the browser.
- Scores remain deterministic MVP evidence summaries, not final hiring judgments.
- Future evaluator influence should be added as an explicit later feature, not hidden inside the deterministic MVP score.
