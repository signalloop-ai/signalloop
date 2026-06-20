# FastAPI Team Task API Advanced v1

You are working on an internal team task API generated from an early AI-assisted
prototype. The service is being prepared for a limited beta with employees, team
members, and team leads.

Public tests are intentionally incomplete. Hidden evaluation checks deeper behavior
around authorization, partial updates, archive/delete semantics, audit events, comments,
and deterministic list behavior.

## What To Do

- Inspect `task_api/main.py` and the public tests.
- Fix focused correctness, authorization, and product-behavior issues.
- Add or update tests for changed behavior.
- Use the AI collaborator for one candidate-identified issue or one failing behavior at
  a time.
- Preserve the visible API shape unless you explain a tradeoff in Submission Review.

## Product Constraints

- Security and team isolation matter more than convenience.
- Team leads should not gain access across unrelated teams.
- Delete should preserve enough evidence for auditability.
- Partial updates should not erase omitted fields.
- Where 403 vs 404 is ambiguous, choose a policy and apply it consistently.
- Keep the in-memory implementation simple; do not add a database or auth provider.

## Useful Commands

```bash
uv run pytest
uv run uvicorn task_api.main:app --reload
```
