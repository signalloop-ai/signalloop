"""add evaluator feedback mode

Revision ID: 0005_add_evaluator_feedback_mode
Revises: 0004_add_submission_mode
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_evaluator_feedback_mode"
down_revision: Union[str, None] = "0004_add_submission_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_attempts",
        sa.Column(
            "evaluator_feedback_mode",
            sa.String(length=50),
            nullable=False,
            server_default="strict",
        ),
    )


def downgrade() -> None:
    op.drop_column("assessment_attempts", "evaluator_feedback_mode")
