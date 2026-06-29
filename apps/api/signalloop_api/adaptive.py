from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from signalloop_api.adaptive_blueprint import UnsupportedAssessmentScopeError, generate_blueprint_payload
from signalloop_api.assessment_files import load_candidate_files
from signalloop_api.assessment_taxonomy.matching import extract_skills_from_text
from signalloop_api.attempts import (
    build_invite_url,
    generate_unique_invite_token,
    get_or_create_assessment_pack,
    resolve_repo_path,
    utc_isoformat,
)
from signalloop_api.auth import get_current_employer
from signalloop_api.audit import record_audit_event
from signalloop_api.database import get_session
from signalloop_api.document_text import DocumentTextExtractionError, extract_document_text
from signalloop_api.models import (
    AssessmentAttempt,
    AssessmentBlueprint,
    CandidateProfile,
    CodeSnapshot,
    Employer,
    RoleProfile,
)
from signalloop_api.schemas import (
    AdaptiveSkillMatchPreviewResponse,
    AssessmentBlueprintResponse,
    BlueprintCreateRequest,
    BlueprintInviteCreateRequest,
    CandidateProfileCreateRequest,
    CandidateProfileResponse,
    CreateAttemptResponse,
    DocumentTextExtractResponse,
    RoleProfileCreateRequest,
    RoleProfileResponse,
)


router = APIRouter(prefix="/employer/adaptive", tags=["adaptive"])
MAX_DOCUMENT_UPLOAD_BYTES = 2_000_000


def _role_response(profile: RoleProfile) -> RoleProfileResponse:
    return RoleProfileResponse(
        id=profile.id,
        title=profile.title,
        role_family=profile.role_family,
        seniority=profile.seniority,
        jd_text=profile.jd_text,
        team_context=profile.team_context,
        expected_ai_usage=profile.expected_ai_usage,
        required_skills=profile.required_skills,
        nice_to_have_skills=profile.nice_to_have_skills,
        extracted_skills=profile.extracted_skills,
        created_at=utc_isoformat(profile.created_at) or "",
    )


def _candidate_response(profile: CandidateProfile) -> CandidateProfileResponse:
    return CandidateProfileResponse(
        id=profile.id,
        candidate_email=profile.candidate_email,
        resume_text=profile.resume_text,
        extracted_skills=profile.extracted_skills,
        extracted_experience=profile.extracted_experience,
        created_at=utc_isoformat(profile.created_at) or "",
    )


def _blueprint_response(blueprint: AssessmentBlueprint) -> AssessmentBlueprintResponse:
    return AssessmentBlueprintResponse(
        id=blueprint.id,
        role_profile_id=blueprint.role_profile_id,
        candidate_profile_id=blueprint.candidate_profile_id,
        title=blueprint.title,
        assessment_pack_slug=blueprint.assessment_pack_slug,
        assessment_level=blueprint.assessment_level,
        timing_mode=blueprint.timing_mode,
        duration_minutes=blueprint.duration_minutes,
        evaluator_feedback_mode=blueprint.evaluator_feedback_mode,
        skill_mapping=blueprint.skill_mapping,
        coverage=blueprint.coverage,
        rationale=blueprint.rationale,
        follow_up_probes=blueprint.follow_up_probes,
        caveats=blueprint.caveats,
        status=blueprint.status,
        approved_at=utc_isoformat(blueprint.approved_at),
        used_at=utc_isoformat(blueprint.used_at),
        created_at=utc_isoformat(blueprint.created_at) or "",
    )


def _get_role_profile(session: Session, employer: Employer, profile_id: int) -> RoleProfile:
    profile = session.get(RoleProfile, profile_id)
    if profile is None or profile.employer_id != employer.id:
        raise HTTPException(status_code=404, detail="Role profile not found")
    return profile


def _get_candidate_profile(session: Session, employer: Employer, profile_id: int) -> CandidateProfile:
    profile = session.get(CandidateProfile, profile_id)
    if profile is None or profile.employer_id != employer.id:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return profile


def _get_blueprint(session: Session, employer: Employer, blueprint_id: int) -> AssessmentBlueprint:
    blueprint = session.get(AssessmentBlueprint, blueprint_id)
    if blueprint is None or blueprint.employer_id != employer.id:
        raise HTTPException(status_code=404, detail="Assessment blueprint not found")
    return blueprint


@router.post("/role-profiles", response_model=RoleProfileResponse, status_code=status.HTTP_201_CREATED)
def create_role_profile(
    payload: RoleProfileCreateRequest,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> RoleProfileResponse:
    extracted = extract_skills_from_text(
        "\n".join([
            payload.jd_text,
            payload.team_context or "",
            " ".join(payload.required_skills or []),
            " ".join(payload.nice_to_have_skills or []),
        ]),
        source="jd",
        default_importance="required",
    )
    profile = RoleProfile(
        employer_id=current_employer.id,
        title=payload.title,
        role_family=payload.role_family,
        seniority=payload.seniority,
        jd_text=payload.jd_text,
        team_context=payload.team_context,
        expected_ai_usage=payload.expected_ai_usage,
        required_skills=payload.required_skills,
        nice_to_have_skills=payload.nice_to_have_skills,
        extracted_skills=extracted,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _role_response(profile)


@router.post("/candidate-profiles", response_model=CandidateProfileResponse, status_code=status.HTTP_201_CREATED)
def create_candidate_profile(
    payload: CandidateProfileCreateRequest,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> CandidateProfileResponse:
    extracted = extract_skills_from_text(payload.resume_text, source="resume")
    profile = CandidateProfile(
        employer_id=current_employer.id,
        candidate_email=str(payload.candidate_email) if payload.candidate_email else None,
        resume_text=payload.resume_text,
        extracted_skills=extracted,
        extracted_experience=_extract_experience(payload.resume_text),
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _candidate_response(profile)


@router.post("/blueprints", response_model=AssessmentBlueprintResponse, status_code=status.HTTP_201_CREATED)
def create_blueprint(
    payload: BlueprintCreateRequest,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> AssessmentBlueprintResponse:
    role = _get_role_profile(session, current_employer, payload.role_profile_id)
    candidate = None
    if payload.candidate_profile_id is not None:
        candidate = _get_candidate_profile(session, current_employer, payload.candidate_profile_id)

    try:
        generated = generate_blueprint_payload(
            role_title=role.title,
            role_family=role.role_family,
            seniority=role.seniority,
            expected_ai_usage=role.expected_ai_usage,
            role_skills=role.extracted_skills,
            candidate_skills=candidate.extracted_skills if candidate else None,
            timing_mode=payload.timing_mode,
            evaluator_feedback_mode=payload.evaluator_feedback_mode,
            duration_minutes=payload.duration_minutes,
        )
    except UnsupportedAssessmentScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    blueprint = AssessmentBlueprint(
        employer_id=current_employer.id,
        role_profile_id=role.id,
        candidate_profile_id=candidate.id if candidate else None,
        status="draft",
        **generated,
    )
    session.add(blueprint)
    session.commit()
    session.refresh(blueprint)
    return _blueprint_response(blueprint)


@router.get("/blueprints", response_model=list[AssessmentBlueprintResponse])
def list_blueprints(
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> list[AssessmentBlueprintResponse]:
    blueprints = session.scalars(
        select(AssessmentBlueprint)
        .where(AssessmentBlueprint.employer_id == current_employer.id)
        .order_by(AssessmentBlueprint.created_at.desc(), AssessmentBlueprint.id.desc())
        .limit(20)
    ).all()
    return [_blueprint_response(blueprint) for blueprint in blueprints]


@router.get("/blueprints/{blueprint_id}", response_model=AssessmentBlueprintResponse)
def get_blueprint(
    blueprint_id: int,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> AssessmentBlueprintResponse:
    return _blueprint_response(_get_blueprint(session, current_employer, blueprint_id))


@router.post("/blueprints/{blueprint_id}/approve", response_model=AssessmentBlueprintResponse)
def approve_blueprint(
    blueprint_id: int,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> AssessmentBlueprintResponse:
    blueprint = _get_blueprint(session, current_employer, blueprint_id)
    if blueprint.status == "used":
        raise HTTPException(status_code=409, detail="Blueprint has already been used")
    if blueprint.assessment_pack_slug.startswith("future_"):
        raise HTTPException(status_code=409, detail="This future assessment blueprint is not invite-ready yet")
    blueprint.status = "approved"
    blueprint.approved_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(blueprint)
    return _blueprint_response(blueprint)


@router.post("/blueprints/{blueprint_id}/invites", response_model=CreateAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_invite_from_blueprint(
    blueprint_id: int,
    payload: BlueprintInviteCreateRequest,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> CreateAttemptResponse:
    blueprint = _get_blueprint(session, current_employer, blueprint_id)
    if blueprint.assessment_pack_slug.startswith("future_"):
        raise HTTPException(status_code=409, detail="This future assessment blueprint is not invite-ready yet")
    if blueprint.status != "approved":
        raise HTTPException(status_code=409, detail="Blueprint must be approved before creating an invite")

    pack = get_or_create_assessment_pack(session, blueprint.assessment_pack_slug)
    timing_note = "" if blueprint.timing_mode == "timed" else " (recommended, not enforced)"
    subs = {"DURATION_MINUTES": str(blueprint.duration_minutes), "TIMING_NOTE": timing_note}
    files = load_candidate_files(resolve_repo_path(pack.candidate_path), subs)
    candidate_email = (
        str(payload.candidate_email)
        if payload.candidate_email
        else blueprint.candidate_profile.candidate_email if blueprint.candidate_profile else None
    )

    attempt = AssessmentAttempt(
        employer_id=current_employer.id,
        assessment_pack_id=pack.id,
        blueprint_id=blueprint.id,
        assessment_level=blueprint.assessment_level,
        timing_mode=blueprint.timing_mode,
        evaluator_feedback_mode=blueprint.evaluator_feedback_mode,
        duration_minutes=blueprint.duration_minutes,
        expires_at=None,
        candidate_email=candidate_email,
        invite_token=generate_unique_invite_token(session),
        status="created",
    )
    session.add(attempt)
    session.flush()

    session.add(CodeSnapshot(attempt_id=attempt.id, kind="initial", files=files))
    blueprint.status = "used"
    blueprint.used_at = datetime.now(timezone.utc)
    record_audit_event(
        session,
        "attempt.created_from_blueprint",
        actor_type="employer",
        attempt_id=attempt.id,
        event_metadata={
            "blueprint_id": blueprint.id,
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


@router.get("/blueprints/{blueprint_id}/skill-match", response_model=AdaptiveSkillMatchPreviewResponse)
def blueprint_skill_match(
    blueprint_id: int,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> AdaptiveSkillMatchPreviewResponse:
    blueprint = _get_blueprint(session, current_employer, blueprint_id)
    return AdaptiveSkillMatchPreviewResponse(
        role_skills=blueprint.role_profile.extracted_skills,
        candidate_skills=blueprint.candidate_profile.extracted_skills if blueprint.candidate_profile else None,
        skill_mapping=blueprint.skill_mapping,
    )


def _extract_experience(text: str) -> dict:
    import re

    years = [
        int(match)
        for match in re.findall(r"\b(\d{1,2})\+?\s*(?:years|yrs|year)\b", text, flags=re.IGNORECASE)
    ]
    return {
        "years_mentioned": max(years) if years else None,
        "source": "resume_text",
    }


@router.post("/extract-document-text", response_model=DocumentTextExtractResponse)
async def extract_uploaded_document_text(
    request: Request,
    x_filename: str = Header(..., alias="X-Filename"),
    current_employer: Employer = Depends(get_current_employer),
) -> DocumentTextExtractResponse:
    del current_employer
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. Upload a file under 2 MB.")

    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. Upload a file under 2 MB.")

    try:
        text = extract_document_text(x_filename, data)
    except DocumentTextExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if len(text) < 20:
        raise HTTPException(status_code=422, detail="Uploaded file did not contain enough readable text.")
    return DocumentTextExtractResponse(filename=x_filename, text=text[:20_000])
