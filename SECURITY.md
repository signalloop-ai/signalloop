# Security Policy

SignalLoop is a pilot-stage hiring evaluation system. Treat it as a reference
implementation, not a hardened production SaaS.

## Reporting Security Issues

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting flow:

https://github.com/signalloop-ai/signalloop/security/advisories/new

If that flow is unavailable, contact the maintainers listed in `AUTHORS.md`
through their GitHub profiles without including exploit details in a public thread.

## Important Boundaries

- Candidate invite tokens are bearer links.
- Hidden tests and scoring rubrics in this open-source repository are public
  demo material and are compromised for real hiring use.
- The constrained AI collaborator must never receive evaluator-only artifacts,
  hidden tests, reference solutions, or scoring internals.
- Local execution uses Docker. Hosted production execution should use isolated
  per-run tasks as documented under `docs/deployment/`.
- Manual evaluator review is required before any hiring decision.
