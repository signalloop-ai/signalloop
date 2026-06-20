from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.assessment_files import load_hidden_test_files
from signalloop_api.attempts import DEFAULT_PACKS, resolve_repo_path
from signalloop_api.audit import record_audit_event
from signalloop_api.database import get_session
from signalloop_api.execution import HTTPWorkerExecutionProvider, execution_error_result
from signalloop_api.models import AssessmentAttempt, CodeSnapshot, FinalSubmission, TestRun
from signalloop_api.schemas import FinalSubmissionRequest, FinalSubmissionResponse
from signalloop_api.timebox import attempt_is_expired


router = APIRouter()
logger = logging.getLogger(__name__)


class HiddenTestRunner(Protocol):
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        ...


class HTTPHiddenTestRunner:
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        return HTTPWorkerExecutionProvider().run_hidden(files, hidden_tests)


class ExecutionProviderHiddenTestRunner:
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        from signalloop_api.execution import get_execution_provider

        return get_execution_provider().run_hidden(files, hidden_tests)


def get_hidden_test_runner() -> HiddenTestRunner:
    return ExecutionProviderHiddenTestRunner()


def hidden_test_error_result(message: str) -> dict:
    return execution_error_result(message)


def hidden_test_files_for_attempt(attempt: AssessmentAttempt) -> dict[str, str]:
    pack_config = DEFAULT_PACKS.get(attempt.assessment_pack.slug)
    configured_path = pack_config.get("evaluator_path") if pack_config else None
    if configured_path:
        evaluator_path = resolve_repo_path(configured_path)
        if evaluator_path.is_dir():
            hidden_tests = load_hidden_test_files(evaluator_path)
            logger.info(
                "Loaded hidden tests from configured pack path",
                extra={
                    "attempt_id": attempt.id,
                    "assessment_pack_slug": attempt.assessment_pack.slug,
                    "hidden_test_count": len(hidden_tests),
                },
            )
            return hidden_tests
        logger.warning(
            "Configured evaluator path is unavailable; falling back to stored assessment pack path",
            extra={
                "attempt_id": attempt.id,
                "assessment_pack_slug": attempt.assessment_pack.slug,
                "configured_evaluator_path": str(evaluator_path),
            },
        )

    evaluator_path = resolve_repo_path(attempt.assessment_pack.evaluator_path)
    hidden_tests = load_hidden_test_files(Path(evaluator_path))
    logger.info(
        "Loaded hidden tests from stored assessment pack path",
        extra={
            "attempt_id": attempt.id,
            "assessment_pack_slug": attempt.assessment_pack.slug,
            "hidden_test_count": len(hidden_tests),
        },
    )
    return hidden_tests


def persist_hidden_test_run(
    session: Session,
    attempt: AssessmentAttempt,
    snapshot: CodeSnapshot,
    result: dict,
) -> TestRun:
    test_run = TestRun(
        attempt_id=attempt.id,
        code_snapshot_id=snapshot.id,
        run_type="hidden",
        status=str(result.get("status", "error")),
        results=result,
        stdout=result.get("stdout"),
        stderr=result.get("stderr"),
        duration_ms=result.get("duration_ms"),
    )
    session.add(test_run)
    session.commit()
    session.refresh(test_run)
    return test_run


@router.post(
    "/candidate/invites/{invite_token}/submit",
    response_model=FinalSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_final_attempt(
    invite_token: str,
    payload: FinalSubmissionRequest,
    session: Session = Depends(get_session),
    hidden_test_runner: HiddenTestRunner = Depends(get_hidden_test_runner),
) -> FinalSubmissionResponse:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted" or attempt.final_submission is not None:
        raise HTTPException(status_code=409, detail="Final submission is immutable")

    submitted_at = datetime.now(timezone.utc)
    submission_mode = "auto_expired" if payload.submission_mode == "auto_expired" or attempt_is_expired(attempt, submitted_at) else "manual"
    snapshot = CodeSnapshot(attempt_id=attempt.id, kind="final_submission", files=payload.files)
    session.add(snapshot)
    session.flush()

    final_submission = FinalSubmission(
        attempt_id=attempt.id,
        code_snapshot_id=snapshot.id,
        final_explanation=payload.final_explanation,
        decision_log=payload.decision_log,
        submitted_at=submitted_at,
    )
    attempt.status = "submitted"
    attempt.submitted_at = submitted_at
    attempt.submission_mode = submission_mode
    session.add(final_submission)
    record_audit_event(
        session,
        "submission.created",
        actor_type="candidate",
        attempt_id=attempt.id,
        event_metadata={"file_count": len(payload.files), "submission_mode": submission_mode},
    )
    session.commit()
    session.refresh(snapshot)
    session.refresh(final_submission)
    session.refresh(attempt)

    try:
        hidden_tests = hidden_test_files_for_attempt(attempt)
        logger.info(
            "Starting hidden evaluation",
            extra={
                "attempt_id": attempt.id,
                "hidden_test_count": len(hidden_tests),
                "file_count": len(payload.files),
            },
        )
        hidden_result = hidden_test_runner.run(payload.files, hidden_tests)
        logger.info(
            "Hidden evaluation completed",
            extra={
                "attempt_id": attempt.id,
                "hidden_status": hidden_result.get("status"),
                "duration_ms": hidden_result.get("duration_ms"),
            },
        )
    except Exception as exc:
        logger.exception(
            "Hidden evaluation failed before result persistence",
            extra={"attempt_id": attempt.id},
        )
        hidden_result = hidden_test_error_result(str(exc))

    hidden_test_run = persist_hidden_test_run(session, attempt, snapshot, hidden_result)
    record_audit_event(
        session,
        "hidden_tests.completed",
        actor_type="system",
        attempt_id=attempt.id,
        event_metadata={"status": hidden_test_run.status, "test_run_id": hidden_test_run.id},
    )
    session.commit()

    return FinalSubmissionResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        submission_id=final_submission.id,
        snapshot_id=snapshot.id,
        hidden_test_run_id=hidden_test_run.id,
        hidden_test_status=hidden_test_run.status,
    )
