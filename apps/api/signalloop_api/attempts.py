from pathlib import Path
from secrets import token_urlsafe
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from signalloop_api.assessment_files import load_candidate_files
from signalloop_api.audit import record_audit_event
from signalloop_api.config import settings
from signalloop_api.database import get_session
from signalloop_api.execution import execution_error_result, get_execution_provider
from signalloop_api.models import AssessmentAttempt, AssessmentPack, CodeSnapshot, TestRun
from signalloop_api.schemas import (
    AssessmentMetadata,
    CandidateAttemptResponse,
    CreateAttemptRequest,
    CreateAttemptResponse,
    EmployerAttemptSummary,
    SaveSnapshotRequest,
    SnapshotResponse,
)


router = APIRouter()

DEFAULT_PACKS = {
    "fastapi_task_api_v1": {
        "title": "FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment",
        "version": "v1",
        "candidate_path": "assessment_packs/fastapi_task_api_v1/candidate",
        "evaluator_path": "assessment_packs/fastapi_task_api_v1/evaluator",
        "seeded_issue_count": 6,
        # Tests that fail on the unmodified starter code — used for public test scoring.
        # Tests NOT in this list are assumed to pass initially and are used for regression scoring.
        "initially_failing_tests": [
            "test_duplicate_user_email_is_rejected",
            "test_blank_task_title_is_rejected",
        ],
    }
}


def resolve_repo_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    return (settings.repo_root / path).resolve()


def get_or_create_assessment_pack(session: Session, slug: str) -> AssessmentPack:
    existing = session.scalar(select(AssessmentPack).where(AssessmentPack.slug == slug))
    if existing is not None:
        return existing

    pack_config = DEFAULT_PACKS.get(slug)
    if pack_config is None:
        raise HTTPException(status_code=404, detail="Assessment pack not found")

    candidate_path = resolve_repo_path(pack_config["candidate_path"])
    evaluator_path = resolve_repo_path(pack_config["evaluator_path"])
    if not candidate_path.is_dir():
        raise HTTPException(status_code=500, detail="Candidate pack path is not available")
    if not evaluator_path.is_dir():
        raise HTTPException(status_code=500, detail="Evaluator pack path is not available")

    pack = AssessmentPack(
        slug=slug,
        title=pack_config["title"],
        version=pack_config["version"],
        candidate_path=str(candidate_path),
        evaluator_path=str(evaluator_path),
        is_active=True,
    )
    session.add(pack)
    session.flush()
    return pack


def build_invite_url(invite_token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/invite/{invite_token}"


def generate_unique_invite_token(session: Session) -> str:
    for _ in range(5):
        token = token_urlsafe(32)
        exists = session.scalar(select(AssessmentAttempt.id).where(AssessmentAttempt.invite_token == token))
        if exists is None:
            return token
    raise HTTPException(status_code=500, detail="Could not generate invite token")


def attempt_summary(attempt: AssessmentAttempt) -> EmployerAttemptSummary:
    pack = attempt.assessment_pack
    report = attempt.evidence_report
    return EmployerAttemptSummary(
        attempt_id=attempt.id,
        candidate_email=attempt.candidate_email,
        status=attempt.status,
        invite_token=attempt.invite_token,
        invite_url=build_invite_url(attempt.invite_token),
        assessment=AssessmentMetadata(
            slug=pack.slug,
            title=pack.title,
            version=pack.version,
            seeded_issue_count=DEFAULT_PACKS.get(pack.slug, {}).get("seeded_issue_count", 0),
        ),
        created_at=attempt.created_at.isoformat(),
        submitted_at=attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        report_id=report.id if report else None,
        recommendation=report.recommendation if report else None,
        score_total=report.score_total if report else None,
    )


@router.post("/assessment-attempts", response_model=CreateAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_assessment_attempt(
    payload: CreateAttemptRequest,
    session: Session = Depends(get_session),
) -> CreateAttemptResponse:
    pack = get_or_create_assessment_pack(session, payload.assessment_pack_slug)
    files = load_candidate_files(resolve_repo_path(pack.candidate_path))
    attempt = AssessmentAttempt(
        employer_id=payload.employer_id,
        assessment_pack_id=pack.id,
        candidate_email=str(payload.candidate_email) if payload.candidate_email else None,
        invite_token=generate_unique_invite_token(session),
        status="created",
    )
    session.add(attempt)
    session.flush()

    initial_snapshot = CodeSnapshot(attempt_id=attempt.id, kind="initial", files=files)
    session.add(initial_snapshot)
    record_audit_event(
        session,
        "attempt.created",
        actor_type="employer",
        attempt_id=attempt.id,
        event_metadata={
            "candidate_email_present": attempt.candidate_email is not None,
            "assessment_pack_slug": pack.slug,
        },
    )

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Attempt could not be created") from exc

    session.refresh(attempt)
    return CreateAttemptResponse(
        attempt_id=attempt.id,
        invite_token=attempt.invite_token,
        invite_url=build_invite_url(attempt.invite_token),
        status=attempt.status,
    )


@router.get("/assessment-attempts", response_model=list[EmployerAttemptSummary])
def list_assessment_attempts(session: Session = Depends(get_session)) -> list[EmployerAttemptSummary]:
    attempts = session.scalars(
        select(AssessmentAttempt).order_by(AssessmentAttempt.id.desc())
    ).all()
    return [attempt_summary(attempt) for attempt in attempts]


@router.get("/candidate/invites/{invite_token}", response_model=CandidateAttemptResponse)
def open_candidate_invite(
    invite_token: str,
    session: Session = Depends(get_session),
) -> CandidateAttemptResponse:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")

    if attempt.status == "created":
        attempt.status = "opened"
        attempt.started_at = datetime.now(timezone.utc)
        record_audit_event(session, "attempt.opened", actor_type="candidate", attempt_id=attempt.id)
        session.commit()
        session.refresh(attempt)

    pack = attempt.assessment_pack
    latest_snapshot = session.scalar(
        select(CodeSnapshot)
        .where(CodeSnapshot.attempt_id == attempt.id)
        .order_by(CodeSnapshot.id.desc())
        .limit(1)
    )
    files = latest_snapshot.files if latest_snapshot is not None else load_candidate_files(resolve_repo_path(pack.candidate_path))
    return CandidateAttemptResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        candidate_email=attempt.candidate_email,
        assessment=AssessmentMetadata(
            slug=pack.slug,
            title=pack.title,
            version=pack.version,
            seeded_issue_count=DEFAULT_PACKS.get(pack.slug, {}).get("seeded_issue_count", 0),
        ),
        files=files,
    )


@router.post("/candidate/invites/{invite_token}/snapshots", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
def save_candidate_snapshot(
    invite_token: str,
    payload: SaveSnapshotRequest,
    session: Session = Depends(get_session),
) -> SnapshotResponse:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Attempt is already submitted")

    if attempt.status in {"created", "opened"}:
        attempt.status = "in_progress"

    snapshot = CodeSnapshot(attempt_id=attempt.id, kind=payload.kind, files=payload.files)
    session.add(snapshot)
    record_audit_event(
        session,
        "snapshot.saved",
        actor_type="candidate",
        attempt_id=attempt.id,
        event_metadata={"kind": payload.kind, "file_count": len(payload.files)},
    )
    session.commit()
    session.refresh(snapshot)
    session.refresh(attempt)

    return SnapshotResponse(
        snapshot_id=snapshot.id,
        attempt_id=attempt.id,
        kind=snapshot.kind,
        status=attempt.status,
    )


@router.post("/candidate/invites/{invite_token}/run-public-tests")
def run_public_tests(
    invite_token: str,
    payload: SaveSnapshotRequest,
    session: Session = Depends(get_session),
) -> dict:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Attempt is already submitted")

    if attempt.status in {"created", "opened"}:
        attempt.status = "in_progress"

    snapshot = CodeSnapshot(attempt_id=attempt.id, kind="public_test_run", files=payload.files)
    session.add(snapshot)
    session.flush()

    try:
        result = get_execution_provider().run_public(payload.files)
    except Exception as exc:
        result = execution_error_result(str(exc))

    test_run = TestRun(
        attempt_id=attempt.id,
        code_snapshot_id=snapshot.id,
        run_type="public",
        status=result.get("status", "error"),
        results=result,
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        duration_ms=result.get("duration_ms", 0),
    )
    session.add(test_run)
    record_audit_event(
        session,
        "test_run.public",
        actor_type="candidate",
        attempt_id=attempt.id,
        event_metadata={"status": result.get("status")},
    )
    session.commit()

    return result
