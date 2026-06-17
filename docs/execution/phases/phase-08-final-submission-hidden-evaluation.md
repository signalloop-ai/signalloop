# Phase 08: Final Submission and Hidden Evaluation

## Goal

Implement final submission and evaluator-only hidden test execution.

## Tasks

- [x] Capture final code snapshot.
- [x] Capture final explanation.
- [x] Capture decision log.
- [x] Lock attempt after submission.
- [x] Run hidden tests in evaluator context.
- [x] Persist hidden test results.

## Acceptance criteria

- [x] Final submission is immutable.
- [x] Candidate cannot access hidden test details.

Status: complete. The API persists a final snapshot/submission, locks further candidate snapshots, runs hidden tests through the worker with evaluator files supplied only by the backend, stores hidden test details in `test_runs`, and returns only a coarse hidden test status to the candidate UI. A live browser/API/worker/Postgres smoke test passed; it also added worker CORS coverage for the Phase 6 browser-to-worker public test path.
