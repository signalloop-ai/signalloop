from __future__ import annotations

import json
from time import monotonic
from typing import Protocol
from uuid import uuid4

import httpx

from signalloop_api.config import settings


class TestExecutionProvider(Protocol):
    def run_public(self, files: dict[str, str]) -> dict:
        ...

    def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        ...


class HTTPWorkerExecutionProvider:
    def run_public(self, files: dict[str, str]) -> dict:
        response = httpx.post(
            f"{settings.execution_worker_url.rstrip('/')}/run-public-tests",
            json={
                "files": files,
                "runtime_image": settings.assessment_runtime_image,
                "timeout_seconds": 60,
            },
            timeout=settings.worker_request_timeout_seconds,
        )
        response.raise_for_status()
        return dict(response.json())

    def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        last_error: httpx.HTTPError | None = None
        for _ in range(settings.worker_request_retries + 1):
            try:
                response = httpx.post(
                    f"{settings.execution_worker_url.rstrip('/')}/run-hidden-tests",
                    json={
                        "files": files,
                        "hidden_tests": hidden_tests,
                        "runtime_image": settings.assessment_runtime_image,
                        "timeout_seconds": 60,
                    },
                    timeout=settings.worker_request_timeout_seconds,
                )
                response.raise_for_status()
                return dict(response.json())
            except httpx.HTTPError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Worker request failed without an error")


class ECSFargateExecutionProvider:
    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for EXECUTION_BACKEND=ecs_fargate") from exc

        self.ecs = boto3.client("ecs", region_name=settings.aws_region)
        self.s3 = boto3.client("s3", region_name=settings.aws_region)

    def run_public(self, files: dict[str, str]) -> dict:
        return self._run_task(
            {
                "files": files,
                "command": ["python", "-m", "pytest", "tests"],
                "timeout_seconds": 60,
            }
        )

    def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        return self._run_task(
            {
                "files": files,
                "hidden_tests": hidden_tests,
                "command": ["python", "-m", "pytest", "tests/test_hidden_api.py"],
                "timeout_seconds": 60,
            }
        )

    def _run_task(self, payload: dict) -> dict:
        require_ecs_settings()
        run_id = uuid4().hex
        input_key = f"runs/{run_id}/input.json"
        output_key = f"runs/{run_id}/output.json"
        input_uri = f"s3://{settings.signalloop_run_bucket}/{input_key}"
        output_uri = f"s3://{settings.signalloop_run_bucket}/{output_key}"

        self.s3.put_object(
            Bucket=settings.signalloop_run_bucket,
            Key=input_key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

        started = monotonic()
        response = self.ecs.run_task(
            cluster=settings.aws_ecs_cluster,
            taskDefinition=settings.aws_ecs_runner_task_definition,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": settings.aws_ecs_subnet_ids,
                    "securityGroups": settings.aws_ecs_security_group_ids,
                    "assignPublicIp": settings.aws_ecs_assign_public_ip,
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": settings.aws_ecs_runner_container,
                        "environment": [
                            {"name": "SIGNALLOOP_RUNNER_INPUT", "value": input_uri},
                            {"name": "SIGNALLOOP_RUNNER_OUTPUT", "value": output_uri},
                        ],
                    }
                ]
            },
        )
        failures = response.get("failures") or []
        if failures:
            raise RuntimeError(f"ECS RunTask failed: {failures}")

        tasks = response.get("tasks") or []
        if not tasks:
            raise RuntimeError("ECS RunTask returned no task")

        task_arn = tasks[0]["taskArn"]
        waiter = self.ecs.get_waiter("tasks_stopped")
        waiter.wait(
            cluster=settings.aws_ecs_cluster,
            tasks=[task_arn],
            WaiterConfig={
                "Delay": settings.aws_ecs_waiter_delay_seconds,
                "MaxAttempts": settings.aws_ecs_waiter_max_attempts,
            },
        )

        described = self.ecs.describe_tasks(cluster=settings.aws_ecs_cluster, tasks=[task_arn])
        stopped_task = (described.get("tasks") or [{}])[0]
        containers = stopped_task.get("containers") or []
        exit_codes = [container.get("exitCode") for container in containers if "exitCode" in container]
        if exit_codes and any(code not in {0, None} for code in exit_codes):
            raise RuntimeError(f"ECS runner container exited with code(s): {exit_codes}")

        result_object = self.s3.get_object(Bucket=settings.signalloop_run_bucket, Key=output_key)
        result = json.loads(result_object["Body"].read().decode("utf-8"))
        result.setdefault("duration_ms", int((monotonic() - started) * 1000))
        return dict(result)


def require_ecs_settings() -> None:
    missing = [
        name
        for name, value in {
            "AWS_REGION": settings.aws_region,
            "AWS_ECS_CLUSTER": settings.aws_ecs_cluster,
            "AWS_ECS_RUNNER_TASK_DEFINITION": settings.aws_ecs_runner_task_definition,
            "AWS_ECS_RUNNER_CONTAINER": settings.aws_ecs_runner_container,
            "AWS_ECS_SUBNET_IDS": settings.aws_ecs_subnet_ids,
            "AWS_ECS_SECURITY_GROUP_IDS": settings.aws_ecs_security_group_ids,
            "SIGNALLOOP_RUN_BUCKET": settings.signalloop_run_bucket,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing ECS execution settings: {', '.join(missing)}")


def get_execution_provider() -> TestExecutionProvider:
    if settings.execution_backend == "ecs_fargate":
        return ECSFargateExecutionProvider()
    return HTTPWorkerExecutionProvider()


def execution_error_result(message: str) -> dict:
    return {
        "status": "error",
        "exit_code": None,
        "stdout": "",
        "stderr": message,
        "duration_ms": 0,
    }
