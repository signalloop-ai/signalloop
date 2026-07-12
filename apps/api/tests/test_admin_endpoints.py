"""Tests for Phase 4 super admin API endpoints.

Verifies: admin can list employers, drill into an employer's attempts, fetch
any evidence report; regular employers get 403; unauthenticated get 401.
"""

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.admin import router
from signalloop_api.auth import get_current_employer, get_current_super_admin
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import (
    AIInteraction,
    AssessmentAttempt,
    AssessmentPack,
    Base,
    CodeSnapshot,
    Employer,
    EvidenceReport,
    TestRun,
)
from signalloop_api import admin as admin_module
from tests.conftest import session_factory as make_session_factory


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    import sqlalchemy as sa
    engine = sa.create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    Base.metadata.drop_all(engine)


def _make_employer(session_factory, *, email: str, role: str | None = None) -> Employer:
    with session_factory() as session:
        emp = Employer(clerk_user_id=f"clerk-{email}", email=email, company_name=None, role=role)
        session.add(emp)
        session.commit()
        session.refresh(emp)
        session.expunge(emp)
        return emp


def _make_attempt(session_factory, *, employer_id: int, status: str = "created", candidate_email: str | None = None) -> AssessmentAttempt:
    with session_factory() as session:
        pack = session.query(AssessmentPack).first()
        if pack is None:
            pack = AssessmentPack(slug="test-pack", title="Test Pack", version="v1", candidate_path="/x", evaluator_path="/y", is_active=True)
            session.add(pack)
            session.commit()
            session.refresh(pack)
        attempt = AssessmentAttempt(
            employer_id=employer_id,
            assessment_pack_id=pack.id,
            assessment_level="standard",
            timing_mode="untimed",
            duration_minutes=90,
            evaluator_feedback_mode="strict",
            candidate_email=candidate_email,
            invite_token=f"token-{employer_id}-{datetime.now(timezone.utc).timestamp()}",
            status=status,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        session.expunge(attempt)
        return attempt


def _make_report(session_factory, *, attempt_id: int, score_total: int = 75, recommendation: str = "advance_with_followups") -> None:
    with session_factory() as session:
        er = EvidenceReport(
            attempt_id=attempt_id,
            report={"metadata": {}, "scores": {"total": score_total}},
            recommendation=recommendation,
            score_total=score_total,
        )
        session.add(er)
        session.commit()


def _make_ai_exchange(session_factory, *, attempt_id: int, prompt: str, tags: list[str] | None = None) -> None:
    """Persist a candidate prompt + assistant reply, mirroring the real endpoint which stores
    the same policy_tags on both rows."""
    with session_factory() as session:
        session.add(AIInteraction(attempt_id=attempt_id, role="candidate", message=prompt, policy_tags=tags or []))
        session.add(AIInteraction(attempt_id=attempt_id, role="assistant", message="reply", policy_tags=tags or []))
        session.commit()


def _make_test_run(session_factory, *, attempt_id: int, status: str) -> None:
    with session_factory() as session:
        session.add(TestRun(attempt_id=attempt_id, run_type="public", status=status, results={}))
        session.commit()


def _client_as(session_factory, employer: Employer) -> TestClient:
    """Build a TestClient with the given employer as the authenticated super admin (or regular employer)."""
    def override_get_session():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = override_get_session
    if employer.role == "super_admin":
        app.dependency_overrides[get_current_super_admin] = lambda: employer
    app.dependency_overrides[get_current_employer] = lambda: employer
    try:
        return TestClient(app)
    finally:
        # clear after test using finalizer in caller; but keep during request
        pass


@pytest.fixture()
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


class TestAdminMe:
    def test_admin_me_returns_admin_identity(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        client = _client_as(session_factory, admin)
        # Override get_current_super_admin to return admin directly
        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        response = client.get("/admin/me")
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "admin@example.com"
        assert body["role"] == "super_admin"

    def test_employer_me_returns_role_for_regular_employer(self, session_factory, cleanup_overrides):
        emp = _make_employer(session_factory, email="emp@example.com", role=None)
        app.dependency_overrides[get_current_employer] = lambda: emp
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)
        response = client.get("/employer/me")
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "emp@example.com"
        assert body["role"] is None


class TestAdminEmployerList:
    def test_admin_can_list_employers(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        _make_employer(session_factory, email="emp1@example.com", role=None)
        _make_employer(session_factory, email="emp2@example.com", role=None)

        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        response = client.get("/admin/employers")
        assert response.status_code == 200
        body = response.json()
        emails = [e["email"] for e in body]
        assert "emp1@example.com" in emails
        assert "emp2@example.com" in emails
        for entry in body:
            assert "invite_count" in entry
            assert "submitted_count" in entry
            assert "report_count" in entry
            assert "avg_score" in entry

    def test_regular_employer_gets_403_on_admin_list(self, session_factory, cleanup_overrides):
        emp = _make_employer(session_factory, email="emp@example.com", role=None)
        app.dependency_overrides[get_current_super_admin] = _raise_403
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)
        response = client.get("/admin/employers")
        assert response.status_code == 403

    def test_unauthenticated_gets_401_on_admin_list(self, session_factory, cleanup_overrides):
        app.dependency_overrides[get_current_super_admin] = _raise_401
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)
        response = client.get("/admin/employers")
        assert response.status_code == 401


class TestAdminEmployerDetail:
    def test_admin_can_get_employer_detail(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        emp = _make_employer(session_factory, email="emp@example.com", role=None)
        _make_attempt(session_factory, employer_id=emp.id, status="submitted", candidate_email="cand@test.com")
        _make_report(session_factory, attempt_id=1, score_total=72)

        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        response = client.get(f"/admin/employers/{emp.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "emp@example.com"
        assert body["attempt_count"] >= 1
        assert len(body["attempts"]) >= 1
        assert "status_breakdown" in body
        assert "score_distribution" in body
        assert "ai_usage" in body
        assert "stuck_signals" in body
        assert "pack_breakdown" in body

    def test_employer_detail_metrics_are_accurate(self, session_factory, cleanup_overrides):
        """Locks the metric fixes: AI messages count candidate prompts only (not the doubled
        candidate+assistant rows), violations count any disallowed tag (not just injection,
        not double-counted), and execution_errors counts error/timeout runs (not test
        failures, not the dead 'error' attempt status)."""
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        emp = _make_employer(session_factory, email="emp@example.com", role=None)
        attempt = _make_attempt(session_factory, employer_id=emp.id, status="submitted")

        # Two candidate prompts: one clean, one a full_solution violation.
        _make_ai_exchange(session_factory, attempt_id=attempt.id, prompt="how do I raise a 409?")
        _make_ai_exchange(session_factory, attempt_id=attempt.id, prompt="give me the full solution", tags=["full_solution"])

        # Test runs: passed + failed are not stuck signals; error + timeout are.
        for st in ("passed", "failed", "error", "timeout"):
            _make_test_run(session_factory, attempt_id=attempt.id, status=st)

        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        body = client.get(f"/admin/employers/{emp.id}").json()
        assert body["ai_usage"]["total_messages"] == 2  # candidate prompts, not 4
        assert body["ai_usage"]["total_violations"] == 1  # full_solution counted once
        assert body["stuck_signals"]["execution_errors"] == 2  # error + timeout
        assert "error_attempts" not in body["stuck_signals"]  # dead signal removed
        assert "failed_test_runs" not in body["stuck_signals"]  # renamed

    def test_admin_gets_404_for_missing_employer(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)
        response = client.get("/admin/employers/99999")
        assert response.status_code == 404


class TestAdminReport:
    def test_admin_can_get_any_employer_report(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        emp = _make_employer(session_factory, email="emp@example.com", role=None)
        attempt = _make_attempt(session_factory, employer_id=emp.id, status="submitted")
        _make_report(session_factory, attempt_id=attempt.id, score_total=65)

        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        response = client.get(f"/admin/attempts/{attempt.id}/report")
        assert response.status_code == 200
        body = response.json()
        assert body["attempt_id"] == attempt.id
        assert body["score_total"] == 65

    def test_admin_gets_404_for_missing_report(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)
        response = client.get("/admin/attempts/99999/report")
        assert response.status_code == 404


class TestAdminQuestionBank:
    def test_admin_can_seed_list_and_approve_question_bank_draft(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        seed_response = client.post("/admin/question-bank/seed-drafts")
        assert seed_response.status_code == 200
        seed_body = seed_response.json()
        assert seed_body["created_sources"] >= 1
        assert seed_body["created_questions"] >= 1

        questions_response = client.get("/admin/question-bank/questions?status_filter=needs_review")
        assert questions_response.status_code == 200
        questions = questions_response.json()
        assert questions
        assert {q["status"] for q in questions} == {"needs_review"}
        first = questions[0]
        assert first["role_tags"]
        assert first["cognitive_tags"]
        assert first["rubric"]["dimensions"]

        update_response = client.patch(
            f"/admin/question-bank/questions/{first['id']}",
            json={"difficulty": "hard", "review_notes": "Looks relevant after metadata adjustment."},
        )
        assert update_response.status_code == 200
        assert update_response.json()["difficulty"] == "hard"

        approve_response = client.post(
            f"/admin/question-bank/questions/{first['id']}/approve",
            json={"review_notes": "Approved for first question bank review set."},
        )
        assert approve_response.status_code == 200
        approved = approve_response.json()
        assert approved["status"] == "approved"
        assert approved["reviewed_by_id"] == admin.id
        assert approved["reviewed_at"] is not None

        edit_after_approval = client.patch(
            f"/admin/question-bank/questions/{first['id']}",
            json={"title": "Should not edit approved questions"},
        )
        assert edit_after_approval.status_code == 409

        delete_after_approval = client.delete(f"/admin/question-bank/questions/{first['id']}")
        assert delete_after_approval.status_code == 204

    def test_admin_can_approve_coding_package_separately(self, session_factory, cleanup_overrides):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        client.post("/admin/question-bank/seed-drafts")
        questions = client.get("/admin/question-bank/questions?status_filter=needs_review").json()
        coding_question = next(q for q in questions if q["question_type"] == "coding")

        package_response = client.patch(
            f"/admin/question-bank/questions/{coding_question['id']}",
            json={
                "package_status": "ready_for_review",
                "coding_package_kind": "existing_assessment_pack",
                "coding_package_ref": "fastapi_task_api_standard_v2",
                "coding_package_notes": "Validated existing FastAPI package.",
            },
        )
        assert package_response.status_code == 200

        approve_content = client.post(
            f"/admin/question-bank/questions/{coding_question['id']}/approve",
            json={"review_notes": "Content approved."},
        )
        assert approve_content.status_code == 200

        approve_package = client.post(
            f"/admin/question-bank/questions/{coding_question['id']}/package/approve",
            json={"review_notes": "Package approved."},
        )
        assert approve_package.status_code == 200
        body = approve_package.json()
        assert body["package_status"] == "package_approved"
        assert body["assessment_ready"] is True

    def test_regular_employer_cannot_access_question_bank(self, session_factory, cleanup_overrides):
        app.dependency_overrides[get_current_super_admin] = _raise_403
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        response = client.get("/admin/question-bank/questions")
        assert response.status_code == 403

    def test_admin_can_import_source_questions_into_review_queue(self, session_factory, cleanup_overrides, monkeypatch):
        admin = _make_employer(session_factory, email="admin@example.com", role="super_admin")
        app.dependency_overrides[get_current_super_admin] = lambda: admin
        app.dependency_overrides[get_session] = _session_override(session_factory)
        client = TestClient(app)

        def fake_import(session):
            from signalloop_api.models import QuestionBankQuestion, QuestionSource

            source = session.query(QuestionSource).filter_by(source_id="h5bp_frontend_questions").one()
            session.add(QuestionBankQuestion(
                source_id=source.id,
                status="needs_review",
                title="Imported frontend question",
                question_type="communication",
                prompt="Explain event delegation in a realistic frontend debugging context.",
                role_tags=["frontend"],
                skill_tags=["javascript"],
                cognitive_tags=["communication_quality"],
                difficulty="medium",
                seniority="mid",
                estimated_minutes=10,
                rubric={"dimensions": ["technical_accuracy"]},
                expected_evidence=["clear explanation"],
                provenance={"source_id": source.source_id},
                generated_by="source_import",
            ))
            session.commit()
            return {"fetched_sources": 1, "created_questions": 1, "errors": []}

        monkeypatch.setattr(admin_module, "import_approved_source_questions", fake_import)
        response = client.post("/admin/question-bank/import-source-questions")
        assert response.status_code == 200
        body = response.json()
        assert body["created_questions"] == 1
        assert body["question_count"] == 1


class TestRoleAssignment:
    def test_assign_role_sets_super_admin_when_email_matches(self, session_factory, cleanup_overrides, monkeypatch):
        from signalloop_api.auth import get_or_create_employer, EmployerIdentity
        from signalloop_api.config import settings

        monkeypatch.setattr(settings, "super_admin_emails", ["admin@example.com"])
        with session_factory() as session:
            identity = EmployerIdentity(clerk_user_id="clerk-admin", email="admin@example.com")
            emp = get_or_create_employer(session, identity)
            assert emp.role == "super_admin"

    def test_assign_role_keeps_null_for_non_admin_email(self, session_factory, cleanup_overrides, monkeypatch):
        from signalloop_api.auth import get_or_create_employer, EmployerIdentity
        from signalloop_api.config import settings

        monkeypatch.setattr(settings, "super_admin_emails", ["admin@example.com"])
        with session_factory() as session:
            identity = EmployerIdentity(clerk_user_id="clerk-emp", email="emp@example.com")
            emp = get_or_create_employer(session, identity)
            assert emp.role is None

    def test_assign_role_downgrades_when_email_removed_from_env(self, session_factory, cleanup_overrides, monkeypatch):
        from signalloop_api.auth import get_or_create_employer, EmployerIdentity
        from signalloop_api.config import settings

        # First login with admin email: should get super_admin
        monkeypatch.setattr(settings, "super_admin_emails", ["admin@example.com"])
        with session_factory() as session:
            identity = EmployerIdentity(clerk_user_id="clerk-admin", email="admin@example.com")
            emp = get_or_create_employer(session, identity)
            assert emp.role == "super_admin"

        # Second login after email removed from env: should downgrade to None
        monkeypatch.setattr(settings, "super_admin_emails", [])
        with session_factory() as session:
            identity = EmployerIdentity(clerk_user_id="clerk-admin", email="admin@example.com")
            emp = get_or_create_employer(session, identity)
            assert emp.role is None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _session_override(factory):
    def override():
        s = factory()
        try:
            yield s
        finally:
            s.close()
    return override


def _raise_403():
    from fastapi import HTTPException, status
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")


def _raise_401():
    from fastapi import HTTPException, status
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Super admin authentication required")
