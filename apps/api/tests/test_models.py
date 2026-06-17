from signalloop_api.models import (
    AIInteraction,
    AssessmentAttempt,
    AssessmentPack,
    CodeSnapshot,
    Employer,
    EvidenceReport,
    FinalSubmission,
    TestRun as TestRunModel,
)


def test_core_model_tables_are_declared() -> None:
    assert Employer.__tablename__ == "employers"
    assert AssessmentPack.__tablename__ == "assessment_packs"
    assert AssessmentAttempt.__tablename__ == "assessment_attempts"
    assert CodeSnapshot.__tablename__ == "code_snapshots"
    assert TestRunModel.__tablename__ == "test_runs"
    assert AIInteraction.__tablename__ == "ai_interactions"
    assert FinalSubmission.__tablename__ == "final_submissions"
    assert EvidenceReport.__tablename__ == "evidence_reports"


def test_model_metadata_contains_expected_tables() -> None:
    table_names = set(Employer.metadata.tables)

    assert {
        "employers",
        "assessment_packs",
        "assessment_attempts",
        "code_snapshots",
        "test_runs",
        "ai_interactions",
        "final_submissions",
        "evidence_reports",
    }.issubset(table_names)
