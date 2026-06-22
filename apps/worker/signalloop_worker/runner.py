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
        "-e", "COLUMNS=200",
        "-v",
        f"{workspace}:/workspace:rw",
        "-w",
        "/workspace",
        request.runtime_image,
        *request.command,
    ]


def classify_status(exit_code: int) -> str:
    return "passed" if exit_code == 0 else "failed"


def result_from_completed_process(
    process: CompletedProcess[str],
    duration_ms: int,
    timings: dict[str, int] | None = None,
) -> PublicTestRunResult:
    return PublicTestRunResult(
        status=classify_status(process.returncode),
        exit_code=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        duration_ms=duration_ms,
        timings=timings or {},
    )


def run_public_tests_in_workspace(request: PublicTestRunRequest, workspace: Path) -> PublicTestRunResult:
    started = monotonic()
    write_workspace(workspace, request.files)
    workspace_written = monotonic()
    result = run_tests_in_workspace(request, workspace)
    timings = dict(result.timings)
    timings["worker_workspace_materialization_ms"] = int((workspace_written - started) * 1000)
    timings["worker_total_ms"] = int((monotonic() - started) * 1000)
    result.timings = timings
    return result


def run_hidden_tests_in_workspace(request: HiddenTestRunRequest, workspace: Path) -> PublicTestRunResult:
    started = monotonic()
    write_workspace(workspace, request.files)
    workspace_written = monotonic()
    write_hidden_tests(workspace, request.hidden_tests)
    hidden_written = monotonic()
    result = run_tests_in_workspace(request, workspace)
    timings = dict(result.timings)
    timings["worker_workspace_materialization_ms"] = int((workspace_written - started) * 1000)
    timings["worker_hidden_test_materialization_ms"] = int((hidden_written - workspace_written) * 1000)
    timings["worker_total_ms"] = int((monotonic() - started) * 1000)
    result.timings = timings
    return result


def run_tests_in_workspace(request: PublicTestRunRequest, workspace: Path) -> PublicTestRunResult:
    setup_started = monotonic()
    docker_command = build_docker_command(request, workspace)
    docker_command_built = monotonic()
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
            timings={
                "worker_command_build_ms": int((docker_command_built - setup_started) * 1000),
                "worker_pytest_ms": duration_ms,
                "worker_total_ms": int((monotonic() - setup_started) * 1000),
            },
        )

    completed = monotonic()
    duration_ms = int((completed - started) * 1000)
    timings = {
        "worker_command_build_ms": int((docker_command_built - setup_started) * 1000),
        "worker_pytest_ms": duration_ms,
        "worker_total_ms": int((completed - setup_started) * 1000),
    }
    return result_from_completed_process(process, duration_ms, timings)
