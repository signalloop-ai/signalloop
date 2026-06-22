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
