# Contributing

SignalLoop is in project closeout and open-source release preparation. The
current release boundary is intentionally narrow:

- improve documentation,
- fix bugs in the existing MVP and Phase 2-6A scope,
- improve local setup and validation,
- improve tests for existing behavior,
- improve assessment authoring guidance.

Do not add large future-scope features without an issue or design note first.
Out-of-scope areas include ATS integration, enterprise SSO, billing,
marketplace features, Kubernetes, video proctoring as a decision engine, and
multi-language assessment execution.

## Development Workflow

1. Read `AGENTS.md`, `CURRENT_STATE.md`, and the relevant docs before changing
   behavior.
2. Keep changes scoped to one issue or enhancement.
3. Add or update tests when behavior changes.
4. Update `docs/development/changes.md` for non-trivial fixes or validation
   findings.
5. Do not commit `.env`, candidate PII, invite tokens, API keys, or generated
   local artifacts.

## Assessment Content

Assessment packs in this repository are public demo/reference content. New
production-quality assessments should be authored in separate private
inventory or contributed only after a clear license, provenance, and review
decision.

Question-bank imports must use allowlisted sources and must retain source,
license, attribution, and review metadata.
