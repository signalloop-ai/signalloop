# ADR: Use Local Docker for Development and ECS/Fargate for Production Execution

## Status

Accepted

## Context

SignalLoop assessment execution must run untrusted candidate code with strong isolation and bounded resources.

The current MVP worker runs assessment tests locally by materializing a workspace and invoking Docker. This is appropriate for development and local end-to-end testing, but common managed web-service platforms do not expose a Docker daemon or Docker socket to running containers. Relying on nested Docker in a hosted web service would make the production deployment fragile and provider-specific.

AWS ECS/Fargate charges for tasks while they run and can start isolated containers on demand. This fits SignalLoop's bursty assessment workload better than an always-on execution host.

## Decision

Use two execution modes:

1. Local development and automated local testing use the existing Docker-based worker.
2. Production execution targets AWS ECS/Fargate per-run tasks.

In the production model, SignalLoop will not use Docker-in-Docker. The API or execution orchestrator will request an ECS `RunTask` operation for each public or hidden test run. Fargate will start the assessment runner container, execute tests, and return results through a defined handoff mechanism such as an API callback, object storage, or database write.

The API-to-execution boundary should remain stable so the candidate and employer product flows do not depend on whether execution is backed by local Docker or ECS/Fargate.

## Consequences

- Render can still be used for the web and API services, but not for production assessment execution.
- Supabase can provide hosted Postgres, and Clerk can provide employer authentication.
- The existing Docker worker remains valid for local development.
- A future deployment/hardening phase must add ECS/Fargate runner packaging, ECR image publishing, task definition configuration, IAM permissions, network configuration, result handoff, timeout handling, and operational logging.
- The production execution path should avoid mounting host Docker sockets into long-running services.
- This decision does not add Kubernetes, ATS integration, enterprise SSO, video proctoring, billing, or marketplace functionality.
