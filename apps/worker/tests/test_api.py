from fastapi.testclient import TestClient

from signalloop_worker import main
from signalloop_worker.main import app, parse_cors_origins
from signalloop_worker.schemas import PublicTestRunResult


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_public_test_endpoint_rejects_hidden_test_paths() -> None:
    client = TestClient(app)

    response = client.post(
        "/run-public-tests",
        json={"files": {"hidden_tests/test_hidden.py": "def test_hidden(): pass"}},
    )

    assert response.status_code == 400
    assert "Disallowed path" in response.json()["detail"]


def test_worker_allows_local_web_cors_preflight() -> None:
    client = TestClient(app)

    response = client.options(
        "/run-public-tests",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_worker_cors_origins_can_be_configured(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_CORS_ORIGINS", "https://web.example.com, http://localhost:3000")

    assert parse_cors_origins() == ["https://web.example.com", "http://localhost:3000"]


def test_public_test_endpoint_returns_structured_result(monkeypatch) -> None:
    def fake_run_public_tests_in_workspace(payload, workspace):
        return PublicTestRunResult(
            status="passed",
            exit_code=0,
            stdout="1 passed",
            stderr="",
            duration_ms=12,
        )

    monkeypatch.setattr(main, "run_public_tests_in_workspace", fake_run_public_tests_in_workspace)
    client = TestClient(app)

    response = client.post(
        "/run-public-tests",
        json={"files": {"tests/test_public.py": "def test_ok(): pass"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "passed",
        "exit_code": 0,
        "stdout": "1 passed",
        "stderr": "",
        "duration_ms": 12,
    }


def test_hidden_test_endpoint_returns_structured_result(monkeypatch) -> None:
    def fake_run_hidden_tests_in_workspace(payload, workspace):
        assert "hidden_tests" not in payload.files
        assert payload.hidden_tests == {"test_hidden_api.py": "def test_hidden(): pass"}
        return PublicTestRunResult(
            status="failed",
            exit_code=1,
            stdout="",
            stderr="hidden failure",
            duration_ms=15,
        )

    monkeypatch.setattr(main, "run_hidden_tests_in_workspace", fake_run_hidden_tests_in_workspace)
    client = TestClient(app)

    response = client.post(
        "/run-hidden-tests",
        json={
            "files": {"task_api/main.py": "print('candidate')"},
            "hidden_tests": {"test_hidden_api.py": "def test_hidden(): pass"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "failed",
        "exit_code": 1,
        "stdout": "",
        "stderr": "hidden failure",
        "duration_ms": 15,
    }
