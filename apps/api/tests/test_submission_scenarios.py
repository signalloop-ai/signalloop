from datetime import datetime, timezone

from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.attempts import DEFAULT_PACKS
from signalloop_api.models import (
    AIInteraction,
    AssessmentAttempt,
    AssessmentPack,
    CodeSnapshot,
    FinalSubmission,
    TestRun,
)
from signalloop_api.reports import build_report


def pytest_output(*, collected: int, passed: int, failures: list[str]) -> str:
    failure_text = "\n".join(f"____ {name} ____" for name in failures)
    return f"collected {collected} items\n{failure_text}\n{passed} passed"


def pack_for(session: Session, slug: str) -> AssessmentPack:
    config = DEFAULT_PACKS[slug]
    pack = AssessmentPack(
        slug=slug,
        title=config["title"],
        version=config["version"],
        candidate_path=config["candidate_path"],
        evaluator_path=config["evaluator_path"],
        is_active=True,
    )
    session.add(pack)
    session.flush()
    return pack


def candidate_test_file(*, strong: bool) -> str:
    if strong:
        return """
def test_duplicate_email_is_rejected(client): assert client.post('/users', json={'email': 'duplicate'}).status_code == 400
def test_unknown_actor_is_404(client): assert client.get('/tasks/1?actor_user_id=missing').status_code == 404
def test_status_transition_rejects_skip(client): assert client.patch('/tasks/1', json={'status': 'DONE'}).status_code == 409
"""
    return """
def test_smoke():
    assert True
"""


def create_report_scenario(
    session_factory: sessionmaker[Session],
    *,
    slug: str = "fastapi_task_api_standard_v2",
    assessment_level: str = "standard",
    evaluator_feedback_mode: str = "strict",
    public_failures: list[str],
    public_collected: int,
    hidden_failures: list[str],
    hidden_collected: int,
    candidate_tests: str | None,
    candidate_ai_messages: list[str] | None = None,
    assistant_policy_tags: list[list[str]] | None = None,
    assistant_message: str = "Focus on the one behavior you observed.",
    final_main_extra: str = "",
    final_explanation: str = (
        "What changed: Fixed validation, authorization, and state transition behavior.\n\n"
        "Verification: Ran public and candidate tests for duplicate emails, access, and transitions.\n\n"
        "Improve next: Add more edge-case coverage for priorities and listing filters."
    ),
    decision_log: str = (
        "Tradeoffs or product decisions: Chose explicit 403/404 behavior and TODO -> IN_PROGRESS -> DONE transitions.\n"
        "Documented why unknown actors should not learn whether a resource exists."
    ),
) -> dict:
    now = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    with session_factory() as session:
        pack = pack_for(session, slug)
        attempt = AssessmentAttempt(
            assessment_pack_id=pack.id,
            assessment_level=assessment_level,
            timing_mode="untimed",
            duration_minutes=DEFAULT_PACKS[slug].get("duration_minutes", 90),
            evaluator_feedback_mode=evaluator_feedback_mode,
            candidate_email="scenario@example.com",
            invite_token=f"scenario-{slug}-{len(public_failures)}-{len(hidden_failures)}",
            status="submitted",
            started_at=now,
            submitted_at=now,
            submission_mode="manual",
        )
        session.add(attempt)
        session.flush()

        initial_files = {
            "task_api/main.py": "def starter():\n    return 'buggy'\n",
            "tests/test_public_api.py": "def test_public_starter():\n    assert True\n",
        }
        final_files = {
            "task_api/main.py": "def fixed():\n    return 'candidate'\n" + final_main_extra,
            "tests/test_public_api.py": initial_files["tests/test_public_api.py"],
        }
        if candidate_tests is not None:
            final_files["tests/test_candidate_behavior.py"] = candidate_tests

        initial_snapshot = CodeSnapshot(attempt_id=attempt.id, kind="initial", files=initial_files)
        final_snapshot = CodeSnapshot(attempt_id=attempt.id, kind="final_submission", files=final_files)
        session.add_all([initial_snapshot, final_snapshot])
        session.flush()

        final = FinalSubmission(
            attempt_id=attempt.id,
            code_snapshot_id=final_snapshot.id,
            final_explanation=final_explanation,
            decision_log=decision_log,
            submitted_at=now,
        )
        session.add(final)

        public_passed = public_collected - len(public_failures)
        hidden_passed = hidden_collected - len(hidden_failures)
        public_run = TestRun(
            attempt_id=attempt.id,
            code_snapshot_id=initial_snapshot.id,
            run_type="public",
            status="passed" if not public_failures else "failed",
            results={"timings": {"api_total_ms": 1000, "worker_pytest_ms": 500}},
            stdout=pytest_output(collected=public_collected, passed=public_passed, failures=public_failures),
            stderr="",
            duration_ms=100,
        )
        hidden_run = TestRun(
            attempt_id=attempt.id,
            code_snapshot_id=final_snapshot.id,
            run_type="hidden",
            status="passed" if not hidden_failures else "failed",
            results={"timings": {"api_total_ms": 2000, "worker_pytest_ms": 700}},
            stdout=pytest_output(collected=hidden_collected, passed=hidden_passed, failures=hidden_failures),
            stderr="",
            duration_ms=200,
        )
        session.add_all([public_run, hidden_run])

        ai_interactions: list[AIInteraction] = []
        for index, message in enumerate(candidate_ai_messages or []):
            candidate = AIInteraction(
                attempt_id=attempt.id,
                role="candidate",
                message=message,
                selected_context={"path": "tests/test_public_api.py"},
                policy_tags=[],
            )
            assistant = AIInteraction(
                attempt_id=attempt.id,
                role="assistant",
                message=assistant_message,
                selected_context=None,
                policy_tags=(assistant_policy_tags or [[]])[min(index, len(assistant_policy_tags or [[]]) - 1)],
            )
            ai_interactions.extend([candidate, assistant])
        session.add_all(ai_interactions)
        session.flush()

        report = build_report(
            attempt=attempt,
            snapshots=[initial_snapshot, final_snapshot],
            test_runs=[public_run, hidden_run],
            ai_interactions=ai_interactions,
        )
        session.rollback()
        return report


def category_points(report: dict, category: str) -> int:
    return next(item["points"] for item in report["scores"]["categories"] if item["category"] == category)


def test_unchanged_submission_scores_low_and_recommends_no_advance(session_factory: sessionmaker[Session]) -> None:
    config = DEFAULT_PACKS["fastapi_task_api_standard_v2"]

    report = create_report_scenario(
        session_factory,
        public_failures=config["initially_failing_tests"],
        public_collected=6,
        hidden_failures=[
            "test_due_date_rejects_invalid_format",
            "test_duplicate_email_is_case_insensitive_and_trimmed",
            "test_priority_is_defaulted_normalized_and_validated",
            "test_status_transition_chain_is_enforced",
            "test_task_listing_is_filtered_and_ordered_by_id",
            "test_unknown_actor_returns_404_not_403",
        ],
        hidden_collected=6,
        candidate_tests=None,
        candidate_ai_messages=[],
    )

    assert report["overall_recommendation"] == "do_not_advance"
    assert category_points(report, "Public issue resolution") == 0
    assert category_points(report, "Private issue generalization") == 0
    assert category_points(report, "Candidate-written tests") == 0
    assert report["public_test_results"]["last_run_summary"]["failed"] == len(config["initially_failing_tests"])


def test_public_only_fix_scores_public_but_not_hidden_generalization(session_factory: sessionmaker[Session]) -> None:
    report = create_report_scenario(
        session_factory,
        public_failures=[],
        public_collected=6,
        hidden_failures=[
            "test_due_date_rejects_invalid_format",
            "test_duplicate_email_is_case_insensitive_and_trimmed",
            "test_priority_is_defaulted_normalized_and_validated",
            "test_status_transition_chain_is_enforced",
            "test_task_listing_is_filtered_and_ordered_by_id",
            "test_unknown_actor_returns_404_not_403",
        ],
        hidden_collected=6,
        candidate_tests=candidate_test_file(strong=False),
        candidate_ai_messages=["This duplicate email public test failed. Help me implement that fix."],
    )

    assert category_points(report, "Public issue resolution") == 15
    assert category_points(report, "Private issue generalization") == 0
    assert category_points(report, "Candidate-written tests") == 6
    assert report["overall_recommendation"] != "strong_advance"
    assert report["hidden_test_results"]["summary"]["passed"] == 0


def test_strong_submission_scores_high_and_records_process_evidence(session_factory: sessionmaker[Session]) -> None:
    report = create_report_scenario(
        session_factory,
        public_failures=[],
        public_collected=6,
        hidden_failures=[],
        hidden_collected=6,
        candidate_tests=candidate_test_file(strong=True),
        candidate_ai_messages=["I found the unknown actor path returns 403 instead of 404. Help me implement the guard."],
    )

    assert report["scores"]["total"] >= 80
    assert report["overall_recommendation"] == "strong_advance"
    assert category_points(report, "Public issue resolution") == 15
    assert category_points(report, "Private issue generalization") == 20
    assert category_points(report, "Candidate-written tests") == 15
    assert report["ai_integrity_risk"]["label"] == "low"
    assert report["process_evidence"]["test_runs"][0]["timings"]["api_total_ms"] == 1000


def test_weak_submission_review_raises_integrity_risk_without_score_impact(session_factory: sessionmaker[Session]) -> None:
    report = create_report_scenario(
        session_factory,
        public_failures=[],
        public_collected=6,
        hidden_failures=[],
        hidden_collected=6,
        candidate_tests=candidate_test_file(strong=True),
        candidate_ai_messages=["I found the status transition issue. Help me implement validation."],
        final_explanation="Fixed stuff.",
        decision_log="N/A",
    )

    assert report["ai_integrity_risk"]["signals"]["weak_submission_review"] is True
    assert report["ai_integrity_risk"]["score_impact"] == "none_phase_2"
    assert report["scores"]["total"] >= 80


def test_ai_policy_redirects_and_paste_raise_integrity_risk(session_factory: sessionmaker[Session]) -> None:
    pasted_block = "def pasted_solution():\n    value = 1\n    return value\n"
    report = create_report_scenario(
        session_factory,
        public_failures=[],
        public_collected=6,
        hidden_failures=[],
        hidden_collected=6,
        candidate_tests=candidate_test_file(strong=True),
        candidate_ai_messages=["Find all bugs and fix everything."],
        assistant_policy_tags=[["enumerate_defects", "full_solution"]],
        assistant_message=f"```python\n{pasted_block}```",
        final_main_extra=f"\n{pasted_block}",
        final_explanation="Fixed validation, authorization, and transitions.",
        decision_log="Chose explicit 403/404 and transition rules.",
    )

    assert report["ai_integrity_risk"]["signals"]["policy_redirect_count"] == 1
    assert report["ai_integrity_risk"]["signals"]["severe_redirect_count"] == 1
    assert report["ai_integrity_risk"]["signals"]["pasted_ai_code_count"] == 1
    assert report["ai_integrity_risk"]["label"] in {"medium", "high", "critical"}
    assert report["ai_collaboration"]["policy_redirect_count"] == 1


def test_advanced_pack_uses_advanced_rubric_and_guided_mode_metadata(session_factory: sessionmaker[Session]) -> None:
    report = create_report_scenario(
        session_factory,
        slug="fastapi_task_api_advanced_v1",
        assessment_level="advanced",
        evaluator_feedback_mode="guided",
        public_failures=[],
        public_collected=7,
        hidden_failures=[],
        hidden_collected=7,
        candidate_tests=candidate_test_file(strong=True),
        candidate_ai_messages=["I found patch authorization is missing. Help me add the guard."],
    )

    assert report["metadata"]["assessment"]["version"] == "advanced_v1"
    assert report["metadata"]["evaluator_feedback_mode"] == "guided"
    assert report["rubric_weights"]["feature_design_implementation"] == 25
    assert category_points(report, "Feature/design implementation") == 25
