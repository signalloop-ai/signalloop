"""add webcam consent

Revision ID: 0007_add_webcam_consent
Revises: 0006_add_proctoring_events
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_add_webcam_consent"
down_revision: Union[str, None] = "0006_add_proctoring_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_attempts",
        sa.Column("webcam_consent", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_attempts", "webcam_consent")
