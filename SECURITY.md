# Security Policy

SignalLoop is a pilot-stage hiring evaluation system. Treat it as a reference
implementation, not a hardened production SaaS.

## Reporting Security Issues

Before the public release, report security issues privately to the maintainers
listed in `AUTHORS.md`.

After the repository is moved to a GitHub organization, enable private
vulnerability reporting and update this file with the organization security
contact.

## Important Boundaries

- Candidate invite tokens are bearer links.
- Hidden tests and scoring rubrics in this open-source repository are public
  demo material and are compromised for real hiring use.
- The constrained AI collaborator must never receive evaluator-only artifacts,
  hidden tests, reference solutions, or scoring internals.
- Local execution uses Docker. Hosted production execution should use isolated
  per-run tasks as documented under `docs/deployment/`.
- Manual evaluator review is required before any hiring decision.
