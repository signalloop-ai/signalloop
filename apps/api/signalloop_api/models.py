from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Employer(TimestampMixin, Base):
    __tablename__ = "employers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clerk_user_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    attempts: Mapped[list["AssessmentAttempt"]] = relationship(back_populates="employer")
    role_profiles: Mapped[list["RoleProfile"]] = relationship(back_populates="employer")
    candidate_profiles: Mapped[list["CandidateProfile"]] = relationship(back_populates="employer")
    assessment_blueprints: Mapped[list["AssessmentBlueprint"]] = relationship(back_populates="employer")


class AssessmentPack(TimestampMixin, Base):
    __tablename__ = "assessment_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(50))
    candidate_path: Mapped[str] = mapped_column(String(500))
    evaluator_path: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    attempts: Mapped[list["AssessmentAttempt"]] = relationship(back_populates="assessment_pack")


class AssessmentAttempt(TimestampMixin, Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employers.id"))
    assessment_pack_id: Mapped[int] = mapped_column(ForeignKey("assessment_packs.id"))
    blueprint_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assessment_blueprints.id"), nullable=True)
    assessment_level: Mapped[str] = mapped_column(String(50), default="standard")
    timing_mode: Mapped[str] = mapped_column(String(50), default="untimed")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=90)
    evaluator_feedback_mode: Mapped[str] = mapped_column(String(50), default="strict", server_default="strict")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    candidate_email: Mapped[Optional[str]] = mapped_column(String(320))
    invite_token: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submission_mode: Mapped[Optional[str]] = mapped_column(String(50))

    employer: Mapped[Optional[Employer]] = relationship(back_populates="attempts")
    blueprint: Mapped[Optional["AssessmentBlueprint"]] = relationship(back_populates="attempts")
    assessment_pack: Mapped[AssessmentPack] = relationship(back_populates="attempts")
    code_snapshots: Mapped[list["CodeSnapshot"]] = relationship(back_populates="attempt")
    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="attempt")
    ai_interactions: Mapped[list["AIInteraction"]] = relationship(back_populates="attempt")
    final_submission: Mapped[Optional["FinalSubmission"]] = relationship(back_populates="attempt")
    webcam_consent: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    evidence_report: Mapped[Optional["EvidenceReport"]] = relationship(back_populates="attempt")
    proctoring_events: Mapped[list["ProctoringEvent"]] = relationship(back_populates="attempt")


class RoleProfile(TimestampMixin, Base):
    __tablename__ = "role_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    role_family: Mapped[str] = mapped_column(String(80))
    seniority: Mapped[str] = mapped_column(String(80))
    jd_text: Mapped[str] = mapped_column(Text)
    team_context: Mapped[Optional[str]] = mapped_column(Text)
    expected_ai_usage: Mapped[int] = mapped_column(Integer, default=50)
    required_skills: Mapped[Optional[list]] = mapped_column(JSON)
    nice_to_have_skills: Mapped[Optional[list]] = mapped_column(JSON)
    extracted_skills: Mapped[dict] = mapped_column(JSON, default=dict)

    employer: Mapped[Employer] = relationship(back_populates="role_profiles")
    blueprints: Mapped[list["AssessmentBlueprint"]] = relationship(back_populates="role_profile")


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    candidate_email: Mapped[Optional[str]] = mapped_column(String(320))
    resume_text: Mapped[str] = mapped_column(Text)
    extracted_skills: Mapped[dict] = mapped_column(JSON, default=dict)
    extracted_experience: Mapped[dict] = mapped_column(JSON, default=dict)

    employer: Mapped[Employer] = relationship(back_populates="candidate_profiles")
    blueprints: Mapped[list["AssessmentBlueprint"]] = relationship(back_populates="candidate_profile")


class AssessmentBlueprint(TimestampMixin, Base):
    __tablename__ = "assessment_blueprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    role_profile_id: Mapped[int] = mapped_column(ForeignKey("role_profiles.id"))
    candidate_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    assessment_pack_slug: Mapped[str] = mapped_column(String(120))
    assessment_level: Mapped[str] = mapped_column(String(50))
    timing_mode: Mapped[str] = mapped_column(String(50))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    evaluator_feedback_mode: Mapped[str] = mapped_column(String(50))
    skill_mapping: Mapped[dict] = mapped_column(JSON)
    coverage: Mapped[dict] = mapped_column(JSON)
    rationale: Mapped[list] = mapped_column(JSON)
    follow_up_probes: Mapped[list] = mapped_column(JSON)
    caveats: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="draft", server_default="draft")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    employer: Mapped[Employer] = relationship(back_populates="assessment_blueprints")
    role_profile: Mapped[RoleProfile] = relationship(back_populates="blueprints")
    candidate_profile: Mapped[Optional[CandidateProfile]] = relationship(back_populates="blueprints")
    attempts: Mapped[list[AssessmentAttempt]] = relationship(back_populates="blueprint")


class CodeSnapshot(TimestampMixin, Base):
    __tablename__ = "code_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"))
    kind: Mapped[str] = mapped_column(String(50))
    files: Mapped[dict] = mapped_column(JSON)

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="code_snapshots")
    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="code_snapshot")
    final_submissions: Mapped[list["FinalSubmission"]] = relationship(back_populates="code_snapshot")


class TestRun(TimestampMixin, Base):
    __tablename__ = "test_runs"
    __test__ = False

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"))
    code_snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("code_snapshots.id"))
    run_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    results: Mapped[dict] = mapped_column(JSON)
    stdout: Mapped[Optional[str]] = mapped_column(Text)
    stderr: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="test_runs")
    code_snapshot: Mapped[Optional[CodeSnapshot]] = relationship(back_populates="test_runs")


class AIInteraction(TimestampMixin, Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"))
    role: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    selected_context: Mapped[Optional[dict]] = mapped_column(JSON)
    policy_tags: Mapped[Optional[list]] = mapped_column(JSON)

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="ai_interactions")


class FinalSubmission(Base):
    __tablename__ = "final_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"), unique=True)
    code_snapshot_id: Mapped[int] = mapped_column(ForeignKey("code_snapshots.id"))
    final_explanation: Mapped[str] = mapped_column(Text)
    decision_log: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="final_submission")
    code_snapshot: Mapped[CodeSnapshot] = relationship(back_populates="final_submissions")


class EvidenceReport(TimestampMixin, Base):
    __tablename__ = "evidence_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"), unique=True)
    report: Mapped[dict] = mapped_column(JSON)
    recommendation: Mapped[Optional[str]] = mapped_column(String(100))
    score_total: Mapped[Optional[int]] = mapped_column(Integer)

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="evidence_report")


class AuditEvent(TimestampMixin, Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120))
    actor_type: Mapped[str] = mapped_column(String(50))
    attempt_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assessment_attempts.id"))
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON)


VALID_PROCTORING_EVENT_TYPES = frozenset({
    "fullscreen_exit",
    "fullscreen_enter",
    "focus_lost",
    "focus_returned",
    "snapshot",
})


class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)

    attempt: Mapped[AssessmentAttempt] = relationship(back_populates="proctoring_events")
