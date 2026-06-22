from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.database import get_session
from signalloop_api.models import AssessmentAttempt, ProctoringEvent, VALID_PROCTORING_EVENT_TYPES
from signalloop_api.schemas import ProctoringEventBatchRequest

router = APIRouter()


def _get_active_attempt(invite_token: str, session: Session) -> AssessmentAttempt:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Attempt is already submitted")
    if attempt.status == "expired":
        raise HTTPException(status_code=409, detail="Attempt has expired")
    return attempt


def _parse_occurred_at(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid occurred_at: {value!r}") from exc


@router.post(
    "/candidate/invites/{invite_token}/proctoring-events/batch",
    status_code=status.HTTP_201_CREATED,
)
def record_proctoring_events(
    invite_token: str,
    payload: ProctoringEventBatchRequest,
    session: Session = Depends(get_session),
) -> dict:
    attempt = _get_active_attempt(invite_token, session)

    invalid = [e.event_type for e in payload.events if e.event_type not in VALID_PROCTORING_EVENT_TYPES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown event type(s): {', '.join(sorted(set(invalid)))}",
        )

    now = datetime.now(timezone.utc)
    rows = []
    for item in payload.events:
        occurred_at = _parse_occurred_at(item.occurred_at)
        # Reject events timestamped more than 1 hour in the future — likely clock skew.
        if (occurred_at - now).total_seconds() > 3600:
            raise HTTPException(
                status_code=422,
                detail=f"occurred_at is too far in the future: {item.occurred_at!r}",
            )
        rows.append(ProctoringEvent(
            attempt_id=attempt.id,
            event_type=item.event_type,
            occurred_at=occurred_at,
            event_metadata=item.metadata,
        ))

    session.add_all(rows)
    session.commit()
    return {"accepted": len(rows)}
