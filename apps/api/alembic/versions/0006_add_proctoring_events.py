"""add proctoring events

Revision ID: 0006_add_proctoring_events
Revises: 0005_add_evaluator_feedback_mode
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_add_proctoring_events"
down_revision: Union[str, None] = "0005_add_evaluator_feedback_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proctoring_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("assessment_attempts.id"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proctoring_events_attempt_id", "proctoring_events", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_proctoring_events_attempt_id", table_name="proctoring_events")
    op.drop_table("proctoring_events")
