"""Shared fixtures for all API tests.

Tests override get_current_employer so route ownership behavior stays fast and
deterministic while production code still requires Clerk.
"""

from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from signalloop_api.auth import get_current_employer
from signalloop_api.database import get_session
from signalloop_api.main import app
from signalloop_api.models import Base, Employer


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    Base.metadata.drop_all(engine)


def make_employer(session_factory: sessionmaker[Session], *, clerk_user_id: str, email: str) -> Employer:
    """Create an employer in the test DB and return it (detached)."""
    with session_factory() as session:
        employer = Employer(clerk_user_id=clerk_user_id, email=email, company_name=None)
        session.add(employer)
        session.commit()
        session.refresh(employer)
        session.expunge(employer)
        return employer


@dataclass
class EmployerContext:
    """Mutable holder so tests can switch the active employer between requests."""
    current: Employer


@pytest.fixture()
def default_employer(session_factory: sessionmaker[Session]) -> Employer:
    return make_employer(session_factory, clerk_user_id="test-employer", email="test@example.com")


@pytest.fixture()
def employer_context(default_employer: Employer) -> EmployerContext:
    return EmployerContext(current=default_employer)


@pytest.fixture()
def client(
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
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
