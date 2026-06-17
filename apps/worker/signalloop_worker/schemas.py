from typing import Literal, Optional

from pydantic import BaseModel, Field


class PublicTestRunRequest(BaseModel):
    files: dict[str, str] = Field(min_length=1)
    runtime_image: str = "signalloop-python-assessment:3.11"
    timeout_seconds: int = Field(default=20, ge=1, le=120)
    command: list[str] = Field(default_factory=lambda: ["python", "-m", "pytest", "tests"])


class HiddenTestRunRequest(PublicTestRunRequest):
    hidden_tests: dict[str, str] = Field(min_length=1)
    command: list[str] = Field(default_factory=lambda: ["python", "-m", "pytest", "tests/test_hidden_api.py"])


class PublicTestRunResult(BaseModel):
    status: Literal["passed", "failed", "error", "timeout"]
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int


HiddenTestRunResult = PublicTestRunResult
