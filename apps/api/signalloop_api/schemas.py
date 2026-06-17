from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CreateAttemptRequest(BaseModel):
    assessment_pack_slug: str = "fastapi_task_api_v1"
    candidate_email: Optional[EmailStr] = None
    employer_id: Optional[int] = None


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
    files: dict[str, str]


class EmployerAttemptSummary(BaseModel):
    attempt_id: int
    candidate_email: Optional[str]
    status: str
    invite_token: str
    invite_url: str
    assessment: AssessmentMetadata
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
    final_explanation: str = Field(min_length=1)
    decision_log: str = ""


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
