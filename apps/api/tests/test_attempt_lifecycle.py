from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.models import AssessmentAttempt, AuditEvent, CodeSnapshot


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
        assert attempt.assessment_level == "standard"
        assert attempt.timing_mode == "untimed"
        assert attempt.duration_minutes == 90
        assert attempt.expires_at is None
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
    assert body["status"] == "created"
    assert body["started_at"] is None
    assert body["expires_at"] is None
    assert body["assessment"]["slug"] == "fastapi_task_api_standard_v2"
    assert "README.md" in body["files"]
    assert "task_api/main.py" in body["files"]
    assert not any("evaluator" in path for path in body["files"])
    assert not any("hidden_tests" in path for path in body["files"])

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.status == "created"
        assert attempt.started_at is None


def test_candidate_accept_starts_attempt_timer(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    created = client.post(
        "/assessment-attempts",
        json={"timing_mode": "timed", "duration_minutes": 120},
    ).json()

    response = client.post(f"/candidate/invites/{created['invite_token']}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "opened"
    assert body["timing_mode"] == "timed"
    assert body["duration_minutes"] == 120
    assert body["started_at"] is not None
    assert body["expires_at"] is not None
    assert body["started_at"].endswith("Z")
    assert body["expires_at"].endswith("Z")

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.status == "opened"
        assert attempt.started_at is not None
        assert attempt.expires_at is not None
        assert attempt.expires_at > attempt.started_at


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
    assert body[0]["assessment"]["slug"] == "fastapi_task_api_standard_v2"
    assert body[0]["assessment_level"] == "standard"
    assert body[0]["timing_mode"] == "untimed"
    assert body[0]["duration_minutes"] == 90
    assert body[0]["expires_at"] is None
    assert body[0]["submission_mode"] is None
    assert body[0]["report_id"] is None


def test_employer_can_create_timed_standard_attempt(client: TestClient) -> None:
    response = client.post(
        "/assessment-attempts",
        json={
            "candidate_email": "candidate@example.com",
            "assessment_level": "standard",
            "timing_mode": "timed",
            "duration_minutes": 120,
        },
    )

    assert response.status_code == 201
    listed = client.get("/assessment-attempts").json()[0]
    assert listed["timing_mode"] == "timed"
    assert listed["duration_minutes"] == 120
    assert listed["created_at"].endswith("Z")


def test_create_attempt_rejects_invalid_duration(client: TestClient) -> None:
    invalid_duration = client.post(
        "/assessment-attempts",
        json={"timing_mode": "timed", "duration_minutes": 45},
    )

    assert invalid_duration.status_code == 422


def test_employer_can_create_advanced_attempt(client: TestClient) -> None:
    response = client.post(
        "/assessment-attempts",
        json={"assessment_level": "advanced"},
    )

    assert response.status_code == 201
    listed = client.get("/assessment-attempts").json()[0]
    assert listed["assessment_level"] == "advanced"
    assert listed["duration_minutes"] == 120
    assert listed["assessment"]["slug"] == "fastapi_task_api_advanced_v1"
    assert listed["assessment"]["version"] == "advanced_v1"


def test_attempt_lifecycle_records_audit_events(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    created = client.post("/assessment-attempts", json={}).json()
    client.post(f"/candidate/invites/{created['invite_token']}/accept")
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


def test_expired_timed_attempt_auto_submits_latest_snapshot_and_blocks_public_tests(
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
    saved = client.post(
        f"/candidate/invites/{token}/snapshots",
        json={"kind": "autosave", "files": {"task_api/main.py": "print('latest')\n"}},
    )
    assert saved.status_code == 201

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

    blocked = client.post(
        f"/candidate/invites/{token}/run-public-tests",
        json={"kind": "public_test_run", "files": {"task_api/main.py": "print('too late')\n"}},
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "Attempt expired and was auto-submitted"

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.status == "submitted"
        assert attempt.submission_mode == "auto_expired"
        assert attempt.final_submission is not None
        assert attempt.final_submission.code_snapshot.files == {"task_api/main.py": "print('latest')\n"}


# ---------------------------------------------------------------------------
# Email validation tests
# ---------------------------------------------------------------------------

def test_create_attempt_rejects_invalid_email_format(client: TestClient) -> None:
    response = client.post(
        "/assessment-attempts",
        json={"candidate_email": "not-an-email"},
    )

    assert response.status_code == 422


def test_create_attempt_rejects_empty_string_email(client: TestClient) -> None:
    response = client.post(
        "/assessment-attempts",
        json={"candidate_email": ""},
    )

    assert response.status_code == 422


def test_create_attempt_accepts_valid_email_and_stores_it(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    response = client.post(
        "/assessment-attempts",
        json={"candidate_email": "stored-candidate@example.com"},
    )

    assert response.status_code == 201
    body = response.json()

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, body["attempt_id"])
        assert attempt is not None
        assert attempt.candidate_email == "stored-candidate@example.com"


# ---------------------------------------------------------------------------
# Phase 2 fields in employer attempt list
# ---------------------------------------------------------------------------

def test_employer_attempt_list_includes_all_phase2_fields(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    response = client.post(
        "/assessment-attempts",
        json={
            "candidate_email": "phase2-check@example.com",
            "assessment_level": "advanced",
            "timing_mode": "timed",
            "duration_minutes": 150,
        },
    )
    assert response.status_code == 201

    listed = client.get("/assessment-attempts")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) >= 1
    item = body[0]

    assert item["assessment_level"] == "advanced"
    assert item["timing_mode"] == "timed"
    assert item["duration_minutes"] == 150
    assert item["expires_at"] is None
    assert item["submission_mode"] is None
    assert isinstance(item["created_at"], str)
    assert item["created_at"].endswith("Z")
