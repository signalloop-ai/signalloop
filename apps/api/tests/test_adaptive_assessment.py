from collections.abc import Generator
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.auth import get_current_employer
from signalloop_api.assessment_taxonomy import skills_by_id
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import AssessmentAttempt, AssessmentBlueprint, CandidateProfile, Employer, RoleProfile
from signalloop_api.reports import get_candidate_verification_runner
from signalloop_api.submissions import get_hidden_test_runner
from tests.conftest import EmployerContext, make_employer


REALISTIC_BACKEND_JD = """
Senior Backend Engineer for an AI infrastructure team. The role requires Python,
FastAPI, API design, authorization, multi-tenant APIs, reliability, observability,
PostgreSQL, Kubernetes basics, and strong AI collaboration. The team builds
internal control-plane APIs for provisioning model-serving workloads and needs
engineers who can debug production behavior and make safe product tradeoffs.
"""

REALISTIC_BACKEND_RESUME = """
Backend engineer with 6 years of experience building Python and FastAPI services.
Built internal APIs, Django admin tools, PostgreSQL-backed workflows, Redis caching,
background jobs, and AWS deployments. Uses ChatGPT and Copilot for debugging and
test design. No direct Kubernetes ownership, but collaborated with platform teams.
"""

MANUAL_FIXTURE_CASES = [
    {
        "name": "backend_python_title_standard",
        "title": "Backend Python Engineer",
        "role_family": "backend",
        "seniority": "mid",
        "invite_ready": True,
        "expected_pack_slug": "fastapi_task_api_standard_v2",
        "team_context": "Backend services for internal operations.",
        "jd": "Backend Python Engineer",
        "resume": "Python engineer working on backend services and automated tests.",
    },
    {
        "name": "fastapi_data_engineer_stays_data",
        "title": "FastAPI Data Engineer",
        "role_family": "data",
        "seniority": "mid",
        "invite_ready": False,
        "expected_pack_slug": "future_data_engineering_v1",
        "team_context": "Batch and streaming analytics pipelines.",
        "jd": "FastAPI data engineer building ingestion pipelines, SQL models, and analytics workflows.",
        "resume": "Data engineer with Python, SQL, orchestration, and API experience.",
    },
    {
        "name": "python_ml_engineer_stays_ai",
        "title": "Python ML Engineer",
        "role_family": "ai",
        "seniority": "senior",
        "invite_ready": False,
        "expected_pack_slug": "future_ai_product_engineering_v1",
        "team_context": "Model evaluation and inference pipelines.",
        "jd": "Python machine learning engineer building model evaluation and inference systems.",
        "resume": "Machine learning engineer with Python and production model experience.",
    },
    {
        "name": "supported_advanced_backend",
        "title": "Senior Backend Engineer",
        "role_family": "backend",
        "seniority": "senior",
        "invite_ready": True,
        "team_context": "Control-plane APIs for a multi-tenant AI infrastructure platform.",
        "jd": """
        We are hiring a Senior Backend Engineer for an AI infrastructure team. The role requires Python,
        FastAPI, API design, authorization, multi-tenant APIs, reliability, observability, PostgreSQL,
        Kubernetes basics, and strong AI collaboration.
        """,
        "resume": """
        Backend engineer with 6 years of Python and FastAPI services, internal APIs, PostgreSQL-backed
        workflows, Redis caching, background jobs, and AWS deployments. No direct Kubernetes ownership,
        but collaborated with platform teams on deployments and monitoring.
        """,
    },
    {
        "name": "mostly_unsupported_frontend",
        "title": "Frontend Platform Engineer",
        "role_family": "frontend",
        "seniority": "senior",
        "invite_ready": False,
        "team_context": "Design system and performance work for a B2B SaaS dashboard.",
        "jd": """
        We need a Frontend Platform Engineer with deep React, TypeScript, component design, frontend
        performance, accessibility, form validation, API integration, Playwright coverage, and AI-assisted
        engineering experience.
        """,
        "resume": """
        Frontend engineer with React and TypeScript experience. Built reusable component libraries,
        complex forms, accessibility improvements, Playwright tests, REST API integration, and
        performance profiling.
        """,
    },
    {
        "name": "supported_mid_backend_standard",
        "title": "Backend Engineer",
        "role_family": "backend",
        "seniority": "mid",
        "invite_ready": True,
        "team_context": "Internal task and workflow APIs for operations teams.",
        "jd": """
        We are hiring a Backend Engineer to build Python APIs. The role requires Python, FastAPI, REST API
        design, input validation, error handling, authorization, pytest, and clear communication.
        """,
        "resume": """
        Software engineer with backend experience using Python APIs, FastAPI, Flask, pytest tests for
        endpoint behavior, validation, and error handling, plus basic PostgreSQL experience.
        """,
    },
    {
        "name": "frontend_jd_with_default_backend_controls",
        "title": "Senior Backend Engineer",
        "role_family": "backend",
        "seniority": "senior",
        "invite_ready": False,
        "expected_pack_slug": "future_frontend_platform_v1",
        "team_context": "Design system and performance work for a B2B SaaS dashboard.",
        "jd": """
        We need a Frontend Platform Engineer with deep React, TypeScript, component design, frontend
        performance, accessibility, form validation, API integration, Playwright coverage, and AI-assisted
        engineering experience.
        """,
        "resume": """
        Frontend engineer with React and TypeScript experience. Built reusable component libraries,
        complex forms, accessibility improvements, Playwright tests, REST API integration, and
        performance profiling.
        """,
    },
    {
        "name": "backend_jd_weak_resume_overlap",
        "title": "Backend API Engineer",
        "role_family": "backend",
        "seniority": "mid",
        "invite_ready": True,
        "team_context": "Tenant-scoped workflow APIs for customer operations.",
        "jd": """
        We need a Backend API Engineer with Python, FastAPI, REST API design, authorization, input
        validation, pytest, reliability, multi-tenant workflow APIs, permission debugging, and regression
        tests.
        """,
        "resume": """
        Software engineer with Java, Spring Boot, SQL, and batch data processing experience. Built
        internal admin tools, supported production incidents, and used Python for scripts but has not
        owned FastAPI services.
        """,
    },
    {
        "name": "data_engineering_unsupported",
        "title": "Data Engineer",
        "role_family": "data",
        "seniority": "senior",
        "invite_ready": False,
        "team_context": "Customer analytics pipelines and warehouse quality checks.",
        "jd": """
        We are hiring a Data Engineer to build ETL pipelines, SQL transformations, warehouse models, data
        quality checks, batch pipeline reliability, warehouse concepts, and incident response for broken
        dashboards.
        """,
        "resume": """
        Data engineer with SQL, Airflow, dbt, Snowflake, BigQuery, data quality checks, dashboard
        reliability, ETL pipelines, and dimensional models for revenue analytics.
        """,
    },
    {
        "name": "infra_kubernetes_unsupported",
        "title": "Platform Engineer",
        "role_family": "infra",
        "seniority": "senior",
        "invite_ready": False,
        "team_context": "Kubernetes platform for internal product teams.",
        "jd": """
        We need a Platform Engineer with Kubernetes, Docker, CI/CD, cloud infrastructure, deployment
        automation, monitoring, incident response, reliability, rollout safety, alert quality, and
        production debugging across services.
        """,
        "resume": """
        Platform engineer running Kubernetes clusters, Docker services, GitHub Actions pipelines, AWS
        infrastructure, monitoring dashboards, SLOs, incident response, and Python scripting.
        """,
    },
    {
        "name": "ai_llm_product_engineer_mixed",
        "title": "AI Product Engineer",
        "role_family": "ai",
        "seniority": "senior",
        "invite_ready": True,
        "team_context": "LLM workflow automation and internal copilots.",
        "jd": """
        We are hiring an AI Product Engineer to build LLM API integrations, prompt workflows, RAG systems,
        evaluation harnesses, hallucination guardrails, backend API design, Python, reliability, and AI
        safety judgment.
        """,
        "resume": """
        Engineer with Python backend experience and LLM products. Integrated OpenAI APIs, prompt chains,
        retrieval-augmented generation prototypes, eval scripts, hallucination guardrails, and tests.
        """,
    },
    {
        "name": "candidate_extra_skills_not_required",
        "title": "Backend Engineer",
        "role_family": "backend",
        "seniority": "mid",
        "invite_ready": True,
        "team_context": "Internal workflow API maintenance.",
        "jd": """
        We need a Backend Engineer for Python APIs. Required skills are Python, FastAPI, REST API design,
        input validation, error handling, authorization, pytest, and communication.
        """,
        "resume": """
        Backend engineer with Python and FastAPI experience. Also claims Kubernetes, Terraform, LLM API
        integration, RAG, Redis, PostgreSQL, and model monitoring from side projects.
        """,
    },
    {
        "name": "non_technical_sales_role_out_of_scope",
        "title": "Enterprise Account Executive",
        "role_family": "support",
        "seniority": "senior",
        "invite_ready": False,
        "out_of_scope": True,
        "team_context": "Enterprise sales for a B2B SaaS product.",
        "jd": """
        We are hiring an Enterprise Account Executive to own pipeline generation, discovery calls,
        procurement negotiation, stakeholder mapping, forecasting, and quarterly revenue targets.
        """,
        "resume": """
        Sales professional with experience in enterprise discovery, account planning, negotiation,
        CRM hygiene, MEDDICC qualification, forecasting, and closing expansion revenue.
        """,
    },
    {
        "name": "mobile_engineer_not_on_roadmap",
        "title": "Mobile Engineer",
        "role_family": "frontend",
        "seniority": "senior",
        "invite_ready": False,
        "out_of_scope": True,
        "team_context": "Native consumer mobile application.",
        "jd": """
        We need a Mobile Engineer with Swift, Kotlin, iOS, Android, mobile release management,
        app store deployment, offline sync, and crash analytics experience.
        """,
        "resume": """
        Mobile engineer with Swift, Kotlin, iOS, Android, App Store releases, Google Play releases,
        offline-first sync, Crashlytics, and native performance profiling experience.
        """,
    },
]


class PassingHiddenTestRunner:
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        return {
            "status": "passed",
            "exit_code": 0,
            "stdout": "collected 5 items\n5 passed",
            "stderr": "",
            "duration_ms": 25,
        }


class PassingVerificationRunner:
    def run(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        return {
            "status": "passed",
            "exit_code": 0,
            "stdout": f"collected {len(candidate_tests)} items\n{len(candidate_tests)} passed",
            "stderr": "",
            "duration_ms": 20,
        }


@pytest.fixture()
def adaptive_client(
    session_factory: sessionmaker[Session],
    employer_context: EmployerContext,
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_employer() -> Employer:
        return employer_context.current

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_employer] = override_get_current_employer
    app.dependency_overrides[get_hidden_test_runner] = lambda: PassingHiddenTestRunner()
    app.dependency_overrides[get_candidate_verification_runner] = lambda: PassingVerificationRunner()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def employer_a(session_factory: sessionmaker[Session]) -> Employer:
    return make_employer(session_factory, clerk_user_id="adaptive-a", email="adaptive-a@example.com")


@pytest.fixture()
def employer_b(session_factory: sessionmaker[Session]) -> Employer:
    return make_employer(session_factory, clerk_user_id="adaptive-b", email="adaptive-b@example.com")


def create_realistic_blueprint(client: TestClient) -> dict:
    role_response = client.post(
        "/employer/adaptive/role-profiles",
        json={
            "title": "Senior Backend Engineer",
            "role_family": "backend",
            "seniority": "senior",
            "jd_text": REALISTIC_BACKEND_JD,
            "team_context": "Control-plane APIs for multi-tenant AI infrastructure.",
            "expected_ai_usage": 70,
        },
    )
    assert role_response.status_code == 201
    role = role_response.json()

    candidate_response = client.post(
        "/employer/adaptive/candidate-profiles",
        json={
            "candidate_email": "candidate@example.com",
            "resume_text": REALISTIC_BACKEND_RESUME,
        },
    )
    assert candidate_response.status_code == 201
    candidate = candidate_response.json()

    blueprint_response = client.post(
        "/employer/adaptive/blueprints",
        json={
            "role_profile_id": role["id"],
            "candidate_profile_id": candidate["id"],
            "timing_mode": "timed",
            "evaluator_feedback_mode": "strict",
        },
    )
    assert blueprint_response.status_code == 201
    return blueprint_response.json()


def make_docx_bytes(paragraphs: list[str]) -> bytes:
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as docx:
        docx.writestr("word/document.xml", xml)
    return buffer.getvalue()


def test_realistic_jd_resume_generates_reviewable_advanced_blueprint(
    adaptive_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    blueprint = create_realistic_blueprint(adaptive_client)

    assert blueprint["assessment_level"] == "advanced"
    assert blueprint["assessment_pack_slug"] == "fastapi_task_api_advanced_v1"
    assert blueprint["duration_minutes"] == 120
    assert blueprint["status"] == "draft"
    assert "backend.fastapi" in blueprint["skill_mapping"]["required_overlap"]
    assert "infra.kubernetes" in blueprint["skill_mapping"]["unsupported_required"]
    assert "backend.multi_tenancy" in blueprint["coverage"]["directly_tested"]
    assert any("Kubernetes" in caveat for caveat in blueprint["caveats"])
    assert any(probe["skill_id"] == "infra.kubernetes" for probe in blueprint["follow_up_probes"])

    with session_factory() as session:
        assert session.scalar(select(RoleProfile)).title == "Senior Backend Engineer"
        assert session.scalar(select(CandidateProfile)).candidate_email == "candidate@example.com"
        persisted = session.scalar(select(AssessmentBlueprint))
        assert persisted is not None
        assert persisted.status == "draft"


def test_document_text_upload_extracts_plain_text(adaptive_client: TestClient) -> None:
    response = adaptive_client.post(
        "/employer/adaptive/extract-document-text",
        headers={"X-Filename": "resume.txt", "Content-Type": "application/octet-stream"},
        content=b"Python FastAPI engineer with authorization and pytest experience.",
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Python FastAPI engineer with authorization and pytest experience."


def test_document_text_upload_extracts_docx(adaptive_client: TestClient) -> None:
    response = adaptive_client.post(
        "/employer/adaptive/extract-document-text",
        headers={"X-Filename": "jd.docx", "Content-Type": "application/octet-stream"},
        content=make_docx_bytes([
            "Senior Backend Engineer",
            "Python FastAPI APIs with validation and authorization.",
        ]),
    )

    assert response.status_code == 200
    assert "Senior Backend Engineer" in response.json()["text"]
    assert "Python FastAPI APIs" in response.json()["text"]


def test_document_text_upload_rejects_unsupported_extension(adaptive_client: TestClient) -> None:
    response = adaptive_client.post(
        "/employer/adaptive/extract-document-text",
        headers={"X-Filename": "resume.png", "Content-Type": "application/octet-stream"},
        content=b"not a supported document",
    )

    assert response.status_code == 422
    assert ".txt, .md, .pdf, or .docx" in response.json()["detail"]


@pytest.mark.parametrize("fixture", MANUAL_FIXTURE_CASES, ids=[case["name"] for case in MANUAL_FIXTURE_CASES])
def test_manual_phase5_fixture_blueprints_are_valid(adaptive_client: TestClient, fixture: dict) -> None:
    role_response = adaptive_client.post(
        "/employer/adaptive/role-profiles",
        json={
            "title": fixture["title"],
            "role_family": fixture["role_family"],
            "seniority": fixture["seniority"],
            "jd_text": fixture["jd"],
            "team_context": fixture["team_context"],
            "expected_ai_usage": 70,
        },
    )
    assert role_response.status_code == 201

    candidate_response = adaptive_client.post(
        "/employer/adaptive/candidate-profiles",
        json={
            "candidate_email": f"{fixture['name']}@example.com",
            "resume_text": fixture["resume"],
        },
    )
    assert candidate_response.status_code == 201

    blueprint_response = adaptive_client.post(
        "/employer/adaptive/blueprints",
        json={
            "role_profile_id": role_response.json()["id"],
            "candidate_profile_id": candidate_response.json()["id"],
            "timing_mode": "timed",
            "evaluator_feedback_mode": "strict",
        },
    )

    if fixture.get("out_of_scope"):
        assert blueprint_response.status_code == 422
        assert "assessment" in blueprint_response.json()["detail"]
        return

    assert blueprint_response.status_code == 201
    blueprint = blueprint_response.json()
    if fixture["invite_ready"]:
        assert blueprint["assessment_pack_slug"] in {"fastapi_task_api_standard_v2", "fastapi_task_api_advanced_v1"}
        assert blueprint["assessment_level"] in {"standard", "advanced"}
        if fixture.get("expected_pack_slug"):
            assert blueprint["assessment_pack_slug"] == fixture["expected_pack_slug"]
    else:
        assert blueprint["assessment_pack_slug"].startswith("future_")
        assert blueprint["assessment_level"].startswith("future_")
        assert "planned" in blueprint["coverage"]["label"]
        if fixture.get("expected_pack_slug"):
            assert blueprint["assessment_pack_slug"] == fixture["expected_pack_slug"]
    assert blueprint["duration_minutes"] in {90, 120}
    assert blueprint["rationale"]
    assert blueprint["caveats"]
    assert blueprint["follow_up_probes"]

    known_skill_ids = set(skills_by_id())
    skill_mapping = blueprint["skill_mapping"]
    for bucket in [
        "role_skill_ids",
        "candidate_skill_ids",
        "required_overlap",
        "required_gap",
        "candidate_extra",
        "unsupported_required",
        "unsupported_claimed",
    ]:
        assert set(skill_mapping[bucket]).issubset(known_skill_ids)

    directly_tested = set(blueprint["coverage"]["directly_tested"])
    unsupported = set(skill_mapping["unsupported_required"]) | set(skill_mapping["unsupported_claimed"])
    assert not directly_tested & unsupported


def test_blueprint_must_be_approved_before_invite_creation(adaptive_client: TestClient) -> None:
    blueprint = create_realistic_blueprint(adaptive_client)

    blocked = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/invites", json={})
    approved = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/approve")
    created = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/invites", json={})

    assert blocked.status_code == 409
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert created.status_code == 201
    assert created.json()["invite_token"]


def test_future_blueprint_is_saved_but_not_invite_ready(adaptive_client: TestClient) -> None:
    fixture = next(case for case in MANUAL_FIXTURE_CASES if case["name"] == "mostly_unsupported_frontend")
    role_response = adaptive_client.post(
        "/employer/adaptive/role-profiles",
        json={
            "title": fixture["title"],
            "role_family": fixture["role_family"],
            "seniority": fixture["seniority"],
            "jd_text": fixture["jd"],
            "team_context": fixture["team_context"],
            "expected_ai_usage": 70,
        },
    )
    candidate_response = adaptive_client.post(
        "/employer/adaptive/candidate-profiles",
        json={
            "candidate_email": "future-frontend@example.com",
            "resume_text": fixture["resume"],
        },
    )
    blueprint = adaptive_client.post(
        "/employer/adaptive/blueprints",
        json={
            "role_profile_id": role_response.json()["id"],
            "candidate_profile_id": candidate_response.json()["id"],
            "timing_mode": "timed",
            "evaluator_feedback_mode": "strict",
        },
    ).json()

    approved = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/approve")
    invite = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/invites", json={})

    assert blueprint["assessment_pack_slug"] == "future_frontend_platform_v1"
    assert approved.status_code == 409
    assert invite.status_code == 409
    assert "not invite-ready" in approved.json()["detail"]


def test_blueprint_list_returns_current_employer_recent_blueprints(
    adaptive_client: TestClient,
    employer_context,
    employer_a: Employer,
    employer_b: Employer,
) -> None:
    employer_context.current = employer_a
    first = create_realistic_blueprint(adaptive_client)
    second = create_realistic_blueprint(adaptive_client)

    employer_context.current = employer_b
    other_employer_blueprint = create_realistic_blueprint(adaptive_client)

    employer_context.current = employer_a
    listed = adaptive_client.get("/employer/adaptive/blueprints")

    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()]
    assert ids[:2] == [second["id"], first["id"]]
    assert other_employer_blueprint["id"] not in ids


def test_invite_from_blueprint_links_attempt_and_preserves_candidate_safety(
    adaptive_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    blueprint = create_realistic_blueprint(adaptive_client)
    adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/approve")
    created = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/invites", json={}).json()

    invite = adaptive_client.get(f"/candidate/invites/{created['invite_token']}")

    assert invite.status_code == 200
    body = invite.json()
    assert body["assessment"]["slug"] == "fastapi_task_api_advanced_v1"
    assert "files" in body
    assert "jd_text" not in body
    assert "resume_text" not in body

    with session_factory() as session:
        attempt = session.get(AssessmentAttempt, created["attempt_id"])
        assert attempt is not None
        assert attempt.blueprint_id == blueprint["id"]
        assert attempt.assessment_level == "advanced"
        assert attempt.duration_minutes == 120
        assert attempt.candidate_email == "candidate@example.com"
        persisted = session.get(AssessmentBlueprint, blueprint["id"])
        assert persisted is not None
        assert persisted.status == "used"


def test_blueprint_backed_report_includes_adaptive_context(adaptive_client: TestClient) -> None:
    blueprint = create_realistic_blueprint(adaptive_client)
    adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/approve")
    created = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/invites", json={}).json()
    token = created["invite_token"]
    final_files = {
        "task_api/main.py": "def fixed():\n    return True\n",
        "tests/test_candidate_api.py": "def test_candidate_added():\n    assert True\n",
    }
    submitted = adaptive_client.post(
        f"/candidate/invites/{token}/submit",
        json={
            "files": final_files,
            "final_explanation": "What changed: Fixed authorization and validation paths.\n\nVerification: Added candidate tests.",
            "decision_log": "Chose strict ownership and explicit errors for multi-tenant safety.",
        },
    )
    assert submitted.status_code == 201

    generated = adaptive_client.post(f"/assessment-attempts/{created['attempt_id']}/evidence-report")

    assert generated.status_code == 201
    report = generated.json()["report"]
    adaptive = report["adaptive_context"]
    assert adaptive["blueprint_id"] == blueprint["id"]
    assert adaptive["role"]["title"] == "Senior Backend Engineer"
    assert "infra.kubernetes" in adaptive["skill_mapping"]["unsupported_required"]
    assert any("Kubernetes" in q for q in report["follow_up_questions"])


def test_adaptive_records_are_employer_scoped(
    adaptive_client: TestClient,
    employer_context,
    employer_a: Employer,
    employer_b: Employer,
) -> None:
    employer_context.current = employer_a
    blueprint = create_realistic_blueprint(adaptive_client)

    employer_context.current = employer_b
    fetch = adaptive_client.get(f"/employer/adaptive/blueprints/{blueprint['id']}")
    approve = adaptive_client.post(f"/employer/adaptive/blueprints/{blueprint['id']}/approve")

    assert fetch.status_code == 404
    assert approve.status_code == 404
