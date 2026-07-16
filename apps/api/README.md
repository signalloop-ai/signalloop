# SignalLoop API

Backend API service for the SignalLoop MVP.

The API loads local environment values from the repository root `.env` file when it starts. Shell environment values take precedence over `.env`.

## Local commands

```sh
uv sync
uv run pytest
uv run uvicorn signalloop_api.main:app --reload
```

See `../../docs/development/testing.md` for the full test checklist and `../../docs/deployment/render-supabase-clerk.md` for hosted env setup.

## Phase 4 lifecycle endpoints

Create an invite-backed attempt:

```sh
curl -X POST http://127.0.0.1:8000/assessment-attempts \
  -H 'Content-Type: application/json' \
  -d '{"candidate_email":"candidate@example.com"}'
```

Open a candidate invite:

```sh
curl http://127.0.0.1:8000/candidate/invites/{invite_token}
```

Persist an edited file snapshot:

```sh
curl -X POST http://127.0.0.1:8000/candidate/invites/{invite_token}/snapshots \
  -H 'Content-Type: application/json' \
  -d '{"kind":"autosave","files":{"task_api/main.py":"..."}}'
```

## Phase 7 AI collaborator endpoint

The AI collaborator is constrained by backend policy before any provider call. Without `OPENAI_API_KEY`, the API uses a deterministic local guidance provider for development and tests.

```sh
curl -X POST http://127.0.0.1:8000/candidate/invites/{invite_token}/ai/messages \
  -H 'Content-Type: application/json' \
  -d '{"message":"This public test assertion failed. How should I debug it?","selected_context":{"path":"tests/test_public_api.py","content":"assert response.status_code == 409"}}'
```

Set these environment variables to use OpenAI:

```sh
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
```

## Phase 8 final submission endpoint

Final submission captures an immutable final code snapshot, final explanation, and decision log. The API then runs evaluator-only hidden tests through the worker and returns only a coarse hidden test status to the candidate.

```sh
curl -X POST http://127.0.0.1:8000/candidate/invites/{invite_token}/submit \
  -H 'Content-Type: application/json' \
  -d '{"files":{"task_api/main.py":"..."},"final_explanation":"...","decision_log":"..."}'
```

## Phase 9 evidence report endpoints

Generate or regenerate an Engineering Evidence Report after final submission:

```sh
curl -X POST http://127.0.0.1:8000/assessment-attempts/{attempt_id}/evidence-report
```

Fetch an existing persisted report:

```sh
curl http://127.0.0.1:8000/assessment-attempts/{attempt_id}/evidence-report
```

The report aggregates snapshots, test runs, hidden evaluation, AI interactions, final explanation, and decision log. It persists deterministic MVP scoring fields and a recommendation in `evidence_reports`. Manual evaluator review is still required before hiring decisions.

## Migrations

Use `DATABASE_URL` to point Alembic at the target database.

```sh
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/signalloop uv run alembic upgrade head
```

For a disposable local migration check without Postgres:

```sh
DATABASE_URL=sqlite:////tmp/signalloop_api.db uv run alembic upgrade head
```

Current migrations:

- `0001_create_core_tables`
- `0002_create_audit_events`
