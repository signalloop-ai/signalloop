"""add question package status

Revision ID: 0011_question_package_status
Revises: 0010_question_bank
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_question_package_status"
down_revision = "0010_question_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("question_bank_questions") as batch_op:
        batch_op.add_column(sa.Column("package_status", sa.String(length=50), server_default="not_required", nullable=False))
        batch_op.add_column(sa.Column("coding_package_kind", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("coding_package_ref", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("coding_package_notes", sa.Text(), nullable=True))

    op.execute(
        "UPDATE question_bank_questions "
        "SET package_status = 'missing' "
        "WHERE question_type = 'coding' AND package_status = 'not_required'"
    )


def downgrade() -> None:
    with op.batch_alter_table("question_bank_questions") as batch_op:
        batch_op.drop_column("coding_package_notes")
        batch_op.drop_column("coding_package_ref")
        batch_op.drop_column("coding_package_kind")
        batch_op.drop_column("package_status")
