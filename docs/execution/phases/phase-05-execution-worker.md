# Phase 05: Execution Worker

## Goal

Implement Docker-based public test execution.

## Tasks

- [x] Create worker service.
- [x] Define test-run API contract.
- [x] Receive code snapshot.
- [x] Run public tests in isolated container.
- [x] Enforce timeout and resource limits.
- [x] Return structured test result.

## Acceptance criteria

- [x] Public tests can run from submitted code snapshot.
- [x] Test result includes pass/fail, stdout/stderr, duration.
- [x] Worker does not expose hidden tests during public run.
