# 06 - UI Enhancements

Status: completed locally.

## Goal

Improve candidate and employer usability for Phase 2 assessment configuration, timing,
and reporting.

## Employer UI

Add:

- polished production login screen with clear SignalLoop positioning,
- assessment selector: Standard vs Advanced,
- timed/untimed selector,
- duration dropdown,
- recommended duration display,
- clear invite URL copy state,
- report metadata for assessment type and timing,
- clearer attempt/report states and status filters.

## Candidate UI

Add:

- assessment type/difficulty display,
- timer when timed,
- warnings at 10, 5, and 1 minute,
- expired state,
- clear auto-submit state,
- improved progress feedback for public tests and final submission,
- clearer instructions that submission-review answers are supporting evidence and implementation/tests matter most,
- accessible Submission Review panel or tab with completion indicator.

The Submission Review should replace separate final-explanation and decision-log text
areas with structured questions:

1. What did you change?
2. What tradeoffs or product decisions did you make?
3. How did you verify your changes?
4. What would you improve next, given more time?
5. Optional: anything else the evaluator should know?

The Submit button should remain available unless the attempt is already submitted or a
backend operation is running. On click, show a final confirmation modal. The modal
should warn that submission is permanent and show:

- public tests run: yes/no,
- candidate tests added or updated: yes/no,
- submission review answered: x/4 required questions.

Do not show hidden-test status before submission. Hidden tests run only after final
submission.

## Report UI

Add:

- assessment type,
- duration and time used,
- submission mode,
- updated score categories,
- FAVO interpretation section,
- AI collaboration breakdown,
- AI integrity risk panel,
- feature/design implementation section,
- score breakdown chart,
- public/hidden test result chart,
- evidence timeline.

## Design Direction

Keep the UI operational and assessment-focused. Avoid marketing-page styling inside the
workspace or report surfaces.

Use a more polished engineering-product visual system:

- neutral base with restrained accent color,
- stronger typography and spacing,
- clear pass/fail/warning status treatment,
- simple charts before adding a heavy charting dependency.

## Implementation Notes

Implemented locally:

- assessment configuration controls were already added in the employer configuration
  task,
- candidate workspace shows assessment/timer metadata and expiry state,
- final submission now uses structured Submission Review prompts,
- Submit remains available unless submitted or a backend operation is running,
- final confirmation modal shows public-test, candidate-test, and review completion
  signals,
- report page renders assessment/timing metadata, score bars, test result bars,
  feature/design summary, FAVO interpretation, and AI integrity risk.

## Local Validation

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.

Playwright e2e was attempted, but this Codex sandbox could not bind
`127.0.0.1:3000`. Run `cd apps/web && npm run test:e2e` locally before deployment.
