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
- `apps/api/signalloop_api/execution.py` with `EXECUTION_BACKEND=ecs_fargate`

Local development still defaults to `EXECUTION_BACKEND=http_worker`. Hosted production can
switch to ECS/Fargate after the AWS resources below exist and the Render API env vars are
set.

## AWS Values Needed

Ask AWS for or create:

```env
AWS_REGION=...
AWS_ACCOUNT_ID=...
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_ECR_RUNNER_REPOSITORY=signalloop-assessment-runner
AWS_ECS_CLUSTER=signalloop
AWS_ECS_RUNNER_TASK_DEFINITION=signalloop-assessment-runner
AWS_ECS_RUNNER_CONTAINER=runner
AWS_ECS_SUBNET_IDS=subnet-...,subnet-...
AWS_ECS_SECURITY_GROUP_IDS=sg-...
AWS_ECS_ASSIGN_PUBLIC_IP=ENABLED
AWS_ECS_WAITER_DELAY_SECONDS=6
AWS_ECS_WAITER_MAX_ATTEMPTS=20
SIGNALLOOP_RUN_BUCKET=your-signalloop-runner-bucket
```

Use subnets that can reach ECR, CloudWatch Logs, and S3. The runner task security group should
have no inbound rules and only the outbound access required by those services.

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

docker buildx build --platform linux/amd64 \
  -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/signalloop-assessment-runner:latest" \
  --push \
  apps/runner
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

## Enable In Render API

After AWS resources are ready, set the Render API service:

```env
EXECUTION_BACKEND=ecs_fargate
AWS_REGION=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_ECS_CLUSTER=signalloop
AWS_ECS_RUNNER_TASK_DEFINITION=signalloop-assessment-runner
AWS_ECS_RUNNER_CONTAINER=runner
AWS_ECS_SUBNET_IDS=subnet-...,subnet-...
AWS_ECS_SECURITY_GROUP_IDS=sg-...
AWS_ECS_ASSIGN_PUBLIC_IP=ENABLED
SIGNALLOOP_RUN_BUCKET=your-signalloop-runner-bucket
```

The API writes payload JSON to S3, calls ECS `RunTask`, waits for task completion, reads
the runner output JSON, and persists the result as the existing public or hidden `TestRun`.

Keep `EXECUTION_BACKEND=http_worker` for local development.
