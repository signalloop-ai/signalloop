from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.auth import get_current_employer
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import AssessmentAttempt, AuditEvent, CodeSnapshot, Employer, FinalSubmission, TestRun
from signalloop_api.submissions import (
    ExecutionProviderHiddenTestRunner,
    HTTPHiddenTestRunner,
    get_hidden_test_runner,
    hidden_test_files_for_attempt,
)


class FakeHiddenTestRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], dict[str, str]]] = []

    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        self.calls.append((files, hidden_tests))
        return {
            "status": "failed",
            "exit_code": 1,
            "stdout": "hidden stdout",
            "stderr": "hidden assertion detail",
            "duration_ms": 42,
        }


class RaisingHiddenTestRunner:
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        raise RuntimeError("ecs hidden run failed")


@pytest.fixture()
def hidden_runner() -> FakeHiddenTestRunner:
    return FakeHiddenTestRunner()


@pytest.fixture()
def client(
    session_factory: sessionmaker[Session],
    hidden_runner: FakeHiddenTestRunner,
    default_employer: Employer,
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_employer() -> Employer:
        return default_employer

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_employer] = override_get_current_employer
    app.dependency_overrides[get_hidden_test_runner] = lambda: hidden_runner
    yield TestClient(app)
    app.dependency_overrides.clear()


def create_attempt(client: TestClient) -> str:
    response = client.post("/assessment-attempts", json={})
    assert response.status_code == 201
    return response.json()["invite_token"]


def test_final_submission_locks_attempt_and_persists_hidden_result(
    client: TestClient,
    session_factory: sessionmaker[Session],
    hidden_runner: FakeHiddenTestRunner,
) -> None:
    token = create_attempt(client)
    files = {
        "task_api/main.py": "print('final')\n",
        "tests/test_candidate_added.py": "def test_added():\n    assert True\n",
    }

    response = client.post(
        f"/candidate/invites/{token}/submit",
        json={
            "files": files,
            "final_explanation": "Fixed focused validation and ownership behavior.",
            "decision_log": "Chose explicit authorization behavior.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "submitted"
    assert body["hidden_test_status"] == "failed"
    assert "hidden assertion detail" not in response.text
    assert hidden_runner.calls
    assert "test_hidden_api.py" in hidden_runner.calls[0][1]

    with session_factory() as session:
        attempt = session.scalar(select(AssessmentAttempt).where(AssessmentAttempt.invite_token == token))
        assert attempt is not None
        assert attempt.status == "submitted"
        assert attempt.submitted_at is not None
        assert attempt.submission_mode == "manual"

        final_submission = session.scalar(select(FinalSubmission).where(FinalSubmission.attempt_id == attempt.id))
        assert final_submission is not None
        assert final_submission.final_explanation == "Fixed focused validation and ownership behavior."
        assert final_submission.decision_log == "Chose explicit authorization behavior."

        snapshot = session.get(CodeSnapshot, final_submission.code_snapshot_id)
        assert snapshot is not None
        assert snapshot.kind == "final_submission"
        assert snapshot.files == files

        hidden_run = session.scalar(select(TestRun).where(TestRun.attempt_id == attempt.id))
        assert hidden_run is not None
        assert hidden_run.run_type == "hidden"
        assert hidden_run.status == "failed"
        assert hidden_run.stderr == "hidden assertion detail"

        events = session.scalars(select(AuditEvent).where(AuditEvent.attempt_id == attempt.id).order_by(AuditEvent.id)).all()
        assert "submission.created" in [event.event_type for event in events]
        assert "hidden_tests.completed" in [event.event_type for event in events]


def test_final_submission_is_immutable_and_blocks_later_snapshots(client: TestClient) -> None:
    token = create_attempt(client)
    payload = {
        "files": {"task_api/main.py": "print('final')"},
        "final_explanation": "Final explanation.",
        "decision_log": "Decision log.",
    }

    first = client.post(f"/candidate/invites/{token}/submit", json=payload)
    second = client.post(f"/candidate/invites/{token}/submit", json=payload)
    snapshot = client.post(
        f"/candidate/invites/{token}/snapshots",
        json={"kind": "autosave", "files": {"task_api/main.py": "print('late')"}},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Final submission is immutable"
    assert snapshot.status_code == 409


def test_final_submission_after_expiry_is_recorded_as_auto_expired(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    created = client.post(
        "/assessment-attempts",
        json={"timing_mode": "timed", "duration_minutes": 60},
    ).json()
    token = created["invite_token"]
    accepted = client.post(f"/candidate/invites/{token}/accept")
    assert accepted.status_code == 200

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

    submitted = client.post(
        f"/candidate/invites/{token}/submit",
        json={
            "files": {"task_api/main.py": "print('expired browser state')\n"},
            "final_explanation": "",
            "decision_log": "",
            "submission_mode": "auto_expired",
        },
    )

    assert submitted.status_code == 201
    assert submitted.json()["status"] == "submitted"

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.submission_mode == "auto_expired"
        assert attempt.final_submission is not None
        assert attempt.final_submission.final_explanation == ""
        assert attempt.final_submission.code_snapshot.files == {
            "task_api/main.py": "print('expired browser state')\n",
        }


def test_final_submission_persists_hidden_error_when_runner_raises(
    session_factory: sessionmaker[Session],
    default_employer: Employer,
) -> None:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_employer() -> Employer:
        return default_employer

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_employer] = override_get_current_employer
    app.dependency_overrides[get_hidden_test_runner] = lambda: RaisingHiddenTestRunner()

    with TestClient(app) as client:
        token = create_attempt(client)
        response = client.post(
            f"/candidate/invites/{token}/submit",
            json={
                "files": {"task_api/main.py": "print('final')"},
                "final_explanation": "Submitted with infrastructure failure handled.",
                "decision_log": "Runner error should be captured.",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "submitted"
    assert body["hidden_test_status"] == "error"

    with session_factory() as session:
        attempt = session.scalar(select(AssessmentAttempt).where(AssessmentAttempt.invite_token == token))
        assert attempt is not None
        hidden_run = session.scalar(select(TestRun).where(TestRun.attempt_id == attempt.id))
        assert hidden_run is not None
        assert hidden_run.run_type == "hidden"
        assert hidden_run.status == "error"
        assert hidden_run.stderr == "ecs hidden run failed"


def test_hidden_tests_resolve_from_current_pack_config_when_stored_path_is_stale(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    token = create_attempt(client)

    with session_factory() as session:
        attempt = session.scalar(select(AssessmentAttempt).where(AssessmentAttempt.invite_token == token))
        assert attempt is not None
        attempt.assessment_pack.evaluator_path = "/tmp/render-old-release/missing/evaluator"
        session.commit()
        session.refresh(attempt)

        hidden_tests = hidden_test_files_for_attempt(attempt)

    assert "test_hidden_api.py" in hidden_tests


def test_execution_provider_hidden_runner_calls_run_hidden(monkeypatch) -> None:
    calls = {}

    class FakeExecutionProvider:
        def run_hidden(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
            calls["files"] = files
            calls["hidden_tests"] = hidden_tests
            return {"status": "passed", "duration_ms": 7}

    monkeypatch.setattr("signalloop_api.execution.get_execution_provider", lambda: FakeExecutionProvider())

    result = ExecutionProviderHiddenTestRunner().run(
        {"task_api/main.py": "app = None\n"},
        {"test_hidden_api.py": "def test_hidden():\n    assert True\n"},
    )

    assert result["status"] == "passed"
    assert calls["files"] == {"task_api/main.py": "app = None\n"}
    assert "test_hidden_api.py" in calls["hidden_tests"]


def test_http_hidden_test_runner_retries_transient_worker_errors(monkeypatch) -> None:
    calls = {"count": 0}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"status": "passed", "duration_ms": 12}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ConnectError("temporary worker connection failure")
        return FakeResponse()

    monkeypatch.setattr("signalloop_api.execution.settings.worker_request_retries", 1)
    monkeypatch.setattr("signalloop_api.execution.httpx.post", fake_post)

    result = HTTPHiddenTestRunner().run({"task_api/main.py": ""}, {"test_hidden.py": ""})

    assert calls["count"] == 2
    assert result["status"] == "passed"
