from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.audit import record_audit_event
from signalloop_api.models import AssessmentAttempt, CodeSnapshot, FinalSubmission


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def start_attempt_if_needed(session: Session, attempt: AssessmentAttempt) -> bool:
    if attempt.started_at is not None:
        return False

    started_at = now_utc()
    attempt.started_at = started_at
    if attempt.timing_mode == "timed":
        attempt.expires_at = started_at + timedelta(minutes=attempt.duration_minutes)
    if attempt.status == "created":
        attempt.status = "opened"
    record_audit_event(
        session,
        "attempt.opened",
        actor_type="candidate",
        attempt_id=attempt.id,
        event_metadata={
            "timing_mode": attempt.timing_mode,
            "duration_minutes": attempt.duration_minutes,
            "expires_at": attempt.expires_at.isoformat() if attempt.expires_at else None,
        },
    )
    return True


def attempt_is_expired(attempt: AssessmentAttempt, at: datetime | None = None) -> bool:
    if attempt.timing_mode != "timed" or attempt.expires_at is None:
        return False
    check_at = ensure_aware_utc(at or now_utc())
    expires_at = ensure_aware_utc(attempt.expires_at)
    return check_at >= expires_at


def latest_snapshot(session: Session, attempt: AssessmentAttempt) -> CodeSnapshot | None:
    return session.scalar(
        select(CodeSnapshot)
        .where(CodeSnapshot.attempt_id == attempt.id)
        .order_by(CodeSnapshot.id.desc())
        .limit(1)
    )


def mark_auto_expired_from_latest_snapshot(session: Session, attempt: AssessmentAttempt) -> FinalSubmission | None:
    if attempt.final_submission is not None:
        return attempt.final_submission

    snapshot = latest_snapshot(session, attempt)
    if snapshot is None:
        snapshot = CodeSnapshot(attempt_id=attempt.id, kind="auto_expired_submission", files={})
        session.add(snapshot)
        session.flush()
    elif snapshot.kind != "auto_expired_submission":
        snapshot = CodeSnapshot(attempt_id=attempt.id, kind="auto_expired_submission", files=snapshot.files)
        session.add(snapshot)
        session.flush()

    submitted_at = now_utc()
    final_submission = FinalSubmission(
        attempt_id=attempt.id,
        code_snapshot_id=snapshot.id,
        final_explanation="",
        decision_log="",
        submitted_at=submitted_at,
    )
    attempt.status = "submitted"
    attempt.submitted_at = submitted_at
    attempt.submission_mode = "auto_expired"
    session.add(final_submission)
    record_audit_event(
        session,
        "submission.auto_expired",
        actor_type="system",
        attempt_id=attempt.id,
        event_metadata={"snapshot_id": snapshot.id, "expires_at": attempt.expires_at.isoformat() if attempt.expires_at else None},
    )
    session.flush()
    return final_submission


def enforce_not_expired(session: Session, attempt: AssessmentAttempt) -> None:
    if not attempt_is_expired(attempt):
        return

    mark_auto_expired_from_latest_snapshot(session, attempt)
    session.commit()
    raise HTTPException(status_code=409, detail="Attempt expired and was auto-submitted")
