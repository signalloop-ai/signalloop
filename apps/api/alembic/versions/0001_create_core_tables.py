"""create core tables

Revision ID: 0001_create_core_tables
Revises: None
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "assessment_packs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("candidate_path", sa.String(length=500), nullable=False),
        sa.Column("evaluator_path", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employer_id", sa.Integer(), nullable=True),
        sa.Column("assessment_pack_id", sa.Integer(), nullable=False),
        sa.Column("candidate_email", sa.String(length=320), nullable=True),
        sa.Column("invite_token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_pack_id"], ["assessment_packs.id"]),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_token"),
    )
    op.create_table(
        "code_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("code_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("run_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"]),
        sa.ForeignKeyConstraint(["code_snapshot_id"], ["code_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("selected_context", sa.JSON(), nullable=True),
        sa.Column("policy_tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "final_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("code_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("final_explanation", sa.Text(), nullable=False),
        sa.Column("decision_log", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"]),
        sa.ForeignKeyConstraint(["code_snapshot_id"], ["code_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
    )
    op.create_table(
        "evidence_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.String(length=100), nullable=True),
        sa.Column("score_total", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
    )


def downgrade() -> None:
    op.drop_table("evidence_reports")
    op.drop_table("final_submissions")
    op.drop_table("ai_interactions")
    op.drop_table("test_runs")
    op.drop_table("code_snapshots")
    op.drop_table("assessment_attempts")
    op.drop_table("assessment_packs")
    op.drop_table("employers")
