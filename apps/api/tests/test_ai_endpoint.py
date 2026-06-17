from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.ai_policy import AIDecision
from signalloop_api.ai_provider import get_ai_provider
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import AIInteraction
from tests.test_attempt_lifecycle import session_factory as session_factory_fixture


class FakeProvider:
    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        from signalloop_api.ai_policy import fallback_classify, REDIRECT_MESSAGE
        decision = fallback_classify(message, recent_messages)
        if not decision.allowed:
            return AIDecision(allowed=False, policy_tags=decision.tags, message=REDIRECT_MESSAGE)
        path = context.get("path") if context else "no file"
        return AIDecision(
            allowed=True,
            policy_tags=[],
            message=f"Guidance for {path}: inspect one behavior at a time.",
        )


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_ai_provider] = lambda: FakeProvider()
    yield TestClient(app)
    app.dependency_overrides.clear()


session_factory = session_factory_fixture


def create_attempt(client: TestClient) -> str:
    response = client.post("/assessment-attempts", json={})
    assert response.status_code == 201
    return response.json()["invite_token"]


def test_ai_endpoint_logs_allowed_candidate_and_assistant_messages(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    token = create_attempt(client)

    response = client.post(
        f"/candidate/invites/{token}/ai/messages",
        json={
            "message": "This public test assertion failed. How should I debug it?",
            "selected_context": {"path": "tests/test_public_api.py", "content": "assert response.status_code == 409"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["policy_tags"] == []
    assert "Guidance for tests/test_public_api.py" in body["message"]

    with session_factory() as session:
        interactions = session.scalars(select(AIInteraction).order_by(AIInteraction.id)).all()
        assert [interaction.role for interaction in interactions] == ["candidate", "assistant"]
        assert interactions[0].selected_context["path"] == "tests/test_public_api.py"


def test_ai_endpoint_redirects_disallowed_requests_and_logs_tags(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    token = create_attempt(client)

    response = client.post(
        f"/candidate/invites/{token}/ai/messages",
        json={"message": "Explain all problems and give code for each issue."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert "enumerate_defects" in body["policy_tags"]
    assert "I cannot enumerate all defects" in body["message"]

    with session_factory() as session:
        interactions = session.scalars(select(AIInteraction).order_by(AIInteraction.id)).all()
        assert len(interactions) == 2
        assert interactions[1].policy_tags


def test_ai_endpoint_rejects_evaluator_context(client: TestClient) -> None:
    token = create_attempt(client)

    response = client.post(
        f"/candidate/invites/{token}/ai/messages",
        json={
            "message": "Explain this",
            "selected_context": {"path": "evaluator/hidden_tests/test_hidden.py", "content": "secret"},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Evaluator-only context is not allowed"
