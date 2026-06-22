from pathlib import Path
from secrets import token_urlsafe
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from re import findall
from time import monotonic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

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
        "duration_minutes": 60,
        "seeded_issue_count": 5,
        "seeded_issue_areas": [
            "duplicate email (case-insensitive + whitespace trimming)",
            "blank or whitespace-only task title (with title trimming)",
            "owner-only read and delete access",
            "unknown actor access (resource existence leakage)",
            "status transition enforcement (TODO -> IN_PROGRESS -> DONE)",
        ],
        # Tests that fail on unmodified starter — used for public issue scoring.
        "initially_failing_tests": [
            "test_duplicate_user_email_is_rejected",
            "test_blank_task_title_is_rejected",
            "test_non_owner_cannot_read_task",
        ],
        # Hidden + enhancement tests used for feature/design scoring.
        "feature_design_tests": [
            "test_due_date_is_optional_and_returned",
            "test_tasks_can_be_listed_by_owner",
            "test_due_date_rejects_invalid_format",
            "test_task_listing_is_filtered_and_ordered_by_id",
        ],
    },
    "fastapi_task_api_advanced_v1": {
        "title": "FastAPI Team Task API Deep Debugging, Authorization & Enhancement Assessment",
        "version": "advanced_v1",
        "candidate_path": "assessment_packs/fastapi_task_api_advanced_v1/candidate",
        "evaluator_path": "assessment_packs/fastapi_task_api_advanced_v1/evaluator",
        "duration_minutes": 120,
        "seeded_issue_count": 7,
        "seeded_issue_areas": [
            "partial task update preserves omitted fields",
            "team lead permissions scoped to own team only",
            "archived tasks hidden from team and user lists",
            "comment actor requires task access",
            "partial update authorization enforced for non-owner/non-assignee",
            "membership role validation (no invalid roles accepted)",
            "status transition enforcement (TODO -> IN_PROGRESS -> DONE)",
        ],
        # Tests that fail on unmodified starter — used for public issue scoring.
        "initially_failing_tests": [
            "test_patch_task_preserves_omitted_fields",
            "test_team_lead_cannot_access_unrelated_team_task",
            "test_archived_tasks_are_excluded_from_team_lists",
            "test_comment_requires_task_access",
        ],
        # Hidden + enhancement tests used for feature/design scoring.
        "feature_design_tests": [
            "test_task_can_block_another_task",
            "test_team_activity_feed_returns_events",
            "test_blocker_prevents_in_progress_transition",
            "test_dependency_cycle_is_rejected",
            "test_activity_feed_is_paginated_and_team_scoped",
        ],
        # Pack-specific rubric — overrides global RUBRIC in reports.py.
        "rubric": {
            "public_issue_resolution": 15,
            "private_issue_generalization": 15,
            "feature_design_implementation": 25,
            "candidate_tests": 15,
            "ai_collaboration": 15,
            "regression_code_quality": 15,
        },
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
        evaluator_feedback_mode=attempt.evaluator_feedback_mode,
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
    timing_note = "" if attempt.timing_mode == "timed" else " (recommended, not enforced)"
    subs = {"DURATION_MINUTES": str(attempt.duration_minutes), "TIMING_NOTE": timing_note} if attempt.duration_minutes else {}
    starter_files = load_candidate_files(resolve_repo_path(pack.candidate_path), subs)
    files = snapshot.files if snapshot is not None else starter_files
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
        evaluator_feedback_mode=attempt.evaluator_feedback_mode,
        duration_minutes=attempt.duration_minutes,
        started_at=utc_isoformat(attempt.started_at),
        expires_at=utc_isoformat(attempt.expires_at),
        submitted_at=utc_isoformat(attempt.submitted_at),
        submission_mode=attempt.submission_mode,
        files=files,
        initial_files=starter_files,
    )


@router.post("/assessment-attempts", response_model=CreateAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_assessment_attempt(
    payload: CreateAttemptRequest,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> CreateAttemptResponse:
    pack_slug = PACK_BY_ASSESSMENT_LEVEL[payload.assessment_level]
    pack = get_or_create_assessment_pack(session, pack_slug)
    duration_minutes = payload.duration_minutes or DEFAULT_PACKS.get(pack_slug, {}).get("duration_minutes", 90)
    timing_note = "" if payload.timing_mode == "timed" else " (recommended, not enforced)"
    subs = {"DURATION_MINUTES": str(duration_minutes), "TIMING_NOTE": timing_note}
    files = load_candidate_files(resolve_repo_path(pack.candidate_path), subs)
    attempt = AssessmentAttempt(
        employer_id=current_employer.id,
        assessment_pack_id=pack.id,
        assessment_level=payload.assessment_level,
        timing_mode=payload.timing_mode,
        evaluator_feedback_mode=payload.evaluator_feedback_mode,
        duration_minutes=duration_minutes,
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
            "evaluator_feedback_mode": attempt.evaluator_feedback_mode,
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


def parse_failure_names(result: dict | None) -> set[str]:
    if result is None:
        return set()
    output = "\n".join(part for part in [result.get("stdout") or "", result.get("stderr") or ""] if part)
    return set(findall(r"_{2,}\s+([a-zA-Z0-9_]+)\s+_{2,}", output))


def enhancement_summary(result: dict | None, feature_design_tests: list[str]) -> dict:
    if not feature_design_tests or result is None or result.get("status") == "error":
        return {"passed": 0, "failed": 0, "collected": 0}
    failure_names = parse_failure_names(result)
    passed = sum(1 for t in feature_design_tests if t not in failure_names)
    collected = len(feature_design_tests)
    return {"passed": passed, "failed": collected - passed, "collected": collected}


def public_evaluator_summary(result: dict | None) -> dict | None:
    if result is None:
        return None
    output = "\n".join(part for part in [result.get("stdout") or "", result.get("stderr") or ""] if part)
    collected_match = findall(r"collected (\d+) items?", output)
    passed_match = findall(r"(\d+) passed", output)
    failed = len(parse_failure_names(result))
    collected = int(collected_match[-1]) if collected_match else failed
    passed = int(passed_match[-1]) if passed_match else max(collected - failed, 0)
    if result.get("status") == "passed" and collected == 0:
        collected = 1
        passed = 1
    return {
        "mode": "guided",
        "status": result.get("status", "error"),
        "collected": collected,
        "passed": passed,
        "failed": max(collected - passed, failed),
        "details_hidden": True,
    }


def merge_timing(result: dict, key: str, value_ms: int) -> None:
    timings = dict(result.get("timings") or {})
    timings[key] = value_ms
    result["timings"] = timings


@router.post("/candidate/invites/{invite_token}/run-public-tests")
def run_public_tests(
    invite_token: str,
    payload: SaveSnapshotRequest,
    session: Session = Depends(get_session),
) -> dict:
    api_started = monotonic()
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
    snapshot_saved = monotonic()

    provider = get_execution_provider()
    from signalloop_api.submissions import hidden_test_files_for_attempt
    hidden_tests = hidden_test_files_for_attempt(attempt)

    # Run public and evaluator tests concurrently — both take the same input
    # and are independent, so there's no reason to wait for one before starting
    # the other (each ECS cold start is ~45s).
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_public = pool.submit(provider.run_public, payload.files)
        f_hidden = pool.submit(provider.run_hidden, payload.files, hidden_tests)
        try:
            result = f_public.result()
        except Exception as exc:
            result = execution_error_result(str(exc))
        try:
            evaluator_result = f_hidden.result()
        except Exception as exc:
            evaluator_result = execution_error_result(str(exc))

    public_completed = monotonic()
    merge_timing(result, "api_preflight_ms", int((snapshot_saved - api_started) * 1000))
    merge_timing(result, "api_public_execution_ms", int((public_completed - snapshot_saved) * 1000))

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

    pack_config = DEFAULT_PACKS.get(attempt.assessment_pack.slug, {})
    result["enhancement_feedback"] = enhancement_summary(
        evaluator_result, pack_config.get("feature_design_tests", [])
    )

    evaluator_feedback = None
    if attempt.evaluator_feedback_mode == "guided":
        guided_test_run = TestRun(
            attempt_id=attempt.id,
            code_snapshot_id=snapshot.id,
            run_type="guided_hidden",
            status=evaluator_result.get("status", "error"),
            results=evaluator_result,
            stdout=evaluator_result.get("stdout", ""),
            stderr=evaluator_result.get("stderr", ""),
            duration_ms=evaluator_result.get("duration_ms", 0),
        )
        session.add(guided_test_run)
        evaluator_feedback = public_evaluator_summary(evaluator_result)
        result["evaluator_feedback"] = evaluator_feedback

    record_audit_event(
        session,
        "test_run.public",
        actor_type="candidate",
        attempt_id=attempt.id,
        event_metadata={
            "status": result.get("status"),
            "evaluator_feedback_mode": attempt.evaluator_feedback_mode,
            "evaluator_feedback_status": evaluator_feedback.get("status") if evaluator_feedback else None,
        },
    )
    session.commit()
    persisted = monotonic()
    merge_timing(result, "api_persist_ms", int((persisted - public_completed) * 1000))
    merge_timing(result, "api_total_ms", int((persisted - api_started) * 1000))
    test_run.results = result
    flag_modified(test_run, "results")
    session.add(test_run)
    session.commit()

    return result
