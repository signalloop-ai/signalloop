from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.ai_policy import AIDecision
from signalloop_api.ai_provider import get_ai_provider
from signalloop_api.auth import get_current_employer
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import Employer, EvidenceReport
from signalloop_api.reports import get_candidate_verification_runner
from signalloop_api.submissions import get_hidden_test_runner


class FakeProvider:
    def evaluate(self, message: str, context: dict | None, recent_messages: list[str], recent_turns: list[tuple[str, str]] | None = None, workspace_files: dict[str, str] | None = None) -> AIDecision:
        return AIDecision(
            allowed=True,
            policy_tags=[],
            message="Focus on the specific failing behavior and verify it with a test.",
        )


class FakeHiddenTestRunner:
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        return {
            "status": "failed",
            "exit_code": 1,
            "stdout": (
                "collected 6 items\n"
                "tests/test_hidden_api.py F....F\n"
                "____ test_duplicate_email_is_case_insensitive_and_conflicts ____\n"
                "____ test_owner_delete_removes_task_and_is_idempotently_not_found_afterward ____\n"
            ),
            "stderr": "",
            "duration_ms": 50,
        }


class FakeCandidateVerificationRunner:
    def __init__(self, failure_names: list[str] | None = None) -> None:
        self._failure_names = failure_names or []

    def run(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        failures_output = "".join(
            f"____ {name} ____\n" for name in self._failure_names
        )
        status = "failed" if self._failure_names else "passed"
        count = len(candidate_tests)
        return {
            "status": status,
            "exit_code": 1 if self._failure_names else 0,
            "stdout": f"collected {count} items\n{failures_output}",
            "stderr": "",
            "duration_ms": 30,
        }


@pytest.fixture()
def client(
    session_factory: sessionmaker[Session],
    default_employer: Employer,
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_employer() -> Employer:
        return default_employer

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_employer] = override_get_current_employer
    app.dependency_overrides[get_hidden_test_runner] = lambda: FakeHiddenTestRunner()
    app.dependency_overrides[get_ai_provider] = lambda: FakeProvider()
    app.dependency_overrides[get_candidate_verification_runner] = lambda: FakeCandidateVerificationRunner()
    yield TestClient(app)
    app.dependency_overrides.clear()


def create_submitted_attempt(client: TestClient) -> int:
    created = client.post("/assessment-attempts", json={}).json()
    token = created["invite_token"]
    client.get(f"/candidate/invites/{token}")
    ai_response = client.post(
        f"/candidate/invites/{token}/ai/messages",
        json={
            "message": "This public test failed around ownership. How should I debug it?",
            "selected_context": {"path": "tests/test_public_api.py", "content": "assert response.status_code == 403"},
        },
    )
    assert ai_response.status_code == 200

    final_files = {
        "task_api/main.py": "def owner_check():\n    return 403\n",
        "tests/test_public_api.py": "def test_public():\n    assert True\n",
        "tests/test_candidate_ownership.py": "def test_owner():\n    assert True\n",
    }
    submitted = client.post(
        f"/candidate/invites/{token}/submit",
        json={
            "files": final_files,
            "final_explanation": "I fixed ownership checks and validated the risky paths with tests.",
            "decision_log": "Chose 403 for known non-owners, 404 for unknown actors, and explicit TODO -> IN_PROGRESS -> DONE transitions.",
        },
    )
    assert submitted.status_code == 201
    return created["attempt_id"]


def test_generate_evidence_report_persists_required_sections(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    attempt_id = create_submitted_attempt(client)

    response = client.post(f"/assessment-attempts/{attempt_id}/evidence-report")

    assert response.status_code == 201
    body = response.json()
    report = body["report"]
    assert body["attempt_id"] == attempt_id
    assert body["report_id"] > 0
    assert body["score_total"] == report["scores"]["total"]
    assert body["recommendation"] == report["overall_recommendation"]
    assert report["metadata"]["timing"]["timing_mode"] == "untimed"
    assert report["metadata"]["timing"]["duration_minutes"] == 90
    assert report["metadata"]["timing"]["submission_mode"] == "manual"
    assert "confidence" not in report["scores"]
    for section in [
        "executive_summary",
        "overall_recommendation",
        "scores",
        "rubric_weights",
        "public_test_results",
        "hidden_test_results",
        "feature_design_implementation",
        "candidate_tests",
        "ai_collaboration",
        "ai_integrity_risk",
        "favo",
        "llm_assisted_review",
        "process_evidence",
        "explanation_submitted",
        "submission_review",
        "timeline",
        "follow_up_questions",
    ]:
        assert section in report
    assert report["ai_integrity_risk"]["score_impact"] == "none_phase_2"
    assert set(report["favo"]) == {"frame", "ask", "verify", "own"}
    assert report["llm_assisted_review"]["status"] == "not_run"
    assert report["candidate_tests"]["added_test_files"] == ["tests/test_candidate_ownership.py"]
    assert "test_duplicate_email_is_case_insensitive_and_conflicts" in report["hidden_test_results"]["summary"]["failure_names"]
    assert len(report["follow_up_questions"]) >= 3
    assert sum(report["rubric_weights"].values()) == 100

    with session_factory() as session:
        evidence_report = session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == attempt_id))
        assert evidence_report is not None
        assert evidence_report.report["metadata"]["attempt_id"] == attempt_id


def test_get_evidence_report_returns_existing_report(client: TestClient) -> None:
    attempt_id = create_submitted_attempt(client)
    generated = client.post(f"/assessment-attempts/{attempt_id}/evidence-report").json()

    response = client.get(f"/assessment-attempts/{attempt_id}/evidence-report")

    assert response.status_code == 200
    assert response.json()["report_id"] == generated["report_id"]


def test_attempt_list_includes_report_summary_after_generation(client: TestClient) -> None:
    attempt_id = create_submitted_attempt(client)
    generated = client.post(f"/assessment-attempts/{attempt_id}/evidence-report").json()

    response = client.get("/assessment-attempts")

    assert response.status_code == 200
    listed_attempt = response.json()[0]
    assert listed_attempt["attempt_id"] == attempt_id
    assert listed_attempt["report_id"] == generated["report_id"]
    assert listed_attempt["recommendation"] == generated["recommendation"]
    assert listed_attempt["score_total"] == generated["score_total"]


def test_detect_pasted_ai_code_flags_new_code_from_ai() -> None:
    from signalloop_api.reports import detect_pasted_ai_code
    from unittest.mock import MagicMock
    from datetime import datetime

    ai_block = "def check_owner(task, actor_id):\n    if task.owner_id != actor_id:\n        return 403\n    return 200"
    assistant = MagicMock()
    assistant.role = "assistant"
    assistant.message = f"Here is one way to approach it:\n```python\n{ai_block}\n```"
    assistant.created_at = datetime(2026, 6, 17, 12, 0, 0)

    initial_files = {"task_api/main.py": "def hello():\n    return 'world'\n"}
    final_files = {"task_api/main.py": f"def hello():\n    return 'world'\n\n{ai_block}\n"}

    result = detect_pasted_ai_code([assistant], initial_files, final_files)

    assert result["pasted_ai_code_count"] == 1
    assert result["matches"][0]["found_in_files"] == ["task_api/main.py"]
    assert "check_owner" in result["matches"][0]["code_preview"]


def test_detect_pasted_ai_code_ignores_quoted_existing_code() -> None:
    from signalloop_api.reports import detect_pasted_ai_code
    from unittest.mock import MagicMock
    from datetime import datetime

    existing_block = "def hello():\n    return 'world'\n    # existing code"
    assistant = MagicMock()
    assistant.role = "assistant"
    assistant.message = f"Your existing code looks like:\n```python\n{existing_block}\n```"
    assistant.created_at = datetime(2026, 6, 17, 12, 0, 0)

    initial_files = {"task_api/main.py": existing_block}
    final_files = {"task_api/main.py": existing_block}

    result = detect_pasted_ai_code([assistant], initial_files, final_files)

    assert result["pasted_ai_code_count"] == 0


def test_detect_large_paste_events_flags_big_additions() -> None:
    from signalloop_api.reports import detect_large_paste_events
    from unittest.mock import MagicMock
    from datetime import datetime

    small_file = "def hello():\n    return 'world'\n"
    big_addition = "\n".join(f"    line_{i} = {i}" for i in range(30))
    large_file = small_file + "\ndef new_func():\n" + big_addition

    snap1 = MagicMock()
    snap1.files = {"task_api/main.py": small_file}
    snap1.created_at = datetime(2026, 6, 17, 12, 0, 0)

    snap2 = MagicMock()
    snap2.files = {"task_api/main.py": large_file}
    snap2.kind = "autosave"
    snap2.created_at = datetime(2026, 6, 17, 12, 1, 0)

    result = detect_large_paste_events([snap1, snap2])

    assert result["large_paste_count"] == 1
    assert result["events"][0]["file"] == "task_api/main.py"
    assert result["events"][0]["lines_added"] >= 25


def test_detect_large_paste_events_ignores_small_additions() -> None:
    from signalloop_api.reports import detect_large_paste_events
    from unittest.mock import MagicMock
    from datetime import datetime

    snap1 = MagicMock()
    snap1.files = {"task_api/main.py": "def hello():\n    return 'world'\n"}
    snap1.created_at = datetime(2026, 6, 17, 12, 0, 0)

    snap2 = MagicMock()
    snap2.files = {"task_api/main.py": "def hello():\n    return 'world'\n\ndef bye():\n    return 'bye'\n"}
    snap2.kind = "autosave"
    snap2.created_at = datetime(2026, 6, 17, 12, 1, 0)

    result = detect_large_paste_events([snap1, snap2])

    assert result["large_paste_count"] == 0


def test_report_generation_requires_final_submission(client: TestClient) -> None:
    created = client.post("/assessment-attempts", json={}).json()

    response = client.post(f"/assessment-attempts/{created['attempt_id']}/evidence-report")

    assert response.status_code == 409
    assert response.json()["detail"] == "Final submission is required before generating an evidence report"


def test_proving_test_scoring_from_verification_run(
    session_factory: sessionmaker[Session],
    default_employer: Employer,
) -> None:
    """Verification runner failures that don't appear in public failures count as proving tests."""
    from signalloop_api.reports import calculate_scores
    from unittest.mock import MagicMock

    rubric = {
        "public_issue_resolution": 15,
        "private_issue_generalization": 20,
        "feature_design_implementation": 20,
        "candidate_tests": 15,
        "ai_collaboration": 15,
        "regression_code_quality": 15,
    }

    pub_run = MagicMock()
    pub_run.run_type = "public"
    pub_run.status = "passed"
    pub_run.stdout = "collected 3 items\n3 passed"
    pub_run.stderr = ""

    verification_summary_two_proving = {
        "status": "failed",
        "collected": 2,
        "passed": 0,
        "failed": 2,
        "failure_names": ["test_duplicate_email_check", "test_blank_title_rejected"],
    }

    result = calculate_scores(
        test_runs=[pub_run],
        hidden_summary={"collected": 0, "passed": 0, "failed": 0, "failure_names": [], "status": "missing"},
        candidate_tests={"candidate_test_file_count": 1, "added_test_files": ["tests/test_new.py"], "modified_test_files": []},
        ai_interactions=[],
        final_explanation="",
        decision_log="",
        snapshots=[],
        initially_failing_tests=[],
        feature_design_tests=[],
        rubric=rubric,
        candidate_verification_summary=verification_summary_two_proving,
    )

    cand_cat = next(c for c in result["categories"] if c["category"] == "Candidate-written tests")
    assert cand_cat["points"] == round(15 * 0.75), "2 proving tests should score 75% of max"
    assert "proving test" in cand_cat["evidence"]


def test_proving_test_scoring_zero_when_all_fail_on_candidate_code(
    session_factory: sessionmaker[Session],
    default_employer: Employer,
) -> None:
    """Tests that fail on BOTH original and candidate code are not proving tests."""
    from signalloop_api.reports import calculate_scores
    from unittest.mock import MagicMock

    rubric = {
        "public_issue_resolution": 15,
        "private_issue_generalization": 20,
        "feature_design_implementation": 20,
        "candidate_tests": 15,
        "ai_collaboration": 15,
        "regression_code_quality": 15,
    }

    pub_run = MagicMock()
    pub_run.run_type = "public"
    pub_run.status = "failed"
    pub_run.stdout = "collected 2 items\n____ test_duplicate_email_check ____\n____ test_blank_title_rejected ____\n"
    pub_run.stderr = ""

    verification_summary_same_failures = {
        "status": "failed",
        "collected": 2,
        "passed": 0,
        "failed": 2,
        "failure_names": ["test_duplicate_email_check", "test_blank_title_rejected"],
    }

    result = calculate_scores(
        test_runs=[pub_run],
        hidden_summary={"collected": 0, "passed": 0, "failed": 0, "failure_names": [], "status": "missing"},
        candidate_tests={"candidate_test_file_count": 1, "added_test_files": ["tests/test_new.py"], "modified_test_files": []},
        ai_interactions=[],
        final_explanation="",
        decision_log="",
        snapshots=[],
        initially_failing_tests=[],
        feature_design_tests=[],
        rubric=rubric,
        candidate_verification_summary=verification_summary_same_failures,
    )

    cand_cat = next(c for c in result["categories"] if c["category"] == "Candidate-written tests")
    assert cand_cat["points"] == 0, "Tests that still fail on candidate code are not proving tests"
