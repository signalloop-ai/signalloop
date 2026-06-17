# AWS ECS/Fargate Execution Scaffold

This directory contains templates for the production execution path described in ADR 0006.

## What This Adds

- A Fargate task definition template for a per-run assessment runner.
- Example container overrides for passing one run's input and output S3 URIs.
- A runner image under `apps/runner` that runs tests directly inside the Fargate task without Docker-in-Docker.

## Required AWS Resources

- ECR repository: `signalloop-assessment-runner`
- S3 bucket for run payloads/results
- ECS cluster
- Fargate task definition based on `task-definition.runner.template.json`
- CloudWatch log group: `/ecs/signalloop-assessment-runner`
- ECS task execution role for pulling ECR images and writing logs
- ECS task role with narrowly scoped S3 read/write access to the run bucket prefix

## Runner Payload Shape

Input JSON:

```json
{
  "files": {
    "task_api/main.py": "...",
    "tests/test_public_api.py": "..."
  },
  "hidden_tests": {
    "test_hidden_api.py": "..."
  },
  "command": ["python", "-m", "pytest", "tests/test_hidden_api.py"],
  "timeout_seconds": 60
}
```

For public runs, omit `hidden_tests` and use `["python", "-m", "pytest", "tests"]`.

Output JSON:

```json
{
  "status": "passed",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "duration_ms": 1234
}
```

## Build And Push Runner Image

```sh
AWS_ACCOUNT_ID=...
AWS_REGION=...

aws ecr create-repository --repository-name signalloop-assessment-runner --region "$AWS_REGION"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t signalloop-assessment-runner:latest apps/runner
docker tag signalloop-assessment-runner:latest "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/signalloop-assessment-runner:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/signalloop-assessment-runner:latest"
```

## Current Integration Status

The runner image and task templates are deployment scaffolding. The API still defaults to
the local/staging HTTP worker path through `EXECUTION_WORKER_URL`. The next implementation
step is adding an API execution provider that writes payloads to S3, calls ECS `RunTask`,
waits for completion, reads the output JSON, and persists the result as the existing
`TestRun` shape.
