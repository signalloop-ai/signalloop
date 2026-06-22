from __future__ import annotations

import json
import subprocess
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from time import monotonic
from typing import Protocol
from uuid import uuid4

import httpx

from signalloop_api.config import settings


_DISALLOWED_PATH_PARTS = {"..", "", "evaluator", "hidden_tests", "__pycache__", ".pytest_cache", ".git", ".venv"}
_DISALLOWED_FILENAMES = {".gitkeep"}


def _validate_relative_path(path_value: str) -> PurePosixPath:
    path = PurePosixPath(path_value)
    if path.is_absolute() or any(part in _DISALLOWED_PATH_PARTS for part in path.parts):
        raise ValueError(f"Disallowed workspace path: {path_value}")
    if path.name in _DISALLOWED_FILENAMES:
        raise ValueError(f"Disallowed workspace file: {path_value}")
    return path


def _write_files(root: Path, files: dict[str, str]) -> None:
    for path_value, content in files.items():
        relative_path = _validate_relative_path(path_value)
        target = root / Path(*relative_path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _write_hidden_tests(root: Path, hidden_tests: dict[str, str]) -> None:
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    for path_value, content in hidden_tests.items():
        path = PurePosixPath(path_value)
        if path.is_absolute() or path.name in _DISALLOWED_FILENAMES or not path.name.endswith(".py"):
            raise ValueError(f"Disallowed hidden test file: {path_value}")
        if any(part in {"..", "", "__pycache__", ".pytest_cache", ".git", ".venv"} for part in path.parts):
            raise ValueError(f"Disallowed hidden test path: {path_value}")
        (tests_dir / path.name).write_text(content, encoding="utf-8")


def _run_subprocess(command: list[str], workspace: Path, timeout_seconds: int) -> dict:
    started = monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "Test run timed out",
            "duration_ms": int((monotonic() - started) * 1000),
        }
    return {
        "status": "passed" if process.returncode == 0 else "failed",
        "exit_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "duration_ms": int((monotonic() - started) * 1000),
    }


class TestExecutionProvider(Protocol):
    def run_public(self, files: dict[str, str]) -> dict:
        ...

    def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        ...

    def run_candidate_verification(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        ...


class HTTPWorkerExecutionProvider:
    def run_public(self, files: dict[str, str]) -> dict:
        started = monotonic()
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
        result = dict(response.json())
        timings = dict(result.get("timings") or {})
        timings["api_worker_request_ms"] = int((monotonic() - started) * 1000)
        result["timings"] = timings
        return result

    def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        last_error: httpx.HTTPError | None = None
        for _ in range(settings.worker_request_retries + 1):
            try:
                started = monotonic()
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
                result = dict(response.json())
                timings = dict(result.get("timings") or {})
                timings["api_worker_request_ms"] = int((monotonic() - started) * 1000)
                result["timings"] = timings
                return result
            except httpx.HTTPError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Worker request failed without an error")

    def run_candidate_verification(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        started = monotonic()
        response = httpx.post(
            f"{settings.execution_worker_url.rstrip('/')}/run-candidate-verification",
            json={
                "files": original_files,
                "hidden_tests": candidate_tests,
                "runtime_image": settings.assessment_runtime_image,
                "timeout_seconds": 60,
                "command": ["python", "-m", "pytest", "tests/", "-v"],
            },
            timeout=settings.worker_request_timeout_seconds,
        )
        response.raise_for_status()
        result = dict(response.json())
        timings = dict(result.get("timings") or {})
        timings["api_worker_request_ms"] = int((monotonic() - started) * 1000)
        result["timings"] = timings
        return result


class DirectExecutionProvider:
    """Runs pytest in-process via subprocess — no Docker, no ECS, no network.

    Safe for pilot use with trusted candidates. Candidate code runs in the
    same OS process as the API (subprocess isolation only).
    """

    def run_public(self, files: dict[str, str]) -> dict:
        return self._run(files, {}, ["python", "-m", "pytest", "tests"])

    def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        return self._run(files, hidden_tests, ["python", "-m", "pytest", "tests/test_hidden_api.py"])

    def run_candidate_verification(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        return self._run(original_files, candidate_tests, ["python", "-m", "pytest", "tests/", "-v"])

    def _run(self, files: dict[str, str], hidden_tests: dict[str, str], command: list[str]) -> dict:
        t0 = monotonic()
        with TemporaryDirectory(prefix="signalloop-direct-run-") as workspace_name:
            workspace = Path(workspace_name)
            _write_files(workspace, files)
            if hidden_tests:
                _write_hidden_tests(workspace, hidden_tests)
            result = _run_subprocess(command, workspace, timeout_seconds=60)
        result.setdefault("timings", {})["direct_total_ms"] = int((monotonic() - t0) * 1000)
        return result


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

    def run_candidate_verification(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        return self._run_task(
            {
                "files": original_files,
                "hidden_tests": candidate_tests,
                "command": ["python", "-m", "pytest", "tests/", "-v"],
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

        started = monotonic()
        self.s3.put_object(
            Bucket=settings.signalloop_run_bucket,
            Key=input_key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )
        input_uploaded = monotonic()

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
        task_requested = monotonic()
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
        task_stopped = monotonic()

        described = self.ecs.describe_tasks(cluster=settings.aws_ecs_cluster, tasks=[task_arn])
        stopped_task = (described.get("tasks") or [{}])[0]
        containers = stopped_task.get("containers") or []
        exit_codes = [container.get("exitCode") for container in containers if "exitCode" in container]
        if exit_codes and any(code not in {0, None} for code in exit_codes):
            raise RuntimeError(f"ECS runner container exited with code(s): {exit_codes}")

        result_object = self.s3.get_object(Bucket=settings.signalloop_run_bucket, Key=output_key)
        result = json.loads(result_object["Body"].read().decode("utf-8"))
        completed = monotonic()
        result.setdefault("duration_ms", int((completed - started) * 1000))
        timings = dict(result.get("timings") or {})
        timings.update(
            {
                "s3_input_upload_ms": int((input_uploaded - started) * 1000),
                "ecs_run_task_ms": int((task_requested - input_uploaded) * 1000),
                "ecs_wait_stopped_ms": int((task_stopped - task_requested) * 1000),
                "s3_output_download_ms": int((completed - task_stopped) * 1000),
                "api_execution_provider_ms": int((completed - started) * 1000),
            }
        )
        result["timings"] = timings
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
    if settings.execution_backend == "direct":
        return DirectExecutionProvider()
    return HTTPWorkerExecutionProvider()


def execution_error_result(message: str) -> dict:
    return {
        "status": "error",
        "exit_code": None,
        "stdout": "",
        "stderr": message,
        "duration_ms": 0,
        "timings": {},
    }
