# 07 - Reporting And FAVO Updates

Status: completed locally, except external LLM-assisted review execution.

## Goal

Update Engineering Evidence Reports to better reflect SignalLoop's thesis: evaluate the
human-AI engineering process, not only final code.

## New Score Categories

- Public issue resolution.
- Private issue generalization.
- Feature/design implementation.
- Candidate-written tests.
- AI collaboration.
- Regression/code quality.

Do not add a standalone written-explanation score category. Structured submission-review
answers should support evidence and follow-up questions, and may inform existing
categories such as feature/design implementation, verification, and ownership.

Remove the current employer-facing report-level confidence label. The MVP confidence
field only describes evidence availability and duplicates information already visible in
section scores and test evidence.

## FAVO

FAVO is report-only. Do not ask the candidate to write FAVO manually.

| FAVO area | Derived from |
|---|---|
| Frame | issue coverage, feature/design behavior, prioritization signals |
| Ask | AI interaction quality and policy tags |
| Verify | public test runs, hidden results, candidate-written tests, run-after-AI behavior |
| Own | final implementation consistency, regression safety, optional notes matching behavior |

## Submission Review Evidence

Replace separate final explanation and decision log surfaces with a structured
Submission Review captured at final submission:

- what changed,
- tradeoffs or product decisions,
- verification performed,
- improvements with more time,
- optional additional evaluator notes.

Reports should render these answers as evidence. They should not be treated as the
primary grading surface.

## Evaluator Feedback Mode

Reports must record whether an attempt used strict or guided evaluator feedback:

- `strict`: candidate saw public test feedback only during active work; hidden counts
  were employer-report-only.
- `guided`: candidate could see aggregate evaluator pass/fail counts during active work.

Guided mode should be visible to employers because it changes score interpretation. It
improves candidate guidance but lets candidates iterate against aggregate hidden
evaluator signal.

Status: implemented locally in report metadata and employer process evidence.

## AI Integrity Risk

Add a report-only AI integrity risk label:

- low,
- medium,
- high,
- critical.

The risk label should be based on captured evidence such as policy redirects, repeated
disallowed prompts, prompt-injection attempts, AI code copied into final files, large
paste events, and weak verification/submission-review evidence.

AI integrity risk must not directly change the numeric score in Phase 2. It should drive
review attention and follow-up questions.

## LLM-Assisted Report Scoring

Phase 2 should use LLM-assisted review where deterministic checks are insufficient,
especially for:

- feature/design implementation,
- code quality,
- AI collaboration interpretation,
- FAVO narrative.

The LLM reviewer must not receive hidden test source, reference solutions, or evaluator
notes that are not needed for the specific review task. Use structured evidence and
summaries where possible.

## Explanation Role

Free-form final explanation should be supporting evidence, not the primary grading
surface.

Reports should prioritize:

- observable implementation behavior,
- tests and verification,
- AI interaction history,
- consistency across code and decisions.

## Implementation Notes

Implemented locally:

- `apps/api/signalloop_api/reports.py`,
- report schemas/types,
- employer report UI,
- report tests,
- report documentation.

Numeric scoring remains deterministic. Reports now include:

- Phase 2 score categories without the employer-facing confidence label,
- structured `submission_review` evidence,
- `favo` interpretation,
- report-only `ai_integrity_risk`,
- `feature_design_implementation`,
- `llm_assisted_review` status.

External LLM-assisted report review is not invoked in the local deterministic path. The
report includes an explicit `llm_assisted_review.status=not_run` section until a bounded
review prompt and safety boundary are added and approved.

## Local Validation

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_evidence_report.py` -> 8 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.

Playwright e2e was attempted, but this Codex sandbox could not bind
`127.0.0.1:3000`. Run `cd apps/web && npm run test:e2e` locally before deployment.
