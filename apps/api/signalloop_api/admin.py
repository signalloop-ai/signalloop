from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from signalloop_api.auth import get_current_super_admin
from signalloop_api.database import get_session
from signalloop_api.models import (
    AIInteraction,
    AssessmentAttempt,
    AssessmentPack,
    CodeSnapshot,
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
    last_activity_rows = session.execute(
        select(
            AssessmentAttempt.employer_id,
            func.max(AssessmentAttempt.created_at).label("last_attempt"),
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

    status_counts: dict[str, int] = {}
    for a in attempts:
        s = a.status if a.status in ("in_progress", "submitted", "expired", "created", "opened") else "other"
        status_counts[s] = status_counts.get(s, 0) + 1

    pack_counts: dict[str, int] = {}
    for a in attempts:
        pack = session.get(AssessmentPack, a.assessment_pack_id)
        if pack:
            pack_counts[pack.slug] = pack_counts.get(pack.slug, 0) + 1

    submitted_ids = [a.id for a in attempts if a.status == "submitted"]
    scores: list[int] = []
    if submitted_ids:
        report_rows = session.scalars(
            select(EvidenceReport).where(EvidenceReport.attempt_id.in_(submitted_ids))
        ).all()
        scores = [r.score_total for r in report_rows if r.score_total is not None]

    score_distribution: dict[str, Optional[float]] = {
        "average": round(sum(scores) / len(scores), 1) if scores else None,
        "median": sorted(scores)[len(scores) // 2] if scores else None,
        "min": min(scores) if scores else None,
        "max": max(scores) if scores else None,
    }

    ai_msg_count = 0
    ai_violation_count = 0
    failed_test_runs = 0
    missing_reports = 0
    for a in attempts:
        ai_rows = session.scalars(
            select(AIInteraction).where(AIInteraction.attempt_id == a.id)
        ).all()
        ai_msg_count += len(ai_rows)
        for ai in ai_rows:
            if ai.policy_tags and any("violation" in (t or "") or "injection" in (t or "") for t in ai.policy_tags):
                ai_violation_count += 1

        tr_rows = session.scalars(
            select(TestRun).where(TestRun.attempt_id == a.id)
        ).all()
        failed_test_runs += sum(1 for tr in tr_rows if tr.status == "error")

        if a.status == "submitted":
            er = session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == a.id))
            if er is None:
                missing_reports += 1

    attempt_list = []
    for a in attempts:
        er = session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == a.id))
        pack = session.get(AssessmentPack, a.assessment_pack_id)
        attempt_list.append({
            "id": a.id,
            "candidate_email": a.candidate_email,
            "assessment_pack_slug": pack.slug if pack else None,
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
        "report_count": sum(1 for a in attempts if session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == a.id))),
        "status_breakdown": status_counts,
        "score_distribution": score_distribution,
        "ai_usage": {
            "total_messages": ai_msg_count,
            "total_violations": ai_violation_count,
        },
        "pack_breakdown": pack_counts,
        "stuck_signals": {
            "failed_test_runs": failed_test_runs,
            "error_attempts": sum(1 for a in attempts if a.status == "error"),
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
