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
- non-blocking run/final-submit progress where practical,
- optional guided evaluator progress when enabled by the employer,
- IDE-style syntax diagnostics and public-test navigation,
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

Default strict mode must not show hidden-test status before submission. Hidden tests run
only after final submission in strict mode.

In guided evaluator feedback mode, the candidate workspace may show aggregate evaluator
progress during active work, for example:

```text
Evaluator checks: 4 passed, 3 failing
Details hidden
```

Guided mode must not expose hidden test names, failure messages, tracebacks, file paths,
or line numbers. The UI should label this clearly as aggregate evaluator progress and
state that details remain hidden.

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

## Candidate IDE Ergonomics

Planned workspace improvements:

- show Python syntax diagnostics while typing using Monaco markers,
- display gutter/file-tree indicators for files with syntax or public-test references,
- parse public pytest output and turn candidate-visible file/line references into links,
- color-code public test output for pass, fail, warning, and neutral sections,
- preserve raw output access while making the common failure path easier to scan.

These enhancements must stay within candidate-visible code and public test output. Hidden
test output must not drive editor hints or clickable locations.

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
- employer invite creation supports strict/guided evaluator feedback mode,
- candidate workspace shows aggregate evaluator counts only in guided mode,
- candidate workspace shows lightweight Python diagnostics, file markers, clickable
  public pytest output, color-coded output, and run duration.

## Local Validation

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.

Playwright e2e was attempted, but this Codex sandbox could not bind
`127.0.0.1:3000`. Run `cd apps/web && npm run test:e2e` locally before deployment.
