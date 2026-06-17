# Phase 07: Constrained AI Collaborator

## Goal

Implement embedded AI assistant with strict MVP guardrails.

## Tasks

- [x] Add AI provider abstraction.
- [x] Implement OpenAI provider.
- [x] Implement assistant system prompt.
- [x] Enforce allowed context boundaries.
- [x] Log all AI messages.
- [x] Add anti-decomposition behavior.
- [x] Add interaction classification tags.

## Acceptance criteria

Assistant must refuse or redirect: find all bugs, explain all problems, give code for each issue, write all missing tests, generate final explanation, rewrite full file.

Status: complete. These redirect cases are covered by backend policy tests and the workspace e2e test covers an assistant redirect in the UI.
