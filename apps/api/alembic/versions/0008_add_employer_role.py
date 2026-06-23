"""add employer role

Revision ID: 0008_add_employer_role
Revises: 0007_add_webcam_consent
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_add_employer_role"
down_revision: Union[str, None] = "0007_add_webcam_consent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employers",
        sa.Column("role", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("employers", "role")
