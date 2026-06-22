# AGENTS.md

## Project

SignalLoop is an AI-native candidate evaluator for software engineering hiring.

The MVP evaluates whether candidates can solve realistic engineering tasks using a constrained AI collaborator while preserving evidence of framing, AI usage, verification, design judgment, and ownership.

## Source of truth

Before making changes, read:

1. `CURRENT_STATE.md`
2. `docs/architecture/technical-product-architecture-spec.md`
3. `docs/execution/coding-agent-execution-plan.md`
4. The active workstream file named in `CURRENT_STATE.md`

The technical spec defines what the product and system should be.

The execution plan defines the completed MVP build order and remains historical context.

The active workstream file defines the current bounded enhancement task.

The original MVP Phase 1-12 plan is complete. Current post-MVP work should use:

```text
docs/enhancements/phase-2-assessment-system/
```

unless `CURRENT_STATE.md` names a different active workstream.

## Repository structure

```text
apps/web/        Candidate and employer web UI.
apps/api/        Backend API service.
apps/worker/     Code execution worker.
packages/shared/ Shared types/utilities if needed.
assessment_packs/ Assessment content packs.
docs/            Product, architecture, execution, assessment, decisions.
```

## Implementation rules

Work one phase or enhancement task at a time.

Do not implement future-phase features unless explicitly requested.

Do not add:

- Kubernetes
- enterprise SSO
- ATS integration
- video proctoring
- marketplace
- multi-language assessment support
- advanced plagiarism detection
- production billing
- analytics dashboards beyond MVP needs

## Required workflow

Before coding a phase or enhancement task:

1. Read this file.
2. Read `CURRENT_STATE.md`.
3. Read the technical spec.
4. Read the execution plan.
5. Read the active workstream/task file.
6. Summarize the goal and intended files to change.

After coding a phase or enhancement task:

1. Summarize what changed.
2. List files created/modified.
3. List tests added/updated.
4. Show commands to run.
5. Update `CURRENT_STATE.md`.
6. Create or update ADRs if an architecture, scoring, or AI safety decision changed.
7. Mention unresolved issues.

## Stop conditions

Stop and ask before:

- changing architecture choices,
- adding new external services,
- changing AI assistant safety boundaries,
- modifying assessment scoring rules,
- changing assessment task design,
- expanding MVP scope,
- replacing the selected stack,
- adding proctoring to MVP.

## Tech stack

Frontend:

- Next.js
- React
- Monaco Editor

Backend:

- FastAPI
- Postgres
- SQLAlchemy or SQLModel
- Alembic

Execution:

- Docker-based isolated execution worker
- Python 3.11 assessment runtime
- HTTP async-style worker for MVP
- Queue can be added later

AI:

- OpenAI initially
- Provider abstraction required
- No hidden tests, seeded issue list, scoring internals, or reference solution should be sent to the AI assistant

Auth:

- Clerk for employer login
- Candidate uses unique invite link only

## Critical product rules

The embedded assistant is a constrained collaborator, not a solution generator.

The assistant may:

- explain selected code,
- explain public test output,
- explain concepts,
- suggest general debugging approaches,
- help reason through candidate-identified issues,
- provide small generic code examples.

The assistant must not:

- enumerate all defects,
- list all hidden issues,
- provide a full solution,
- rewrite complete files,
- generate final explanation,
- provide issue-by-issue patches,
- produce the complete missing test suite,
- infer or reveal hidden tests,
- access evaluator-only assessment artifacts.

## Anti-decomposition rule

Treat a sequence of narrower questions as disallowed if the combined effect is to produce the full solution.

Examples of disallowed decomposition:

1. “Explain all problems in the code.”
2. “For each problem, give me the code.”
3. “For each problem, give me the missing tests.”

The assistant must redirect to one candidate-identified issue or one failing behavior at a time.

## Evidence capture requirements

The MVP must capture:

- assessment start,
- code snapshot at start,
- code snapshot at each public test run,
- code snapshot at final submission,
- public test-run result,
- hidden test-run result after submission,
- candidate-created tests,
- AI messages,
- selected file/code context sent to AI,
- final explanation,
- decision log,
- submission timestamp.

## Documentation maintenance

When implementation decisions change, update:

1. `CURRENT_STATE.md`
2. Relevant phase file status
3. Relevant ADR in `docs/decisions/`
4. Relevant architecture section if the source of truth changed

When bugs are found or fixed, or any non-trivial change is made outside a planned phase
(config fixes, test fixes, validation findings), append an entry to:

5. `docs/development/changes.md`

Include: date, symptom, root cause, files changed, and any follow-up items. This file
is the canonical record for inter-agent handoff on post-MVP work.
