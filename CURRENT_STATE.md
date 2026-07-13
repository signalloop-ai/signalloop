# Current State

## Project status

MVP phases 1–12 and the post-MVP enhancement workstreams — Phase 2 (Assessment System),
Phase 3 (Proctoring), and Phase 4 (Super Admin Portal) — are implemented, validated, and
merged to `main`. Local and hosted pilot are working: Render web/API, Supabase persistence,
Clerk employer/admin auth, and candidate execution (`direct` on the hosted pilot; Docker
worker locally; ECS/Fargate scaffold for production).

**Phase 5 (Role-Adaptive Assessment System) MVP is implemented locally.**
Implementation docs live under
`docs/enhancements/phase-5-role-adaptive-assessment/`.

**Phase 6A (Question Bank Governance Foundation) is complete locally.**
Docs live under
`docs/enhancements/phase-6-question-bank-assessment-builder/`.

The AI collaborator was substantially redesigned post-MVP into a two-component architecture
with progressive disclosure — see `docs/retrospectives/ai-collaborator-journey.md` for the
full design history, and `docs/prompts/ai-collaborator-policy.md` for the current policy.

## Current phase

**Active workstream:** project closeout and open-source release preparation.

Open-source release preparation started:

- repository-level Apache-2.0 license file,
- author and citation metadata for joint publication,
- NOTICE and third-party assessment/question-bank source notes,
- contribution and security guidance,
- release checklist under `docs/release/open-source-release-plan.md`,
- internally authored question-bank source metadata now uses `Apache-2.0` instead of
  `Proprietary`.

Closeout browser hardening is implemented locally:

- candidate invite responses now include persisted webcam consent,
- a previously declined webcam choice survives page reloads without prompting again,
- a previously granted choice still prompts after reload so a new camera stream is established
  instead of silently disabling snapshot capture,
- the live hosted smoke spec now handles the optional webcam step, current submission-modal
  order, and the compact hidden-test status pill.

Hosted candidate smoke on 2026-07-13 reached the Render web/API and direct execution backend:
the workspace loaded, public tests executed, the AI anti-enumeration redirect appeared, final
submission completed, and hidden evaluation returned a result. The local smoke-spec corrections
still need deployment followed by one fresh-invite production rerun before the hosted checklist is
formally green.

Closeout validation:

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 297 passed, 51 skipped.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 23 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_closeout_webcam.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed with 4 known warnings.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e -- --workers=1` -> 35 passed, 2 skipped.

Phase 6A question-bank foundation is implemented locally:

- approved question bank as the unit of assessment content,
- super admin AI draft generation, edit, review, and approval,
- approved source allowlist captured for controlled public-source ingestion,
- question bank database model and migration,
- seeded draft-question queue across backend, frontend, system design, data, platform, and
  critical AI usage,
- Super Admin Question Bank page for metadata edit, approve, and reject,
- super-admin-only question-bank APIs.

Deferred question-level adaptive scope:

- role-based assessment blueprint assembly from approved questions,
- employer review with same-slot question swaps,
- mixed coding and written-response candidate assessments,
- AI-assisted draft scoring with reviewer override support,
- shared constrained AI-helper policy across all question types.

Phase 6A is governance infrastructure, not an employer/candidate assessment flow. Its approved
questions are not yet assembled into employer blueprints, delivered to candidates, or scored in
reports. Those capabilities remain a documented future problem.

The usable Phase 5 flow is **guided role matching**: role/JD requirements are mapped to the
closest currently registered assessment (Standard or Advanced FastAPI), or reported as
unsupported. It does not compose a new assessment from individual questions. Candidate resume
context is used for gaps, follow-up probes, and report context, not scored-question selection.

**Last completed implementation workstream:** Phase 5 — Role-Adaptive Assessment System MVP.

The Phase 5 MVP adds an adaptive planning layer before invite creation:

- employer pastes or uploads role/JD requirements and optional candidate resume text,
- system maps both into a versioned skill taxonomy,
- system recommends a reviewable assessment blueprint,
- employer approves the blueprint before sending an invite,
- the existing candidate assessment flow remains unchanged,
- blueprint-backed reports show role context, skill coverage, caveats, and follow-up probes.

Core Phase 5 boundary: for v1, the role/JD determines the comparable core assessment. Resume
data influences rationale, caveats, and follow-up probes, but does not automatically give
different candidates for the same role different scored coding tasks. Current executable
support remains limited to Standard FastAPI v2 and Advanced FastAPI v1; unsupported skills are
shown explicitly as caveats/follow-up areas, not scored evidence.

Phase 5 implemented:

- static skill taxonomy in `apps/api/signalloop_api/assessment_taxonomy/skills.json`,
- current module coverage in `apps/api/signalloop_api/assessment_taxonomy/module_coverage.json`,
- strict taxonomy loader/validator,
- deterministic skill extraction and matching,
- title-aware contextual family precedence so backend Python roles can match current FastAPI
  coverage without allowing Python/FastAPI keywords to override data, frontend, platform, or
  explicit ML-engineering role families,
- role profiles, candidate profiles, and assessment blueprints,
- approved blueprint -> invite creation,
- nullable attempt blueprint link,
- adaptive report context for blueprint-backed reports,
- optional guided role matching in the employer Assessments view.
- guided role matching document text extraction for TXT/MD, DOCX, and best-effort
  text-based PDF uploads. Scanned PDFs are not OCR-supported.

Validation:

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 288 passed, 51 skipped.
- `DATABASE_URL=sqlite:////tmp/signalloop_phase5_adaptive_migration_2.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q` -> 27 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed with 4 known warnings.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e -- --workers=1` -> 33 passed, 2 skipped.

Open follow-ups outside Phase 5: production execution isolation (`ecs_fargate`, see
`docs/deployment/production-isolation-plan.md`) and optional local S3 for snapshots. Earlier
phase notes follow as historical record.

**Phase 4 is implemented.** The super admin portal is built and validated:
recruitment list, per-employer operational summary, and drill-through to any
employer's evidence report. Admin uses the same Clerk login; role is assigned
from `SUPER_ADMIN_EMAILS` env var. Admin is view-only — cannot create invites.

Phase 2 is complete. All 11 planned Phase 2 tasks are implemented, locally validated,
and deployed to Render. The current state reflects the June 2026 UI polish session which
also switched hosted execution to `DirectExecutionProvider` (`EXECUTION_BACKEND=direct`).

## Settled state after June 2026 Calibr dark redesign

- **New design language** derived from the Calibr reference UI is documented in
  `docs/design/calibr-design-language.md` (dark navy palette, Inter + JetBrains Mono,
  component patterns, and the supported-vs-unsupported product mapping).
- **Theme flipped light → dark in one place.** `apps/web/src/app/globals.css` `:root` now
  holds the Calibr dark tokens (`--bg0..bg4`, `--b0..b2`, `--t0..t2`, semantic fg/bg pairs)
  plus legacy aliases (`--bg`, `--panel`, `--accent`, …) so existing class selectors resolve
  to dark values. All raw-hex selectors were remapped to tokens. Score thresholds:
  ≥80 green, 60–79 amber, <60 red. Applies to employer, admin, evidence report, and the
  candidate workspace (Monaco was already `vs-dark`).
- **Fonts:** Inter + JetBrains Mono loaded via `<link>` in `layout.tsx`; all numeric values
  (scores, counts, timers) use `var(--font-mono)`.
- **Brand logo** recolored from teal (`#0f766e`/`#5eead4`) to the blue/cyan accent
  (`#3b82f6`/`#22d3ee`) across employer, admin, report, and candidate pages.
- **Employer "Build assessment" flow** restructured to the Calibr layout: a single
  "Coding challenge (Python)" module card with a **Basic/Advanced** level selector
  (mapped to `standard_v2` / `advanced_v1`), plus a right-hand **Assessment summary** panel
  (Modules / Total time tiles) holding the candidate email, **Timing enforcement**
  (Strict = timed/hard-cutoff vs Untimed; "Soft limit" intentionally dropped), evaluator
  feedback, and Send invite. The Calibr "Score visibility" control is intentionally absent
  (not supported). Other Calibr modules (system design, SQL, psychometric, etc.) are not
  offered — coding is the only module.
- **Clerk sign-in modal + UserButton popover** keep Clerk's default (readable) light
  surface with only `colorPrimary` tinted to our blue. Forcing a dark `colorBackground`
  (and Clerk's `dark` base theme, which did not apply in this version) made the modal text
  and the "Continue with Google" button invisible — both were removed. Verified in-browser:
  the sign-in modal renders with a clearly visible Google button. `@clerk/themes` is not a
  dependency.
- **Employer portal restructured into the Calibr app shell**: fixed top bar + left
  sidebar with a Workspace nav (Overview, Assessments, Candidates, Reports) and an Account
  section (Settings, Help & docs — placeholders). Client-side view switching via `nav`
  state, no routing change.
  - **Overview**: four colored stat tiles (total/submitted/in-progress/invited), explicit
    Manual selection vs Guided role matching creation-path guidance, How-it-works, and
    recent-activity feed.
  - **Assessments**: the live "Coding challenge" card (Basic/Advanced) + send panel, plus a
    "More assessment types — Coming soon" roadmap grid (Debugging, System design, AI & LLM,
    SQL, Logical reasoning, Psychometric, Communication) shown as non-selectable preview
    cards with per-module accent icons. These remain unsupported — they only advertise the
    roadmap.
  - **Candidates**: filterable (All/Submitted/In progress/Invited) attempt table.
  - **Reports**: submitted attempts with report links.
- **Local full stack confirmed running** for manual testing: API (`uvicorn` on `:8015` with
  local Postgres, migrations current) + web (`:3000`). With the API down, the employer page
  shows "Failed to fetch" and counts stay at 0 — that was the cause of the
  "counts not incrementing / Send invite does nothing / candidate data not updating" reports,
  not a frontend bug. Send invite verified working (count incremented, invite URL generated).
- **Verification:** web `tsc --noEmit` clean and `next build` passing. Playwright e2e:
  **30 passed / 2 skipped** (the two live specs auto-skip without API tokens) with
  `--workers=1`. The employer create-invite e2e was updated for the new segmented controls
  (level/timing/evaluator are now `role="group"` buttons; submit is "Send invite"; the email
  input carries `aria-label="Candidate email"`). Employer dashboard, candidate IDE (populated,
  `vs-dark` Monaco), and evidence report were all visually confirmed in-browser in the dark
  theme. Pre-existing lint findings (set-state-in-effect, snapshot exhaustive-deps) are
  unchanged; one new no-page-custom-font warning from the font `<link>`.

## Last completed phase

Phase 4: Super Admin Portal (roster, employer detail, report drill-through).

Phase 2: Assessment System Enhancement (all tasks, including hosted deployment and
UX polish close-out).

## What exists

- Portable Markdown documentation structure.
- Technical Product & Architecture Spec.
- Coding Agent Execution Plan.
- Phase-by-phase execution files.
- Phase index and developer setup notes.
- Initial ADRs.
- ADR 0006 documenting local Docker execution for development and AWS ECS/Fargate per-run tasks for production execution.
- ADR 0007 documenting LLM-based AI policy evaluation with fallback classification.
- ADR 0008 documenting the deterministic six-category MVP scoring rubric.
- Render Blueprint scaffold for web/API deployment.
- AWS ECS/Fargate runner scaffold for future production execution.
- API-side execution provider switch with `EXECUTION_BACKEND=http_worker` for local/staging and `EXECUTION_BACKEND=ecs_fargate` for AWS ECS/Fargate.
- Assessment design documentation.
- Prompt policy documentation.
- Report structure documentation.
- Placeholder app folders: `apps/web`, `apps/api`, `apps/worker`.
- Shared package placeholder: `packages/shared`.
- Assessment pack implementation: `assessment_packs/fastapi_task_api_v1`.
- Phase 2 standard assessment pack implementation:
  `assessment_packs/fastapi_task_api_standard_v2`.
- Phase 2 advanced assessment pack implementation:
  `assessment_packs/fastapi_task_api_advanced_v1`.
- Root `.gitignore` and `.env.example`.
- Candidate assessment README, starter FastAPI app, public tests, and historical final explanation template for the MVP pack.
- Evaluator-only hidden tests, reference solution notes, scoring rubric, manual evaluation form, and reference solution.
- `uv` documented as the Python dependency and command runner for assessment development.
- Backend API project in `apps/api` with FastAPI app, SQLAlchemy models, Alembic migrations, database session setup, health endpoint, and tests.
- Candidate attempt lifecycle API endpoints for creating invites, opening candidate invite links, returning candidate-safe assessment metadata/files, and saving snapshots.
- Worker service in `apps/worker` with public test-run API, Docker runtime image definition, workspace materialization, hidden/evaluator file rejection, timeout/resource controls, and tests.
- Web app in `apps/web` with candidate invite workspace UI, Monaco editor, direct public test execution through the worker, and structured Submission Review form.
- Candidate workspace polish from local validation: visible candidate instructions, resizable file/AI/submission panels, independent scroll containers, Enter-to-send chat, explicit save status, and visible submission requirements.
- Backend-to-worker public test-run orchestration through `POST /candidate/invites/{token}/run-public-tests`, with public test snapshots and `TestRun` records persisted for evidence reports.
- Constrained AI collaborator endpoint with provider abstraction, OpenAI provider, local fallback provider, system prompt, guardrail classifier, context boundary checks, AI message logging, policy tags, and workspace chat UI.
- Phase 2 AI policy tightening is implemented locally: the assistant may compare
  tradeoffs but must not choose the candidate's design, and prompt-injection attempts
  are classified as disallowed evidence.
- Final submission endpoint with immutable final code snapshot, structured Submission Review evidence, attempt locking, backend-orchestrated hidden worker run, hidden `TestRun` persistence, and candidate-safe submission response.
- Worker hidden-test endpoint for backend-supplied evaluator tests.
- Skipped-by-default live full-stack Playwright smoke test enabled with `LIVE_INVITE_TOKEN`.
- Engineering Evidence Report generation and fetch endpoints, with persisted report JSON, recommendation, score total, scoring categories, FAVO analysis, timeline, and follow-up questions.
- Phase 2 deterministic scoring rubric is implemented in the report generator for
  public issue resolution, private issue generalization, feature/design implementation,
  candidate-written tests, AI collaboration, and regression/code quality.
- Employer attempt list API endpoint with invite URLs and evidence report summary metadata.
- Employer web portal at `/employer` with Clerk login (always required), invite creation, candidate attempt list, and report detail pages.
- Employer invite creation now supports Phase 2 assessment configuration fields:
  standard assessment, timed/untimed mode, and fixed duration options of 60, 90,
  120, and 150 minutes. Employers can select Standard FastAPI v2 or Advanced
  FastAPI v1.
- Time-boxed assessment flow is implemented locally: candidate accept starts the
  server timer, timed attempts show a countdown with warnings, expiry auto-submits
  the current browser files when the tab is open, backend expiry is enforced on
  snapshots/public tests/AI/final submission, and reports include timing metadata.
- Phase 2 UI enhancements are implemented locally: candidate Submission Review uses
  structured prompts plus a final confirmation modal, and employer reports show
  timing metadata, native score/test bars, feature/design summary, FAVO-style
  interpretation, and AI integrity risk.
- Phase 2 report generation is implemented locally with deterministic score sections,
  structured Submission Review evidence, FAVO, AI integrity risk, feature/design
  implementation, and explicit LLM-assisted review status.
- Backend employer routes enforce Clerk-user employer ownership for invite creation,
  attempt listing, and evidence-report generate/fetch. Both local and production
  environments always require a valid Clerk JWT — no dev-fallback bypass exists.
  `EMPLOYER_AUTH_REQUIRED` and the local employer identity config have been removed.
- API audit events persisted in `audit_events` through Alembic migration `0002_create_audit_events`.
- API request validation/fallback error handlers and basic in-memory rate limiting.
- Retry-bounded hidden worker calls with configurable timeout/retry settings.
- Worker CORS origins configurable through `WORKER_CORS_ORIGINS`.
- Local and hosted environment templates: `.env.local.example` and `.env.render-supabase.example`.
- Render + Supabase + Clerk pilot deployment guide at `docs/deployment/render-supabase-clerk.md`.
- AWS ECS/Fargate execution deployment guide at `docs/deployment/aws-ecs-fargate-execution.md`.
- Root README updated with current MVP status, local run sequence, test commands, deployment direction, and known-limits pointer.
- Development handoff docs: `docs/development/testing.md`, `docs/development/known-limitations.md`, and `docs/development/local-pilot-checklist.md`.
- Phase 2 enhancement documentation under `docs/enhancements/phase-2-assessment-system/`.
- Phase 2 planning decisions include Clerk-user-based strict employer isolation,
  structured Submission Review, report-only AI integrity risk, removal of the
  employer-facing generic confidence label, richer report/candidate UI polish, and
  a planned configurable evaluator feedback mode.
- Evaluator feedback mode is implemented locally. Strict mode remains the default:
  public test feedback during active work, with hidden/evaluator counts employer-report-only.
  Guided mode shows aggregate evaluator pass/fail counts during active work while still
  hiding hidden test names, tracebacks, failure messages, file paths, and line numbers.
- Execution timing breakdown is implemented locally for API/worker public runs, guided
  evaluator runs, and final hidden evaluation so latency can be measured before changing
  ECS/Fargate architecture.
- Candidate IDE ergonomics are implemented locally: lightweight Python syntax diagnostics,
  clickable public-test file/line output, color-coded public test output, and file
  indicators based only on candidate-visible files and public test output.
- Deterministic API scenario tests cover representative candidate submission outcomes:
  unchanged starter code, public-only fixes, strong submissions, weak submission review,
  AI-risk evidence, standard rubric, and advanced rubric/guided mode metadata.
- Opt-in live OpenAI policy validation exists and passed locally for the real
  OpenAI-backed AI collaborator prompt across allowed and blocked candidate question types.
- Advanced FastAPI assessment design is specified in
  `docs/assessment/fastapi-task-api-advanced-v1.md` and implemented in
  `assessment_packs/fastapi_task_api_advanced_v1/`.

## Settled state after June 2026 redesign

- Standard v2 rubric: 15/20/20/15/15/15 (public/private/feature/tests/ai/regression), 60 min default.
- Advanced v1 rubric: 15/15/25/15/15/15 (feature gets 25 pts), 120 min default.
- AI collaboration scoring tiers: 0 use = 8/15 (floor), clean use = 15/15, 1 violation = 6/15, 2–3 = 3/15, 4+ = 0/15.
- LLM-assisted review section hidden from employer report UI (field still present in JSON payload).
- Assessment pack READMEs include "How your submission is evaluated" section covering quality expectations.
- API test suite: 76 passed / 11 skipped.

## Settled state after June 2026 proving-tests + AI policy session

- **Candidate test scoring** uses proving tests, not keyword heuristics. A proving test
  fails on the original starter code AND passes on the candidate's submitted code.
  Scoring: 0→0, 1→6, 2→11, 3+→15. Verification runs at report-generation time via the
  new worker endpoint `POST /run-candidate-verification`.
- **Standard v2** `seeded_issue_count` is now 5 (priority test removed — priority had
  no public test signal and was unfair to candidates).
- **AI policy** system prompt leads with "Default: answer the question." The
  `no_issue_identified` tag fires only for vague "find my bugs" requests with no specific
  issue, code, or test named. Post-implementation review and conceptual questions are
  always answered. Code responses must give only the changed lines, not whole functions.
  Prompt-injection patterns expanded.
- **Assessment READMEs** use `{{DURATION_MINUTES}}` placeholder substituted at serve
  time; no more hardcoded time limits in pack files.
- **Submitted code viewer** appears in the employer report page (tab-based, defaults to
  `task_api/main.py`, max-height 520 px). The `submitted_code` field is present in the
  report JSON sorted as: `task_api/` first, `tests/` second, config files last.
- AI policy test suite: 59 tests (was 10), including 9 prompt-injection cases.

## Settled state after June 2026 progress checklist + enhancement feedback session

- **Enhancement feedback** is always computed and returned on every public test run,
  regardless of guided/strict mode. The evaluator's hidden tests always run; the
  `feature_design_tests` list in the pack config determines which hidden tests count as
  enhancement tests. Applies to standard_v2 and advanced_v1.
- **`enhancement_summary()` error guard**: if the evaluator Docker run fails,
  `enhancement_feedback` returns all-zeros rather than incorrectly reporting all tests as
  passing.
- **Hidden checks progress item** (guided mode) now shows only the non-enhancement hidden
  tests (edge-case/quality), so counts are non-overlapping with "Enhancements built".
  In strict mode, a static row "additional behaviors evaluated at submission" is always
  shown so candidates know edge-case testing exists.
- **Candidate test count** correctly shows tests added beyond the original starter.
  Root cause fixed: `initial_files` is now a separate API field (original starter from
  pack path, never overwritten by a snapshot). Previously both `files` and `initialFiles`
  were set to the current snapshot on load, making the diff always zero.
- **Evaluator notes removed from test output panel**: the "Notes: additional behaviors
  evaluated…" and "Evaluator checks: N passed…" paragraphs are removed. The progress
  checklist is now the single source for all evaluator feedback.
- **Test count**: `initial_files: dict[str, str]` added to `CandidateAttemptResponse`
  schema.

## Settled state after June 2026 UX polish + DirectExecution session

- **DirectExecutionProvider**: `EXECUTION_BACKEND=direct` runs pytest inline in the API
  process via subprocess. ~7s vs ~50s ECS cold start. Used on Render for pilot only — no
  container isolation. Switch to `ecs_fargate` for production. Both
  `.env.example` and `.env.render-supabase.example` updated to `direct`.
- **Candidate workspace** fully redesigned as an IDE-style layout: left file explorer,
  top bar with logo + status chips + progress pills + Run/Submit buttons, right panel
  with "What to do" (resizable) + AI Collaborator sections, collapsible bottom test
  output drawer.
- **Status chips** conditionally render: Public tests, Edge cases, Enhancements, My tests
  chips only appear when real data exists. Divider hidden when no chips are visible.
  Status label "started" → "In progress". Duration: "Recommended 90 min".
- **Chip labels finalized**: "Public" → "Public tests", "Hidden" → "Edge cases",
  "Enhanced" / "Feature/design" → "Enhancements", "Tests" → "My tests".
- **Elapsed timer** shown during test run and submission ("Running tests… 3s").
- **Employer portal** professionally redesigned: SignalLoop logo, auto-poll every 30s
  (no Refresh button), inline Create invite button next to email field, inline Details
  button next to assessment select, colored score badge, `timeAgo` helper for sent-at
  display, assessment detail modal sourced from evaluator rubric MD files, flat table
  header (no border/card on header row).
- **Evidence report** professionally redesigned: logo in header, amber Regenerate button
  with confirm dialog, CSS `data-tooltip` metric card tooltips, follow-up interview
  questions promoted above score breakdown, FAVO section subtitle, process evidence as
  mini metric cards, score breakdown bar chart with jump-link labels, "Enhancements"
  label throughout (was "Feature/design implementation").
- **Score breakdown**: bar chart labels are anchor `<a>` tags that scroll to the
  corresponding detail section. Score chip list removed — bar chart is the only
  summary element.
- **Web typecheck/build**: passing. All changes pushed to `main` and deployed to Render.

## Settled state after June 2026 report polish + scoring fixes session

- **Evidence report redesigned**: score summaries always visible; verbose lists
  (failure names, seeded areas, file diffs, AI prompts, timeline) collapsed behind
  `<details>/<summary>` Disclosure components. Page is crisp at a glance and detailed
  on demand.
- **Regression scoring proportional**: `reg_score = rubric_weight × (1 - regressed/originally_passing)`.
  A candidate who regresses 1 of 10 tests loses 10% of the regression category, not all of
  it. Candidate-added tests are excluded from regression detection via `original_test_names`
  set built from initial files.
- **Candidate test display**: employer report now shows "N functions added · M modified"
  instead of file/function/assertion counts. Backend `candidate_test_evidence()` does a
  name-level function diff — `functions_added` = new test names, `functions_modified` =
  existing names whose body changed. HTTP assertion count removed from display (kept for
  scoring heuristic).
- **Large paste threshold**: `PASTE_LINE_THRESHOLD` raised from 8 → 25 lines. Prevents
  single test functions from being flagged as suspicious pastes.
- **Integrity risk thresholds updated**: `large_paste_count >= 3` (was ≥2) triggers
  "high"; 1–2 large pastes → "medium". Prevents two legitimate large test writes from
  producing a "high" integrity label.
- **Submission review format**: employer report now shows only non-empty fields
  dynamically. Old 4-field form and new 2-field form both display correctly. Candidates
  who filled only "What changed" see just that field; no empty label/dash rows.
- **Weak submission review threshold**: `required_question_count` now comes from the
  form format. New 2-field form has 1 required field (what changed); only an empty
  submission triggers `weak_review = true`.
- **`flag_modified` for JSON persistence**: `flag_modified(evidence_report, "report")`
  added before commit in the report generate endpoint so SQLAlchemy flushes JSON column
  updates on regenerate.
- **API test suite**: 127 passed, 11 skipped.

## Settled state after June 2026 Phase 3 proctoring session

- **Webcam consent prompt**: candidate sees an opt-in webcam prompt before the workspace
  loads. Consent is recorded via `POST /candidate/invites/{token}/webcam-consent`. "Skip"
  dismisses the prompt and shows the workspace without webcam.
- **Proctoring events**: focus-loss and fullscreen-exit events are queued client-side and
  flushed in batches via `POST /candidate/invites/{token}/proctoring-events/batch`.
  Events are flushed before final submission.
- **Snapshot thumbnails**: employer report shows webcam snapshot thumbnails in a
  `.snapshot-strip` for attempts with webcam consent.
- **Focus-loss timeline**: employer report shows a collapsible "Focus-loss timeline (N events)"
  table with duration and timestamps.
- **Integrity score banners**: employer report shows no banner (low), amber (medium), or
  red (high/critical) integrity banners with contributing factor summaries.
- **Submission mode**: `auto_expired` submission mode is tracked and displayed; webcam
  prompt auto-hides when `submitted=true` to avoid blocking the auto-submit flow.
- **E2E test coverage**: 30 tests across candidate-workspace, employer-portal, and
  phase-3-proctoring specs all pass with `--workers=1`.
- **API test suite**: all passing.

## Settled state after June 2026 Phase 4 super admin portal session

- **Super admin portal** at `/admin` gives the operator full visibility into
  all employers, their attempts, and evidence reports — without logging in as
  that employer. Admin is **view-only**: cannot create invites, regenerate
  reports, or modify anything.
- **Auth model**: same Clerk app as employers. `SUPER_ADMIN_EMAILS` env var
  (comma-separated, case-insensitive) drives role assignment at login. A new
  nullable `role` column on `employers` (migration `0008_add_employer_role`)
  stores `'super_admin'` or `NULL`. Role is re-evaluated on every login, so
  removing an email from the env var downgrades on next session.
- **`get_current_super_admin`** FastAPI dependency protects all `/admin/*`
  endpoints: 401 if unauthenticated, 403 if authenticated but not admin.
  Regular `get_current_employer` is unchanged — no behavior change for
  non-admin employers.
- **`GET /employer/me`** returns `{ id, email, role }` so the frontend can
  route admins to `/admin` and bounce non-admins from `/admin` to `/employer`.
- **Admin API** (`apps/api/signalloop_api/admin.py`): `GET /admin/me`,
  `GET /admin/employers` (roster with invite/submitted/report counts + avg
  score), `GET /admin/employers/{id}` (Tier 2: status breakdown, score
  distribution, AI usage, pack breakdown, stuck signals, full attempt list),
  `GET /admin/attempts/{id}/report` (any employer's report, no ownership
  check).
- **Frontend**: `/admin` (roster, auto-refresh 60s), `/admin/employers/[id]`
  (per-employer drill-down with metric cards + attempt table),
  `/admin/reports/[attemptId]` (full evidence report view, admin can see any
  employer's report). Layout reuses employer-portal styling, no invite
  creation controls visible.
- **Admin email**: `redacted-personal-email@example.com` (set in `SUPER_ADMIN_EMAILS`).
- **API test suite**: 12 admin endpoint tests added
  (`tests/test_admin_endpoints.py`); all pass. Full suite 336 passed, 11
  skipped, 1 pre-existing unrelated failure (AI policy paste heuristic).
- **Web typecheck/build**: passing. Admin routes registered:
  `/admin` (static), `/admin/employers/[id]` (dynamic),
  `/admin/reports/[attemptId]` (dynamic).

## Settled state after June 2026 AI collaborator permanent redesign

- **Root cause of recurring AI-collaborator bugs was structural**: three independent
  classifiers (LLM classifier, Python keyword `fallback_classify`, and a keyword output
  guard) each re-decided the same thing and overrode one another, so every keyword fix
  created a new false positive.
- **New architecture is two components, one responsibility each.** The **classifier**
  (`CLASSIFIER_PROMPT`) is the single source of truth for block-vs-allow and leans allow;
  it never decides code-vs-Socratic. The **generator** (`GENERATOR_PROMPT`, Mode A/Mode B)
  is the only owner of the give-code-vs-coach decision and its output is returned verbatim.
- **Three behavior rules** (generator): (1) candidate identified the problem — public,
  hidden, or enhancement — and knows the fix → give the changed lines; (2) candidate asks
  the assistant to find the problem → coach Socratically (not a block, not a scored
  violation); (3) general/concept question → answer directly.
- **One deterministic block**: `is_pasted_test_code()` pre-gate (structural, runs before the
  LLM). `fallback_classify` is now lenient/availability-only and never overrides a working
  LLM. `no_issue_identified` is no longer emitted/blocked.
- **Message-ordering bug fixed** in `ai.py`: recent candidate messages are now passed
  chronologically (oldest→newest).
- Deleted `tests/test_ai_output_guard.py`; rewrote `test_ai_policy.py` and
  `test_two_step_pipeline.py` to assert the contract instead of keyword internals.
- **API test suite: 254 passed.** Decision rationale and the do-not-add-a-third-layer rule
  are documented in `docs/prompts/ai-collaborator-policy.md` and `docs/development/changes.md`
  (2026-06-23 entry).
- **Live regression net** (`tests/test_live_ai_policy.py`, 42 cases) grounds scenarios in the
  real seeded issues of both shipped packs and was run against real models (`gpt-4o` /
  `gpt-4o-mini`): **42 passed**. Run with
  `cd apps/api && RUN_LIVE_AI_TESTS=1 uv run pytest tests/test_live_ai_policy.py`.
- The live net caught one real false positive on first run (a single "make that change for
  me" follow-up tagged `anti_decomposition`); fixed by tightening the classifier prompt
  (anti_decomposition now requires a broad multi-issue sweep) with a counter-example and a
  live test that a genuine sweep still blocks.

## Settled state after June 2026 AI collaborator pedagogy + docs completion

- **Progressive disclosure** is the collaborator's pedagogy: guide first, give code once the
  candidate demonstrates the approach. Bug fix → minimal changed lines (never whole function);
  enhancement/test → focused code once the gist is shown; concept → answered directly. The gate
  is demonstrated understanding, not a turn count; pure deflection never yields code.
- Classifier loosened so single-feature/single-test requests and "give me the code for this"
  follow-ups are allowed (the generator gates them); singular "find the bug for me" is fishing,
  not enumerate_defects.
- **Workspace grounding:** the generator reads the candidate's candidate-visible files and
  answers about their actual code.
- **Prod model:** generator runs on `gpt-4o` (default + both `.env` examples). `gpt-5` failed
  in prod because it needs `max_completion_tokens` and a larger budget (reasoning model); the
  OpenAI error is now logged instead of swallowed.
- **Candidate guidance:** the AI Collaborator panel has a collapsible "How to work with the AI"
  tips block, and both candidate READMEs have a how-to + good/bad prompt table.
- **Docs:** `docs/retrospectives/ai-collaborator-journey.md` (full design history, blog-ready);
  architecture spec §12/§17 updated to the two-component + progressive-disclosure design and
  Phase 3/4 marked implemented; `docs/deployment/production-isolation-plan.md` for the
  `ecs_fargate` path.
- All work merged to `main`. API suite 261 passed; live AI suite 48 passed; web build + e2e pass.

## What does not exist yet

- External LLM-assisted report review is not invoked yet; reports include
  `llm_assisted_review.status=not_run` until a bounded prompt and safety boundary are
  added.

## Next task

**All phases complete and merged to `main`.** No active build task. Candidate-facing,
employer, and admin flows are working on the hosted pilot.

Optional follow-ups (not blocking the pilot):
- Production execution isolation: move hosted execution from `direct` to `ecs_fargate`
  (`docs/deployment/production-isolation-plan.md`).
- Local snapshots via S3 (needs an admin-created dev bucket + CORS), or keep the inline
  data-URL fallback that already works locally.
- Optional `gpt-5` generator support (needs `max_completion_tokens` + a larger budget); the
  pilot runs on `gpt-4o`.

Phase 3 (proctoring) and Phase 4 (super admin portal) are implemented, validated, and merged.

Phase 2 historical reference: see `docs/development/changes.md` for the full session-by-session log. Phase 2 final hosted validation (2026-06-18) passed with API tests 38 passed, worker tests 22 passed, web typecheck/lint/build passed, Playwright e2e 2 passed/1 skipped, and a full browser-level attempt (public tests → submission → hidden evaluation → report generation → report rendering) working on Render without browser console errors.

## Notes for next coding agent

The original MVP phase plan is complete through Phase 12. Use it as historical context, not the active implementation plan.

Current closeout reference:

`docs/enhancements/phase-6-question-bank-assessment-builder/`

Phase 6A governance is complete. Question-level adaptive composition is deferred and must begin
as a new explicitly bounded enhancement if work resumes.

Deployment architecture note: use local Docker worker for development/testing. Production execution should target AWS ECS/Fargate per-run assessment runner tasks instead of Docker-in-Docker on Render or another managed web-service runtime. Render remains suitable for web/API, Supabase for Postgres, and Clerk for employer auth.
