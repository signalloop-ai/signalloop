"""add attempt configuration

Revision ID: 0003_add_attempt_configuration
Revises: 0002_create_audit_events
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_attempt_configuration"
down_revision: Union[str, None] = "0002_create_audit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_attempts",
        sa.Column("assessment_level", sa.String(length=50), server_default="standard", nullable=False),
    )
    op.add_column(
        "assessment_attempts",
        sa.Column("timing_mode", sa.String(length=50), server_default="untimed", nullable=False),
    )
    op.add_column(
        "assessment_attempts",
        sa.Column("duration_minutes", sa.Integer(), server_default="90", nullable=False),
    )
    op.add_column("assessment_attempts", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("assessment_attempts", "expires_at")
    op.drop_column("assessment_attempts", "duration_minutes")
    op.drop_column("assessment_attempts", "timing_mode")
    op.drop_column("assessment_attempts", "assessment_level")
