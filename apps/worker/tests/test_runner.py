from pathlib import Path
from subprocess import CompletedProcess

from signalloop_worker.runner import build_docker_command, result_from_completed_process, run_hidden_tests_in_workspace
from signalloop_worker.schemas import HiddenTestRunRequest, PublicTestRunRequest


def test_build_docker_command_uses_public_execution_constraints(tmp_path: Path) -> None:
    request = PublicTestRunRequest(files={"tests/test_public.py": "def test_ok(): assert True"})

    command = build_docker_command(request, tmp_path)

    assert command[:2] == ["docker", "run"]
    assert "--network" in command
    assert "none" in command
    assert "--memory" in command
    assert "512m" in command
    assert "--pids-limit" in command
    assert f"{tmp_path}:/workspace:rw" in command
    assert request.runtime_image in command


def test_result_from_completed_process_classifies_pass_and_failure() -> None:
    passed = result_from_completed_process(CompletedProcess(args=[], returncode=0, stdout="ok", stderr=""), 12)
    failed = result_from_completed_process(CompletedProcess(args=[], returncode=1, stdout="", stderr="bad"), 34)

    assert passed.status == "passed"
    assert passed.exit_code == 0
    assert passed.duration_ms == 12
    assert failed.status == "failed"
    assert failed.exit_code == 1
    assert failed.stderr == "bad"


def test_hidden_test_run_writes_evaluator_tests_before_execution(monkeypatch, tmp_path: Path) -> None:
    def fake_run_tests_in_workspace(request, workspace):
        assert (workspace / "task_api" / "main.py").exists()
        assert (workspace / "tests" / "test_hidden_api.py").read_text() == "def test_hidden(): pass"
        return result_from_completed_process(CompletedProcess(args=[], returncode=0, stdout="ok", stderr=""), 9)

    monkeypatch.setattr("signalloop_worker.runner.run_tests_in_workspace", fake_run_tests_in_workspace)
    request = HiddenTestRunRequest(
        files={"task_api/main.py": "print('candidate')"},
        hidden_tests={"test_hidden_api.py": "def test_hidden(): pass"},
    )

    result = run_hidden_tests_in_workspace(request, tmp_path)

    assert result.status == "passed"
    assert result.stdout == "ok"
