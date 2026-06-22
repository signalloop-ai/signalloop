"""Tests for the proctoring event batch endpoint.

Covers: happy path, validation errors, attempt state guards, edge cases.
All tests use SQLite in-memory DB via the shared conftest fixtures.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker, Session

from signalloop_api.models import AssessmentAttempt, AssessmentPack, ProctoringEvent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iso(dt: datetime) -> str:
    return dt.isoformat()


NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)


def _create_attempt(
    session_factory: sessionmaker[Session],
    *,
    status: str = "in_progress",
) -> tuple[str, int]:
    """Create a minimal pack + attempt and return (invite_token, attempt_id)."""
    with session_factory() as session:
        pack = AssessmentPack(
            slug="test-pack",
            title="Test Pack",
            version="v1",
            candidate_path="assessment_packs/test",
            evaluator_path="assessment_packs/test/evaluator",
        )
        session.add(pack)
        session.flush()

        attempt = AssessmentAttempt(
            assessment_pack_id=pack.id,
            invite_token="tok-proctoring-test",
            status=status,
            assessment_level="standard",
            timing_mode="untimed",
            duration_minutes=90,
            evaluator_feedback_mode="strict",
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return attempt.invite_token, attempt.id


def _batch(events: list[dict]) -> dict:
    return {"events": events}


def _event(
    event_type: str = "focus_lost",
    occurred_at: datetime | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "event_type": event_type,
        "occurred_at": _iso(occurred_at or NOW),
        **({"metadata": metadata} if metadata is not None else {}),
    }


# ── Happy path ────────────────────────────────────────────────────────────────

def test_single_event_accepted(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    token, attempt_id = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_lost")]),
    )
    assert resp.status_code == 201
    assert resp.json() == {"accepted": 1}


def test_batch_of_multiple_events_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, attempt_id = _create_attempt(session_factory)
    events = [
        _event("focus_lost", NOW),
        _event("focus_returned", NOW + timedelta(seconds=45), {"duration_seconds": 45}),
        _event("fullscreen_exit", NOW + timedelta(minutes=5)),
        _event("fullscreen_enter", NOW + timedelta(minutes=5, seconds=2)),
    ]
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch(events),
    )
    assert resp.status_code == 201
    assert resp.json() == {"accepted": 4}


def test_events_persisted_in_db(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, attempt_id = _create_attempt(session_factory)
    meta = {"duration_seconds": 30}
    client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_returned", metadata=meta)]),
    )
    with session_factory() as session:
        rows = session.query(ProctoringEvent).filter_by(attempt_id=attempt_id).all()
    assert len(rows) == 1
    assert rows[0].event_type == "focus_returned"
    assert rows[0].event_metadata == {"duration_seconds": 30}


def test_metadata_is_optional(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([{"event_type": "fullscreen_exit", "occurred_at": _iso(NOW)}]),
    )
    assert resp.status_code == 201


def test_all_valid_event_types_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    for event_type in ("fullscreen_exit", "fullscreen_enter", "focus_lost", "focus_returned"):
        resp = client.post(
            f"/candidate/invites/{token}/proctoring-events/batch",
            json=_batch([_event(event_type)]),
        )
        assert resp.status_code == 201, f"Expected 201 for {event_type!r}, got {resp.status_code}"


def test_naive_datetime_accepted_and_stored(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Naive ISO timestamps (no tz offset) should be accepted, treated as UTC, and persisted."""
    token, attempt_id = _create_attempt(session_factory)
    naive_ts = "2026-06-22T12:00:00"
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([{"event_type": "focus_lost", "occurred_at": naive_ts}]),
    )
    assert resp.status_code == 201
    with session_factory() as session:
        row = session.query(ProctoringEvent).filter_by(attempt_id=attempt_id).first()
    assert row is not None
    # SQLite strips tz info on readback; check the value was stored (not rejected or dropped).
    assert row.occurred_at.year == 2026
    assert row.occurred_at.hour == 12


def test_occurred_at_with_timezone_offset_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_lost", occurred_at=datetime(2026, 6, 22, 8, 0, 0, tzinfo=timezone.utc))]),
    )
    assert resp.status_code == 201


def test_attempt_in_opened_status_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Events should be recorded even before the first test run (status=opened)."""
    token, _ = _create_attempt(session_factory, status="opened")
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("fullscreen_exit")]),
    )
    assert resp.status_code == 201


def test_attempt_in_created_status_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Fullscreen request happens at workspace open before accept — allow it."""
    token, _ = _create_attempt(session_factory, status="created")
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("fullscreen_enter")]),
    )
    assert resp.status_code == 201


# ── Attempt state guards ──────────────────────────────────────────────────────

def test_submitted_attempt_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory, status="submitted")
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_lost")]),
    )
    assert resp.status_code == 409
    assert "submitted" in resp.json()["detail"].lower()


def test_expired_attempt_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory, status="expired")
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_lost")]),
    )
    assert resp.status_code == 409
    assert "expired" in resp.json()["detail"].lower()


def test_unknown_token_returns_404(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    resp = client.post(
        "/candidate/invites/no-such-token/proctoring-events/batch",
        json=_batch([_event("focus_lost")]),
    )
    assert resp.status_code == 404


# ── Validation errors ─────────────────────────────────────────────────────────

def test_unknown_event_type_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("screen_recorded")]),
    )
    assert resp.status_code == 422
    assert "screen_recorded" in resp.json()["detail"]


def test_mixed_valid_and_invalid_event_types_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_lost"), _event("hack_the_planet")]),
    )
    assert resp.status_code == 422


def test_empty_events_list_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json={"events": []},
    )
    assert resp.status_code == 422


def test_batch_exceeding_max_size_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    events = [_event("focus_lost", NOW + timedelta(seconds=i)) for i in range(51)]
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch(events),
    )
    assert resp.status_code == 422


def test_malformed_occurred_at_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([{"event_type": "focus_lost", "occurred_at": "not-a-date"}]),
    )
    assert resp.status_code == 422


def test_future_timestamp_beyond_one_hour_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    far_future = datetime.now(timezone.utc) + timedelta(hours=2)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([_event("focus_lost", far_future)]),
    )
    assert resp.status_code == 422


def test_missing_event_type_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([{"occurred_at": _iso(NOW)}]),
    )
    assert resp.status_code == 422


def test_missing_occurred_at_rejected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token, _ = _create_attempt(session_factory)
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch([{"event_type": "focus_lost"}]),
    )
    assert resp.status_code == 422


# ── Isolation ─────────────────────────────────────────────────────────────────

def test_events_stored_on_correct_attempt(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Events from one token must not bleed into another attempt's rows."""
    token_a, id_a = _create_attempt(session_factory)

    with session_factory() as session:
        pack = session.query(AssessmentPack).first()
        attempt_b = AssessmentAttempt(
            assessment_pack_id=pack.id,
            invite_token="tok-b",
            status="in_progress",
            assessment_level="standard",
            timing_mode="untimed",
            duration_minutes=90,
            evaluator_feedback_mode="strict",
        )
        session.add(attempt_b)
        session.commit()
        session.refresh(attempt_b)
        id_b = attempt_b.id

    client.post(
        f"/candidate/invites/{token_a}/proctoring-events/batch",
        json=_batch([_event("fullscreen_exit")]),
    )

    with session_factory() as session:
        rows_a = session.query(ProctoringEvent).filter_by(attempt_id=id_a).count()
        rows_b = session.query(ProctoringEvent).filter_by(attempt_id=id_b).count()

    assert rows_a == 1
    assert rows_b == 0


def test_large_batch_at_limit_accepted(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Exactly 50 events (the max) must be accepted."""
    token, _ = _create_attempt(session_factory)
    events = [_event("focus_lost", NOW + timedelta(seconds=i)) for i in range(50)]
    resp = client.post(
        f"/candidate/invites/{token}/proctoring-events/batch",
        json=_batch(events),
    )
    assert resp.status_code == 201
    assert resp.json() == {"accepted": 50}
