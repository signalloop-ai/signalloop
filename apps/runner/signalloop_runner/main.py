from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.parse import urlparse


DISALLOWED_PARTS = {"..", "", "evaluator", "hidden_tests", "__pycache__", ".pytest_cache", ".git", ".venv"}
DISALLOWED_FILENAMES = {".gitkeep"}


def validate_relative_path(path_value: str) -> PurePosixPath:
    path = PurePosixPath(path_value)
    if path.is_absolute() or any(part in DISALLOWED_PARTS for part in path.parts):
        raise ValueError(f"Disallowed workspace path: {path_value}")
    if path.name in DISALLOWED_FILENAMES:
        raise ValueError(f"Disallowed workspace file: {path_value}")
    return path


def write_files(root: Path, files: dict[str, str]) -> None:
    for path_value, content in files.items():
        relative_path = validate_relative_path(path_value)
        target = root / Path(*relative_path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def write_hidden_tests(root: Path, hidden_tests: dict[str, str]) -> None:
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    for path_value, content in hidden_tests.items():
        path = PurePosixPath(path_value)
        if path.is_absolute() or path.name in DISALLOWED_FILENAMES or not path.name.endswith(".py"):
            raise ValueError(f"Disallowed hidden test file: {path_value}")
        if any(part in {"..", "", "__pycache__", ".pytest_cache", ".git", ".venv"} for part in path.parts):
            raise ValueError(f"Disallowed hidden test path: {path_value}")
        (tests_dir / path.name).write_text(content, encoding="utf-8")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError(f"Expected s3://bucket/key URI, got: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def read_json(location: str) -> dict:
    if location.startswith("s3://"):
        import boto3

        bucket, key = parse_s3_uri(location)
        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
        return json.loads(body.decode("utf-8"))
    return json.loads(Path(location).read_text(encoding="utf-8"))


def write_json(location: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    if location.startswith("s3://"):
        import boto3

        bucket, key = parse_s3_uri(location)
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=data, ContentType="application/json")
        return
    Path(location).parent.mkdir(parents=True, exist_ok=True)
    Path(location).write_bytes(data)


def result_from_exception(exc: BaseException) -> dict:
    return {
        "status": "error",
        "exit_code": None,
        "stdout": "",
        "stderr": str(exc),
        "duration_ms": 0,
    }


def run_tests(payload: dict) -> dict:
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Payload must include non-empty files")

    hidden_tests = payload.get("hidden_tests") or {}
    command = payload.get("command")
    if not command:
        command = ["python", "-m", "pytest", "tests/test_hidden_api.py" if hidden_tests else "tests"]
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise ValueError("command must be a list of strings")

    timeout_seconds = int(payload.get("timeout_seconds", 60))

    with TemporaryDirectory(prefix="signalloop-fargate-run-") as workspace_name:
        workspace = Path(workspace_name)
        write_files(workspace, files)
        if hidden_tests:
            write_hidden_tests(workspace, hidden_tests)

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


def main() -> int:
    input_uri = os.getenv("SIGNALLOOP_RUNNER_INPUT")
    output_uri = os.getenv("SIGNALLOOP_RUNNER_OUTPUT")
    if not input_uri or not output_uri:
        print("SIGNALLOOP_RUNNER_INPUT and SIGNALLOOP_RUNNER_OUTPUT are required", file=sys.stderr)
        return 2

    try:
        payload = read_json(input_uri)
        result = run_tests(payload)
    except BaseException as exc:
        result = result_from_exception(exc)

    write_json(output_uri, result)
    print(json.dumps({"status": result["status"], "duration_ms": result["duration_ms"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
