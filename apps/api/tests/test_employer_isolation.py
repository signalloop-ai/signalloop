"""Employer isolation tests.

Uses a single TestClient with a switchable EmployerContext so tests can make
requests as different employers without fighting over app.dependency_overrides.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.auth import get_current_employer
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import Employer
from signalloop_api.submissions import get_hidden_test_runner
from tests.conftest import EmployerContext, make_employer


class PassingHiddenTestRunner:
    def run(self, files: dict[str, str], hidden_tests: dict[str, str]) -> dict:
        return {
            "status": "passed",
            "exit_code": 0,
            "stdout": "collected 1 item\n1 passed",
            "stderr": "",
            "duration_ms": 25,
        }


@pytest.fixture()
def employer_a(session_factory: sessionmaker[Session]) -> Employer:
    return make_employer(session_factory, clerk_user_id="employer-a", email="employer-a@example.com")


@pytest.fixture()
def employer_b(session_factory: sessionmaker[Session]) -> Employer:
    return make_employer(session_factory, clerk_user_id="employer-b", email="employer-b@example.com")


@pytest.fixture()
def isolation_client(
    session_factory: sessionmaker[Session],
    employer_context: EmployerContext,
) -> Generator[TestClient, None, None]:
    """Client with PassingHiddenTestRunner wired in, plus the switchable employer."""

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
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def create_attempt(client: TestClient, candidate_email: str) -> dict:
    response = client.post("/assessment-attempts", json={"candidate_email": candidate_email})
    assert response.status_code == 201
    return response.json()


def submit_attempt(client: TestClient, invite_token: str) -> None:
    response = client.post(
        f"/candidate/invites/{invite_token}/submit",
        json={
            "files": {"task_api/main.py": "print('final')\n"},
            "final_explanation": "Submitted for tenant isolation test.",
            "decision_log": "Ownership should be enforced by employer.",
        },
    )
    assert response.status_code == 201


def test_attempt_list_is_scoped_to_current_employer(
    isolation_client: TestClient,
    employer_context: EmployerContext,
    employer_a: Employer,
    employer_b: Employer,
) -> None:
    employer_context.current = employer_a
    attempt_a = create_attempt(isolation_client, "candidate-a@example.com")

    employer_context.current = employer_b
    attempt_b = create_attempt(isolation_client, "candidate-b@example.com")

    employer_context.current = employer_a
    response_a = isolation_client.get("/assessment-attempts")

    employer_context.current = employer_b
    response_b = isolation_client.get("/assessment-attempts")

    assert response_a.status_code == 200
    assert [a["attempt_id"] for a in response_a.json()] == [attempt_a["attempt_id"]]
    assert response_b.status_code == 200
    assert [a["attempt_id"] for a in response_b.json()] == [attempt_b["attempt_id"]]


def test_employer_cannot_generate_or_fetch_another_employers_report(
    isolation_client: TestClient,
    employer_context: EmployerContext,
    employer_a: Employer,
    employer_b: Employer,
) -> None:
    employer_context.current = employer_a
    attempt_a = create_attempt(isolation_client, "candidate-a@example.com")
    submit_attempt(isolation_client, attempt_a["invite_token"])

    generated = isolation_client.post(f"/assessment-attempts/{attempt_a['attempt_id']}/evidence-report")
    assert generated.status_code == 201

    employer_context.current = employer_b
    cross_generate = isolation_client.post(f"/assessment-attempts/{attempt_a['attempt_id']}/evidence-report")
    cross_fetch = isolation_client.get(f"/assessment-attempts/{attempt_a['attempt_id']}/evidence-report")

    assert cross_generate.status_code == 404
    assert cross_fetch.status_code == 404


def test_unauthenticated_request_is_rejected() -> None:
    response = TestClient(app).get("/assessment-attempts")
    assert response.status_code == 401


def test_candidate_invite_routes_do_not_require_employer_auth(
    isolation_client: TestClient,
    employer_context: EmployerContext,
    employer_a: Employer,
) -> None:
    employer_context.current = employer_a
    created = create_attempt(isolation_client, "candidate-a@example.com")

    response = TestClient(app).get(f"/candidate/invites/{created['invite_token']}")

    assert response.status_code == 200
    assert response.json()["attempt_id"] == created["attempt_id"]
