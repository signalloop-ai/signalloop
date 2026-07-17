# Build Week GPT-5.6 Report Advisory

Status: implemented and validated locally and on the hosted pilot on 2026-07-17. The restricted
Clerk judge account and email/password login were also validated.

## Goal

Extend SignalLoop with one bounded AI capability: a GPT-5.6 employer advisory that interprets safe
process evidence without changing the deterministic evaluation.

## Scope

- Separate report-advisory provider using the OpenAI Responses API and `gpt-5.6` by default.
- Explicit allowlist; the complete report is never sent to the provider.
- Structured output: summary, evidence gaps, and interview focus.
- Non-scoring employer-report section.
- Opt-in configuration and fail-open behavior; enabled for the hosted pilot.
- Focused API safety/persistence tests and web type validation.

## Out of Scope

- Changing scores, rubric weights, FAVO, integrity labels, or recommendations.
- Sending hidden tests, seeded issue areas, evaluator notes, code, or proctoring artifacts.
- Replacing the constrained candidate collaborator.
- Changing assessment task design.

## Enablement

```text
REPORT_ADVISORY_ENABLED=true
REPORT_ADVISORY_MODEL=gpt-5.6
REPORT_ADVISORY_TIMEOUT_SECONDS=30
```

`OPENAI_API_KEY` must also be configured. If the advisory call fails, the persisted deterministic
report remains complete and marks the advisory as unavailable.

## Validation

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_evidence_report.py -q`
- `cd apps/web && npm run typecheck`
- Synthetic live `gpt-5.6` Responses API call returned schema-valid, non-scoring output.
- Restricted Clerk judge account completed hosted email/password login and remained employer-only.
- Hosted Attempt #40 completed the invite, candidate submission, hidden evaluation, and employer
  report flow. Regenerating the report with the feature enabled rendered the GPT-5.6 advisory.
- The advisory was visibly labeled non-scoring and limited to summary, evidence gaps, and interview
  focus. The deterministic result remained 8/100 with recommendation `do not advance`.
