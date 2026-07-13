# Changes Log

Running record of bugs found, fixes applied, and important config changes made during
post-MVP validation. Read this before touching the files listed under each entry.

---

## 2026-07-13 — Persisted webcam decline and live smoke alignment

**Symptom:** A hosted candidate smoke reached the optional webcam screen after rules acceptance,
and the same prompt returned on every fresh page even after the candidate declined and the API
persisted that choice. The live smoke spec also used the pre-modal submission order and expected
older hidden-test result copy.

**Root cause:** The candidate invite response omitted `webcam_consent`, so the web workspace
always initialized consent as unanswered. The live smoke spec had not been updated when the
optional webcam step, modal-based submission review, and compact hidden-test status pill were
introduced.

**Files changed:**
- `apps/api/signalloop_api/schemas.py` — exposes persisted webcam consent in the candidate-safe
  invite response.
- `apps/api/signalloop_api/attempts.py` — maps the attempt's consent value into invite responses.
- `apps/api/tests/test_attempt_lifecycle.py` — verifies the public consent PATCH -> invite GET
  persistence seam.
- `apps/web/src/app/invite/[inviteToken]/page.tsx` — restores a persisted decline on load/accept;
  prior grants still re-prompt so an active media stream is re-established after reload.
- `apps/web/tests/e2e/phase-3-proctoring.spec.ts` — covers reload after a persisted decline.
- `apps/web/tests/e2e/live-full-stack-smoke.spec.ts` — handles optional webcam consent, current
  submission-modal order, and current hidden-test status copy.
- `CURRENT_STATE.md` — records the closeout hardening and validation status.
- `docs/development/changes.md` — records this fix for handoff.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` passed, 297 tests with 51 skipped.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` passed, 23 tests.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_closeout_webcam.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` passed.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run lint` passed with 4 known warnings.
- `cd apps/web && npm run build` passed.
- `cd apps/web && npm run test:e2e -- --workers=1` passed, 35 tests with 2 live tests skipped.

**Follow-up items:** Deploy the API/web changes, create a fresh throwaway invite, and rerun the
corrected hosted smoke spec so the production command itself finishes green.

---

## 2026-07-13 — Open-source cleanup and hosted deployment repair

**Symptom:** After the GitHub organization transfer, Render API deploys failed because the API
service was configured as Docker and looked for a root `Dockerfile`. The project also still had
local/generated artifacts in the working tree that should not be part of the open-source release.

**Root cause:** The Render API service runtime had changed from Python to Docker during the source
reconnect. The repo also contained local tooling/deck outputs and an unrelated marketing draft
that were never intended as SignalLoop release artifacts.

**Files changed:**
- `.gitignore`
- `README.md`
- `CURRENT_STATE.md`
- `docs/development/changes.md`
- `docs/release/open-source-release-plan.md`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/README.md`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/frontend-platform-engineer-jd.docx`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/frontend-platform-engineer-jd.pdf`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/data-engineer-analytics-platform-jd.docx`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/data-engineer-analytics-platform-jd.pdf`

**Removed local/untracked artifacts:**
- `docs/marketing/blog-ccr-setup.md`
- `opencode.json`
- `outputs/`

**Validation:**
- Render API service `signalloop-api` patched back to `runtime=python`.
- Render API deploy `dep-d9a76t7avr4c73anfjv0` completed with status `live`.
- `https://signalloop-api.onrender.com/health` -> 200 `{"status":"ok"}`.
- `https://signalloop-web.onrender.com/employer` -> HTTP 200.
- After the webcam-consent fix was deployed, a fresh hosted candidate smoke passed against
  production attempt `34`: workspace loaded, public tests executed, the AI anti-enumeration
  redirect appeared, final submission completed, hidden status rendered, and the persisted invite
  response showed `webcam_consent=false`.

**Follow-up items:** Revoke or rotate the Render CLI token used for the repair; confirm `rdhoot`
accepted the GitHub invite and has the intended access level; run final secret/history scan before
making the repository public; complete the remaining release-demo checks for employer report
generation and guided role matching.

---

## 2026-07-12 — Open-source release scaffold

**Symptom:** The project was ready to move from implementation closeout into public-release
preparation, but the repository did not yet contain license, notice, authorship, citation,
contribution, security, or release-boundary files. Internal question-bank source metadata also
still labeled SignalLoop-authored content as proprietary.

**Root cause:** The project had been developed privately through MVP and post-MVP phases, so
open-source release metadata had not been added yet.

**Files changed:**
- `LICENSE`
- `NOTICE`
- `AUTHORS.md`
- `CITATION.cff`
- `THIRD_PARTY_NOTICES.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `docs/release/open-source-release-plan.md`
- `apps/api/signalloop_api/admin.py`
- `README.md`
- `CURRENT_STATE.md`

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py -q`
  -> 17 passed.
- `git ls-files | rg '(^|/)\\.env($|\\.)|\\.pem$|\\.key$|secret|credential|token'`
  -> only tracked env example templates matched.
- Tracked-file credential pattern check found only false positives from SignalLoop package names
  beginning with `signalloop-fastapi...`; no API key, GitHub token, AWS key, Slack token, or
  private-key filename/content pattern was found in tracked files.

**Follow-up items:** Update the final GitHub organization URL in `CITATION.cff`, run a
secret/history scan, and sanitize demo/blog artifacts before making the repository public.

**Update:** Planned GitHub organization namespace selected as `signalloop-ai`; `CITATION.cff`
now points to `https://github.com/signalloop-ai/signalloop`.

---

## 2026-07-12 — Guided role matching contextual family precedence

**Symptom:** A short but explicit `Backend Python Engineer` role was rejected because Python was
present in the taxonomy and current assessment coverage but absent from the narrow FastAPI-fit
gate. Simply accepting Python or FastAPI globally could incorrectly route data, ML, frontend, or
platform roles to a backend assessment.

**Root cause:** Role titles were stored but excluded from taxonomy extraction, and eligibility
used individual backend technology signals without a symmetric primary-family context rule.

**Files changed:**
- `apps/api/signalloop_api/adaptive.py`
- `apps/api/signalloop_api/adaptive_blueprint.py`
- `apps/api/tests/test_adaptive_assessment.py`
- `apps/web/src/app/employer/page.tsx`
- `docs/enhancements/phase-5-role-adaptive-assessment/03-blueprint-generation.md`
- `CURRENT_STATE.md`

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_adaptive_assessment.py tests/test_assessment_taxonomy.py -q` -> 30 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 296 passed, 51 skipped.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed with 4 known warnings.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1` -> 8 passed.

**Follow-up items:** Keep role interpretation deterministic for the closeout release. A hybrid LLM
interpreter with deterministic final eligibility remains a possible future enhancement, not part
of v0.1.

---

## 2026-07-12 — Project closeout boundary and guided role matching language

**Symptom:** The employer portal called the Phase 5 recommendation flow an Adaptive Builder even
though it selects between the registered Standard and Advanced FastAPI packs rather than
assembling a new assessment from Phase 6A questions. Project status also left the broader Phase 6
workstream active after the decision to wrap the project at the governance foundation.

**Root cause:** Phase 5 and Phase 6 planning language described the intended adaptive direction,
while the shipped employer/candidate boundary remained role-to-assessment matching.

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/admin/question-bank/page.tsx`
- `apps/web/tests/e2e/employer-portal.spec.ts`
- `README.md`
- `CURRENT_STATE.md`
- `docs/README.md`
- `docs/development/known-limitations.md`
- `docs/enhancements/README.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/README.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/phase-6-execution-plan.md`

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py tests/test_question_bank_ingestion.py tests/test_adaptive_assessment.py tests/test_assessment_taxonomy.py -q` -> 45 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 293 passed, 51 skipped.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 23 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_release_migration.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed through `0012_concept_question_types`.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed with 4 known warnings.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e -- --workers=1` -> 33 passed, 2 skipped.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1` -> 8 passed.

**Follow-up items:** Question-level blueprint composition, mixed-question delivery, and scoring
remain a future enhancement. The current question bank is governance infrastructure only.

---

## 2026-07-01 — Phase 6A question-bank type filter and readiness labels

**Symptom:** The Super Admin question bank showed `content needs review` next to a generic
`not ready` label, which made it unclear whether readiness referred to content approval or a
coding package. There was also no top-level way to filter by question type.

**Root cause:** Readiness and package status were shown as generic card labels, and filtering was
only implemented by review status.

**Files changed:**
- `apps/web/src/app/admin/question-bank/page.tsx`

**Validation:**
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py tests/test_question_bank_ingestion.py -q`
  -> 18 passed.

**Follow-up:** If the question bank grows past review-page scale, move question-type filtering to
the API query instead of client-side filtering inside the current status tab.

---

## 2026-07-01 — Phase 6A imported concept questions misclassified as communication

**Symptom:** Source-imported React questions such as "What are synthetic events in React" appeared
as `communication` questions in Super Admin.

**Root cause:** The source-ingestion default `question_type` was `communication`, so React,
JavaScript, and frontend concept-question sources inherited the wrong type unless explicitly
overridden.

**Files changed:**
- `apps/api/signalloop_api/question_bank_ingestion.py`
- `apps/api/alembic/versions/0012_reclassify_imported_concept_questions.py`
- `apps/api/tests/test_question_bank_ingestion.py`
- `apps/web/src/app/admin/question-bank/page.tsx`
- `docs/enhancements/phase-6-question-bank-assessment-builder/01-product-requirements.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/02-approved-question-bank.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/04-ai-helper-and-scoring.md`

**Validation:**
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase6a_concept_reclassify_final.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head`
  -> passed through `0012_concept_question_types`.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py tests/test_question_bank_ingestion.py -q`
  -> 18 passed.
- `cd apps/web && npm run typecheck` -> passed.
- Local Postgres question bank reset completed: 74 old question rows cleared, including 11 approved
  rows; 8 internal seed questions and 58 approved-source questions re-imported as 66
  `needs_review` rows.

**Follow-up:** As the question bank grows, keep concept questions separate from communication
questions; communication remains for final explanation and stakeholder-facing written-response
tasks.

---

## 2026-06-30 — Phase 6A implementation: Super Admin question bank foundation

**Symptom:** Phase 6 planning identified source approval and question approval as the first
required step before employer-side dynamic assessment assembly.

**Root cause:** The product needs a reviewed inventory of approved questions before the builder
can generate reliable role-level assessments.

**Files changed:**
- `apps/api/signalloop_api/models.py`
- `apps/api/signalloop_api/schemas.py`
- `apps/api/signalloop_api/admin.py`
- `apps/api/signalloop_api/question_bank_seed.py`
- `apps/api/signalloop_api/question_bank_ingestion.py`
- `apps/api/alembic/versions/0010_add_question_bank.py`
- `apps/api/tests/test_admin_endpoints.py`
- `apps/api/tests/test_question_bank_ingestion.py`
- `apps/web/src/app/admin/api.ts`
- `apps/web/src/app/admin/types.ts`
- `apps/web/src/app/admin/page.tsx`
- `apps/web/src/app/admin/question-bank/page.tsx`
- `CURRENT_STATE.md`
- `docs/architecture/technical-product-architecture-spec.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/README.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/05-source-allowlist.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/phase-6-execution-plan.md`

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py -q`
  -> 15 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py tests/test_question_bank_ingestion.py -q`
  -> 17 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py tests/test_adaptive_assessment.py tests/test_assessment_taxonomy.py -q`
  -> 42 passed before source-ingestion endpoint rename; rerun focused admin/ingestion set after rename passed.
- Local configured Postgres import completed: 58 source-imported questions plus 7 internal/AI-draft seed
  questions, 65 total in `needs_review`.

**Follow-up:** Review and approve/reject imported questions in Super Admin, then use approved
questions for role-based blueprint assembly.

---

## 2026-07-01 — Phase 6A question package workflow and cleanup controls

**Symptom:** Coding questions such as FastAPI API prompts could be content-approved without any
clear indication of whether runnable code/tests were attached. Super Admin also needed a way to
review approved questions and delete bad imports during the inventory-building stage.

**Root cause:** The initial question-bank model tracked one review status for all question types,
but coding questions need separate content and executable-package review states.

**Files changed:**
- `apps/api/signalloop_api/models.py`
- `apps/api/signalloop_api/schemas.py`
- `apps/api/signalloop_api/admin.py`
- `apps/api/signalloop_api/question_bank_seed.py`
- `apps/api/signalloop_api/question_bank_ingestion.py`
- `apps/api/alembic/versions/0011_add_question_package_status.py`
- `apps/api/tests/test_admin_endpoints.py`
- `apps/web/src/app/admin/api.ts`
- `apps/web/src/app/admin/types.ts`
- `apps/web/src/app/admin/question-bank/page.tsx`
- `docs/architecture/technical-product-architecture-spec.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/01-product-requirements.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/02-approved-question-bank.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/phase-6-execution-plan.md`

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_admin_endpoints.py tests/test_question_bank_ingestion.py -q`
  -> 18 passed.
- `cd apps/web && npm run typecheck` -> passed.
- Local Postgres migrated through `0011_question_package_status`; existing question rows were
  synced so FastAPI Standard/Advanced are package-approved, generic coding drafts are missing
  package, and non-coding questions are package-not-required.

**Follow-up:** Replace Phase 6A delete with deprecate/archive once approved questions can be
referenced by employer blueprints or candidate attempts.

---

## 2026-06-30 — Phase 6 planning docs: question bank assessment builder

**Symptom:** Phase 5 adaptive builder selected between current FastAPI packs, but the next
product direction needed a documented plan for role-based assessment assembly from an approved
question bank.

**Root cause:** The question-bank model, public-source ingestion boundary, super-admin review
flow, employer same-slot swap rules, resume boundary, and mixed-question AI/scoring rules were
agreed in discussion but not yet captured as source-of-truth docs.

**Files changed:**
- `docs/enhancements/phase-6-question-bank-assessment-builder/README.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/01-product-requirements.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/02-approved-question-bank.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/03-role-based-assessment-builder.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/04-ai-helper-and-scoring.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/05-source-allowlist.md`
- `docs/enhancements/phase-6-question-bank-assessment-builder/phase-6-execution-plan.md`
- `CURRENT_STATE.md`
- `docs/README.md`
- `docs/enhancements/README.md`
- `docs/architecture/technical-product-architecture-spec.md`

**Follow-up:** Before implementation, select the first Phase 6 task boundary and decide whether
the first build starts with question-bank schema/admin review or employer blueprint assembly.

---

## 2026-06-30 — Adaptive builder upload fixture expansion

**Symptom:** Manual upload testing had a backend JD fixture but lacked frontend and data-role
JD files in PDF/DOCX formats.

**Root cause:** Earlier Phase 5 fixtures focused on the current invite-ready backend/FastAPI
path rather than planned/future assessment routing examples.

**Files changed:**
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/frontend-platform-engineer-jd.docx`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/frontend-platform-engineer-jd.pdf`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/data-engineer-analytics-platform-jd.docx`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/data-engineer-analytics-platform-jd.pdf`
- `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/README.md`

**Validation:** `file` identifies the new files as Word 2007+ DOCX and PDF 1.4. `unzip -t`
passes for both DOCX files. PDF render QA was skipped because `pdftoppm` is not installed in
this environment.

---

## 2026-06-29 — Employer Overview explains adaptive builder path

**Symptom:** The employer Overview still described assessment creation as a
direct invite flow, so the Adaptive builder relationship to the Coding challenge
path was not visible until entering the Assessments view.

**Root cause:** Phase 5 added the adaptive creation path to Assessments, but the
Overview help text and empty state were still written around the earlier direct
invite model.

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/tests/e2e/employer-portal.spec.ts`
- `CURRENT_STATE.md`

**Follow-up:** Keep Overview copy aligned when future assessment types move from
planned/future coverage into executable assessment packs.

---

## 2026-06-29 — Phase 5 MVP implementation: role-adaptive assessment system

- Implemented adaptive persistence:
  `RoleProfile`, `CandidateProfile`, `AssessmentBlueprint`, and nullable
  `AssessmentAttempt.blueprint_id`.
- Added Alembic migration `0009_add_adaptive_assessment_blueprints`.
- Added deterministic JD/resume skill extraction and classification using the static taxonomy.
- Added blueprint generation for Standard/Advanced FastAPI selection, skill coverage,
  rationale, caveats, and follow-up probes.
- Added employer adaptive API endpoints under `/employer/adaptive/*`.
- Added an optional adaptive builder in the employer Assessments view; the existing quick
  invite path remains available.
- Added adaptive report context for blueprint-backed attempts only.
- Added realistic JD/resume API e2e coverage in `apps/api/tests/test_adaptive_assessment.py`.
- Added manual QA fixtures in
  `docs/enhancements/phase-5-role-adaptive-assessment/manual-test-fixtures.md`.
- Fixed the employer page lint error by deferring the initial refresh call from `useEffect`.
- Validation:
  - `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 272 passed, 51 skipped.
  - `DATABASE_URL=sqlite:////tmp/signalloop_phase5_adaptive_migration_2.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
  - `cd apps/web && npm run typecheck` -> passed.
  - `cd apps/web && npm run lint` -> passed with 4 known warnings.
  - `cd apps/web && npm run build` -> passed.
  - `cd apps/web && npm run test:e2e -- --workers=1` -> 30 passed, 2 skipped.
- Follow-up: manual product review of adaptive builder UX with real employer copy, then hosted
  smoke after migration is applied.

---

## 2026-06-29 — Phase 5 Task 1: taxonomy and module coverage

- Implemented the first Phase 5 backend foundation: static skill taxonomy and assessment
  module coverage under `apps/api/signalloop_api/assessment_taxonomy/`.
- Added `skills.json` with current backend/FastAPI coverage plus roadmap skills across
  frontend, full-stack, infra, data, ML/AI, and engineering judgment.
- Added `module_coverage.json` for Standard FastAPI v2 and Advanced FastAPI v1, separating
  directly tested, partially tested, and not-tested skills.
- Added `loader.py` validation for duplicate IDs, invalid assessability/evidence values,
  unknown coverage skill references, unsupported skills that claim modules, and supported
  module claims not backed by module coverage.
- Added `apps/api/tests/test_assessment_taxonomy.py`.
- Validation:
  - `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py`
    -> 6 passed.
  - `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 267 passed, 51 skipped.
- Follow-up: Phase 5 Task 2 should add adaptive persistence (`RoleProfile`,
  `CandidateProfile`, `AssessmentBlueprint`, and nullable attempt blueprint link).

---

## 2026-06-29 — Phase 5 planning: role-adaptive assessment system

- Added the planning workstream under `docs/enhancements/phase-5-role-adaptive-assessment/`.
- Defined the Phase 5 MVP boundary: pasted JD/resume intake, versioned skill taxonomy,
  skill matching, reviewable assessment blueprints, employer approval, and adaptive report
  context.
- Captured the product decision that, for v1, the role/JD determines the comparable core
  assessment while resume data drives rationale, caveats, and follow-up probes. Resume data
  should not automatically give different candidates for the same role different scored tasks.
- Documented that current executable assessment support remains Standard FastAPI v2 and
  Advanced FastAPI v1; unsupported skills must be shown as caveats/follow-up areas rather than
  scored evidence.
- Updated `CURRENT_STATE.md`, `docs/README.md`, `docs/enhancements/README.md`, and the
  architecture spec to mark Phase 5 as the active planning workstream. Also corrected the
  stale architecture-spec status that said Phase 3 proctoring was not implemented.
- No code changes in this entry — documentation/planning only.

---

## 2026-06-24 — Documentation pass: AI collaborator retrospective + phases complete

- Wrote `docs/retrospectives/ai-collaborator-journey.md` — the full design history of the AI
  collaborator (keyword matching → single LLM call → two-step + output guard whack-a-mole →
  two-component redesign → progressive-disclosure pedagogy), why each version failed, the final
  design, and the lessons. Blog-ready.
- Architecture spec: rewrote §12 (Constrained AI collaborator) to the two-component +
  progressive-disclosure design; updated §17/§20 (no_issue_identified superseded; Phase 3
  marked implemented; added Phase 4 super admin portal).
- Marked all phases complete in `docs/execution/phases/README.md` and CURRENT_STATE (MVP 1–12
  + enhancement Phases 2/3/4). Added a docs index entry for `retrospectives/`.
- No code changes in this entry — documentation only.

---

## 2026-06-24 — Super admin role: resolve email from Clerk (real bug)

Admin login always landed in the employer portal. Root cause: Clerk's default session token
has **no email claim**, so `verify_clerk_token` fell back to a synthetic
`{clerk_user_id}@clerk.local` address that can never match `SUPER_ADMIN_EMAILS`. Since admin
role assignment is email-based, no one could ever become admin — locally *or* on Render.

Fix (`auth.py`): when the JWT has no email, resolve the user's primary email from the Clerk
Backend API (`GET /v1/users/{id}` with `CLERK_SECRET_KEY`), cached per user id. Falls back to
the synthetic address if the lookup fails (auth still succeeds; user just isn't matched as
admin). This also corrects employer emails (previously stored as `@clerk.local`).

Verified end-to-end against the real Clerk API: the admin account
configured in `SUPER_ADMIN_EMAILS` resolves and assigns `super_admin`. Added
`tests/test_auth_email_resolution.py` (4 tests: primary-email selection, caching,
no-secret, API-failure). API suite: **261 passed**.

Note: admin role is keyed on the account's email, and the JWT lacks email by default — so this
Clerk Backend API resolution is required in every environment.

---

## 2026-06-23 — Super Admin Portal: review fixes (correctness + missing sections)

Code review of the phase-4 super admin portal surfaced metric bugs and a duplicated report
renderer. Fixed:

### Backend (`admin.py`)
- **AI message count was doubled** — counted every `AIInteraction` row, but each candidate
  turn stores two (candidate + assistant). Now counts candidate-role prompts only.
- **AI violation count was wrong** — the `"violation"/"injection"` substring heuristic only
  caught `prompt_injection`. Now uses `ai_policy.DISALLOWED_TAGS` (all real violations),
  counted on assistant rows only (no double-count).
- **"Failed test runs" counted the wrong status** — counted only `error`. Renamed to
  `execution_errors` and counts `error` + `timeout` (real test *failures* are normal work,
  not a stuck signal).
- **Removed dead `error_attempts`** signal (`status == "error"` is not a real attempt status).
- **N+1 queries** in `get_employer_detail` replaced with a few grouped queries (packs,
  reports, AI, test runs fetched once each); `report_count`/scores derived from those maps.
- **`last_activity`** now uses `max(coalesce(submitted_at, started_at, created_at))` instead
  of just `created_at`.
- Removed unused `CodeSnapshot` import.

### Frontend
- **Admin report view was a stale fork** missing the FAVO and follow-up-questions sections
  (and rendering fewer details). Extracted the employer report renderer into a shared
  `app/_components/EvidenceReportView.tsx` used by BOTH the employer and admin report pages,
  so admins now see the full report and the two can't drift. Admin view is read-only (no
  Regenerate button).
- **Roster search** added (filter by email/company).
- **Single-sourced the API base URL** — admin `api.ts` re-exports it from the employer client.
- Updated admin `types.ts` (`stuck_signals.execution_errors`; `AdminEvidenceReport` aliases
  `EvidenceReportResponse`).
- Aligned the three admin `useEffect` data-loads to the deferred `setTimeout(…,0)` pattern the
  employer report page already uses, clearing the `set-state-in-effect` lint errors in the
  admin portal. (Pre-existing lint issues in `employer/page.tsx` and the invite page are
  outside this scope.)

### Tests
- Added `test_employer_detail_metrics_are_accurate` locking the AI message/violation counts
  and `execution_errors` (and that `error_attempts`/`failed_test_runs` are gone).
- API suite: **257 passed**. Web typecheck + build pass.

---

## 2026-06-23 — AI Collaborator: workspace context (act like a coding agent)

### Why

Candidates are used to coding assistants that read their actual code. The collaborator only
saw a single manually-selected snippet (`selected_context`), so questions like "what does
delete_task do?" got generic textbook answers when nothing was selected.

### Changed

- `ai.py` now assembles the candidate's current source from their latest snapshot
  (`candidate_workspace_files`) and passes it to the generator as `workspace_files`. Filtered
  defensively: only `.py` under `task_api/` and `tests/`, excludes evaluator/hidden paths and
  config/readme noise, bounded to 16k chars. Snapshots are candidate-visible only to begin
  with; the filter is belt-and-suspenders.
- `ai_provider.evaluate` gained an optional `workspace_files` param. New
  `_build_generator_user_content` assembles the generator message like a coding agent sees a
  request: workspace files, the focused file (selected_context as a pointer), conversation,
  then the question.
- `GENERATOR_PROMPT` gained a "Use the candidate's workspace" rule: read their actual code and
  ground answers in THEIR implementation; don't invent code that isn't there.
- The classifier still sees only the current message (no workspace) — it judges abuse, not code.

### Tests

- Live: `test_workspace_grounded_explanation` ("what does delete_task do?" → describes the real
  pop/404/`{deleted, task_id}` behavior); focus tests now pass the workspace to mirror the
  endpoint. Verified end-to-end: with no selected_context the endpoint answer is grounded in
  the snapshot code.
- Offline guardrail: `test_candidate_workspace_files_filters_to_candidate_source` (evaluator/
  hidden/config excluded) and empty-input handling.
- Offline: **256 passed**. Live: **45 passed**.

---

## 2026-06-23 — AI Collaborator: conversation context flow fix

### Why

A real exchange exposed the generator re-answering OLD requests: after helping with a
non-owner block and a title-whitespace fix, a plain "what does delete_task do?" produced a
response that re-dumped both prior fixes plus a delete explanation. Two flow bugs:

1. The generator's "Recent conversation" contained only the candidate's PAST requests — none
   of the assistant's replies. Prior asks therefore looked unanswered, so the model
   re-implemented them. It also could not resolve references to its OWN prior answers
   ("ok, make that change for me").
2. Nothing told the generator to answer only the current message.

### Changed

- `ai.py` now fetches the recent transcript of BOTH roles (last 8 interactions, chronological)
  and passes it to the generator as `recent_turns`. The candidate-only `recent_messages` list
  is kept separately for the degraded keyword fallback (assistant redirect text would
  false-trigger its abuse patterns, e.g. "issue-by-issue").
- `ai_provider.evaluate` gained an optional `recent_turns` param (Protocol +
  LocalGuidanceProvider + OpenAIProvider). New `_format_history` builds the generator context
  from the real transcript (labels each turn, truncates long lines), falling back to
  candidate-only when no transcript is supplied.
- `GENERATOR_PROMPT` gained a "Focus on the current message" rule: answer only the current
  message; earlier turns are reference-only (already handled); never re-answer them or
  volunteer unrequested changes.
- The generator's history framing now states the turns are already handled and for reference
  only.

### Tests

- Added live tests (section H): `test_focus_does_not_reanswer_prior_requests` (the reported
  delete_task scenario) and `test_focus_resolves_reference_to_prior_answer` ("make that change
  for me" resolves to the assistant's prior suggestion). Both pass against real models.
- Updated the fake providers in `test_ai_endpoint.py` / `test_evidence_report.py` for the new
  signature.
- Verified end-to-end through the live endpoint: the multi-turn replay now answers only the
  current question.
- Offline: **254 passed**. Live: **44 passed**.

---

## 2026-06-23 — AI Collaborator: permanent two-component redesign

### Why

The AI collaborator had accumulated a long series of recurring false-positive bugs (over-
blocking legitimate candidate questions, losing follow-up context). Root cause was
structural: **three** independent classifiers each made the same decision with different
logic and overrode one another — the LLM classifier, the Python keyword `fallback_classify`
(which also ran during normal operation to "validate" `anti_decomposition`), and a keyword
`_guard_generator_output` output guard that could blank a good answer. Each bug fix added
more keywords/examples, creating new false positives elsewhere.

### Decision (approved by product owner)

- Trust the LLM as the single source of truth; keyword logic runs only when the LLM is
  unavailable, and leans allow.
- Lean allow when ambiguous (the report's AI-collaboration scoring still captures patterns).
- Keep blocking pasted test code, as one narrow deterministic rule.

### Changed

- **`ai_policy.py`**
  - `CLASSIFIER_PROMPT` rewritten short and principle-based (was ~135 lines of bug-reaction
    examples). It decides only block-vs-allow, never code-vs-Socratic. Leans allow.
  - `GENERATOR_PROMPT` rewritten into explicit Mode A (give changed lines — for a candidate-
    identified public/hidden/enhancement issue OR a concept question) and Mode B (one
    Socratic question when the candidate is fishing). The generator is the ONLY owner of the
    code-vs-coach decision.
  - `parse_classifier_response` simplified: trust the LLM; removed the `anti_decomposition`
    fallback cross-check that let keywords override a working LLM. Fallback runs only on parse
    failure.
  - `fallback_classify` is now lenient/availability-only: high-precision explicit abuse
    phrases only, no fuzzy single-word matching, `no_issue_identified` removed. Default allow.
  - New `is_pasted_test_code()` (shared structural detector) and `redirect_message_for_tag()`.
  - `no_issue_identified` removed from `DISALLOWED_TAGS` — vague fishing is coached, not
    blocked, and was never a scored violation.
- **`ai_provider.py`**
  - Deleted the entire output-guard layer (`_guard_generator_output`, `_is_test_failure_paste`,
    `_identifies_issue_verbally`, `_contains_code`, `_SOLUTION_PATTERNS`, `_TEST_FAILURE_SIGNALS`,
    `_VERBAL_ISSUE_IDENTIFICATION`, `_SOCRATIC_FALLBACK`). Generator output is returned verbatim.
  - `evaluate()`: deterministic test-paste pre-gate → LLM classify → generate. One responsibility
    per step.
- **`ai.py`**: fixed a message-ordering bug — recent candidate messages were fetched newest-first
  but consumed as chronological, so the generator/classifier saw the oldest 3 of the last 6 in
  reverse. Now reversed to chronological (oldest→newest). This undercut the earlier
  "follow-up context" fix.

### Tests

- Deleted `tests/test_ai_output_guard.py` (the guard is gone).
- Rewrote `tests/test_ai_policy.py` to test the lenient fallback contract (leans allow; blocks
  only high-precision abuse + pasted test code) instead of pinning brittle keyword internals.
- Rewrote `tests/test_two_step_pipeline.py`: pre-gate behavior, verbatim generator output, vague
  fishing now allowed+coached, call-count isolation.
- Rewrote `tests/test_live_ai_policy.py` into a real regression net (42 cases) grounded in the
  actual seeded issues of both shipped packs (standard v2: duplicate email, unused
  `actor_user_id` in `get_task`/`delete_task`, `update_task_status` transitions, priority/
  due-date enhancements; advanced v1: `patch_task` partial-update, `is_team_lead` not
  team-scoped, `add_comment` access check, archived-task filtering). Categories: candidate-
  identified issue, verbal diagnosis + failure, concept, post-impl review, multi-turn
  follow-ups, vague-fishing-is-coached, and the block categories.
- Ran the live net against real models (`gpt-4o` generator / `gpt-4o-mini` classifier). It
  caught one real regression: the follow-up "ok, make that change for me" (after the
  candidate asked how to fix one issue) was tagged `anti_decomposition`. Fixed by tightening
  the classifier prompt — anti_decomposition now requires a broad MULTI-issue sweep, and a
  single named follow-up is explicitly allowed with a counter-example. Added a live test that
  a genuine multi-issue sweep still blocks, so the rule isn't disabled.
- Full offline API suite: **254 passed**. Live suite: **42 passed** against real models.

### Follow-up: context-bleed false positive (found via live endpoint smoke test)

After restarting the API and smoke-testing the real endpoint, a candidate-identified request
("in create_user I don't see duplicate email handling, can you help me with code for this?")
was blocked as `full_solution` — but only when a prior turn ("how do I raise a 409?") was in
the history. Reproduced 15/15. Root cause: the classifier was being fed recent messages and
mis-read the *combination* as building a full solution.

Fix: the classifier now judges the CURRENT message alone (`ai_provider.evaluate` no longer
passes history to the classifier call). Conversation context belongs to the generator — an
allowed-only path that cannot cause a false block — which still receives `recent_messages`.
Tightened the `full_solution` definition (naming one issue is never full_solution), reworded
`anti_decomposition` to a single-message sweep, and pinned the reproduced phrasing as an ALLOW
example. After the fix: 0/15 blocked; abuse still blocks; 254 offline + 42 live still pass;
endpoint replay of the original sequence allows all turns.

### Files

- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/signalloop_api/ai_provider.py`
- `apps/api/signalloop_api/ai.py`
- `apps/api/tests/test_ai_policy.py`, `test_two_step_pipeline.py`, `test_live_ai_policy.py`
- `docs/prompts/ai-collaborator-policy.md`

---

## 2026-06-22 — Phase 2 Close-out: Direct Execution + Full UI Polish

### DirectExecutionProvider — inline pytest, no ECS cold start

**Why:** ECS/Fargate per-run tasks averaged ~50s due to container spin-up. For a pilot
with trusted candidates, running pytest in-process (subprocess isolation only) is
sufficient and drops the round-trip to ~7s.

**Changed:**
- New `DirectExecutionProvider` class in `execution.py` with `run_public`, `run_hidden`,
  and `run_candidate_verification` methods. Each creates a `TemporaryDirectory`, writes
  candidate + hidden files via `_write_files` / `_write_hidden_tests`, runs pytest via
  `subprocess.run`, and returns the same result dict shape as the HTTP/ECS providers.
- `get_execution_provider()` returns `DirectExecutionProvider` when
  `EXECUTION_BACKEND=direct`.
- Both `.env.example` and `.env.render-supabase.example` updated to `EXECUTION_BACKEND=direct`.
- Helper functions `_validate_relative_path`, `_write_files`, `_write_hidden_tests`,
  `_run_subprocess` extracted as module-level utilities shared across providers.

**Files changed:**
- `apps/api/signalloop_api/execution.py`
- `.env.example`, `.env.render-supabase.example`

**Architecture note:** `direct` is pilot-only. Switch to `ecs_fargate` for production
to restore subprocess isolation in a Docker container per run.

---

### Elapsed timer UI during test run

**Why:** No visual feedback while pytest runs left candidates uncertain if anything was
happening.

**Changed:**
- `running` state gates a `setInterval` that increments `runElapsed` every second.
- Topbar shows "Running tests… 3s" via `publicRunMessage` while running; clears on result.
- Same pattern for `submitElapsed` / `submissionMessage` during final submission.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

---

### Candidate workspace — full IDE-style overhaul

**Why:** Candidate workspace had no clear visual hierarchy. Progress, instructions, AI
chat, and test output competed for space with no logical grouping.

**Changed:**
- Left sidebar: IDE-style file explorer with `EXPLORER` header and autosave chip.
- Top bar: SignalLoop SVG logo, status box (progress chips + divider + status pills +
  operation message), Run Tests + Submit buttons.
- Right panel: two independent scrollable sections — "What to do" (fixed height,
  vertically resizable via drag handle) and "AI Collaborator" (grows to fill remaining
  space).
- Bottom: collapsible test output drawer (auto-expands when results arrive). Test panel
  header shows "2/5 failed" or "5/5 passed" count format.
- Submit: clicking Submit opens a confirm modal containing 4-row status summary +
  notes textareas + Submit final button. Separate submission drawer removed.
- Autosave note shown in editor tab bar.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
- `apps/web/src/app/globals.css`

---

### Status chips — progressive disclosure + relabeling

**Why:** Showing empty "○ Public · ○ Edge cases · ○ Enhancements · ○ My tests" chips
before any test run was run was confusing — there was no meaningful data to display.

**Changed:**
- Progress chips are hidden until there is real data: Public tests chip appears after
  first run, Edge cases after first run (guided mode), Enhancements after first run (if
  collected > 0), My tests after candidate adds a test.
- Divider between chips and status pills only renders when at least one chip is visible.
- Labels: "Public" → "Public tests", "Hidden" → "Edge cases", "Enhanced" →
  "Enhancements", "Tests" → "My tests".
- `attempt.status === "started"` displays as "In progress".
- Duration pill: "Recommended 90m" → "Recommended 90 min".
- "What to do" item 5 notes: *"these count at final submission, not on each run."*
- Submit modal: "Hidden checks" → "Edge cases", "Candidate tests" → "My tests".

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

---

### Employer portal — professional UI overhaul

**Why:** Employer portal looked like a debug tool — no logo, raw table, manual refresh
button, assessment dropdown with no context, bottom-of-form Create invite button.

**Changed:**
- SignalLoop logo added to header and auth screen (`employer-brand` component).
- Manual Refresh button removed; replaced with `setInterval` auto-poll every 30s
  (a "Refreshing…" chip appears in the section title during the fetch).
- Professional subtitle: "Manage candidate assessments, track progress, and review
  AI-assisted evidence reports."
- Assessment dropdown: option labels show quick summary (e.g.,
  "Standard FastAPI v2 — 3 bugs · 4 hidden · 2 enhancements · 90 min").
- "View details" → "Details" button placed inline (col 2) next to the assessment select.
- Assessment detail modal: sourced from evaluator rubrics; shows public tests, hidden
  edge cases, enhancements, and scoring weights for both packs.
- Create invite button moved inline (col 2) next to the email input.
- Timing / Evaluator selects span both columns to avoid gap.
- Score column: colored pill badge (green ≥ 80, orange ≥ 60, red < 60).
- Attempt rows: email stacked with "Sent Xm ago", "started" → "In progress", level tag
  below status pill.
- Table header: no border/card — flat uppercase label row sitting above bordered data
  cards so column labels visually belong to each column below them.
- Invite URL: rendered as readonly monospace input + Copy button side by side.
- Empty state: "No candidates invited yet — create an invite above to get started."
- Metric card labels: "Total attempts" → "Total invites", "Reports" → "Reports ready".

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/globals.css`

---

### Evidence report — professional UI overhaul

**Why:** Report page had no logo, a redundant Refresh button, raw metric values with no
explanation, and the most action-oriented content (follow-up interview questions) buried
near the bottom.

**Changed:**
- SignalLoop logo + candidate email + assessment name in header. "Evidence Report" title
  now shows who the report is for without scrolling.
- Refresh button removed. Regenerate button styled amber (warning) and gated by a
  `window.confirm` dialog to prevent accidental overwrites.
- CSS `data-tooltip` system (no JS/library): hovering any metric card shows a dark
  tooltip explaining the value. Applied to Timing, Time used, Submission, Evaluator mode.
- AI integrity risk badge surfaced in the recommendation banner when elevated
  (medium/high/critical) — previously buried in the AI collaboration section.
- Follow-up interview questions moved above score breakdown — they are the most
  action-oriented output and now appear right after the executive summary, with a teal
  left-border callout style.
- FAVO section subtitle: "Frame · Ask · Verify · Own — how the candidate structured
  their problem-solving process."
- Submission review section subtitle: "Candidate's own words on what they changed and why."
- Process evidence: Snapshots + Test runs shown as mini metric cards (visual iteration
  signal) instead of plain text.
- Score breakdown: bar chart labels are anchor jump-links to detail sections below
  (hover turns teal + underline). Score list with duplicated evidence text removed.
- "Feature / design implementation" renamed to "Enhancements" everywhere: bar chart
  label, detail section title, `CATEGORY_LABELS` map, section anchor ID.

**Files changed:**
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/globals.css`

---

## 2026-06-22 — Report Polish, Scoring Fixes, Integrity Risk Tuning

### Evidence report redesigned (collapsible sections)

**Why:** The employer report was showing every detail inline — failure names, seeded
areas, AI prompts, timeline events — making it hard to read at a glance.

**Changed:**
- Added `Disclosure` component using `<details>/<summary>` for verbose lists: test
  failure names, initially-failing tests, seeded issue areas, file diffs, flagged AI
  prompts, process evidence, and timeline.
- Score summaries and key metrics always visible; details collapsed by default.
- Added `.report-disclosure`, `.report-disclosure-body` CSS.

**Files changed:**
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/globals.css`

### Regression scoring proportional

**Why:** A candidate who broke 1 of 10 originally-passing tests lost 100% of the
regression category (step function). That's too harsh for a single accidental failure.

**Changed:**
- `reg_score = rubric_weight × max(0, 1 - regressed / originally_passing_count)`.
- `original_test_names` built from initial starter files via `extract_test_names()` and
  passed to `calculate_scores()`.
- Candidate-added test functions excluded from regression detection: a new test that
  fails is not a regression of an original passing test.

**Files changed:**
- `apps/api/signalloop_api/reports.py`

### Candidate test evidence — function-level diff

**Why:** `candidate_test_evidence()` was counting all test functions in touched files
including unchanged ones, overcounting by as many as the original file had.

**Changed:**
- Backend: new `_extract_test_fn_bodies()` extracts per-function bodies. `functions_added`
  = new test names in final not in initial; `functions_modified` = names in both with
  changed body content.
- Employer report shows "N functions added · M modified" instead of file/function/HTTP
  assertion counts. HTTP assertions removed from display (kept for scoring heuristic only).

**Files changed:**
- `apps/api/signalloop_api/reports.py`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/employer/types.ts`

### Large paste threshold raised (8 → 25 lines)

**Why:** 8 consecutive new lines flagged single test functions as suspicious pastes.
A candidate writing several test functions at once would routinely trigger it.

**Changed:**
- `PASTE_LINE_THRESHOLD = 25` in `reports.py`.
- Test updated to use 30-line addition and assert `>= 25`.

**Files changed:**
- `apps/api/signalloop_api/reports.py`
- `apps/api/tests/test_evidence_report.py`

### Integrity risk thresholds updated

**Why:** `large_paste_count >= 2` triggered "high", but two large pastes to test files
during a 2-hour assessment can be normal. "High" should require a clear pattern.

**Changed:**
- `large_paste_count >= 3` (was ≥ 2) now triggers "high"; 1–2 pastes → "medium".
- `weak_review` now compares against `required_question_count` (dynamic) instead of
  hardcoded 2. New 2-field form has 1 required field; old 4-field form retains 4.

**Files changed:**
- `apps/api/signalloop_api/reports.py`

### Submission review display — new 2-field format

**Why:** Employer report showed 4 field labels (What changed, Tradeoffs, Verification,
Given more time) even when candidates only filled 1 field on the new 2-field form.

**Changed:**
- Employer report renders only non-empty submission review fields dynamically. Works for
  both old 4-field and new 2-field submissions.
- New form: only `what_changed` required; `additional_notes` is optional. `weak_review`
  triggered only when `what_changed` is empty.

**Files changed:**
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/api/signalloop_api/reports.py`

---

## 2026-06-22 — Enhancement Feedback, Progress Checklist Improvements, Candidate Test Count

### Enhancement feedback always shown (both packs, both modes)

**Why:** Enhancement progress was only visible in guided mode and relied on candidate's own
tests, which is wrong — enhancements are evaluated by the evaluator's hidden tests, not by
the candidate's test results.

**Changed:**
- `run_public_tests` always runs the evaluator hidden tests (not just in guided mode) and
  always injects `enhancement_feedback: {passed, failed, collected}` into the response,
  computed from `feature_design_tests` in the pack config.
- `enhancement_summary()` now returns all-zeros if the evaluator run errored (previously
  it incorrectly counted all enhancement tests as "passed" when Docker failed).
- Frontend "Enhancements built" checklist item uses `collected > 0` as gate (not object
  truthiness), so a failed evaluator run shows "run tests to check" rather than "0/N".

**Files changed:**
- `apps/api/signalloop_api/attempts.py`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

### Hidden checks item split from enhancements

**Why:** Previously "Hidden checks" in guided mode counted all 8 hidden tests including the
5 enhancement tests, which overlapped with "Enhancements built" (also 5 tests). The counts
were misleading.

**Changed:**
- Guided mode: "Hidden checks" now shows only the non-enhancement hidden tests
  (edge-case/quality tests). Computed as `evaluator_feedback - enhancement_feedback` per
  dimension (passed, failed, collected). Guarded with `Math.max(0, …)` to prevent negatives.
- Strict mode: "Hidden checks" now shows a static row — "additional behaviors evaluated at
  submission" — so candidates know edge-case tests exist without seeing counts.
- Progress order: Hidden checks above Enhancements built.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

### Candidate test count and initial_files fix

**Why:** `candidateTestsAdded` always returned false after a page reload because both
`files` and `initialFiles` were set to `body.files` (the current snapshot), making the
diff always zero.

**Changed:**
- API now returns `initial_files` (original starter code, always loaded from pack path,
  never from snapshot) alongside `files` (current working snapshot).
- Frontend sets `initialFiles` from `body.initial_files`, not `body.files`.
- Candidate tests checklist item now shows count: "N added (scored at submission)" using a
  `def test_` line count diff between current and initial test files.
- Removed the "Notes: additional behaviors evaluated…" and "Evaluator checks: N passed…"
  paragraphs from the test output panel header — the progress checklist is now the single
  source of truth for all evaluator feedback.

**Files changed:**
- `apps/api/signalloop_api/schemas.py` — added `initial_files` to `CandidateAttemptResponse`
- `apps/api/signalloop_api/attempts.py` — `candidate_attempt_response()` loads `starter_files` separately
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

---

## 2026-06-21 — Proving Tests, AI Policy Improvements, Submitted Code Viewer, Dynamic README

### Proving tests for candidate-written test scoring

**Changed:** Candidate test scoring now uses a deterministic proving-test approach instead
of a keyword/count heuristic.

A "proving test" is a candidate-written test that:
1. Fails on the original unmodified starter code (proves it caught a real bug).
2. Passes on the candidate's submitted code (proves the candidate fixed it).

Scoring: 0 proving → 0 pts, 1 → 6 pts (40%), 2 → 11 pts (75%), 3+ → 15 pts (full).

Candidate verification runs at report-generation time via a new worker endpoint
`POST /run-candidate-verification`. The worker receives the original impl files as
`files` and the candidate's submitted test files as `hidden_tests`, reusing
`run_hidden_tests_in_workspace`. If the worker is unreachable, the category scores 0
rather than blocking report generation.

**Files changed:**
- `apps/api/signalloop_api/reports.py` — `run_candidate_verification_if_possible()`,
  `calculate_scores()` proving-test branch, `build_report()` verification call
- `apps/api/tests/test_evidence_report.py` — `FakeCandidateVerificationRunner`,
  proving-test scoring tests, zero-proving-test test

### AI policy improvements

**Changed:** System prompt rewritten with "Default: answer the question" as the lead.
`no_issue_identified` is now narrowly scoped — it must not fire on post-implementation
review, conceptual questions, or any message where the candidate has done work.

New code response constraint: give only the specific changed lines, not the entire
function. The candidate must integrate the change themselves.

ISSUE_IDENTIFIED_SIGNALS expanded: "i added", "i implemented", "i modified", "i updated",
"i created", "i fixed", "i changed", "i wrote", "from this error", "from the error",
"what format", "how do i", "how to", "how does".

DISALLOWED_PATTERNS expanded for prompt injection: "you are now a different", "without
restrictions".

AI policy test suite expanded from 10 to 59 tests including: 21 allowed legitimate
candidate question cases (covering all 8 user-reported false positives), 16 disallowed
bulk/protected requests, 8 vague-diagnosis redirect cases, 9 prompt injection cases.

**Files changed:**
- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/tests/test_ai_policy.py`

### Priority hidden test removed from standard v2

**Changed:** `test_priority_is_defaulted_normalized_and_validated` removed from
`assessment_packs/fastapi_task_api_standard_v2/evaluator/hidden_tests/test_hidden_api.py`.

Priority had zero public signal (not in starter `TaskCreate`, not tested publicly) and was
flagged as unfair to candidates. `seeded_issue_areas` entry removed and `seeded_issue_count`
changed from 7 to 5 in `DEFAULT_PACKS`.

**Files changed:**
- `assessment_packs/fastapi_task_api_standard_v2/evaluator/hidden_tests/test_hidden_api.py`
- `apps/api/signalloop_api/attempts.py`

### Dynamic time limit in assessment READMEs

**Changed:** Hardcoded time limits replaced with `{{DURATION_MINUTES}}` placeholder in
both pack READMEs. A new `apply_placeholders()` function in `assessment_files.py`
substitutes `{{KEY}}` tokens at serve time. `load_candidate_files()` accepts an optional
`substitutions` dict; `create_assessment_attempt` and `candidate_attempt_response` in
`attempts.py` pass `{"DURATION_MINUTES": str(attempt.duration_minutes)}`.

**Files changed:**
- `apps/api/signalloop_api/assessment_files.py`
- `apps/api/signalloop_api/attempts.py`
- `assessment_packs/fastapi_task_api_standard_v2/candidate/README.md`
- `assessment_packs/fastapi_task_api_advanced_v1/candidate/README.md`

### Submitted code viewer in employer report

**Changed:** `build_report()` now includes a `submitted_code` section with the candidate's
final snapshot files, sorted: `task_api/` first, `tests/` second, config files last.

The employer report page renders a tab-based `FileViewer` component (default tab:
`task_api/main.py`, max-height 520 px scrollable code block).

**Files changed:**
- `apps/api/signalloop_api/reports.py`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/globals.css` (added `.file-viewer`, `.file-viewer-tab`,
  `.file-viewer-content` CSS; added `overflow-wrap` and `word-break` to `.report-list`)

---

## 2026-06-20 — Assessment Redesign: Quality-Embedded Scoring + Advanced v1 Pack

**Decision:** Redesign both assessment packs to embed quality as a modifier within each
scoring category (public issues, hidden issues, enhancements) instead of treating quality
as a separate category.

**Standard v2 changes:**
- 3 public issues (failing tests: duplicate email, blank title, non-owner read)
- 4 hidden issues: email case/whitespace normalization, priority defaulting/validation,
  status transition enforcement, unknown actor 404 vs 403 distinction
- 2 enhancements: `due_date` field with ISO validation + `GET /tasks?owner_id=` listing
- Time limit: 60 minutes
- Rubric: 15/20/20/15/15/15

**Advanced v1 changes (new pack):**
- 4 public issues: partial update field preservation, team lead scoping, archived tasks
  in lists, comment access check
- 3 hidden issues: patch authorization, membership role validation, status transitions
- 2 enhancements: task dependencies (blocking + DFS cycle detection) + team activity feed
  (paginated, team-scoped)
- Time limit: 120 minutes
- Rubric: 15/15/25/15/15/15 (feature weight increased to 25)

**AI collaborator policy redesign:**
- Replaced Socratic tutor rule with single principle: candidate must identify the issue;
  once they have, AI helps implement the fix
- Renamed `direct_diagnosis` tag → `no_issue_identified`
- AI now allows implementation help when candidate has named a specific issue

**Scoring changes:**
- `RUBRIC` global in `reports.py` reflects standard v2 default weights
- Per-pack `"rubric"` key in `DEFAULT_PACKS` overrides weights for advanced v1
- `calculate_scores` now accepts `rubric` parameter and uses pack rubric throughout
- `build_favo` feature threshold is now proportional (70% of pack feature max)
- `build_report` emits `pack_rubric` not global `RUBRIC` as `rubric_weights`

**Files changed:**
- `assessment_packs/fastapi_task_api_standard_v2/candidate/README.md`
- `assessment_packs/fastapi_task_api_standard_v2/candidate/tests/test_public_api.py`
- `assessment_packs/fastapi_task_api_standard_v2/evaluator/hidden_tests/test_hidden_api.py`
- `assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution/task_api/main.py`
- `assessment_packs/fastapi_task_api_standard_v2/evaluator/SCORING_RUBRIC.md`
- `assessment_packs/fastapi_task_api_standard_v2/evaluator/REFERENCE_SOLUTION_NOTES.md`
- `assessment_packs/fastapi_task_api_advanced_v1/candidate/README.md`
- `assessment_packs/fastapi_task_api_advanced_v1/candidate/tests/test_public_api.py`
- `assessment_packs/fastapi_task_api_advanced_v1/evaluator/hidden_tests/test_hidden_api.py`
- `assessment_packs/fastapi_task_api_advanced_v1/evaluator/reference_solution/task_api/main.py`
- `assessment_packs/fastapi_task_api_advanced_v1/evaluator/SCORING_RUBRIC.md`
- `assessment_packs/fastapi_task_api_advanced_v1/evaluator/REFERENCE_SOLUTION_NOTES.md`
- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/reports.py`
- `apps/api/tests/test_ai_policy.py`
- `docs/architecture/technical-product-architecture-spec.md`

**Validation:** 67/67 API tests pass (3 skipped). Reference solution passes all hidden
and candidate public tests for both packs.

---

## 2026-06-20 — Implemented Phase 2 UX And Feedback Enhancements

**Decision:** Add execution timing breakdown, configurable evaluator feedback mode, and
candidate IDE ergonomics to the Phase 2 enhancement list.

**Context:** Candidate feedback raised that strict hidden-test handling can feel too
ambiguous because hidden failures are only visible after final submission. The product
direction is to support both modes rather than choose one permanently before more pilot
feedback.

**Implemented local behavior:**

- Execution timing breakdown records where run latency is spent before changing
  infrastructure.
- Strict mode remains the default for hiring: public test feedback during active work;
  hidden/evaluator counts visible only in employer reports.
- Guided mode may show aggregate evaluator pass/fail counts during active work.
- Guided mode must not expose hidden test names, tracebacks, failure messages, file
  paths, or line numbers.
- Reports must record the mode used because guided mode changes score interpretation.
- Candidate IDE ergonomics may add syntax diagnostics, clickable public pytest output,
  color-coded public output, and file indicators using only candidate-visible files and
  public test output.

**Implementation files added/changed:**

- `apps/api/alembic/versions/0005_add_evaluator_feedback_mode.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/execution.py`
- `apps/api/signalloop_api/models.py`
- `apps/api/signalloop_api/reports.py`
- `apps/api/signalloop_api/schemas.py`
- `apps/api/signalloop_api/submissions.py`
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/worker/signalloop_worker/runner.py`
- `apps/worker/signalloop_worker/schemas.py`
- `apps/worker/tests/test_api.py`
- `apps/web/src/app/employer/api.ts`
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/employer/types.ts`
- `apps/web/src/app/globals.css`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 68 passed, 3 skipped.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 22 passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e -- --workers=1` -> 17 passed, 2 skipped.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_enhancements_migration.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- Local Postgres migrated through `0005_add_evaluator_feedback_mode`.
- Live local Playwright candidate smoke passed against the migrated Postgres/API/worker stack for:
  - standard/strict invite,
  - advanced/guided invite.
- Clerk-authenticated employer portal was opened with the user's local Clerk session; standard
  and advanced evidence reports rendered for the submitted live-smoke attempts.
- Added deterministic API submission-scenario coverage for unchanged, public-only, strong,
  weak-review, AI-risk, standard, and advanced report outcomes.
- Expanded AI policy fallback tests for public-test explanation, framework concept help,
  missing-test requests, hidden-test requests, final-explanation requests, full-solution
  requests, and issue-by-issue patch requests.
- Added skipped-by-default live OpenAI policy validation covering allowed named-issue help,
  allowed public-test explanation, no-issue redirect, enumerate-defects block, hidden-tests
  block, final-explanation block, prompt-injection block, and missing-tests block.
- Fixed LLM response parsing so a disallowed `no_issue_identified` response with a blank
  message still uses the required Socratic redirect.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 76 passed, 11 skipped.
- `cd apps/api && RUN_LIVE_AI_TESTS=1 UV_CACHE_DIR=.uv-cache uv run pytest tests/test_live_ai_policy.py -q` -> 8 passed.

**Files changed:**

- `docs/architecture/technical-product-architecture-spec.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-product-scope.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `docs/enhancements/phase-2-assessment-system/03-employer-assessment-configuration.md`
- `docs/enhancements/phase-2-assessment-system/06-ui-enhancements.md`
- `docs/enhancements/phase-2-assessment-system/07-reporting-and-favo-updates.md`

**Validation:** Documentation-only change. No runtime checks required.

---

## 2026-06-20 — Local Phase 2 Validation Cleanup

**Symptom:** Review of the latest Phase 2 changes found local validation drift:

- `next.config.ts` could inline empty public env values when root `.env` was absent or
  shell values were set.
- `npm run typecheck` failed in the candidate workspace e2e test.
- Real-Postgres `schema_health` tests were collected by the default API test command.
- Local docs still described the removed employer dev-login fallback.
- Real API Playwright helper still clicked the removed "Use local employer login"
  button.

**Root cause:** Clerk-only auth and Phase 2 live testing changes were applied across
code, tests, and docs at different times, leaving stale local setup assumptions.

**Files changed:**

- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `README.md`
- `apps/web/README.md`
- `apps/web/next.config.ts`
- `apps/web/tests/e2e/candidate-workspace.spec.ts`
- `apps/web/tests/e2e/real-api-invite-flow.spec.ts`
- `apps/api/tests/test_schema_health.py`
- `docs/development/testing.md`
- `docs/development/known-limitations.md`
- `docs/development/local-pilot-checklist.md`
- `docs/enhancements/phase-2-assessment-system/03-employer-assessment-configuration.md`
- `docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`

**What changed:**

- `next.config.ts` now prefers `process.env` values with root `.env` as fallback.
- Schema-health tests now skip unless `RUN_SCHEMA_HEALTH_TESTS=1`.
- Local docs now state that employer routes require Clerk locally and in production.
- Real API invite Playwright test now uses a pre-created `REAL_API_INVITE_TOKEN`.
- Candidate auto-expiry e2e test uses a mutable capture holder that typechecks.
- Stale docs saying Advanced is disabled were updated to reflect the implemented
  Advanced pack.

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 66 passed, 3 skipped.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 22 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- --workers=1`
  -> 16 passed, 2 skipped.
- Local live Standard candidate flow passed against disposable SQLite API, local Docker
  worker, and built web server.
- Local live Advanced candidate flow passed against the same local stack.
- Persisted live test-run outputs confirmed pytest ran inside the Docker assessment
  image for both public and hidden runs.

**Follow-up:** Real employer portal invite creation remains Clerk-only. Full employer
real-API Playwright creation requires a real signed-in Clerk browser session or a
valid test Clerk token.

---

## 2026-06-19 — Clerk-Only Auth + Local/Production Parity

**Symptom / goal:**

- Employer portal was showing "Local dev login active until Clerk keys are configured"
  even after Clerk was set up, because `EMPLOYER_AUTH_REQUIRED` could be toggled off and
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` was empty in the shell (overriding the root `.env`).
- 10–15 second API latency on employer auth calls because `PyJWKClient` was instantiated
  per-request with no cache.
- Employer page stuck in "Loading employer session" after server restart due to Clerk's
  `getToken` reference changing during initialization causing a cancel-restart loop in
  `useEffect`.
- User requirement: local and production environments must be identical — no dev
  fallback auth paths.

**Root cause:**

- `EMPLOYER_AUTH_REQUIRED` flag allowed bypassing Clerk JWT verification locally via a
  custom `X-Dev-Employer-Id` header and hardcoded employer config values.
- `PyJWKClient` constructed fresh on every request, causing TCP timeout stalls when the
  JWKS endpoint was slow.
- Shell had `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=''` which took precedence over the root
  `.env` value via Next.js's `process.env` auto-inlining.
- `getToken` from `useAuth()` gets a new function reference when Clerk initializes,
  recreating the `useCallback`, triggering the `useEffect` cleanup, and looping.

**Files changed:**

- `apps/api/signalloop_api/auth.py`
- `apps/api/signalloop_api/config.py`
- `apps/api/tests/conftest.py` (new — shared fixtures)
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/api/tests/test_ai_endpoint.py`
- `apps/api/tests/test_cors.py`
- `apps/api/tests/test_employer_isolation.py`
- `apps/api/tests/test_evidence_report.py`
- `apps/api/tests/test_final_submission.py`
- `apps/web/next.config.ts`
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/tests/e2e/employer-portal.spec.ts`

**What changed:**

- Removed `EMPLOYER_AUTH_REQUIRED`, `local_employer_clerk_user_id`, and
  `local_employer_email` from config. Both environments now always require a valid Clerk
  JWT — no dev bypass.
- Removed `local_employer_identity` branch from `auth.py`. `get_current_employer` only
  calls `verify_clerk_token`.
- `PyJWKClient` is now a module-level singleton with `cache_keys=True`, instantiated
  once at import time. Eliminates per-request HTTPS fetches and the 10–15 s stall.
- New `apps/api/tests/conftest.py` with shared `session_factory`, `default_employer`,
  `employer_context`, and `client` fixtures. All test files updated to use
  `app.dependency_overrides[get_current_employer]` instead of relying on dev fallback.
- `EmployerContext` dataclass in conftest lets isolation tests switch authenticated
  employer between requests without two-client contention on `app.dependency_overrides`.
- `apps/web/next.config.ts` injects root `.env` values into `process.env` before the
  config object so that a shell-exported empty variable does not shadow the file value.
- Added `allowedDevOrigins: ["127.0.0.1"]` to `next.config.ts` so HMR works when the
  browser connects via `127.0.0.1`.
- Employer dashboard (`page.tsx`) rewritten to Clerk-only: removed `DevPortal`,
  `ClerkEmployerPortal`, `isDev`, and `localSessionActive`. One code path.
- Added `isClerkLoaded` guard in `useEffect` on both the employer dashboard and the
  evidence report page — prevents the cancel-restart loop caused by `getToken` reference
  churn during Clerk initialization.
- Playwright `employer-portal.spec.ts`: added `mockClerkSignedIn` helper that
  intercepts `**clerk.accounts.dev/v1/client**`, returning a fake authenticated session
  for `GET /v1/client` and `{ object: "token", jwt }` for token refresh endpoints.

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> all passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npx playwright test tests/e2e/employer-portal.spec.ts` -> 5 passed.

---

## 2026-06-19 — Phase 2 Live E2E Findings

**Symptom:** Live local browser testing initially passed through the UI but exposed
several real integration issues:

- Parallel local fallback invite creation could fail with `UNIQUE constraint failed:
  employers.email`.
- Timed attempts could auto-expire immediately in the browser because API responses
  serialized naive timestamps without a UTC marker.
- A non-default web port failed browser fetches until API CORS included that origin.
- Public/hidden worker runs failed before pytest collection when the API used
  `ASSESSMENT_RUNTIME_IMAGE=python:3.11-slim`.
- The live Playwright smoke still asserted old Phase 1 final explanation fields and a
  Standard-only title.

**Root cause:**

- Local employer fallback did not handle unique-email collisions robustly.
- SQLite returns naive datetimes even when the app writes UTC-aware values; browser
  `Date.parse()` interpreted those as local time.
- Local live smoke services were split across `3100` and `8016` without matching CORS.
- `.env.example` still documented a generic Python image instead of the assessment
  runtime image.
- The live smoke test had not been updated for Phase 2 structured Submission Review or
  Advanced assessment titles.

**Files changed:**

- `.env.example`
- `apps/api/signalloop_api/auth.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/api/tests/test_employer_isolation.py`
- `apps/web/tests/e2e/live-full-stack-smoke.spec.ts`
- `docs/development/testing.md`
- `CURRENT_STATE.md`

**What changed:**

- Local fallback employer creation now recovers from unique collisions without merging
  distinct Clerk users by email.
- Candidate/employer attempt timestamps now serialize as UTC ISO strings ending in
  `Z`.
- Live Playwright smoke now uses Phase 2 Submission Review fields, accepts Standard or
  Advanced FastAPI titles, and has a live-worker timeout.
- `.env.example` now points local worker execution at
  `signalloop-python-assessment:3.11`.
- Testing docs now call out CORS/base URL alignment and the required local assessment
  runtime image.

**Validation:**

- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 57 passed.
- `cd apps/worker && UV_CACHE_DIR=.uv-cache uv run pytest` -> 22 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `docker build -f docker/python-assessment.Dockerfile -t signalloop-python-assessment:3.11 .`
  from `apps/worker` -> passed.
- `docker run --rm signalloop-python-assessment:3.11 python -m pytest --version`
  -> `pytest 8.3.4`.
- Live Standard browser smoke passed once against the disposable local API/worker/web,
  then persisted worker output inspection showed the API had used the wrong runtime image.
- Live Advanced browser smoke passed once against the disposable local API/worker/web,
  then persisted worker output inspection showed the API had used the wrong runtime image.

**Follow-up:**

- Re-run fresh Standard and Advanced live Playwright smokes locally with
  `ASSESSMENT_RUNTIME_IMAGE=signalloop-python-assessment:3.11`; the final rerun after
  correcting the runtime image was blocked by the Codex escalation usage limit.
- After those pass, generate reports for the fresh attempts and verify employer report
  pages in the browser.

---

## 2026-06-19 — Playwright E2E Sandbox Fix

**Symptom:** `npm run test:e2e` was unreliable in Codex. Playwright first failed while
trying to bind `127.0.0.1:3000` even though a dev server was already running; direct
browser launch then failed inside the macOS sandbox with a Chromium Mach-port permission
error.

**Root cause:** The Playwright config always tried to manage the web server, and the
Codex sandbox can block both local server binding and Chromium's macOS browser-process
registration. Once run outside the sandbox, the employer report test also had one stale
strict-mode assertion because "Public issue resolution" now appears in both the chart
label and score-card title.

**Files changed:**

- `apps/web/playwright.config.ts`
- `apps/web/tests/e2e/employer-portal.spec.ts`
- `docs/development/testing.md`
- `docs/enhancements/phase-2-assessment-system/05-advanced-assessment-pack.md`
- `CURRENT_STATE.md`

**What changed:**

- Added `PLAYWRIGHT_BASE_URL` for non-default local/hosted targets.
- Added `PLAYWRIGHT_SKIP_WEBSERVER=1` so e2e can reuse an already-running web server.
- Tightened the employer report assertion to avoid duplicate-text strict-mode failure.
- Documented the reusable local command.

**Validation:**

- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e -- --workers=1`
  -> 2 passed, 1 skipped.

**Follow-up:** The skipped live smoke remains intentional. Run it only with API, worker,
web, and a valid `LIVE_INVITE_TOKEN`.

---

## 2026-06-19 — Phase 2 Task 02 AI Collaborator Policy Tightening

**Symptom:** The AI collaborator policy allowed tradeoff discussion, but the classifier
did not explicitly distinguish "compare tradeoffs" from "choose the answer for me" and
did not tag prompt-injection attempts.

**Root cause:** MVP policy tags focused on all-defects/full-solution/final-explanation
requests and did not encode Phase 2 design-choice ownership or prompt-injection evidence.

**Files changed:**

- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/signalloop_api/ai_provider.py`
- `apps/api/tests/test_ai_policy.py`
- `apps/api/tests/test_ai_endpoint.py`
- `docs/prompts/ai-collaborator-policy.md`
- `docs/enhancements/phase-2-assessment-system/02-ai-collaborator-policy-tightening.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `CURRENT_STATE.md`

**What changed:**

- Added disallowed `choose_design` and `prompt_injection` tags.
- Added a specific redirect for requests asking the assistant to choose an assessment
  design decision.
- Updated the system prompt and local fallback classifier.
- Updated provider fallback behavior to preserve task-specific redirect messages.
- Added AI policy and endpoint tests for tradeoff comparison, design-choice redirect, and
  prompt-injection detection.

**Validation:**

- `cd apps/api && uv run pytest tests/test_ai_policy.py tests/test_ai_endpoint.py tests/test_ai_provider.py`
  -> 11 passed.
- `cd apps/api && uv run pytest` -> 49 passed.

**Follow-up:** AI integrity risk remains report-only and will be surfaced in the reporting
task.

---

## 2026-06-19 — Phase 2 Task 01 Standard v2 Assessment And Rubric

**Symptom:** The MVP assessment and deterministic scoring model were too shallow for the
next phase of human-AI engineering evaluation.

**Root cause:** `fastapi_task_api_v1` was designed as the historical MVP/pilot pack, and
the MVP scoring rubric overweighted simple public/hidden test totals and a generic
written explanation category.

**Files changed:**

- `assessment_packs/fastapi_task_api_standard_v2/`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/reports.py`
- `apps/api/signalloop_api/schemas.py`
- `apps/api/tests/test_attempt_lifecycle.py`
- `apps/web/tests/e2e/candidate-workspace.spec.ts`
- `apps/web/tests/e2e/employer-portal.spec.ts`
- `docs/enhancements/phase-2-assessment-system/01-assessment-rubric-and-standard-pack.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `docs/architecture/technical-product-architecture-spec.md`
- `docs/development/known-limitations.md`
- `CURRENT_STATE.md`

**What changed:**

- Created `assessment_packs/fastapi_task_api_standard_v2/` and kept v1 intact.
- Added priority handling as the standard-v2 feature/design dimension.
- Standard v2 starter public tests intentionally pass 2 and fail 4.
- Standard v2 reference solution passes 6 public and 7 hidden tests.
- Default invite pack changed to `fastapi_task_api_standard_v2`.
- Report scoring now uses Phase 2 categories:
  public issue resolution, private issue generalization, feature/design implementation,
  candidate-written tests, AI collaboration, and regression/code quality.
- Candidate-written test scoring now considers test function count, HTTP assertions, and
  edge-case signals instead of only counting touched files.

**Validation:**

- `cd assessment_packs/fastapi_task_api_standard_v2/candidate && uv run pytest`
  -> expected 2 passed, 4 failed.
- `cd assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution && uv run pytest -c pyproject.toml --rootdir=. ../../candidate/tests`
  -> 6 passed.
- `cd assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution && uv run pytest -c pyproject.toml --rootdir=. ../hidden_tests`
  -> 7 passed.
- `cd apps/api && uv run pytest` -> 45 passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run typecheck` -> passed after build regenerated `.next/types`.
- `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.

**Follow-up:** Implement structured submission review and report-only AI integrity risk in
their bounded Phase 2 tasks.

---

## 2026-06-19 — Phase 2 Task 08 Multi-Tenant Employer Isolation

**Symptom:** Employer portal login was a frontend gate only. Backend employer routes could
list all attempts, create attempts with a client-supplied `employer_id`, and generate or
fetch reports by attempt id without ownership checks.

**Root cause:** The MVP shipped with Clerk only on the web surface; the API did not verify
Clerk identity or derive tenant ownership server-side.

**Files changed:**

- `apps/api/pyproject.toml`
- `apps/api/uv.lock`
- `apps/api/signalloop_api/auth.py`
- `apps/api/signalloop_api/config.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/reports.py`
- `apps/api/tests/test_employer_isolation.py`
- `apps/web/src/app/employer/api.ts`
- `apps/web/src/app/employer/page.tsx`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `docs/deployment/render-supabase-clerk.md`
- `docs/development/known-limitations.md`
- `docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `CURRENT_STATE.md`

**What changed:**

- Added backend Clerk JWT verification with `PyJWT[crypto]`.
- Added `get_current_employer` and local-only dev employer fallback.
- Invite creation now derives `attempt.employer_id` from the authenticated employer and
  ignores client-supplied `employer_id`.
- Attempt listing is scoped to the authenticated employer.
- Evidence-report generation/fetch validates attempt ownership.
- Employer web API calls send Clerk bearer tokens when available.
- Added tenant isolation API tests.

**Validation:**

- `cd apps/api && uv run pytest` -> 45 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.

**Follow-up:** Set `EMPLOYER_AUTH_REQUIRED=true` plus Clerk JWT issuer/JWKS env values in
Render before deploying this change.

---

## 2026-06-19 — Phase 2 Planning Freeze Updates

**Symptom:** Phase 2 scope had open decisions around employer isolation, report
confidence, AI misuse indicators, structured candidate submission evidence, and UI polish.

**Root cause:** The MVP validated the end-to-end flow but left several post-MVP decisions
as conversational context rather than durable implementation guidance.

**Files changed:**

- `CURRENT_STATE.md`
- `docs/architecture/technical-product-architecture-spec.md`
- `docs/enhancements/phase-2-assessment-system/README.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-execution-plan.md`
- `docs/enhancements/phase-2-assessment-system/phase-2-product-scope.md`
- `docs/enhancements/phase-2-assessment-system/02-ai-collaborator-policy-tightening.md`
- `docs/enhancements/phase-2-assessment-system/06-ui-enhancements.md`
- `docs/enhancements/phase-2-assessment-system/07-reporting-and-favo-updates.md`
- `docs/enhancements/phase-2-assessment-system/08-multi-tenant-employer-isolation.md`

**What changed:**

- Added strict Clerk-user-based employer isolation as a Phase 2 task.
- Captured that AI integrity risk is report-only and must not directly affect numeric
  score in Phase 2.
- Captured removal of the generic employer-facing report confidence label.
- Captured structured Submission Review and final-submit confirmation behavior.
- Captured report/candidate UI polish direction, including simple report charts and
  an AI integrity risk panel.

**Follow-up:** Implement one bounded Phase 2 task at a time. Multi-tenant isolation should
be completed before broader external pilot usage.

---

## 2026-06-17 — Hosted Render/Supabase/AWS E2E Smoke Findings

**Why:** First hosted e2e smoke was run against:

- API: `https://signalloop-api.onrender.com`
- Web: `https://signalloop-web.onrender.com`

**What was verified:**

- API `/health` returned 200.
- Web root returned 200.
- API could query the Supabase-backed attempt list.
- Hosted invite creation worked and generated a web invite URL.
- Candidate invite opened against the deployed web app with no browser console errors.
- Candidate workspace loaded assessment files and the rules gate.
- Employer report page rendered a generated report with no browser console errors.

**Findings:**

1. Production execution is blocked by AWS IAM.
   - Public test execution returned `AccessDenied` on `s3:PutObject`.
   - The Render API IAM user `signalloop-render-api` cannot write run payloads to
     `s3://SIGNALLOOP_RUN_BUCKET/runs/...`.
   - ECS did not start because the API failed before `RunTask`.
2. Hosted final submission can leave an attempt submitted without a hidden test run.
   - The UI submit request timed out while waiting for the hidden evaluation status.
   - The API attempt state became `submitted`.
   - Evidence report generation succeeded afterward, but hidden tests showed `missing`.
   - Follow-up: make submission/hidden evaluation atomic enough for MVP, or store a
     pending/error hidden test run if execution fails or the request is interrupted.

**Files changed:**

- `docs/development/changes.md`
- `CURRENT_STATE.md`

**Follow-up items:**

- Add least-privilege S3 permissions for the Render API IAM user.
- Confirm ECS `RunTask`, `DescribeTasks`, and `iam:PassRole` permissions after S3 is fixed.
- Confirm the ECS task role can read/write the same S3 run prefix.
- Re-run hosted public tests, final submission, and report generation.

**Update after S3 input permission fix:**

- A fresh hosted attempt was created and public test execution no longer failed on
  `s3:PutObject`.
- The request waited for the ECS/Fargate task path and then failed with S3 `NoSuchKey`
  while reading the expected `runs/{run_id}/output.json`.
- This means the API can write the input payload and reach the wait/read stage, but the
  runner task did not produce the expected output object.
- Next check CloudWatch logs for `/ecs/signalloop-assessment-runner` and verify the ECS
  task role can read and write `arn:aws:s3:::SIGNALLOOP_RUN_BUCKET/runs/*`.

**Update after linux/amd64 runner image fix:**

- A fresh hosted attempt was created and public test execution returned a real pytest
  result from ECS/Fargate.
- ECS runner output was successfully written to S3 and read by the API.
- The run failed during pytest collection because the Fargate runner image had `pytest`
  and `boto3`, but did not include the assessment runtime dependencies:
  `fastapi`, `httpx`, and `uvicorn`.
- Fixed `apps/runner/Dockerfile` to install the same candidate runtime dependencies used
  by the local Docker assessment image.
- Local Docker smoke with a FastAPI `TestClient` test now passes inside
  `signalloop-assessment-runner:local`.
- Follow-up: rebuild and push the runner image with `--platform linux/amd64`, then rerun
  the hosted public test, final submission, and report flow.

**Update after runner dependency image push:**

- A fresh hosted attempt was created on 2026-06-18.
- Hosted public test execution now works end-to-end through Render API, S3, ECS/Fargate,
  runner output, and API persistence.
- Public test result on unchanged starter code was expected: 2 passed, 2 failed.
- Final submission still returned a generic API 500 while the attempt was marked
  `submitted`, leaving no hidden test run/report for that attempt.
- Local hidden-run reproduction returns a valid failed hidden-test result, so the hosted
  failure is likely an uncaught AWS/runtime exception in the hidden-evaluation path.
- Fixed `apps/api/signalloop_api/submissions.py` to convert any hidden-evaluation
  exception into a persisted hidden test `error` result instead of returning 500 after
  the attempt is submitted.
- Added regression coverage in `apps/api/tests/test_final_submission.py`.
- `cd apps/api && uv run pytest` now reports 36 passed.
- Follow-up: deploy this API fix to Render, then rerun final submission and report
  generation on a fresh hosted attempt.

**Update after Render API redeploy with submission hardening:**

- A fresh hosted attempt was created on 2026-06-18.
- Hosted public execution still works end-to-end and returned the expected unchanged
  starter result: 2 passed, 2 failed.
- Final submission now returns 201 instead of a generic 500.
- A hidden `TestRun` is persisted and linked to the submission.
- Evidence report generation succeeds and renders in the hosted employer report page.
- The hidden run status is currently `error`, not a real hidden pytest `failed` result.
  The report endpoint does not expose hidden stderr, so the next step is checking Render
  API logs or adding an internal diagnostics path to identify the hidden-run exception.

**Update after hidden-test path-resolution deploy:**

- A fresh hosted attempt was created on 2026-06-18 after deploying the fix that resolves
  evaluator hidden tests from the current pack config before falling back to the stored
  DB path.
- Hosted public execution still works end-to-end and returned the expected unchanged
  starter result: 2 passed, 2 failed.
- Final submission returned 201 and persisted a hidden `TestRun`.
- Hidden status still persisted as `error`; evidence report generation succeeded but
  hidden tests still showed `collected: 0`, `passed: 0`, `failed: 0`, `status: error`.
- The path-resolution fix was therefore not sufficient, or the deployed API still cannot
  complete the hidden-run setup for another reason. Need Render API logs or an internal
  diagnostics endpoint/temporary admin check that exposes the hidden-run error for
  attempt 6/test run 9.

**Update after local DB check and hidden logging patch:**

- Local `.env` points at `localhost:5432/signalloop`, not the hosted Supabase database
  used by Render, so querying `test_runs.id = 9` locally did not inspect the hosted
  hidden run. That local row was a public test run.
- Added Render/API-side logging around hidden test loading and hidden evaluation:
  configured vs stored evaluator path fallback, hidden test count, runner start,
  runner completion, and exception traceback before error-result persistence.
- No hidden test source content is logged.
- `cd apps/api && uv run pytest` reports 37 passed.
- Follow-up: deploy this logging patch, submit a fresh hosted attempt, then inspect Render
  API logs around final submission to identify the exact hidden-run exception.

**Update after hidden runner adapter fix:**

- Root cause found from Render/API logs: `submit_final_attempt()` expected the hidden
  runner dependency to expose `.run(...)`, but `get_hidden_test_runner()` was returning
  `ECSFargateExecutionProvider`, which exposes `.run_hidden(...)`.
- Fix deployed: hidden execution now uses an adapter that calls
  `get_execution_provider().run_hidden(...)`.
- Fresh hosted attempt 7 validated the full hosted path:
  - public ECS/Fargate execution returned expected unchanged-starter result: 2 passed,
    2 failed,
  - final submission returned 201 with `hidden_test_status: failed`,
  - hidden ECS/Fargate execution collected 6 tests, passed 1, failed 5,
  - evidence report generation returned 201 with score 26 and recommendation
    `do_not_advance`,
  - hosted employer report page rendered without browser console errors.

**Full validation round before user pilot testing:**

- Local automated checks:
  - `cd apps/api && uv run pytest` -> 38 passed,
  - `cd apps/worker && uv run pytest` -> 22 passed,
  - `cd apps/web && npm run typecheck` -> passed,
  - `cd apps/web && npm run lint` -> passed,
  - `cd apps/web && npm run build` -> passed,
  - `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.
- Updated stale Playwright assertions to match current UI copy and duplicate report text:
  candidate hidden status text and employer report summary assertion.
- Hosted browser-level e2e with fresh attempt 8:
  - candidate invite loaded,
  - public tests ran from hosted web UI through ECS/Fargate,
  - final submission ran hidden tests through ECS/Fargate,
  - evidence report generated with score 26 and recommendation `do_not_advance`,
  - hidden summary was collected 6, passed 1, failed 5,
  - hosted report page rendered without browser console errors.
- Final hosted checks:
  - `https://signalloop-api.onrender.com/health` returned 200,
  - hosted employer portal rendered Clerk sign-in state without browser console errors.

**UX follow-up after user pilot notes:**

- Observed production test and submit latency is expected from the AWS ECS/Fargate
  per-run model: API writes input to S3, starts a fresh isolated Fargate task, waits for
  container startup/test execution, then reads output from S3 and persists the result.
- Added non-blocking inline progress messages while public tests and final submission are
  running so candidates see that the isolated job is still in progress.
- Changed the root web route to redirect directly to `/employer`, removing the extra
  landing screen before Clerk login for employer users. Candidate access remains invite
  URL based.
- Checks after the UX update:
  - `cd apps/web && npm run typecheck` -> passed,
  - `cd apps/web && npm run lint` -> passed,
  - `cd apps/web && npm run build` -> passed,
  - `cd apps/web && npm run test:e2e` -> 2 passed, 1 skipped.

---

## 2026-06-17 — Hosted Deployment Scaffold: Render, Supabase, and ECS/Fargate

**Why:** Local validation is far enough along to prepare the external deployment path:
Render for web/API, Supabase for Postgres, Clerk for employer auth, and AWS ECS/Fargate
for production execution without Docker-in-Docker.

**What changed:**

- Added root `render.yaml` Blueprint for Render web/API services using root-relative
  monorepo commands.
- Clarified environment split:
  - local root `.env` for local dev,
  - Render environment settings for production/pilot,
  - Supabase dashboard for database credentials,
  - Clerk dashboard for auth keys,
  - AWS resources/env vars for ECS/Fargate execution.
- Removed obsolete `NEXT_PUBLIC_WORKER_URL` from env templates because browser public
  test execution now goes through the API. Also removed stale web README, Playwright
  config, and candidate page references.
- Added `apps/runner` Fargate runner image that runs tests directly in the task and
  reads/writes JSON payloads from local files or S3.
- Added ECS task definition and run-task override templates under `infra/aws/ecs`.
- Added AWS ECS/Fargate deployment guide.
- Added AWS credential/resource placeholders for the future Render API to ECS integration.

**Files changed:**
- `render.yaml`
- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `apps/runner/Dockerfile`
- `apps/runner/signalloop_runner/__init__.py`
- `apps/runner/signalloop_runner/main.py`
- `apps/web/README.md`
- `apps/web/playwright.config.ts`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
- `infra/aws/ecs/task-definition.runner.template.json`
- `infra/aws/ecs/run-task-overrides.example.json`
- `infra/aws/ecs/README.md`
- `docs/deployment/render-supabase-clerk.md`
- `docs/deployment/aws-ecs-fargate-execution.md`
- `CURRENT_STATE.md`

**Follow-up items:**

- Push the repo to GitHub and connect Render to that GitHub repository.
- Create Supabase, Clerk, and Render service env vars from `.env.render-supabase.example`.
- Create AWS ECR/S3/ECS/IAM resources.
- Run hosted integration testing after AWS ECR/S3/ECS/IAM resources are created.

---

## 2026-06-17 — API ECS/Fargate Execution Provider

**Why:** The deployment scaffold needed the API-side execution provider before production
candidate execution can use AWS ECS/Fargate instead of a raw HTTP worker.

**What changed:**

- Added `apps/api/signalloop_api/execution.py` with a shared execution provider boundary.
- Local/staging default remains `EXECUTION_BACKEND=http_worker`.
- Production can use `EXECUTION_BACKEND=ecs_fargate`, which writes run payloads to S3,
  calls ECS `RunTask`, waits for completion, reads runner output JSON from S3, and
  returns the existing public/hidden test result shape.
- Public and hidden test paths now use the shared provider.
- Added AWS ECS env vars to templates and Render Blueprint.
- Added a fake-client unit test for ECS provider behavior.

**Files changed:**
- `apps/api/signalloop_api/execution.py`
- `apps/api/signalloop_api/config.py`
- `apps/api/signalloop_api/attempts.py`
- `apps/api/signalloop_api/submissions.py`
- `apps/api/tests/test_execution.py`
- `apps/api/tests/test_final_submission.py`
- `apps/api/pyproject.toml`
- `apps/api/uv.lock`
- `.env.example`
- `.env.local.example`
- `.env.render-supabase.example`
- `render.yaml`
- `docs/deployment/aws-ecs-fargate-execution.md`
- `docs/deployment/render-supabase-clerk.md`
- `CURRENT_STATE.md`

**Validation:**
- `cd apps/api && uv run pytest` — 35 passed.
- `cd apps/web && npm run typecheck` — passed.
- `cd apps/web && npm run lint` — passed.

---

## 2026-06-17 — Candidate Workspace: Final Submission UX Fixes

**Why:** Several submission flow issues found during live testing — 422 errors with unhelpful messages, FINAL_EXPLANATION.md still visible in file tree, seeded hint not visible after test run, and hidden test status message was raw/technical.

**What changed:**

- `final_explanation` is now **required** before Submit is enabled. `decision_log` remains optional. Backend schema enforces `min_length=1` on `final_explanation` only.
- `FINAL_EXPLANATION.md` was already filtered server-side (`IGNORED_FILENAMES`) but requires an API restart to take effect.
- 422 error responses now show the field-level message (e.g. `final_explanation: String should have at least 1 character`) instead of just the HTTP status.
- Seeded hint ("N additional behaviors evaluated beyond these public tests") moved above the `<pre>` output block so it's always visible after running tests. Was previously pushed below the fold by `height: 100%` on the output element.
- `.test-panel` changed from `display: grid` to `display: flex; flex-direction: column`. `.output` changed from `height: 100%` to `flex: 1` so it scrolls internally and doesn't consume all panel space.
- Hidden test result message after submission changed from raw `"failed"/"passed"` status to `"Some hidden tests failed."` / `"All hidden tests passed."` — shown in both topbar and submission panel.
- Seeded issue count (`6`) is static — it is the total count of seeded behaviors, not a live counter of remaining failures. Candidates cannot see hidden test results during the assessment.
- e2e test updated: Submit now asserts disabled before explanation filled, enabled after.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/api/signalloop_api/schemas.py`
- `apps/web/tests/e2e/candidate-workspace.spec.ts`

---

## 2026-06-17 — AI Policy: LLM-based Intent Classification

**Why:** Pattern matching (`"fix all"`, `"find all bugs"`, etc.) is too brittle — slight rephrasing bypasses it entirely. "Can you fix all the errors?" was not caught. The LLM already understands semantic intent; using it to classify is more accurate and adds no extra latency.

**What changed:**

- Single LLM call now handles both classification AND response generation. The system prompt instructs the model to output JSON: `{allowed: bool, policy_tags: [], message: str}`. No separate classification step.
- `ai_policy.py` — updated `SYSTEM_PROMPT` with explicit JSON output format and tag definitions. Old `classify_message()` renamed to `fallback_classify()` (used only when JSON parsing fails).
- `ai_provider.py` — `AIProvider.complete()` replaced by `AIProvider.evaluate()` returning `AIDecision(allowed, policy_tags, message)`. `parse_ai_decision()` handles JSON parsing with fallback to pattern matching on failure.
- `ai.py` — no longer calls `classify_message` separately; calls `provider.evaluate()` directly.
- `LocalGuidanceProvider` (no-OpenAI-key fallback) uses `fallback_classify` internally.
- Tests updated: `FakeProvider.complete()` → `FakeProvider.evaluate()`, `classify_message` → `fallback_classify`, removed `"public_test_output"` hint tag assertion (hint tags only existed in pattern path, not LLM path).

**Files changed:**
- `apps/api/signalloop_api/ai_policy.py`
- `apps/api/signalloop_api/ai_provider.py`
- `apps/api/signalloop_api/ai.py`
- `apps/api/tests/test_ai_policy.py`
- `apps/api/tests/test_ai_endpoint.py`
- `apps/api/tests/test_evidence_report.py`

---

## 2026-06-17 — Public Test Results Persisted to Database

**Why:** Public tests were called directly from the browser to the worker. The result was shown to the candidate but never saved to the DB, so the evidence report had nothing to score — always showed "No public test run recorded" and 0 points for public test coverage.

**What changed:**

- New API endpoint `POST /candidate/invites/{token}/run-public-tests` — saves a snapshot, calls the worker, stores the result as a `TestRun` with `run_type="public"`, and returns the result to the frontend.
- Frontend now calls this API endpoint instead of the worker directly. `NEXT_PUBLIC_WORKER_URL` is no longer needed for public test runs.
- The separate `saveSnapshot("public_test_run")` call before running tests is removed — the new endpoint handles the snapshot internally.

**Files changed:**
- `apps/api/signalloop_api/attempts.py`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`

---

## 2026-06-17 — Evidence Report: Dynamic Follow-up Questions + Report UI Rewrite

**Why:** Follow-up questions were hardcoded static strings — same 4 questions for every candidate regardless of what they did. Report UI was using old section names (`favo_analysis`, `functional_correctness`, etc.) that no longer exist after the rubric redesign, leaving sections blank.

**What changed:**

- `build_follow_up_questions()` now generates questions dynamically from the evidence:
  - Names the specific failing hidden test area
  - Asks about 403 vs 404 only if they didn't address it in their explanation
  - Asks about status transitions if not mentioned
  - Asks about test coverage only if no candidate tests were written
  - Asks about AI policy redirects if any occurred
  - Asks about AI code paste or large paste events if detected
  - Asks for elaboration if final explanation is under 80 chars
- Report UI (`employer/reports/[attemptId]/page.tsx`) fully rewritten to use new section names: `public_test_results`, `hidden_test_results`, `candidate_tests`, `ai_collaboration`, `process_evidence`, `explanation_submitted`, `timeline`, `follow_up_questions`
- `employer/types.ts` updated to match new report structure — old types (`favo_analysis`, `seeded_issue_coverage`, etc.) removed
- CSS: added `report-label`, `report-list`, `report-notes`, `report-warn`, `timeline-list` classes
- Scoring fixes: regression gives 0 (not 8) when no public test run recorded; AI collaboration gives 0 (not 5) when no AI messages sent

**Files changed:**
- `apps/api/signalloop_api/reports.py`
- `apps/web/src/app/employer/reports/[attemptId]/page.tsx`
- `apps/web/src/app/employer/types.ts`
- `apps/web/src/app/globals.css`

---

## 2026-06-17 — Evidence Report: AI Paste Detection (External Code)

**Why:** Candidates could paste large blocks of code from ChatGPT or other external sources without any trace in the AI collaboration panel. This is invisible in the current report.

**Approach:** Option B — snapshot diff analysis. The execution worker already saves snapshots (autosave + before test runs). By comparing consecutive snapshots with `difflib.SequenceMatcher`, we can detect when 8+ consecutive lines appear in a single snapshot interval, which is a strong signal of an external paste.

**What changed:** `ai_collaboration` section in the evidence report now includes:
- `large_paste_events` — list of `{file, lines_added, snapshot_kind, at, code_preview}` for every detected large paste
- `pasted_ai_code` — list of code blocks from AI responses that also appear verbatim in final submitted files (but not in initial files)

**Detection thresholds:**
- `PASTE_LINE_THRESHOLD = 8` — minimum consecutive new lines to flag as a potential external paste
- AI code paste: code block must be 3+ lines and 40+ chars to be worth matching

**Files changed:**
- `apps/api/signalloop_api/reports.py` — added `detect_large_paste_events()`, `detect_pasted_ai_code()`, `extract_code_blocks()`; wired into `build_report`
- `apps/api/tests/test_evidence_report.py` — added 4 unit tests: flags new AI code in final files, ignores existing code quoted by AI, flags big paste between snapshots, ignores small additions

---

## 2026-06-17 — Evidence Report: Full AI Message History

**Why:** The employer could see *that* policy redirects happened and *how many*, but not *what the candidate actually asked*. A candidate who tried to get the full solution multiple times should be visible in the report.

**What changed:** `ai_collaboration` section in the evidence report now includes:
- `policy_redirect_count` — total disallowed prompts
- `flagged_prompts` — list of `{message, policy_tags, at}` for every prompt that triggered a policy redirect (paired with the preceding candidate message)
- `all_candidate_messages` — full list of `{message, at}` for every candidate prompt, so the employer can read the entire AI conversation

**Files changed:**
- `apps/api/signalloop_api/reports.py` — expanded `ai_collaboration` section in `build_report`

---

## 2026-06-17 — E2E Test Update (post UI/scoring changes)

**Context:** Multiple UI and scoring changes were made in this session. Ran full e2e suite to catch regressions.

**Failures found and fixed:**
- `candidate-workspace.spec.ts` line 116: asserted Save button disabled after submission — Save button was removed (auto-snapshot now). Removed assertion.
- `candidate-workspace.spec.ts` mock: missing `seeded_issue_count` in mock `assessment` object. Added `seeded_issue_count: 6`.
- Added new assertions: seeded issue note visible after test run; Submit button enabled before textareas are filled (now optional).

**Files changed:**
- `apps/web/tests/e2e/candidate-workspace.spec.ts`

**Test status after fixes:**

| Check | Result |
|---|---|
| `cd apps/api && uv run pytest` | 30 passed |
| `cd apps/worker && uv run pytest` | 22 passed |
| `cd apps/web && npm run typecheck` | clean |
| `cd apps/web && npm run test:e2e` | 2 passed, 1 skipped |

---

## 2026-06-17 — Scoring Rubric Redesign

**Why:** Original rubric had 9 overlapping categories (100 pts) where seeded issue coverage was only 15 pts despite being the primary signal. Public tests had no separate score. Too complex to explain or maintain.

**New rubric (all weights in `RUBRIC` dict at top of `reports.py` — change there only):**

| Category | Points |
|---|---|
| Public test coverage | 20 |
| Hidden test coverage | 30 |
| Regression | 15 |
| Candidate-written tests | 15 |
| AI collaboration | 10 |
| Explanation and decisions | 10 |
| **Total** | **100** |

**Key design decisions:**
- `RUBRIC` dict is the single source of truth for all point values — rebalancing requires changing one dict only
- Public tests scored from last run pass rate (4 tests × 5 pts each)
- Hidden tests scored from parsed pytest output (6 tests × 5 pts each)
- Regression inferred from public test pass count (can't determine which specific tests ran)
- `parse_pytest_output()` replaces old `hidden_test_summary()` and is used for both public and hidden runs
- `SEEDED_ISSUE_AREAS` updated to list all 6 seeded issues (was missing "unknown actor access" and "idempotent delete")

**Files changed:**
- `apps/api/signalloop_api/reports.py` — full rewrite of scoring section; new `RUBRIC` config dict; new `parse_pytest_output()`; renamed report sections to match new categories; imports `DEFAULT_PACKS` from `attempts` to access `initially_failing_tests`
- `apps/api/signalloop_api/attempts.py` — added `initially_failing_tests` list to `DEFAULT_PACKS` entry
- `apps/api/tests/test_evidence_report.py` — updated section name assertions and key checks to match new report structure
- `assessment_packs/fastapi_task_api_v1/evaluator/SCORING_RUBRIC.md` — rewritten to match new rubric
- `docs/architecture/technical-product-architecture-spec.md` — sections 15 (report structure) and 16 (scoring rubric) updated to reflect new category names and weights

**Key scoring logic:**
- Public test score: `initially_failing_tests` from `DEFAULT_PACKS` defines which tests count. A test is "fixed" if it was in the initially-failing list but is NOT in the final run's failure names. Tests that already pass in the starter code contribute 0 to public test coverage (they go to regression instead).
- Regression score: any test NOT in `initially_failing_tests` that appears in failure names after candidate changes = regression.

---

## 2026-06-17 — E2E Validation Round 1

### Context

First automated e2e pass after Phase 12 completion. All 12 phases were already coded.
Goal: run the test plan from `local-pilot-checklist.md` against the locally running stack
and fix any failures before hosted deployment.

### Environment at the time of testing

| Service | Port | Process |
|---|---|---|
| Next.js web | 3000 | `npm run dev` |
| SignalLoop API | 8015 | `uvicorn signalloop_api.main:app --port 8015` |
| Worker | 9000 | `uvicorn signalloop_worker.main:app --port 9000` |
| Assessment task_api (unrelated) | 8000 | Running from `/signalloop/ass1` |

---

### Bug 1 — API port mismatch in `.env` (critical, broke all live API calls)

**Symptom:** All real API calls from the web UI silently failed. The SignalLoop API was
running on port 8015, but `.env` had `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
Port 8000 was occupied by an unrelated `task_api` process returning 404 for all
SignalLoop routes.

**Files changed:**
- `.env` — `NEXT_PUBLIC_API_URL` changed from `8000` to `8015`

**Note for next agent:** The `.env.example` documents port 8000 as the canonical
default. The mismatch arose because the API was started manually on 8015. If you
restart the API on 8000, revert `.env` accordingly. The `playwright.config.ts` webServer
command already uses 8015 to match the running API. Keep `.env` and the config in sync.

**Action required after this change:** Restart the Next.js dev server so `NEXT_PUBLIC_`
vars are re-read from the updated `.env`.

---

### Bug 2 — Hidden evaluation result not visible after submission (e2e test failure)

**Symptom:** `candidate-workspace.spec.ts` line 115 failed:
```
expect(getByText("Hidden evaluation recorded with status: failed")).toBeVisible()
```
The element was in the DOM but Playwright reported it as `hidden` on every retry (14x
over 5 seconds). Root cause: the `<p>` was inside `.submission-panel` (`overflow: auto`,
240px tall). Filling the textareas scrolls the panel ~106px down. After submission the
paragraph renders near the top (y≈54px), below the scroll viewport (y=106 to y=346).

Multiple scroll recovery approaches were tried and all failed to satisfy Playwright's
visibility check within the 5-second assertion window:
- `window.setTimeout(() => scrollTo({top:0}), 0)` — original code, failed
- `useEffect + scrollIntoView({block:"nearest"})` — failed
- `useLayoutEffect + scrollIntoView({block:"nearest"})` — failed
- `useLayoutEffect + scrollTo({top:0})` — failed

**Fix:** Moved the exact status text to the topbar (always visible, never inside a
scroll container), which is the right UX location for status information. The submission
panel now shows a summary with different text (`"Evaluation complete. Hidden test
status: ..."`) to avoid duplicate Playwright locator matches.

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - Added `{submissionResult ? <span>Hidden evaluation recorded with status: ...</span>}` in
    the topbar `<div className="topbar-actions">`, right after the "submitted" status pill
  - Changed panel paragraph text to `"Evaluation complete. Hidden test status: ..."`
  - Removed the failed `window.setTimeout + scrollTo` and the replacement ref/effect code

---

### Bug 3 — Employer portal e2e test blocked by Clerk sign-in (test failure + hidden test bug)

**Symptom:** `employer-portal.spec.ts` timed out at line 117 waiting for
`button[name="Use local employer login"]`. With Clerk keys set in `.env`, the page
rendered only "Sign in with Clerk". After fixing that, it then timed out at line 128
on `getByRole("link", { name: "View" }).nth(1)`.

**Root cause 1:** `EmployerPortal` unconditionally rendered `ClerkEmployerPortal`
whenever `clerkConfigured` was true. `ClerkEmployerPortal` passes `onLocalLogin={() => undefined}`
(a no-op) to `AuthPanel`, so clicking the button did nothing.

**Root cause 2:** `.nth(1)` (second "View" link) was wrong. After creating a new invite,
the list has one "created" attempt (no View link) and one "submitted" attempt (one View
link). Only one View link exists; `.nth(1)` is out of bounds.

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
  - Added `const isDev = process.env.NODE_ENV !== "production"`
  - Changed `EmployerPortal` to use local session flow when `isDev`, even if
    `clerkConfigured` — Clerk sign-in still works in dev because `ClerkProvider` wraps
    the whole app; local bypass just skips `ClerkEmployerPortal`'s gating
  - `AuthPanel` now renders "Use local employer login" when `!clerkConfigured || isDev`
  - `localSessionActive` state initialiser skips false-init when `isDev`

- `apps/web/tests/e2e/employer-portal.spec.ts`
  - Line 128: `.nth(1)` → `.nth(0)` (only one View link exists after invite creation)

**Production safety:** The `isDev` condition uses `process.env.NODE_ENV !== "production"`.
In production builds (`NODE_ENV=production`), Clerk-configured deployments still enforce
Clerk-only sign-in. The local bypass is dev-mode only.

---

### Test status after fixes (2026-06-17)

| Check | Result |
|---|---|
| `cd apps/api && uv run pytest` | 30 passed |
| `cd apps/worker && uv run pytest` | 22 passed |
| `cd apps/web && npm run typecheck` | clean |
| `cd apps/web && npm run lint` | clean |
| `cd apps/web && npm run test:e2e` | 2 passed, 1 skipped |

The skipped test is `live-full-stack-smoke.spec.ts` — requires `LIVE_INVITE_TOKEN` and
live running services.

---

## 2026-06-17 — Candidate UX Round 2

### Change 1 — Auto-snapshot replaces manual Save button

**Why:** The Save button implied code changes needed to be saved to work, which was false. Monaco state is live in the browser. Save was only for evidence capture (snapshots). Removed the button; snapshots now fire automatically 60s after the last keystroke (debounced), plus before every public test run (already existed).

**Files changed:**
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - Removed `saving` state and `Save` lucide import
  - Added `autoSnapshotTimeoutRef` and cleanup effect
  - Monaco `onChange` now schedules a 60s debounced `saveSnapshot("autosave")`
  - Removed Save button from topbar
  - `saveStatus` initial value changed from "No manual save yet." to `""`; only shown when non-empty
  - `saveSnapshot` messages updated: "Auto-snapshot saved." / "Snapshot saved before test run."

---

### Change 2 — Seeded issue count shown after public test run

**Why:** Candidates had no signal that public tests don't cover all evaluated behaviors. After running tests, they now see "Note: this assessment has N seeded behaviors evaluated beyond these public tests."

**Implementation:** `seeded_issue_count` added to `AssessmentMetadata` schema and to `DEFAULT_PACKS` config (6 for fastapi_task_api_v1). The value is looked up from `DEFAULT_PACKS` at response time — no DB migration needed.

**Files changed:**
- `apps/api/signalloop_api/schemas.py` — added `seeded_issue_count: int = 0` to `AssessmentMetadata`
- `apps/api/signalloop_api/attempts.py` — added `"seeded_issue_count": 6` to `DEFAULT_PACKS`; updated both `AssessmentMetadata(...)` calls to include it
- `apps/web/src/app/invite/[inviteToken]/page.tsx` — added `seeded_issue_count` to frontend type; note rendered below `<pre class="output">` when `testResult` is present

---

### Change 3 — Removed FINAL_EXPLANATION.md; explanation fields are now optional

**Why:** Candidates had to fill a structured file in the editor AND two UI textareas, which was redundant. Removed the file; the UI textareas remain as the single capture point. Textareas are now encouraged but no longer block submission (5 points at stake, not a hard gate).

**Files changed:**
- `apps/api/signalloop_api/assessment_files.py` — added `"FINAL_EXPLANATION.md"` to `IGNORED_FILENAMES` so it is no longer served to candidates
- `apps/api/signalloop_api/schemas.py` — `FinalSubmissionRequest.final_explanation` and `.decision_log` changed from `Field(min_length=1)` to `""` (optional)
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - `canSubmit` simplified to `!submitted` (no textarea content gate)
  - Removed `submitRequirements` list
  - Submission help text updated: "Explanation and decision log are optional but count for 5 points."
  - Sidebar "What to do" step 5 updated to reflect optional nature

---

## 2026-06-17 — UI Polish Round 1

### Fix 1 — Broken text layout in Final Submission panel

**Symptom:** Text content under the "Final Submission" panel was visually overlapping/overflowing. The submission help paragraph and save status text were collapsed and overlapping each other.

**Root cause:** `.test-panel` and `.submission-panel` shared a CSS rule with `grid-template-rows: auto minmax(0, auto)`. The `minmax(0, auto)` second row collapses the help text `<p>` (second DOM child of `.submission-panel`) to zero height under the 240px parent height constraint, causing visual overflow and overlap.

**Fix:** Added a `.submission-panel`-only override after the shared rule:
```css
.submission-panel {
  grid-template-rows: unset;
}
```
This lets all rows in `.submission-panel` size naturally to content while preserving the `minmax(0, auto)` behavior in `.test-panel` (which needs it to constrain the `pre.output` element).

**Files changed:**
- `apps/web/src/app/globals.css` — added `.submission-panel { grid-template-rows: unset; }` after `.test-panel { border-right: ... }` rule

---

### Fix 2 — Copy button after invite creation (employer portal)

**Symptom:** After creating an invite, only a decorative `ClipboardCopy` icon appeared next to the URL — clicking it did nothing.

**Fix:** Replaced the decorative icon with a functional button. Added `copied` state and `copyInviteUrl()` function using `navigator.clipboard.writeText`. Button label toggles "Copy" → "Copied!" for 2 seconds on click.

**Files changed:**
- `apps/web/src/app/employer/page.tsx`
  - Added `const [copied, setCopied] = useState(false)` in `EmployerDashboard`
  - Added `copyInviteUrl()` function
  - Replaced `<ClipboardCopy>` icon-only markup with a `<button className="command-button secondary">` wrapping the icon and label

---

### Fix 3 — AI Collaborator chat scroll broken (outer panel scrolls instead of message list)

**Symptom:** Scrolling in the chat messages area (top portion of the AI Collaborator panel) did nothing. Scroll only worked after clicking inside the textarea at the bottom.

**Root cause:** `.assistant-panel` had `overflow: auto`. `.assistant-chat` inside it had `height: calc(100vh - 113px)` — a fixed height much larger than the actual available height (which is `100vh` minus topbar, resize handle, and bottom panel). So `.assistant-panel` itself overflowed its grid cell. When hovering over the chat messages area, mouse-wheel events were captured by `.assistant-panel` (the outer scroll container), not `.chat-messages` (the inner one). The click-textarea workaround happened to position the scroll viewport such that the inner `.chat-messages` was the topmost scrollable element.

**Fix:**
1. Made `.assistant-panel` a flex column with `overflow: hidden` — it no longer scrolls itself; it now contains its children via flex layout.
2. Replaced `.assistant-chat { height: calc(100vh - 113px) }` with `flex: 1` — the chat container fills the remaining panel space after the header without overflowing.
3. Changed `.chat-messages` grid row from `minmax(220px, 1fr)` to `minmax(0, 1fr)` — avoids a forced 220px minimum that could cause overflow in short viewports now that the parent is properly sized.
4. Also added `chatMessagesRef` with a `useEffect` to auto-scroll to the latest message on each update, so new messages are always visible.

**Files changed:**
- `apps/web/src/app/globals.css`
  - `.assistant-panel`: added `display: flex; flex-direction: column; overflow: hidden`
  - `.assistant-chat`: replaced `height: calc(100vh - 113px)` with `flex: 1`; changed first grid row to `minmax(0, 1fr)`
- `apps/web/src/app/invite/[inviteToken]/page.tsx`
  - Added `chatMessagesRef = useRef<HTMLDivElement | null>(null)`
  - Added `useEffect(() => { el.scrollTop = el.scrollHeight }, [chatMessages])`
  - Added `ref={chatMessagesRef}` on `.chat-messages` div

---

### Other findings (not fixed, recorded for next agent)

- `ASSESSMENT_RUNTIME_IMAGE=python:3.11-slim` in `.env` is a dead variable — no code
  reads it. The worker defaults to `signalloop-python-assessment:3.11` in
  `apps/worker/signalloop_worker/schemas.py`. Both images exist locally. Safe to ignore
  or remove.

- `OPENAI_MODEL=gpt-5` is set in both `.env` and `.env.example`. This uses OpenAI's
  Responses API (`/v1/responses`). Validity depends on OpenAI's current model catalogue.
  If AI chat returns errors in the live smoke test, verify the model name is current.

- Backend-to-worker public test orchestration is still not implemented (known, per
  `CURRENT_STATE.md`). Public tests are called directly from the browser to the worker.

---

## 2026-06-19 — Phase 2 Employer Assessment Configuration

### Change — Invite-level assessment and timing configuration

**Why:** Phase 2 needs employers to choose the standard assessment and timing
expectations per invite before timer enforcement and advanced packs are implemented.

**Implementation:**
- Added `assessment_level`, `timing_mode`, `duration_minutes`, and `expires_at` to
  `assessment_attempts` through Alembic migration `0003_add_attempt_configuration`.
- Extended the attempt creation API with fixed validation for standard/advanced,
  timed/untimed, and 60/90/120/150 minute durations.
- Kept advanced assessment intentionally unavailable until the advanced pack task;
  the employer UI shows it as planned/disabled and the API rejects advanced creation.
- Updated the employer invite form and attempt list to display timing configuration.
- Hardened API validation error serialization so Pydantic validator errors return a
  clean 422 response.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 51 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_config_migration_check_2.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-19 — Phase 2 Advanced FastAPI Pack Implementation

### Change — Advanced pack implemented and enabled

**Why:** Employer invite configuration already exposes assessment difficulty. Leaving
Advanced disabled made the Standard/Advanced choice feel unfinished.

**Implementation:**
- Added `assessment_packs/fastapi_task_api_advanced_v1/`.
- Added candidate starter app, README, public tests, requirements, pyproject, and lock
  file.
- Added evaluator hidden tests, reference solution, reference notes, scoring rubric,
  and manual evaluation form.
- Added `fastapi_task_api_advanced_v1` to API `DEFAULT_PACKS`.
- Mapped `assessment_level=advanced` to the advanced pack and default 120-minute
  duration.
- Enabled the Advanced option in the employer invite form.
- Added API coverage for creating Advanced attempts.
- Made candidate file loading ignore `.uv-cache` generated during local dependency
  attempts.

**Validation:**
- Advanced starter public tests using existing assessment virtualenv:
  `1 passed, 5 failed` on unmodified starter code.
- Advanced reference solution against public tests:
  `6 passed`.
- Advanced reference solution against hidden tests:
  `7 passed`.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 55 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

**Follow-up:**
- External LLM-assisted report review is still not invoked; reports continue to show
  `llm_assisted_review.status=not_run`.

---

## 2026-06-19 — Phase 2 Reporting And FAVO Updates

### Change — Phase 2 report evidence sections

**Why:** Employer reports should evaluate the human-AI engineering process, not only
final code or generic confidence.

**Implementation:**
- Removed the report-level `scores.confidence` field from generated reports.
- Added structured `submission_review` evidence parsed from final submission review
  answers.
- Added deterministic `favo` interpretation for Frame, Ask, Verify, and Own.
- Added report-only `ai_integrity_risk` with low/medium/high/critical labels and
  `score_impact=none_phase_2`.
- Added `feature_design_implementation` as a top-level report section.
- Added `llm_assisted_review` status metadata. External LLM review is not invoked in
  the local deterministic path.
- Updated employer report UI/types to render the backend-provided sections.
- Updated architecture docs to reflect structured Submission Review, FAVO, AI
  integrity risk, and Phase 2 rubric categories.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_evidence_report.py` -> 8 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-19 — Phase 2 UI Enhancements

### Change — Structured submission review, confirmation, and report visuals

**Why:** Phase 2 needs clearer candidate submission expectations and more readable
employer reports without expanding into a dashboard product.

**Implementation:**
- Replaced separate final explanation/decision-log inputs with structured Submission
  Review prompts:
  - What did you change?
  - What tradeoffs or product decisions did you make?
  - How did you verify your changes?
  - What would you improve next, given more time?
  - Optional evaluator notes.
- Submit now opens a confirmation modal and shows public-test, candidate-test, and
  review completion signals before final submission.
- Manual submission no longer requires review text at the API layer; review answers
  remain supporting evidence.
- Employer report page now shows timing metadata, native score bars, public/hidden
  test bars, feature/design summary, FAVO-style interpretation, and AI integrity risk.
- Added modal, chart, and FAVO styling in the shared web CSS.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-19 — Phase 2 Advanced Pack Specification

### Change — Advanced FastAPI pack design documented

**Why:** Phase 2 needs a deeper FastAPI assessment direction, but the advanced pack
implementation should remain separate from standard v2 and timer work.

**Implementation:**
- Added `docs/assessment/fastapi-task-api-advanced-v1.md` with domain, endpoints,
  seeded issue areas, feature/design requirements, public/hidden test direction,
  AI collaboration signal, rubric mapping, and non-goals.
- Marked `05-advanced-assessment-pack.md` as specification completed only.
- Linked the spec from the Phase 2 execution plan and docs index.

**Validation:**
- Confirmed this task is documentation-only.
- Did not create `assessment_packs/fastapi_task_api_advanced_v1/`.

---

## 2026-06-19 — Phase 2 Time-Boxed Assessment Flow

### Change — Timed attempts and expiry enforcement

**Why:** Phase 2 needs employer-selectable timed assessments without trusting only the
browser countdown.

**Implementation:**
- Added `submission_mode` to `assessment_attempts` through Alembic migration
  `0004_add_submission_mode`.
- Added explicit `POST /candidate/invites/{token}/accept`; loading an invite is now
  passive and accepting the rules starts `started_at` plus `expires_at` for timed
  attempts.
- Candidate invite responses now include timing metadata.
- Candidate workspace shows a countdown for timed attempts, warnings at 10/5/1
  minute, and auto-submits current browser files at expiry.
- Backend enforces expiry on snapshots, public test runs, AI messages, and final
  submission.
- Closed/stale-tab expiry records an `auto_expired` final submission from the latest
  persisted snapshot when the next backend action arrives.
- Evidence reports now include timing mode, duration, time used, start, expiry,
  submission timestamp, and submission mode.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_attempt_lifecycle.py tests/test_final_submission.py tests/test_evidence_report.py tests/test_ai_endpoint.py` -> 30 passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest` -> 54 passed.
- `cd apps/api && DATABASE_URL=sqlite:////tmp/signalloop_phase2_timer_migration_check.db UV_CACHE_DIR=.uv-cache uv run alembic upgrade head` -> passed.
- `cd apps/web && npm run typecheck` -> passed.
- `cd apps/web && npm run lint` -> passed.
- `cd apps/web && npm run build` -> passed.
- `cd apps/web && npm run test:e2e` was attempted but blocked by sandbox `EPERM`
  while binding `127.0.0.1:3000`; run it locally before deployment.

---

## 2026-06-23 — Phase 4: Super Admin Portal

### Super admin portal — operator visibility across all employers

**Why:** The operator had no single place to see who the employers are, how
much they use the platform, and whether anything is stuck. The super admin
portal gives view-only visibility without needing to log in as each employer.

**Changed:**
- New nullable `role` column on `employers` table (migration
  `0008_add_employer_role`). `NULL` = regular employer, `'super_admin'` = admin.
  Safe, additive migration — no backfill, no table rewrite.
- New `SUPER_ADMIN_EMAILS` env var (comma-separated, case-insensitive) in
  `config.py`. Role assignment happens in `get_or_create_employer` at every
  login: email matches env var → `role='super_admin'`, otherwise `NULL`.
  Removing an email from the env var downgrades the role on next login.
- New `get_current_super_admin` dependency in `auth.py`: returns 401 if
  unauthenticated, 403 if authenticated but not admin. Existing
  `get_current_employer` is unchanged — no behavior change for regular
  employers.
- New `/employer/me` endpoint returns `{ id, email, role }` so the frontend
  can route by role.
- New `apps/api/signalloop_api/admin.py` router with 4 GET endpoints, all
  protected by `get_current_super_admin`:
  - `GET /admin/me` — admin identity
  - `GET /admin/employers` — roster with invite/submitted/report counts and
    avg score (single query per aggregate, no N+1)
  - `GET /admin/employers/{id}` — Tier 2 per-employer summary: status
    breakdown, score distribution, AI usage, pack breakdown, stuck signals,
    full attempt list
  - `GET /admin/attempts/{id}/report` — any employer's evidence report,
    skips the ownership check that the employer endpoint enforces
- Frontend admin portal at `/admin`:
  - `apps/web/src/app/admin/layout.tsx` — Clerk auth wrapper + role check
    (redirects non-admins to `/employer`)
  - `apps/web/src/app/admin/page.tsx` — roster table (auto-refresh 60s)
  - `apps/web/src/app/admin/employers/[id]/page.tsx` — per-employer
    drill-down with metric cards, status/pack breakdowns, attempt table
  - `apps/web/src/app/admin/reports/[attemptId]/page.tsx` — full evidence
    report view (reuses report rendering; no Regenerate button — admin is
    view-only)
  - `apps/web/src/app/admin/api.ts` + `types.ts` — admin API client + types
- `apps/web/src/app/employer/page.tsx` now checks role on login and
  redirects `super_admin` users to `/admin`.
- `SUPER_ADMIN_EMAILS` added to `.env.example` and
  `.env.render-supabase.example` with a placeholder.

**Files created:**
- `apps/api/alembic/versions/0008_add_employer_role.py`
- `apps/api/signalloop_api/admin.py`
- `apps/api/tests/test_admin_endpoints.py`
- `apps/web/src/app/admin/layout.tsx`
- `apps/web/src/app/admin/page.tsx`
- `apps/web/src/app/admin/api.ts`
- `apps/web/src/app/admin/types.ts`
- `apps/web/src/app/admin/employers/[id]/page.tsx`
- `apps/web/src/app/admin/reports/[attemptId]/page.tsx`
- `docs/enhancements/phase-4-super-admin-portal/README.md`
- `docs/enhancements/phase-4-super-admin-portal/01-backend-auth-and-schema.md`
- `docs/enhancements/phase-4-super-admin-portal/02-backend-admin-api.md`
- `docs/enhancements/phase-4-super-admin-portal/03-frontend-admin-portal.md`

**Files modified:**
- `apps/api/signalloop_api/models.py` — added `role` column to `Employer`
- `apps/api/signalloop_api/auth.py` — `_assign_role`, `get_current_super_admin`
- `apps/api/signalloop_api/config.py` — `super_admin_emails` setting
- `apps/api/signalloop_api/schemas.py` — `EmployerInfoResponse`
- `apps/api/signalloop_api/attempts.py` — `GET /employer/me`
- `apps/api/signalloop_api/main.py` — registered admin router
- `apps/web/src/app/employer/page.tsx` — role check + redirect to `/admin`
- `.env.example`, `.env.render-supabase.example` — `SUPER_ADMIN_EMAILS`
- `CURRENT_STATE.md` — Phase 4 status

**Migration collision note:** Migration `0008` is on the `employers` table.
Phase 3 migrations `0006`/`0007` are on `proctoring_events` /
`assessment_attempts`. No table-level conflict. If another agent creates an
`0008` concurrently, renumber to `0009` (trivial fix).

**Validation:**
- `cd apps/api && .venv/bin/python -m alembic upgrade head` → 0008 applied.
- `cd apps/api && .venv/bin/python -m pytest tests/test_admin_endpoints.py -x -q` → 12 passed.
- `cd apps/api && .venv/bin/python -m pytest tests/ -q --tb=no` → 336 passed, 11 skipped, 1 pre-existing unrelated failure (AI policy paste heuristic in `test_two_step_pipeline.py`).
- `cd apps/web && npm run typecheck` → passed.
- `cd apps/web && npm run build` → passed. Admin routes registered: `/admin` (static), `/admin/employers/[id]` (dynamic), `/admin/reports/[attemptId]` (dynamic).
- `cd apps/web && npm run lint` → 3 errors, 4 warnings (same count as before changes; all pre-existing `react-hooks/set-state-in-effect` pattern used across the existing employer/invite pages).

**Follow-up items:**
- Set `SUPER_ADMIN_EMAILS` in the Render environment
  (and in local `.env`) before testing admin login.
- Deploy to Render to validate hosted admin flow end-to-end.
- Consider extracting the shared evidence-report rendering into a single
  component to avoid duplication between the employer and admin report pages
  (post-Phase 4 cleanup).

## 2026-06-29 — Phase 5 Adaptive Blueprint Duplicate Skill Keys

**Symptom:** Generating an adaptive blueprint could show React's duplicate
key warning for skills such as `infra.kubernetes`.

**Root cause:** The adaptive UI merged unsupported required skills and
unsupported claimed skills. A skill can legitimately appear in both buckets,
but the renderer used the skill ID directly as the React child key.

**Files changed:**
- `apps/web/src/app/employer/page.tsx` — deduplicates rendered skill pills in
  the adaptive builder preview.
- `apps/web/src/app/_components/EvidenceReportView.tsx` — deduplicates
  rendered skill pills in the evidence report adaptive context.
- `apps/web/tests/e2e/employer-portal.spec.ts` — adds duplicate-key regression
  coverage for adaptive builder and adaptive report rendering.
- `apps/api/tests/test_adaptive_assessment.py` — adds an eight-fixture Phase 5
  JD/resume sweep covering supported backend, frontend, weak-overlap backend,
  data, infra, AI/LLM, and candidate-extra-skill cases.
- `docs/development/changes.md` — recorded the bug fix for handoff.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q`
  passed, 19 tests.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run test:e2e -- --workers=1` passed, 32 tests and 2
  skipped live tests.

**Follow-up items:** None.

## 2026-06-29 — Phase 5 JD/Resume Upload Text Extraction

**Symptom:** Adaptive Builder required employers to paste JD and resume text,
which made testing with real documents awkward.

**Root cause:** Phase 5 originally scoped intake to pasted text only.

**Files changed:**
- `apps/api/signalloop_api/document_text.py` — added text extraction for
  `.txt`, `.md`, `.docx`, and best-effort text-based `.pdf`.
- `apps/api/signalloop_api/adaptive.py` — added authenticated
  `POST /employer/adaptive/extract-document-text` raw-byte upload endpoint with
  2 MB limit.
- `apps/api/signalloop_api/schemas.py` — added document extraction response
  schema.
- `apps/api/tests/test_adaptive_assessment.py` — added TXT, DOCX, and rejected
  extension extraction coverage.
- `apps/web/src/app/employer/api.ts` — added document extraction client.
- `apps/web/src/app/employer/page.tsx` — added JD and resume file inputs in
  Adaptive Builder; extracted text fills the existing textareas.
- `apps/web/tests/e2e/employer-portal.spec.ts` — added JD upload coverage in
  the adaptive builder E2E.
- `CURRENT_STATE.md`, `docs/enhancements/phase-5-role-adaptive-assessment/phase-5-execution-plan.md`,
  and `docs/enhancements/phase-5-role-adaptive-assessment/manual-test-fixtures.md`
  — documented upload support and PDF limitations.
- `docs/development/changes.md` — recorded the upload change.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_adaptive_assessment.py -q`
  passed, 21 tests.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q`
  passed, 27 tests.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1`
  passed, 8 tests.

**Follow-up items:** Add OCR or a stronger PDF parser if scanned/complex PDFs
become important for pilot usage.

## 2026-06-29 — Phase 5 Saved Blueprint List and Adaptive Invite Result

**Symptom:** Saved blueprints listed too many rows, status dots were unexplained,
future assessment blueprints did not visually stand apart enough, and after
approving an adaptive blueprint the invite link was not shown in the adaptive
flow.

**Root cause:** The adaptive builder reused parent invite state intended for the
direct coding form, which is hidden in adaptive mode. Saved blueprint rows also
used raw status color dots without a legend or text status.

**Files changed:**
- `apps/web/src/app/employer/page.tsx` — limits saved blueprints to the latest
  five, adds status labels and color meaning, uses amber for future modules, and
  shows an adaptive invite result panel with copy/open actions after approval.
- `apps/web/tests/e2e/employer-portal.spec.ts` — extends adaptive builder E2E
  coverage to approve a blueprint and assert the adaptive invite URL is visible.
- `docs/development/changes.md` — recorded the UX fix.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q`
  passed, 24 tests.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1`
  passed, 8 tests.

**Follow-up items:** None.

## 2026-06-29 — Phase 5 Future vs Out-of-Scope Blueprint Classification

**Symptom:** Frontend/data/infra JDs could be routed to a backend FastAPI
adaptive assessment, while non-roadmap roles needed a clearer distinction from
planned future assessment families.

**Root cause:** Blueprint selection only distinguished current FastAPI packs from
unsupported skills. It did not model planned-but-not-invite-ready assessment
families separately from out-of-scope roles.

**Files changed:**
- `apps/api/signalloop_api/adaptive_blueprint.py` — added future blueprint
  generation for planned frontend, data, infra/platform, and AI assessment
  families; added out-of-scope handling for unmapped/non-roadmap roles.
- `apps/api/signalloop_api/adaptive.py` — returns 422 only for out-of-scope
  JDs; future assessment blueprints are saved normally.
- `apps/api/tests/test_adaptive_assessment.py` — expanded manual fixture sweep
  to cover future frontend/data/infra, invite-ready backend/API, non-technical
  out-of-scope, and mobile-not-on-roadmap cases.
- `apps/web/src/app/employer/page.tsx` — future blueprints are shown as planned
  assessments and cannot send invites.
- `apps/web/src/app/employer/types.ts` — allows future assessment levels in
  blueprint responses.
- `apps/web/tests/e2e/employer-portal.spec.ts` — added UI coverage for future
  blueprints and disabled invite actions.
- `docs/enhancements/phase-5-role-adaptive-assessment/manual-test-fixtures.md`
  — added out-of-scope fixtures and updated future-assessment expectations.
- `docs/development/changes.md` — recorded the classification change.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q`
  passed, 23 tests.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1`
  passed, 8 tests.

**Follow-up items:** If mobile/native or security assessments enter the roadmap,
add explicit taxonomy families and future blueprint mappings for them.

## 2026-06-29 — Phase 5 Frontend JD Overrides Default Backend Controls

**Symptom:** A frontend-dominant JD/resume could still select the backend FastAPI
assessment when the employer left the adaptive builder's role title/family
controls at their default backend values.

**Root cause:** Blueprint selection trusted the selected/default role family too
early. A single backend-ish term such as API contracts could satisfy FastAPI fit
before considering that extracted frontend skills dominated the JD.

**Files changed:**
- `apps/api/signalloop_api/adaptive_blueprint.py` — family-dominance check now
  routes frontend/data/infra-dominant JDs to future blueprints even when stale
  role controls are backend.
- `apps/api/tests/test_adaptive_assessment.py` — added regression fixture for a
  frontend JD/resume with default backend role controls.
- `docs/enhancements/phase-5-role-adaptive-assessment/manual-test-fixtures.md`
  — added the same manual fixture as Fixture 4B.
- `docs/development/changes.md` — recorded the regression fix.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_adaptive_assessment.py -q`
  passed, 18 tests.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_assessment_taxonomy.py tests/test_adaptive_assessment.py -q`
  passed, 24 tests.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1`
  passed, 8 tests.

**Follow-up items:** None.

## 2026-06-29 — Phase 5 Adaptive Builder UX Clarification and Saved Blueprints

**Symptom:** The adaptive builder did not clearly explain team context, made the
adaptive path feel mandatory, did not let employers inspect the selected
assessment from the generated blueprint, and did not show previously generated
blueprints when returning to the Assessments screen.

**Root cause:** Blueprint persistence existed in the backend, but the employer
UI only held the generated blueprint in local component state. The generated
blueprint card also summarized coverage without linking back to the existing
Standard/Advanced assessment detail modal.

**Files changed:**
- `apps/api/signalloop_api/adaptive.py` — added employer-scoped
  `GET /employer/adaptive/blueprints` for recent saved blueprints.
- `apps/web/src/app/employer/api.ts` — added adaptive blueprint list client.
- `apps/web/src/app/employer/page.tsx` — clarified adaptive builder copy,
  renamed team context to optional product/team context, added saved-blueprint
  selection, added assessment detail access from blueprint cards, and disabled
  invite creation for already-used blueprints.
- `apps/api/tests/test_adaptive_assessment.py` — added saved-blueprint list
  employer-isolation coverage.
- `apps/web/tests/e2e/employer-portal.spec.ts` — adjusted adaptive blueprint
  mocks for the new list request.
- `docs/enhancements/phase-5-role-adaptive-assessment/manual-test-fixtures.md`
  — documented team context meaning for manual QA.
- `docs/development/changes.md` — recorded the UX/API change for handoff.

**Validation:**
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_adaptive_assessment.py -q`
  passed, 14 tests.
- `cd apps/web && npm run typecheck` passed.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1`
  passed, 7 tests.

**Follow-up items:** Consider adding a dedicated blueprint detail page if saved
blueprints need deeper review, editing, or deletion.

## 2026-06-29 — Phase 5 Mutually Exclusive Assessment Creation Paths

**Symptom:** The Assessments screen showed Adaptive Builder and the direct
Coding Challenge form at the same time, making it unclear whether an invite was
coming from a generated blueprint or from manual employer selection.

**Root cause:** Phase 5 added the adaptive builder beside the existing quick
invite form without a mode selector. Both paths were active in one screen.

**Files changed:**
- `apps/web/src/app/employer/page.tsx` — added a Creation path selector with
  Direct coding challenge and Adaptive builder modes. The direct coding form is
  hidden in adaptive mode, and the adaptive builder is hidden in direct mode.
- `apps/web/tests/e2e/employer-portal.spec.ts` — updated adaptive E2E coverage
  to switch modes and verify the direct Send invite button is hidden in
  adaptive mode.
- `docs/enhancements/phase-5-role-adaptive-assessment/manual-test-fixtures.md`
  — documented Direct vs Adaptive as alternate creation paths.
- `docs/development/changes.md` — recorded the UX change.

**Validation:**
- `cd apps/web && npm run typecheck` passed.
- `cd apps/api && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_adaptive_assessment.py -q`
  passed, 14 tests.
- `cd apps/web && npm run test:e2e -- tests/e2e/employer-portal.spec.ts --workers=1`
  passed, 7 tests.

**Follow-up items:** None.
