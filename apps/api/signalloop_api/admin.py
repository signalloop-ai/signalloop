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
    QuestionBankQuestion,
    QuestionSource,
    TestRun,
)
from signalloop_api.question_bank_seed import APPROVED_SOURCES, SEED_QUESTIONS
from signalloop_api.question_bank_ingestion import import_approved_source_questions
from signalloop_api.schemas import (
    EmployerInfoResponse,
    QuestionBankImportResponse,
    QuestionBankQuestionResponse,
    QuestionBankQuestionUpdateRequest,
    QuestionBankReviewRequest,
    QuestionBankSeedResponse,
    QuestionSourceResponse,
)


router = APIRouter(prefix="/admin")


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _source_response(source: QuestionSource) -> QuestionSourceResponse:
    return QuestionSourceResponse(
        id=source.id,
        source_id=source.source_id,
        name=source.name,
        url=source.url,
        license=source.license,
        recommended_use=source.recommended_use,
        attribution_required=source.attribution_required,
        notes=source.notes,
        status=source.status,
        created_at=_utc_iso(source.created_at) or "",
    )


def _question_response(question: QuestionBankQuestion) -> QuestionBankQuestionResponse:
    assessment_ready = (
        question.status == "approved"
        and (
            question.question_type != "coding"
            or question.package_status == "package_approved"
        )
    )
    return QuestionBankQuestionResponse(
        id=question.id,
        source=_source_response(question.source) if question.source else None,
        version=question.version,
        status=question.status,
        title=question.title,
        question_type=question.question_type,
        prompt=question.prompt,
        role_tags=question.role_tags or [],
        skill_tags=question.skill_tags or [],
        cognitive_tags=question.cognitive_tags or [],
        difficulty=question.difficulty,
        seniority=question.seniority,
        estimated_minutes=question.estimated_minutes,
        rubric=question.rubric or {},
        expected_evidence=question.expected_evidence or [],
        provenance=question.provenance or {},
        generated_by=question.generated_by,
        package_status=question.package_status,
        coding_package_kind=question.coding_package_kind,
        coding_package_ref=question.coding_package_ref,
        coding_package_notes=question.coding_package_notes,
        assessment_ready=assessment_ready,
        reviewed_by_id=question.reviewed_by_id,
        reviewed_at=_utc_iso(question.reviewed_at),
        review_notes=question.review_notes,
        created_at=_utc_iso(question.created_at) or "",
    )


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


def _upsert_question_sources(session: Session) -> tuple[dict[str, QuestionSource], int]:
    existing = {
        source.source_id: source
        for source in session.scalars(select(QuestionSource)).all()
    }
    created = 0
    for item in APPROVED_SOURCES:
        source = existing.get(item["source_id"])
        if source is None:
            source = QuestionSource(**item)
            session.add(source)
            existing[item["source_id"]] = source
            created += 1
        else:
            for field, value in item.items():
                setattr(source, field, value)

    internal = existing.get("internal_signal_loop")
    if internal is None:
        internal = QuestionSource(
            source_id="internal_signal_loop",
            name="SignalLoop internal authored",
            url="internal://signalloop/question-bank",
            license="Apache-2.0",
            recommended_use="internal_authored",
            attribution_required=False,
            notes="SignalLoop-authored or reviewed AI-draft questions released with the project license.",
            status="approved_for_drafts",
        )
        session.add(internal)
        existing["internal_signal_loop"] = internal
        created += 1
    return existing, created


@router.post("/question-bank/seed-drafts", response_model=QuestionBankSeedResponse)
def seed_question_bank_drafts(
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankSeedResponse:
    sources, created_sources = _upsert_question_sources(session)
    session.flush()

    existing_titles = set(session.scalars(select(QuestionBankQuestion.title)).all())
    created_questions = 0
    for seed in SEED_QUESTIONS:
        if seed["title"] in existing_titles:
            continue
        source = sources[seed["source_source_id"]]
        provenance = {
            "source_id": source.source_id,
            "source_url": source.url,
            "license": source.license,
            "attribution_required": source.attribution_required,
            "notes": source.notes,
        }
        question = QuestionBankQuestion(
            source_id=source.id,
            status="needs_review",
            title=seed["title"],
            question_type=seed["question_type"],
            prompt=seed["prompt"],
            role_tags=seed["role_tags"],
            skill_tags=seed["skill_tags"],
            cognitive_tags=seed["cognitive_tags"],
            difficulty=seed["difficulty"],
            seniority=seed["seniority"],
            estimated_minutes=seed["estimated_minutes"],
            rubric=seed["rubric"],
            expected_evidence=seed["expected_evidence"],
            provenance=provenance,
            generated_by=seed["generated_by"],
            package_status=seed.get("package_status") or ("missing" if seed["question_type"] == "coding" else "not_required"),
            coding_package_kind=seed.get("coding_package_kind"),
            coding_package_ref=seed.get("coding_package_ref"),
            coding_package_notes=seed.get("coding_package_notes"),
        )
        session.add(question)
        created_questions += 1
    session.commit()

    source_count = session.scalar(select(func.count(QuestionSource.id))) or 0
    question_count = session.scalar(select(func.count(QuestionBankQuestion.id))) or 0
    return QuestionBankSeedResponse(
        source_count=int(source_count),
        question_count=int(question_count),
        created_sources=created_sources,
        created_questions=created_questions,
    )


@router.post("/question-bank/import-source-questions", response_model=QuestionBankImportResponse)
def import_question_bank_source_questions(
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankImportResponse:
    _upsert_question_sources(session)
    session.flush()
    result = import_approved_source_questions(session)
    question_count = session.scalar(select(func.count(QuestionBankQuestion.id))) or 0
    return QuestionBankImportResponse(
        fetched_sources=result["fetched_sources"],
        created_questions=result["created_questions"],
        errors=result["errors"],
        question_count=int(question_count),
    )


@router.get("/question-bank/sources", response_model=list[QuestionSourceResponse])
def list_question_sources(
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> list[QuestionSourceResponse]:
    sources = session.scalars(select(QuestionSource).order_by(QuestionSource.source_id)).all()
    return [_source_response(source) for source in sources]


@router.get("/question-bank/questions", response_model=list[QuestionBankQuestionResponse])
def list_question_bank_questions(
    status_filter: Optional[str] = None,
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> list[QuestionBankQuestionResponse]:
    stmt = select(QuestionBankQuestion).order_by(QuestionBankQuestion.created_at.desc(), QuestionBankQuestion.id.desc())
    if status_filter:
        stmt = stmt.where(QuestionBankQuestion.status == status_filter)
    questions = session.scalars(stmt).all()
    return [_question_response(question) for question in questions]


@router.patch("/question-bank/questions/{question_id}", response_model=QuestionBankQuestionResponse)
def update_question_bank_question(
    question_id: int,
    payload: QuestionBankQuestionUpdateRequest,
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankQuestionResponse:
    question = session.get(QuestionBankQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    content_fields = {
        "title",
        "question_type",
        "prompt",
        "role_tags",
        "skill_tags",
        "cognitive_tags",
        "difficulty",
        "seniority",
        "estimated_minutes",
        "rubric",
        "expected_evidence",
    }
    incoming = payload.model_dump(exclude_unset=True)
    if question.status == "approved" and any(field in incoming for field in content_fields):
        raise HTTPException(status_code=409, detail="Approved question content cannot be edited in place")

    effective_question_type = incoming.get("question_type", question.question_type)
    if effective_question_type != "coding" and incoming.get("package_status") not in (None, "not_required"):
        raise HTTPException(status_code=400, detail="Only coding questions can require coding package review")

    for field, value in incoming.items():
        setattr(question, field, value)
    if "question_type" in incoming and question.question_type != "coding":
        question.package_status = "not_required"
        question.coding_package_kind = None
        question.coding_package_ref = None
        question.coding_package_notes = None
    elif "question_type" in incoming and question.question_type == "coding" and question.package_status == "not_required":
        question.package_status = "missing"
    session.commit()
    session.refresh(question)
    return _question_response(question)


@router.post("/question-bank/questions/{question_id}/approve", response_model=QuestionBankQuestionResponse)
def approve_question_bank_question(
    question_id: int,
    payload: QuestionBankReviewRequest,
    session: Session = Depends(get_session),
    admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankQuestionResponse:
    question = session.get(QuestionBankQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.status == "deprecated":
        raise HTTPException(status_code=409, detail="Deprecated questions cannot be approved")

    question.status = "approved"
    question.reviewed_by_id = admin.id
    question.reviewed_at = datetime.now(timezone.utc)
    question.review_notes = payload.review_notes
    session.commit()
    session.refresh(question)
    return _question_response(question)


@router.post("/question-bank/questions/{question_id}/package/approve", response_model=QuestionBankQuestionResponse)
def approve_question_bank_question_package(
    question_id: int,
    payload: QuestionBankReviewRequest,
    session: Session = Depends(get_session),
    admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankQuestionResponse:
    question = session.get(QuestionBankQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.question_type != "coding":
        raise HTTPException(status_code=400, detail="Only coding questions have package approval")
    if not question.coding_package_kind or not question.coding_package_ref:
        raise HTTPException(status_code=409, detail="Coding package kind and reference are required before approval")

    question.package_status = "package_approved"
    question.reviewed_by_id = admin.id
    question.reviewed_at = datetime.now(timezone.utc)
    question.coding_package_notes = payload.review_notes or question.coding_package_notes
    session.commit()
    session.refresh(question)
    return _question_response(question)


@router.post("/question-bank/questions/{question_id}/package/reject", response_model=QuestionBankQuestionResponse)
def reject_question_bank_question_package(
    question_id: int,
    payload: QuestionBankReviewRequest,
    session: Session = Depends(get_session),
    admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankQuestionResponse:
    question = session.get(QuestionBankQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.question_type != "coding":
        raise HTTPException(status_code=400, detail="Only coding questions have package review")

    question.package_status = "rejected"
    question.reviewed_by_id = admin.id
    question.reviewed_at = datetime.now(timezone.utc)
    question.coding_package_notes = payload.review_notes or question.coding_package_notes
    session.commit()
    session.refresh(question)
    return _question_response(question)


@router.post("/question-bank/questions/{question_id}/reject", response_model=QuestionBankQuestionResponse)
def reject_question_bank_question(
    question_id: int,
    payload: QuestionBankReviewRequest,
    session: Session = Depends(get_session),
    admin: Employer = Depends(get_current_super_admin),
) -> QuestionBankQuestionResponse:
    question = session.get(QuestionBankQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.status == "approved":
        raise HTTPException(status_code=409, detail="Approved questions should be deprecated, not rejected")

    question.status = "rejected"
    question.reviewed_by_id = admin.id
    question.reviewed_at = datetime.now(timezone.utc)
    question.review_notes = payload.review_notes
    session.commit()
    session.refresh(question)
    return _question_response(question)


@router.delete("/question-bank/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_bank_question(
    question_id: int,
    session: Session = Depends(get_session),
    _admin: Employer = Depends(get_current_super_admin),
) -> None:
    question = session.get(QuestionBankQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    session.delete(question)
    session.commit()
