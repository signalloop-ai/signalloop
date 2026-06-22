"""
Schema health tests — require the real Postgres database to be running.

These tests catch migration gaps like the one found in manual testing where
migrations 0003 and 0004 were never applied to the real Postgres DB, causing
500s on every employer API call. SQLite-backed tests always passed because
Base.metadata.create_all() builds the full schema regardless of migration state.

Run only when the real Postgres DB is available:

    cd apps/api && uv run pytest tests/test_schema_health.py -v

Skip in CI that does not have Postgres by marking or filtering with:

    pytest -m "not schema_health"
"""

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect

from signalloop_api.database import engine
from signalloop_api.models import Base

pytestmark = [
    pytest.mark.schema_health,
    pytest.mark.skipif(
        os.getenv("RUN_SCHEMA_HEALTH_TESTS") != "1",
        reason="Set RUN_SCHEMA_HEALTH_TESTS=1 to run real Postgres schema checks",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_dir() -> Path:
    return Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_model_tables_exist_in_database() -> None:
    """Every table defined in Base.metadata must exist in the real Postgres DB."""
    inspector = sa_inspect(engine)
    model_tables = set(Base.metadata.tables.keys())
    missing = []
    for table_name in model_tables:
        if not inspector.has_table(table_name):
            missing.append(table_name)
    assert not missing, (
        f"The following tables are missing from the database (migrations not applied?): "
        f"{missing}"
    )


def test_assessment_attempts_has_all_phase2_columns() -> None:
    """
    assessment_attempts must have the Phase 2 columns added in migrations 0003 and 0004.

    If migrations 0003/0004 were never applied, these columns will be absent even though
    the SQLAlchemy model declares them — which causes 500s on every employer API call.
    """
    inspector = sa_inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("assessment_attempts")}
    required_phase2_columns = {
        "assessment_level",
        "timing_mode",
        "duration_minutes",
        "expires_at",
        "submission_mode",
    }
    missing = required_phase2_columns - columns
    assert not missing, (
        f"assessment_attempts is missing Phase 2 columns: {missing}. "
        "Run: cd apps/api && alembic upgrade head"
    )


def test_alembic_migrations_are_up_to_date() -> None:
    """
    `alembic current` must report the current revision as (head).

    A missing (head) label means the DB is behind — i.e. some migration scripts
    have not been applied.
    """
    result = subprocess.run(
        ["alembic", "current"],
        cwd=str(_api_dir()),
        capture_output=True,
        text=True,
        timeout=30,
    )
    combined_output = result.stdout + result.stderr
    assert result.returncode == 0, (
        f"alembic current failed (exit {result.returncode}):\n{combined_output}"
    )
    assert "head" in combined_output.lower(), (
        "alembic current output does not contain 'head' — database is not fully migrated.\n"
        f"Output:\n{combined_output}\n"
        "Run: cd apps/api && alembic upgrade head"
    )
