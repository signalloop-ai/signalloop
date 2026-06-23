from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from signalloop_api.ai_policy import DISALLOWED_TAGS
from signalloop_api.auth import get_current_super_admin
from signalloop_api.database import get_session
from signalloop_api.models import (
    AIInteraction,
    AssessmentAttempt,
    AssessmentPack,
    Employer,
    EvidenceReport,
    TestRun,
)
from signalloop_api.schemas import EmployerInfoResponse


router = APIRouter(prefix="/admin")


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _employer_summary_row(
    employer: Employer,
    invite_count: int,
    attempt_count: int,
    submitted_count: int,
    report_count: int,
    last_activity: Optional[datetime],
    avg_score: Optional[float],
) -> dict:
    return {
        "id": employer.id,
        "email": employer.email,
        "company_name": employer.company_name,
        "role": employer.role,
        "created_at": _utc_iso(employer.created_at),
        "last_activity_at": _utc_iso(last_activity),
        "invite_count": invite_count,
        "attempt_count": attempt_count,
        "submitted_count": submitted_count,
        "report_count": report_count,
        "avg_score": round(avg_score, 1) if avg_score is not None else None,
    }


@router.get("/me", response_model=EmployerInfoResponse)
def get_admin_info(
    admin: Employer = Depends(get_current_super_admin),
) -> EmployerInfoResponse:
    return EmployerInfoResponse(id=admin.id, email=admin.email, role=admin.role)


@router.get("/employers")
def list_employers(
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> list[dict]:
    employers = session.scalars(select(Employer).order_by(Employer.id)).all()

    attempt_counts = dict(
        session.execute(
            select(AssessmentAttempt.employer_id, func.count(AssessmentAttempt.id))
            .group_by(AssessmentAttempt.employer_id)
        ).all()
    )
    submitted_counts = dict(
        session.execute(
            select(AssessmentAttempt.employer_id, func.count(AssessmentAttempt.id))
            .where(AssessmentAttempt.status == "submitted")
            .group_by(AssessmentAttempt.employer_id)
        ).all()
    )
    report_counts = dict(
        session.execute(
            select(AssessmentAttempt.employer_id, func.count(EvidenceReport.id))
            .select_from(AssessmentAttempt)
            .join(EvidenceReport, EvidenceReport.attempt_id == AssessmentAttempt.id)
            .group_by(AssessmentAttempt.employer_id)
        ).all()
    )
    # Last activity = the most recent meaningful timestamp per employer (submission, then
    # attempt start, then invite creation) rather than just when the invite was created.
    last_activity_rows = session.execute(
        select(
            AssessmentAttempt.employer_id,
            func.max(
                func.coalesce(
                    AssessmentAttempt.submitted_at,
                    AssessmentAttempt.started_at,
                    AssessmentAttempt.created_at,
                )
            ).label("last_attempt"),
        ).group_by(AssessmentAttempt.employer_id)
    ).all()
    last_activity = {row.employer_id: row.last_attempt for row in last_activity_rows}

    avg_score_rows = session.execute(
        select(
            AssessmentAttempt.employer_id,
            func.avg(EvidenceReport.score_total).label("avg_score"),
        )
        .select_from(AssessmentAttempt)
        .join(EvidenceReport, EvidenceReport.attempt_id == AssessmentAttempt.id)
        .group_by(AssessmentAttempt.employer_id)
    ).all()
    avg_scores = {row.employer_id: float(row.avg_score) for row in avg_score_rows if row.avg_score is not None}

    result = []
    for emp in employers:
        ac = int(attempt_counts.get(emp.id, 0))
        sc = int(submitted_counts.get(emp.id, 0))
        rc = int(report_counts.get(emp.id, 0))
        result.append(
            _employer_summary_row(
                employer=emp,
                invite_count=ac,
                attempt_count=ac,
                submitted_count=sc,
                report_count=rc,
                last_activity=last_activity.get(emp.id) or emp.created_at,
                avg_score=avg_scores.get(emp.id),
            )
        )
    return result


@router.get("/employers/{employer_id}")
def get_employer_detail(
    employer_id: int,
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> dict:
    employer = session.get(Employer, employer_id)
    if employer is None:
        raise HTTPException(status_code=404, detail="Employer not found")

    attempts = session.scalars(
        select(AssessmentAttempt)
        .where(AssessmentAttempt.employer_id == employer_id)
        .order_by(AssessmentAttempt.id.desc())
    ).all()
    attempt_ids = [a.id for a in attempts]

    # Resolve everything attempts reference in a few grouped queries (no per-attempt N+1).
    pack_slug_by_id: dict[int, str] = {}
    pack_ids = {a.assessment_pack_id for a in attempts}
    if pack_ids:
        pack_slug_by_id = {
            p.id: p.slug
            for p in session.scalars(select(AssessmentPack).where(AssessmentPack.id.in_(pack_ids))).all()
        }

    report_by_attempt: dict[int, EvidenceReport] = {}
    if attempt_ids:
        report_by_attempt = {
            er.attempt_id: er
            for er in session.scalars(select(EvidenceReport).where(EvidenceReport.attempt_id.in_(attempt_ids))).all()
        }

    # AI usage: count the candidate's prompts (not the assistant echoes) and the assistant
    # replies that carried a real policy violation. Each candidate turn stores two rows
    # (candidate + assistant) with the same tags, so counting one role per metric avoids
    # double-counting.
    ai_message_count = 0
    ai_violation_count = 0
    if attempt_ids:
        for ai in session.scalars(select(AIInteraction).where(AIInteraction.attempt_id.in_(attempt_ids))).all():
            if ai.role == "candidate":
                ai_message_count += 1
            elif ai.role == "assistant" and ai.policy_tags and any(t in DISALLOWED_TAGS for t in ai.policy_tags):
                ai_violation_count += 1

    # Stuck signal: runs that failed to execute (infra error or timeout), not ordinary test
    # failures, which are a normal part of the work.
    execution_errors = 0
    if attempt_ids:
        execution_errors = sum(
            1
            for tr in session.scalars(select(TestRun).where(TestRun.attempt_id.in_(attempt_ids))).all()
            if tr.status in ("error", "timeout")
        )

    status_counts: dict[str, int] = {}
    pack_counts: dict[str, int] = {}
    for a in attempts:
        status_counts[a.status] = status_counts.get(a.status, 0) + 1
        slug = pack_slug_by_id.get(a.assessment_pack_id)
        if slug:
            pack_counts[slug] = pack_counts.get(slug, 0) + 1

    scores = [er.score_total for er in report_by_attempt.values() if er.score_total is not None]
    score_distribution: dict[str, Optional[float]] = {
        "average": round(sum(scores) / len(scores), 1) if scores else None,
        "median": sorted(scores)[len(scores) // 2] if scores else None,
        "min": min(scores) if scores else None,
        "max": max(scores) if scores else None,
    }

    missing_reports = sum(
        1 for a in attempts if a.status == "submitted" and a.id not in report_by_attempt
    )

    attempt_list = []
    for a in attempts:
        er = report_by_attempt.get(a.id)
        attempt_list.append({
            "id": a.id,
            "candidate_email": a.candidate_email,
            "assessment_pack_slug": pack_slug_by_id.get(a.assessment_pack_id),
            "status": a.status,
            "created_at": _utc_iso(a.created_at),
            "submitted_at": _utc_iso(a.submitted_at),
            "score_total": er.score_total if er else None,
            "recommendation": er.recommendation if er else None,
            "report_id": er.id if er else None,
        })

    return {
        "id": employer.id,
        "email": employer.email,
        "company_name": employer.company_name,
        "role": employer.role,
        "created_at": _utc_iso(employer.created_at),
        "invite_count": len(attempts),
        "attempt_count": len(attempts),
        "submitted_count": status_counts.get("submitted", 0),
        "report_count": len(report_by_attempt),
        "status_breakdown": status_counts,
        "score_distribution": score_distribution,
        "ai_usage": {
            "total_messages": ai_message_count,
            "total_violations": ai_violation_count,
        },
        "pack_breakdown": pack_counts,
        "stuck_signals": {
            "execution_errors": execution_errors,
            "missing_reports": missing_reports,
        },
        "attempts": attempt_list,
    }


@router.get("/attempts/{attempt_id}/report")
def get_admin_evidence_report(
    attempt_id: int,
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> dict:
    evidence_report = session.scalar(
        select(EvidenceReport).where(EvidenceReport.attempt_id == attempt_id)
    )
    if evidence_report is None:
        raise HTTPException(status_code=404, detail="Evidence report not found")
    return {
        "attempt_id": evidence_report.attempt_id,
        "report_id": evidence_report.id,
        "recommendation": evidence_report.recommendation,
        "score_total": evidence_report.score_total,
        "report": evidence_report.report,
    }
