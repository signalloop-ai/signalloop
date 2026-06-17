# AWS ECS/Fargate Execution Deployment

## Scope

This document covers the production execution direction from ADR 0006.

Local development keeps using the Docker-based worker. Production execution should use
per-run AWS ECS/Fargate tasks so candidate code does not require Docker-in-Docker inside
Render or another long-running web service.

## Current Repository State

Implemented scaffolding:

- `apps/runner/Dockerfile`
- `apps/runner/signalloop_runner/main.py`
- `infra/aws/ecs/task-definition.runner.template.json`
- `infra/aws/ecs/run-task-overrides.example.json`
- `infra/aws/ecs/README.md`

Not implemented yet:

- API provider that uploads payloads to S3, calls ECS `RunTask`, waits for completion,
  reads output JSON, and persists the existing `TestRun` result shape.

Until that API provider exists, hosted Render/API can only run candidate tests through a
trusted HTTP worker configured by `EXECUTION_WORKER_URL`.

## AWS Values Needed

Ask AWS for or create:

```env
AWS_REGION=
AWS_ACCOUNT_ID=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_ECR_RUNNER_REPOSITORY=signalloop-assessment-runner
AWS_ECS_CLUSTER=
AWS_ECS_RUNNER_TASK_DEFINITION=signalloop-assessment-runner
AWS_ECS_RUNNER_CONTAINER=runner
AWS_ECS_SUBNET_IDS=subnet-abc,subnet-def
AWS_ECS_SECURITY_GROUP_IDS=sg-abc
AWS_ECS_ASSIGN_PUBLIC_IP=DISABLED
SIGNALLOOP_RUN_BUCKET=
```

If the task runs in private subnets, add either NAT egress or VPC endpoints for ECR,
CloudWatch Logs, and S3.

Use a narrowly scoped IAM user/access key for Render only if an OIDC-based integration is
not available for your account. The policy should allow only the required ECS `RunTask`,
task description, and S3 read/write operations for the SignalLoop runner resources.

## Build Runner Image

```sh
AWS_ACCOUNT_ID=...
AWS_REGION=...

aws ecr create-repository \
  --repository-name signalloop-assessment-runner \
  --region "$AWS_REGION"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t signalloop-assessment-runner:latest apps/runner
docker tag signalloop-assessment-runner:latest \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/signalloop-assessment-runner:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/signalloop-assessment-runner:latest"
```

## Validate Runner Locally

Create `/tmp/signalloop-runner-input.json`:

```json
{
  "files": {
    "tests/test_sample.py": "def test_sample():\n    assert True\n"
  },
  "command": ["python", "-m", "pytest", "tests"],
  "timeout_seconds": 30
}
```

Run:

```sh
docker build -t signalloop-assessment-runner:local apps/runner
docker run --rm \
  -e SIGNALLOOP_RUNNER_INPUT=/tmp/input.json \
  -e SIGNALLOOP_RUNNER_OUTPUT=/tmp/output.json \
  -v /tmp/signalloop-runner-input.json:/tmp/input.json:ro \
  -v /tmp:/tmp \
  signalloop-assessment-runner:local

cat /tmp/output.json
```

Expected result shape:

```json
{
  "status": "passed",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "duration_ms": 123
}
```

## API Integration To Add Next

Add an execution provider in `apps/api` with this behavior:

1. Create a run id.
2. Write input payload JSON to `s3://$SIGNALLOOP_RUN_BUCKET/runs/$RUN_ID/input.json`.
3. Call ECS `RunTask` with overrides for:
   - `SIGNALLOOP_RUNNER_INPUT`
   - `SIGNALLOOP_RUNNER_OUTPUT`
4. Wait for task completion with a timeout.
5. Read `runs/$RUN_ID/output.json` from S3.
6. Return the same result object currently produced by the local HTTP worker.
7. Persist the result as the existing public or hidden `TestRun`.

Keep the local HTTP worker path as the default for development.
