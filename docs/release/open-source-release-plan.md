# Open-Source Release Plan

Status: initial release-prep checklist.

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

Recommended GitHub setup:

1. Create a free GitHub organization for the project.
2. Add both original collaborators as owners or maintainers.
3. Transfer the repository into the organization before making it public.
4. Keep `AUTHORS.md` and `CITATION.cff` in the repository.
5. Publish blog posts with both collaborators credited.

This avoids making the project look like single-person work just because the
repository started in a personal account.

## Before Making The Repo Public

- Confirm `AUTHORS.md` and `CITATION.cff` still match both authors' preferred public names.
- Confirm `CITATION.cff` uses the final organization repository URL.
- Run a secret scan across git history and the current tree.
- Remove or rewrite any generated artifacts, local pitch-deck outputs, personal
  email addresses, invite tokens, and screenshots that should not be public.
- Confirm `.env` is ignored and not tracked.
- Confirm demo docs do not include private Render, Clerk, Supabase, or email
  details.
- Run the local validation commands listed in `README.md`.
- Tag an initial release such as `v0.1.0`.

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
