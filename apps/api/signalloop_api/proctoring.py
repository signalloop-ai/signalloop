import re
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.config import settings
from signalloop_api.database import get_session
from signalloop_api.models import AssessmentAttempt, ProctoringEvent, VALID_PROCTORING_EVENT_TYPES
from signalloop_api.schemas import (
    ProctoringEventBatchRequest,
    SnapshotUploadUrlRequest,
    SnapshotUploadUrlResponse,
    WebcamConsentRequest,
)

_SAFE_FILENAME = re.compile(r"^[\w\-]+\.jpe?g$", re.IGNORECASE)

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


@router.patch(
    "/candidate/invites/{invite_token}/webcam-consent",
    status_code=status.HTTP_204_NO_CONTENT,
)
def set_webcam_consent(
    invite_token: str,
    payload: WebcamConsentRequest,
    session: Session = Depends(get_session),
) -> None:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Attempt is already submitted")
    attempt.webcam_consent = payload.consented
    session.commit()


@router.post(
    "/candidate/invites/{invite_token}/snapshot-upload-url",
    response_model=SnapshotUploadUrlResponse,
    status_code=status.HTTP_200_OK,
)
def get_snapshot_upload_url(
    invite_token: str,
    payload: SnapshotUploadUrlRequest,
    session: Session = Depends(get_session),
) -> SnapshotUploadUrlResponse:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Attempt is already submitted")
    if attempt.status == "expired":
        raise HTTPException(status_code=409, detail="Attempt has expired")
    if attempt.webcam_consent is not True:
        raise HTTPException(status_code=403, detail="Webcam consent not granted")

    filename = payload.filename
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(
            status_code=422,
            detail="filename must be alphanumeric with hyphens/underscores and end in .jpg or .jpeg",
        )

    if not settings.s3_bucket:
        raise HTTPException(status_code=503, detail="S3 not configured")

    s3_key = f"snapshots/{attempt.id}/{filename}"
    try:
        s3 = boto3.client("s3", region_name=settings.aws_region)
        upload_url: str = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": s3_key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=300,
        )
    except ClientError as exc:
        raise HTTPException(status_code=503, detail="Could not generate upload URL") from exc

    return SnapshotUploadUrlResponse(upload_url=upload_url, s3_key=s3_key)
