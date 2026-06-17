# Known Limitations

These are intentional MVP boundaries or unresolved follow-up items.

## Execution

- Local development uses the Docker-based worker.
- Production execution with AWS ECS/Fargate per-run tasks is documented in ADR 0006 but not implemented.
- Backend-to-worker orchestration exists for both public and hidden test runs. Public test results are persisted as `TestRun` records with `run_type="public"` via `POST /candidate/invites/{token}/run-public-tests`.
- The worker must not be deployed to a platform that requires Docker-in-Docker or a host Docker socket inside a managed web-service container.

## Deployment

- Render/Supabase/Clerk deployment has documentation and env templates, but no hosted integration test has been run from this repo yet.
- Supabase should be configured through `DATABASE_URL`; no Supabase client SDK is used in the app.
- Clerk is wired into the web app. Backend Clerk authorization enforcement is not yet implemented; Phase 10/11 rely on the employer portal frontend login and local development fallback.

## Security And Pilot Hardening

- Rate limiting is in-memory and suitable only for a small pilot. It resets on process restart and is not shared across service replicas.
- Audit events are persisted for key lifecycle actions, but there is no admin audit viewer.
- Candidate invite tokens are bearer links. Anyone with a valid link can open that candidate workspace.
- No video proctoring, ATS integration, enterprise SSO, billing, marketplace, advanced plagiarism detection, or multi-assessment marketplace exists in the MVP.

## Assessment And Scoring

- The Engineering Evidence Report uses deterministic MVP heuristics and captured evidence. Manual evaluator review is still required before hiring decisions.
- The AI collaborator guardrails use LLM-based intent classification (single call returning structured JSON with `allowed`, `policy_tags`, `message`). Pattern matching is a fallback only. The LLM can still be manipulated via subtle multi-turn decomposition.
- There is one assessment pack: `fastapi_task_api_v1`.

## Product Workflow

- There is no employer organization/team management beyond the minimal employer portal.
- There is no email sending for invites; the employer copies the generated invite URL.
- There is no candidate account system; candidates use unique invite links.
