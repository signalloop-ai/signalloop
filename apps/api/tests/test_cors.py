"""
CORS header tests — including the bug where 500 responses bypass CORS middleware.

FastAPI's generic exception handler returns a JSONResponse directly, which can bypass
CORS middleware. This test suite verifies that every response type carries the
`access-control-allow-origin` header when an Origin header is present.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from signalloop_api.auth import get_current_employer
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import Employer

ORIGIN = "http://127.0.0.1:3000"
ORIGIN_HEADERS = {"origin": ORIGIN}


@pytest.fixture()
def client(
    session_factory: sessionmaker[Session],
    default_employer: Employer,
) -> Generator[TestClient, None, None]:
    # Need raise_server_exceptions=False so 500s are returned, not re-raised
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
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Preflight (OPTIONS)
# ---------------------------------------------------------------------------

def test_preflight_options_returns_200_with_cors_header(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "origin": ORIGIN,
            "access-control-request-method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ORIGIN


# ---------------------------------------------------------------------------
# 2xx responses
# ---------------------------------------------------------------------------

def test_get_health_includes_cors_header(client: TestClient) -> None:
    response = client.get("/health", headers=ORIGIN_HEADERS)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ORIGIN


def test_get_assessment_attempts_includes_cors_header(client: TestClient) -> None:
    response = client.get("/assessment-attempts", headers=ORIGIN_HEADERS)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ORIGIN


def test_post_assessment_attempts_201_includes_cors_header(client: TestClient) -> None:
    response = client.post(
        "/assessment-attempts",
        json={"candidate_email": "cors-test@example.com"},
        headers=ORIGIN_HEADERS,
    )
    assert response.status_code == 201
    assert response.headers.get("access-control-allow-origin") == ORIGIN


# ---------------------------------------------------------------------------
# 4xx responses
# ---------------------------------------------------------------------------

def test_404_unknown_route_includes_cors_header(client: TestClient) -> None:
    response = client.get("/this-route-does-not-exist", headers=ORIGIN_HEADERS)
    assert response.status_code == 404
    assert response.headers.get("access-control-allow-origin") == ORIGIN


def test_422_invalid_body_includes_cors_header(client: TestClient) -> None:
    # duration_minutes=45 is not in {60, 90, 120, 150} — triggers 422
    response = client.post(
        "/assessment-attempts",
        json={"timing_mode": "timed", "duration_minutes": 45},
        headers=ORIGIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.headers.get("access-control-allow-origin") == ORIGIN


# ---------------------------------------------------------------------------
# 500 responses — the bug that was NOT caught by prior tests
# ---------------------------------------------------------------------------

def test_500_response_includes_cors_header(
    session_factory: sessionmaker[Session],
    default_employer: Employer,
) -> None:
    """
    Force a 500 by making get_session raise a RuntimeError after auth succeeds.
    The generic exception handler in main.py returns a JSONResponse directly,
    which previously bypassed CORSMiddleware and omitted the CORS header.
    """

    def broken_get_session() -> Generator[Session, None, None]:
        raise RuntimeError("Simulated database failure for CORS test")
        yield  # make it a generator

    def override_get_current_employer() -> Employer:
        return default_employer

    app.dependency_overrides[get_session] = broken_get_session
    app.dependency_overrides[get_current_employer] = override_get_current_employer
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/assessment-attempts", headers=ORIGIN_HEADERS)
        assert response.status_code == 500
        assert response.headers.get("access-control-allow-origin") == ORIGIN, (
            "CORS header missing on 500 response — "
            "the generic exception handler bypasses CORSMiddleware"
        )
    finally:
        app.dependency_overrides.clear()
