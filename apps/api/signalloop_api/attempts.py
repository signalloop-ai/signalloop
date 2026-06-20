from pathlib import Path
from secrets import token_urlsafe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from signalloop_api.assessment_files import load_candidate_files
from signalloop_api.auth import get_current_employer
from signalloop_api.audit import record_audit_event
from signalloop_api.config import settings
from signalloop_api.database import get_session
from signalloop_api.execution import execution_error_result, get_execution_provider
from signalloop_api.models import AssessmentAttempt, AssessmentPack, CodeSnapshot, Employer, TestRun
from signalloop_api.schemas import (
    AssessmentMetadata,
    CandidateAttemptResponse,
    CreateAttemptRequest,
    CreateAttemptResponse,
    EmployerAttemptSummary,
    SaveSnapshotRequest,
    SnapshotResponse,
)
from signalloop_api.timebox import enforce_not_expired, latest_snapshot, start_attempt_if_needed


router = APIRouter()

DEFAULT_PACKS = {
    "fastapi_task_api_v1": {
        "title": "FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment",
        "version": "v1",
        "candidate_path": "assessment_packs/fastapi_task_api_v1/candidate",
        "evaluator_path": "assessment_packs/fastapi_task_api_v1/evaluator",
        "seeded_issue_count": 6,
        "seeded_issue_areas": [
            "duplicate email handling",
            "empty or whitespace-only task title",
            "invalid status transitions",
            "ownership/access behavior",
            "delete behavior",
        ],
        # Tests that fail on the unmodified starter code — used for public test scoring.
        # Tests NOT in this list are assumed to pass initially and are used for regression scoring.
        "initially_failing_tests": [
            "test_duplicate_user_email_is_rejected",
            "test_blank_task_title_is_rejected",
        ],
        "feature_design_tests": [
            "test_only_owner_can_read_or_delete_task",
            "test_status_values_and_transitions_are_enforced",
        ],
    },
    "fastapi_task_api_standard_v2": {
        "title": "FastAPI Backend Debugging, Hardening & Product Tradeoff Assessment",
        "version": "standard_v2",
        "candidate_path": "assessment_packs/fastapi_task_api_standard_v2/candidate",
        "evaluator_path": "assessment_packs/fastapi_task_api_standard_v2/evaluator",
        "seeded_issue_count": 7,
        "seeded_issue_areas": [
            "duplicate email (case-insensitive + whitespace trimming)",
            "blank or whitespace-only task title (with title trimming)",
            "task priority defaulting, normalization, and validation",
            "owner-only read and delete access",
            "unknown actor access (resource existence leakage)",
            "status transition enforcement (TODO -> IN_PROGRESS -> DONE)",
            "idempotent owner delete (second delete returns 404)",
        ],
        "initially_failing_tests": [
            "test_duplicate_user_email_is_rejected",
            "test_blank_task_title_is_rejected",
            "test_task_priority_defaults_and_accepts_high",
            "test_non_owner_cannot_read_task",
        ],
        "feature_design_tests": [
            "test_task_priority_defaults_and_accepts_high",
            "test_task_priority_is_defaulted_normalized_and_validated",
            "test_non_owner_cannot_read_task",
            "test_only_owner_can_read_or_delete_task",
            "test_status_values_and_transitions_are_enforced",
        ],
    },
    "fastapi_task_api_advanced_v1": {
        "title": "FastAPI Team Task API Deep Debugging, Authorization & Product Judgment Assessment",
        "version": "advanced_v1",
        "candidate_path": "assessment_packs/fastapi_task_api_advanced_v1/candidate",
        "evaluator_path": "assessment_packs/fastapi_task_api_advanced_v1/evaluator",
        "seeded_issue_count": 9,
        "seeded_issue_areas": [
            "email normalization and duplicate user detection",
            "team membership duplicate handling and role validation",
            "team lead permissions scoped to own team",
            "partial task update preserves omitted fields",
            "status transition and completion-context behavior",
            "task audit events are complete and accurate",
            "archived tasks are hidden from default lists",
            "pagination and sorting are deterministic",
            "comment actor validation and task access",
        ],
        "initially_failing_tests": [
            "test_duplicate_user_email_is_normalized_and_rejected",
            "test_patch_task_preserves_omitted_fields",
            "test_archived_tasks_are_excluded_from_team_lists",
            "test_status_transition_requires_in_progress_before_done",
            "test_team_lead_cannot_access_unrelated_team_task",
        ],
        "feature_design_tests": [
            "test_membership_role_is_validated_and_duplicates_conflict",
            "test_team_lead_access_is_limited_to_own_team",
            "test_partial_update_preserves_description_and_assignee",
            "test_status_transition_and_audit_events_are_complete",
            "test_archived_task_is_hidden_and_second_delete_is_not_found",
            "test_comment_actor_must_have_task_access",
            "test_team_task_list_is_deterministically_sorted_and_paginated",
        ],
    },
}

PACK_BY_ASSESSMENT_LEVEL = {
    "standard": "fastapi_task_api_standard_v2",
    "advanced": "fastapi_task_api_advanced_v1",
}


def utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


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
        assessment_level=attempt.assessment_level,
        timing_mode=attempt.timing_mode,
        duration_minutes=attempt.duration_minutes,
        expires_at=utc_isoformat(attempt.expires_at),
        submission_mode=attempt.submission_mode,
        created_at=utc_isoformat(attempt.created_at) or "",
        submitted_at=utc_isoformat(attempt.submitted_at),
        report_id=report.id if report else None,
        recommendation=report.recommendation if report else None,
        score_total=report.score_total if report else None,
    )


def candidate_attempt_response(session: Session, attempt: AssessmentAttempt) -> CandidateAttemptResponse:
    pack = attempt.assessment_pack
    snapshot = latest_snapshot(session, attempt)
    files = snapshot.files if snapshot is not None else load_candidate_files(resolve_repo_path(pack.candidate_path))
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
        timing_mode=attempt.timing_mode,
        duration_minutes=attempt.duration_minutes,
        started_at=utc_isoformat(attempt.started_at),
        expires_at=utc_isoformat(attempt.expires_at),
        submitted_at=utc_isoformat(attempt.submitted_at),
        submission_mode=attempt.submission_mode,
        files=files,
    )


@router.post("/assessment-attempts", response_model=CreateAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_assessment_attempt(
    payload: CreateAttemptRequest,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> CreateAttemptResponse:
    pack_slug = PACK_BY_ASSESSMENT_LEVEL[payload.assessment_level]
    pack = get_or_create_assessment_pack(session, pack_slug)
    files = load_candidate_files(resolve_repo_path(pack.candidate_path))
    attempt = AssessmentAttempt(
        employer_id=current_employer.id,
        assessment_pack_id=pack.id,
        assessment_level=payload.assessment_level,
        timing_mode=payload.timing_mode,
        duration_minutes=payload.duration_minutes or 90,
        expires_at=None,
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
            "assessment_level": attempt.assessment_level,
            "timing_mode": attempt.timing_mode,
            "duration_minutes": attempt.duration_minutes,
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
def list_assessment_attempts(
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> list[EmployerAttemptSummary]:
    attempts = session.scalars(
        select(AssessmentAttempt)
        .where(AssessmentAttempt.employer_id == current_employer.id)
        .order_by(AssessmentAttempt.id.desc())
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

    return candidate_attempt_response(session, attempt)


@router.post("/candidate/invites/{invite_token}/accept", response_model=CandidateAttemptResponse)
def accept_candidate_invite(
    invite_token: str,
    session: Session = Depends(get_session),
) -> CandidateAttemptResponse:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        return candidate_attempt_response(session, attempt)

    start_attempt_if_needed(session, attempt)
    session.commit()
    session.refresh(attempt)
    return candidate_attempt_response(session, attempt)


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
    enforce_not_expired(session, attempt)

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
    enforce_not_expired(session, attempt)

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
