# Open-Source Release Plan

Status: active release-prep checklist.

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
3. Keep the repository private until cleanup and hosted smoke testing are complete.
4. Add both original collaborators as owners or maintainers.
5. Keep `AUTHORS.md` and `CITATION.cff` in the repository.
6. Publish blog posts with both collaborators credited.

This avoids making the project look like single-person work just because the
repository started in a personal account.

## Before Making The Repo Public

- Confirm `AUTHORS.md` and `CITATION.cff` still match both authors' preferred public names.
- Confirm `CITATION.cff` still uses the final organization repository URL:
  `https://github.com/signalloop-ai/signalloop`.
- Confirm Ritesh Dhoot (`rdhoot`) has accepted the org/repo invite and has the intended access
  level.
- Revoke or rotate the Render CLI token used during the Render runtime repair.
- Run a secret scan across git history and the current tree.
- Remove or rewrite any generated artifacts, local pitch-deck outputs, personal email addresses,
  invite tokens, and screenshots that should not be public.
- Confirm `.env` is ignored and not tracked.
- Confirm demo docs do not include private Render, Clerk, Supabase, or email
  details.
- Run the local validation commands listed in `README.md`.
- Run a hosted smoke test after the GitHub org transfer and Render source/runtime repair.
  Candidate flow smoke passed on 2026-07-13 with production attempt `34`; employer report
  generation and guided role-matching demo checks still need final release review.
- Tag an initial release such as `v0.1.0`.

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

- create employer invite,
- open candidate workspace,
- run public tests,
- ask one allowed AI coaching question,
- submit final explanation,
- view the evidence report,
- briefly show guided role matching and the unsupported-role result.
