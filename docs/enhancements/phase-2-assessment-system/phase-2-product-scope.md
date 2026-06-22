# Phase 2 Product Scope

## Objective

Improve SignalLoop from a validated MVP flow into a stronger assessment system for
engineering hiring.

## Product Thesis

SignalLoop evaluates the human-AI engineering process, not just final code.

The report should help employers understand whether a candidate can:

- frame a realistic engineering task,
- use AI without over-delegating,
- verify output with tests and inspection,
- make safe and consistent design decisions,
- own the final implementation.

## Scope

Phase 2 includes:

- a common rubric for standard and advanced assessments,
- a versioned standard FastAPI assessment plan,
- a planned advanced FastAPI assessment,
- tighter AI collaborator policy,
- employer assessment configuration,
- execution timing breakdown,
- configurable evaluator feedback mode,
- candidate IDE ergonomics,
- optional time-boxed assessment flow,
- strict multi-tenant employer isolation based on Clerk user identity,
- candidate and employer UI enhancements,
- reporting updates with FAVO interpretation,
- LLM-assisted report scoring/review where deterministic checks are insufficient.

## Out Of Scope

Do not add:

- Kubernetes,
- enterprise SSO,
- ATS integration,
- video proctoring,
- marketplace,
- production billing,
- multi-language assessment support,
- broad analytics dashboards.

## Current MVP Baseline

The current pack remains:

```text
assessment_packs/fastapi_task_api_v1/
```

It should be treated as the MVP/pilot reference pack. Phase 2 standard implementation
should use a new versioned pack rather than mutating v1 after pilot usage.

## Priority Order

1. Assessment depth.
2. Strict employer isolation.
3. Timer.
4. Render/pilot UI polish.
5. Advanced pack documentation.
6. Advanced pack implementation later.
7. Execution timing breakdown.
8. Configurable evaluator feedback mode after pilot feedback.
9. Candidate IDE ergonomics.

## Execution Timing Breakdown

SignalLoop should persist and expose enough timing data to explain public/final run
latency before optimizing infrastructure. Measure API preflight, payload upload,
execution-provider startup, runner startup, pytest execution, output handoff, DB
persistence, and total request time. Candidate UI should show simple run duration and
non-blocking running state; detailed timing can stay in internal logs or employer/admin
surfaces.

Status: implemented locally for API/worker run results, final hidden evaluation, and
employer report process evidence.

## Evaluator Feedback Mode

SignalLoop should support two employer-selectable feedback modes for future iteration:

- **Strict mode**: candidates see public test results during the attempt. Hidden evaluator
  tests run after final submission, and hidden pass/fail counts are employer-report-only.
- **Guided mode**: candidates may see aggregate evaluator progress during the attempt,
  such as hidden/evaluator checks passed and failing. Test names, failure messages,
  tracebacks, file paths, and line numbers remain hidden.

Strict mode should remain the default for hiring because it preserves stronger evaluator
signal. Guided mode improves candidate feedback and may be useful for pilots, practice,
junior hiring, or employers who prefer iterative feedback. Reports must record which
mode was used so scores are interpreted correctly.

Status: implemented locally as an attempt-level employer configuration for Standard and
Advanced invites.

## Candidate IDE Ergonomics

The browser workspace should feel like a focused assessment IDE without becoming a full
VS Code clone. Planned improvements:

- Python syntax diagnostics while typing, with editor markers and gutter indicators.
- Clickable public pytest output that opens the referenced file and line.
- Color-coded test output for pass/fail/warning/neutral sections.
- File-tree indicators when public test output or syntax diagnostics reference a file.
- Better editor ergonomics such as search, bracket matching, auto-indent, and later
  formatting.

These features must use candidate-visible files and public test output only. They must
not infer or reveal hidden evaluator details.

Status: implemented locally for lightweight Python diagnostics, file markers,
clickable public pytest output, color-coded output, and run-duration display.
