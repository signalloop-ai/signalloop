# FastAPI Task API v1 Assessment

## Title

FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment

## Purpose

Evaluate debugging, validation, authorization, state transition reasoning, product tradeoff decisions, test design, AI collaboration, and ownership.

## Candidate-visible

- scenario,
- organizational constraints,
- starter code,
- public tests,
- broad TODO comments,
- AI policy,
- final explanation template,
- decision log.

## Evaluator-only

- seeded issue list,
- hidden tests,
- reference solution,
- scoring internals.

## Design decisions

1. Unauthorized access behavior: 403 vs 404.
2. Status transition policy: allow TODO -> DONE directly or require TODO -> IN_PROGRESS -> DONE.
