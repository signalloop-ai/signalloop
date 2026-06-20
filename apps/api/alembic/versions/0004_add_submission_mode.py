"""add submission mode

Revision ID: 0004_add_submission_mode
Revises: 0003_add_attempt_configuration
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_submission_mode"
down_revision: Union[str, None] = "0003_add_attempt_configuration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessment_attempts", sa.Column("submission_mode", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("assessment_attempts", "submission_mode")
