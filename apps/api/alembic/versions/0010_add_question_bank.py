"""add question bank

Revision ID: 0010_question_bank
Revises: 0009_adaptive_blueprints
Create Date: 2026-06-30
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_question_bank"
down_revision = "0009_adaptive_blueprints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=120), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("license", sa.String(length=120), nullable=False),
        sa.Column("recommended_use", sa.String(length=80), nullable=False),
        sa.Column("attribution_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="approved_for_drafts", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "question_bank_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="needs_review", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("question_type", sa.String(length=80), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("role_tags", sa.JSON(), nullable=False),
        sa.Column("skill_tags", sa.JSON(), nullable=False),
        sa.Column("cognitive_tags", sa.JSON(), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False),
        sa.Column("seniority", sa.String(length=80), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("expected_evidence", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("generated_by", sa.String(length=80), server_default="seed", nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["employers.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["question_sources.id"]),
    )
    op.create_index("ix_question_bank_questions_source_id", "question_bank_questions", ["source_id"])
    op.create_index("ix_question_bank_questions_status", "question_bank_questions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_question_bank_questions_status", table_name="question_bank_questions")
    op.drop_index("ix_question_bank_questions_source_id", table_name="question_bank_questions")
    op.drop_table("question_bank_questions")
    op.drop_table("question_sources")
