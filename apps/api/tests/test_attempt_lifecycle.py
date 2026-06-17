from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import AssessmentAttempt, AuditEvent, Base, CodeSnapshot


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_attempt_generates_invite_and_initial_snapshot(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    response = client.post(
        "/assessment-attempts",
        json={"candidate_email": "candidate@example.com"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["attempt_id"] > 0
    assert body["invite_token"]
    assert body["invite_url"].endswith(f"/invite/{body['invite_token']}")
    assert body["status"] == "created"

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, body["attempt_id"])
        assert attempt is not None
        assert attempt.status == "created"
        assert attempt.started_at is None
        snapshots = session.scalars(select(CodeSnapshot)).all()
        assert len(snapshots) == 1
        assert snapshots[0].kind == "initial"
        assert "task_api/main.py" in snapshots[0].files
        assert ".gitkeep" not in snapshots[0].files
        assert "uv.lock" not in snapshots[0].files
        assert not any("hidden_tests" in path for path in snapshots[0].files)
        assert not any(path.startswith("../") for path in snapshots[0].files)


def test_candidate_can_open_invite_and_receive_metadata_and_files(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    created = client.post("/assessment-attempts", json={}).json()

    response = client.get(f"/candidate/invites/{created['invite_token']}")

    assert response.status_code == 200
    body = response.json()
    assert body["attempt_id"] == created["attempt_id"]
    assert body["status"] == "opened"
    assert body["assessment"]["slug"] == "fastapi_task_api_v1"
    assert "README.md" in body["files"]
    assert "task_api/main.py" in body["files"]
    assert not any("evaluator" in path for path in body["files"])
    assert not any("hidden_tests" in path for path in body["files"])

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.status == "opened"
        assert attempt.started_at is not None


def test_candidate_snapshot_persists_edited_files_and_marks_in_progress(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    created = client.post("/assessment-attempts", json={}).json()
    edited_files = {
        "task_api/main.py": "print('edited')\n",
        "tests/test_candidate_added.py": "def test_added():\n    assert True\n",
    }

    response = client.post(
        f"/candidate/invites/{created['invite_token']}/snapshots",
        json={"kind": "autosave", "files": edited_files},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "autosave"
    assert body["status"] == "in_progress"

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.status == "in_progress"
        snapshots = session.scalars(
            select(CodeSnapshot).where(CodeSnapshot.attempt_id == attempt.id).order_by(CodeSnapshot.id)
        ).all()
        assert [snapshot.kind for snapshot in snapshots] == ["initial", "autosave"]
        assert snapshots[-1].files == edited_files


def test_candidate_invite_returns_latest_snapshot_files(client: TestClient) -> None:
    created = client.post("/assessment-attempts", json={}).json()
    edited_files = {"task_api/main.py": "print('latest')\n"}

    snapshot_response = client.post(
        f"/candidate/invites/{created['invite_token']}/snapshots",
        json={"kind": "autosave", "files": edited_files},
    )
    reopened = client.get(f"/candidate/invites/{created['invite_token']}")

    assert snapshot_response.status_code == 201
    assert reopened.status_code == 200
    assert reopened.json()["files"] == edited_files


def test_unknown_invite_returns_404(client: TestClient) -> None:
    response = client.get("/candidate/invites/not-a-token")

    assert response.status_code == 404


def test_employer_can_list_created_attempts(client: TestClient) -> None:
    created = client.post(
        "/assessment-attempts",
        json={"candidate_email": "candidate@example.com"},
    ).json()

    response = client.get("/assessment-attempts")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["attempt_id"] == created["attempt_id"]
    assert body[0]["candidate_email"] == "candidate@example.com"
    assert body[0]["invite_url"].endswith(f"/invite/{created['invite_token']}")
    assert body[0]["assessment"]["slug"] == "fastapi_task_api_v1"
    assert body[0]["report_id"] is None


def test_attempt_lifecycle_records_audit_events(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    created = client.post("/assessment-attempts", json={}).json()
    client.get(f"/candidate/invites/{created['invite_token']}")
    client.post(
        f"/candidate/invites/{created['invite_token']}/snapshots",
        json={"kind": "autosave", "files": {"task_api/main.py": "print('edited')\n"}},
    )

    with session_factory() as session:
        events = session.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
        assert [event.event_type for event in events] == [
            "attempt.created",
            "attempt.opened",
            "snapshot.saved",
        ]
        assert events[-1].event_metadata == {"kind": "autosave", "file_count": 1}
