from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired, run
from time import monotonic

from signalloop_worker.schemas import HiddenTestRunRequest, PublicTestRunRequest, PublicTestRunResult
from signalloop_worker.workspace import write_hidden_tests, write_workspace


def build_docker_command(request: PublicTestRunRequest, workspace: Path) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cpus",
        "1",
        "--memory",
        "512m",
        "--pids-limit",
        "128",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "-v",
        f"{workspace}:/workspace:rw",
        "-w",
        "/workspace",
        request.runtime_image,
        *request.command,
    ]


def classify_status(exit_code: int) -> str:
    return "passed" if exit_code == 0 else "failed"


def result_from_completed_process(process: CompletedProcess[str], duration_ms: int) -> PublicTestRunResult:
    return PublicTestRunResult(
        status=classify_status(process.returncode),
        exit_code=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        duration_ms=duration_ms,
    )


def run_public_tests_in_workspace(request: PublicTestRunRequest, workspace: Path) -> PublicTestRunResult:
    write_workspace(workspace, request.files)
    return run_tests_in_workspace(request, workspace)


def run_hidden_tests_in_workspace(request: HiddenTestRunRequest, workspace: Path) -> PublicTestRunResult:
    write_workspace(workspace, request.files)
    write_hidden_tests(workspace, request.hidden_tests)
    return run_tests_in_workspace(request, workspace)


def run_tests_in_workspace(request: PublicTestRunRequest, workspace: Path) -> PublicTestRunResult:
    docker_command = build_docker_command(request, workspace)
    started = monotonic()
    try:
        process = run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=request.timeout_seconds,
            check=False,
        )
    except TimeoutExpired as exc:
        duration_ms = int((monotonic() - started) * 1000)
        return PublicTestRunResult(
            status="timeout",
            exit_code=None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "Test run timed out",
            duration_ms=duration_ms,
        )

    duration_ms = int((monotonic() - started) * 1000)
    return result_from_completed_process(process, duration_ms)
