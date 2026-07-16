# Open-Source Release Plan

Status: release candidate; three external gates remain before visibility change.

## Release Boundary

SignalLoop can be published as an Apache-2.0 reference implementation for:

- constrained AI-assisted coding assessments,
- evidence capture,
- deterministic evidence report generation,
- employer invite/report workflows,
- guided role matching to registered FastAPI assessment packs,
- Phase 6A question-bank governance infrastructure.

The open-source release should not claim that SignalLoop already supports
question-level adaptive assessment composition. That remains future work.

## Assessment Content Policy

Include the existing FastAPI assessment packs as public demo/reference content.
This makes the project runnable and understandable, but it also means the
included hidden tests, rubrics, and evaluator notes are not secure production
inventory.

For real hiring use, adopters should create private assessment packs, calibrate
them with reviewers, and keep hidden tests outside public repositories.

Question-bank source imports must retain their original license and attribution
metadata. SignalLoop-authored code and content are Apache-2.0 unless a file or
directory says otherwise.

## Joint Publication

GitHub setup:

1. GitHub organization selected: `signalloop-ai`.
2. Repository transferred to `https://github.com/signalloop-ai/signalloop`.
3. Keep the repository private until the checklist below is complete.
4. Add both original collaborators as owners or maintainers.
5. Keep `AUTHORS.md` and `CITATION.cff` in the repository.
6. Publish blog posts with both collaborators credited.

This avoids making the project look like single-person work just because the
repository started in a personal account.

## Before Making The Repo Public

- [x] Confirm `AUTHORS.md` and `CITATION.cff` match the public names already used in the README
  and project metadata.
- [x] Confirm `CITATION.cff` uses the final organization repository URL:
  `https://github.com/signalloop-ai/signalloop`.
- [x] Confirm Ritesh Dhoot (`rdhoot`) has accepted the org/repo invite and has the intended access
  level. Verified 2026-07-16: organization member and repository admin; no pending invitation.
- [ ] Revoke or rotate the Render CLI token used during the Render runtime repair. This requires
  the Render account/dashboard login and must be completed by an account owner.
- [x] Run a secret scan across git history and the current tree. Gitleaks 8.30.1 scanned 90 commits
  with no leaks; the current-tree scan is also clean.
- [x] Remove generated artifacts, personal email addresses, and live invite values from the
  current tree. The remaining localhost invite in the demo runbook is now an explicit placeholder.
- [ ] Rewrite the published git history to remove the previously sanitized personal Gmail
  addresses, the old localhost invite token whose status is unknown, and private-pilot AWS
  account/network identifiers; alternatively, explicitly accept that disclosure before changing
  visibility. A rewrite requires a coordinated force-push and replacement release tag.
- [x] Confirm `.env` is ignored and not tracked.
- [x] Confirm release-facing docs contain no private Render, Clerk, Supabase, email, or
  environment-specific AWS account/network identifiers.
- [x] Run the local validation commands listed in `README.md`.
- [x] Run hosted candidate smoke after the GitHub organization transfer and Render runtime
  repair. Attempt 34 passed on 2026-07-13; API/web reachability was reconfirmed 2026-07-16.
- [x] Review employer report generation and guided role matching through the complete local
  Playwright release suite.
- [ ] Perform one final Clerk-authenticated hosted employer report and guided-role review from the
  Codex desktop app, which has Browser control. The VS Code extension does not.
- [x] Preserve the existing signed `v0.1.0` pilot tag. Use `v0.1.1` for the public release
  candidate rather than moving a published tag if history is preserved. If history is rewritten,
  replace the old private pilot tag only as part of the coordinated force-push.
- [ ] After the repository becomes public, enable GitHub private vulnerability reporting and
  secret scanning, then publish the `v0.1.1` GitHub release.

## 2026-07-16 Release-Candidate Validation

- API: 297 passed, 51 skipped.
- Worker: 23 passed.
- Alembic: complete SQLite migration chain through `0012_concept_question_types`.
- Web typecheck: passed.
- Web lint: passed with four known warnings and no errors.
- Web production build: passed.
- Playwright: 35 passed, 2 credential-dependent live tests skipped.
- Hosted reachability: API health returned `{"status":"ok"}`; employer page returned HTTP 200.
- GitHub CI workflow added for API/worker tests, migrations, and web typecheck/lint/build.

## Cleanup Decisions

- Keep public SignalLoop role/JD sample fixtures, including generated DOCX and text-based PDF
  files under `docs/enhancements/phase-5-role-adaptive-assessment/sample-upload-files/`.
- Exclude unrelated local tooling and generated artifacts such as `opencode.json` and `outputs/`.
- Exclude unrelated marketing drafts that are not about SignalLoop.

## Hosted Smoke Checklist

Use the hosted employer smoke account.

1. Open `https://signalloop-web.onrender.com/employer`.
2. Sign in with Clerk.
3. Create a real manual-selection invite using a throwaway candidate email.
4. Open the candidate invite link.
5. Run public tests.
6. Send one allowed AI coaching prompt.
7. Submit the candidate attempt with a short final explanation.
8. Generate and view the evidence report in the employer portal.
9. Separately check guided role matching with the included backend, frontend, and data sample JDs.

## Blog And Demo Track

Suggested first public blog:

`Building SignalLoop: what should a coding assessment measure when candidates can use AI?`

Core argument:

- AI is now part of realistic engineering work.
- The assessment should measure framing, verification, judgment, and ownership,
  not just whether someone can type code unaided.
- The constrained collaborator is deliberately not a solution generator.
- Evidence reports should show how the candidate worked, not only whether tests
  passed.
- Adaptive composition is the future problem; the current release intentionally
  ships role-guided matching plus question-bank governance.

Demo scope:

- view the short end-to-end demo at `docs/assets/demo/signalloop-demo.mp4`,
- show super admin cross-employer visibility and question-bank governance,
- create employer invite,
- open candidate workspace,
- run public tests,
- ask one allowed AI coaching question,
- submit final explanation,
- view the evidence report,
- briefly show guided role matching and the unsupported-role result.
