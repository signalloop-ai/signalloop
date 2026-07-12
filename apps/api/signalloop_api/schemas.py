from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


VALID_DURATIONS = {60, 90, 120, 150}
DEFAULT_DURATIONS = {"standard": 90, "advanced": 120}


class CreateAttemptRequest(BaseModel):
    assessment_pack_slug: str = "fastapi_task_api_standard_v2"
    assessment_level: Literal["standard", "advanced"] = "standard"
    timing_mode: Literal["untimed", "timed"] = "untimed"
    evaluator_feedback_mode: Literal["strict", "guided"] = "strict"
    duration_minutes: Optional[int] = None
    candidate_email: Optional[EmailStr] = None
    employer_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_configuration(self) -> "CreateAttemptRequest":
        if self.duration_minutes is None:
            self.duration_minutes = DEFAULT_DURATIONS[self.assessment_level]
        if self.duration_minutes not in VALID_DURATIONS:
            raise ValueError("duration_minutes must be one of 60, 90, 120, or 150")
        return self


class CreateAttemptResponse(BaseModel):
    attempt_id: int
    invite_token: str
    invite_url: str
    status: str


class AssessmentMetadata(BaseModel):
    slug: str
    title: str
    version: str
    seeded_issue_count: int = 0


class CandidateAttemptResponse(BaseModel):
    attempt_id: int
    status: str
    candidate_email: Optional[str]
    assessment: AssessmentMetadata
    timing_mode: str
    evaluator_feedback_mode: str
    duration_minutes: int
    started_at: Optional[str]
    expires_at: Optional[str]
    submitted_at: Optional[str]
    submission_mode: Optional[str]
    files: dict[str, str]
    initial_files: dict[str, str]


class EmployerAttemptSummary(BaseModel):
    attempt_id: int
    candidate_email: Optional[str]
    status: str
    invite_token: str
    invite_url: str
    assessment: AssessmentMetadata
    assessment_level: str
    timing_mode: str
    evaluator_feedback_mode: str
    duration_minutes: int
    expires_at: Optional[str]
    submission_mode: Optional[str]
    created_at: str
    submitted_at: Optional[str]
    report_id: Optional[int]
    recommendation: Optional[str]
    score_total: Optional[int]


class SaveSnapshotRequest(BaseModel):
    files: dict[str, str] = Field(min_length=1)
    kind: str = "autosave"


class SnapshotResponse(BaseModel):
    snapshot_id: int
    attempt_id: int
    kind: str
    status: str


class FinalSubmissionRequest(BaseModel):
    files: dict[str, str] = Field(min_length=1)
    final_explanation: str = ""
    decision_log: str = ""
    submission_mode: Literal["manual", "auto_expired"] = "manual"


class FinalSubmissionResponse(BaseModel):
    attempt_id: int
    status: str
    submission_id: int
    snapshot_id: int
    hidden_test_run_id: Optional[int]
    hidden_test_status: str


class AIMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    selected_context: Optional[dict] = None


class AIMessageResponse(BaseModel):
    message: str
    allowed: bool
    policy_tags: list[str]


class EvidenceReportResponse(BaseModel):
    attempt_id: int
    report_id: int
    recommendation: Optional[str]
    score_total: Optional[int]
    report: dict


class ProctoringEventItem(BaseModel):
    event_type: str
    occurred_at: str
    metadata: Optional[dict] = None


class ProctoringEventBatchRequest(BaseModel):
    events: list[ProctoringEventItem] = Field(min_length=1, max_length=50)


class WebcamConsentRequest(BaseModel):
    consented: bool


class SnapshotUploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=200)


class SnapshotUploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str


class EmployerInfoResponse(BaseModel):
    id: int
    email: str
    role: Optional[str]


class RoleProfileCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    role_family: Literal["backend", "frontend", "fullstack", "infra", "data", "ai", "security", "support"] = "backend"
    seniority: Literal["junior", "mid", "senior", "staff"] = "mid"
    jd_text: str = Field(min_length=20, max_length=20000)
    team_context: Optional[str] = Field(default=None, max_length=5000)
    expected_ai_usage: int = Field(default=50, ge=0, le=100)
    required_skills: Optional[list[str]] = None
    nice_to_have_skills: Optional[list[str]] = None


class RoleProfileResponse(BaseModel):
    id: int
    title: str
    role_family: str
    seniority: str
    jd_text: str
    team_context: Optional[str]
    expected_ai_usage: int
    required_skills: Optional[list[str]]
    nice_to_have_skills: Optional[list[str]]
    extracted_skills: dict
    created_at: str


class CandidateProfileCreateRequest(BaseModel):
    candidate_email: Optional[EmailStr] = None
    resume_text: str = Field(min_length=20, max_length=20000)


class CandidateProfileResponse(BaseModel):
    id: int
    candidate_email: Optional[str]
    resume_text: str
    extracted_skills: dict
    extracted_experience: dict
    created_at: str


class BlueprintCreateRequest(BaseModel):
    role_profile_id: int
    candidate_profile_id: Optional[int] = None
    timing_mode: Literal["untimed", "timed"] = "timed"
    evaluator_feedback_mode: Literal["strict", "guided"] = "strict"
    duration_minutes: Optional[int] = None

    @model_validator(mode="after")
    def validate_duration(self) -> "BlueprintCreateRequest":
        if self.duration_minutes is not None and self.duration_minutes not in VALID_DURATIONS:
            raise ValueError("duration_minutes must be one of 60, 90, 120, or 150")
        return self


class AssessmentBlueprintResponse(BaseModel):
    id: int
    role_profile_id: int
    candidate_profile_id: Optional[int]
    title: str
    assessment_pack_slug: str
    assessment_level: str
    timing_mode: str
    duration_minutes: int
    evaluator_feedback_mode: str
    skill_mapping: dict
    coverage: dict
    rationale: list
    follow_up_probes: list
    caveats: list
    status: str
    approved_at: Optional[str]
    used_at: Optional[str]
    created_at: str


class BlueprintInviteCreateRequest(BaseModel):
    candidate_email: Optional[EmailStr] = None


class AdaptiveSkillMatchPreviewResponse(BaseModel):
    role_skills: dict
    candidate_skills: Optional[dict]
    skill_mapping: dict


class DocumentTextExtractResponse(BaseModel):
    filename: str
    text: str


class QuestionSourceResponse(BaseModel):
    id: int
    source_id: str
    name: str
    url: str
    license: str
    recommended_use: str
    attribution_required: bool
    notes: Optional[str]
    status: str
    created_at: str


class QuestionBankQuestionResponse(BaseModel):
    id: int
    source: Optional[QuestionSourceResponse]
    version: int
    status: str
    title: str
    question_type: str
    prompt: str
    role_tags: list[str]
    skill_tags: list[str]
    cognitive_tags: list[str]
    difficulty: str
    seniority: str
    estimated_minutes: int
    rubric: dict
    expected_evidence: list[str]
    provenance: dict
    generated_by: str
    package_status: str
    coding_package_kind: Optional[str]
    coding_package_ref: Optional[str]
    coding_package_notes: Optional[str]
    assessment_ready: bool
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[str]
    review_notes: Optional[str]
    created_at: str


class QuestionBankQuestionUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    question_type: Optional[str] = Field(default=None, max_length=80)
    prompt: Optional[str] = Field(default=None, min_length=20, max_length=20000)
    role_tags: Optional[list[str]] = None
    skill_tags: Optional[list[str]] = None
    cognitive_tags: Optional[list[str]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    seniority: Optional[str] = Field(default=None, max_length=80)
    estimated_minutes: Optional[int] = Field(default=None, ge=1, le=240)
    rubric: Optional[dict] = None
    expected_evidence: Optional[list[str]] = None
    package_status: Optional[Literal["not_required", "missing", "draft", "ready_for_review", "package_approved", "rejected"]] = None
    coding_package_kind: Optional[str] = Field(default=None, max_length=80)
    coding_package_ref: Optional[str] = Field(default=None, max_length=255)
    coding_package_notes: Optional[str] = Field(default=None, max_length=5000)
    review_notes: Optional[str] = Field(default=None, max_length=5000)


class QuestionBankReviewRequest(BaseModel):
    review_notes: Optional[str] = Field(default=None, max_length=5000)


class QuestionBankSeedResponse(BaseModel):
    source_count: int
    question_count: int
    created_sources: int
    created_questions: int


class QuestionBankImportResponse(BaseModel):
    fetched_sources: int
    created_questions: int
    errors: list[dict]
    question_count: int
