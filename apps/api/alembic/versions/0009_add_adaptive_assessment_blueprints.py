"""add adaptive assessment blueprints

Revision ID: 0009_adaptive_blueprints
Revises: 0008_add_employer_role
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_adaptive_blueprints"
down_revision = "0008_add_employer_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("role_family", sa.String(length=80), nullable=False),
        sa.Column("seniority", sa.String(length=80), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("team_context", sa.Text(), nullable=True),
        sa.Column("expected_ai_usage", sa.Integer(), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("nice_to_have_skills", sa.JSON(), nullable=True),
        sa.Column("extracted_skills", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
    )
    op.create_index("ix_role_profiles_employer_id", "role_profiles", ["employer_id"])

    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("candidate_email", sa.String(length=320), nullable=True),
        sa.Column("resume_text", sa.Text(), nullable=False),
        sa.Column("extracted_skills", sa.JSON(), nullable=False),
        sa.Column("extracted_experience", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
    )
    op.create_index("ix_candidate_profiles_employer_id", "candidate_profiles", ["employer_id"])

    op.create_table(
        "assessment_blueprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("role_profile_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("assessment_pack_slug", sa.String(length=120), nullable=False),
        sa.Column("assessment_level", sa.String(length=50), nullable=False),
        sa.Column("timing_mode", sa.String(length=50), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("evaluator_feedback_mode", sa.String(length=50), nullable=False),
        sa.Column("skill_mapping", sa.JSON(), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.JSON(), nullable=False),
        sa.Column("follow_up_probes", sa.JSON(), nullable=False),
        sa.Column("caveats", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"]),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
        sa.ForeignKeyConstraint(["role_profile_id"], ["role_profiles.id"]),
    )
    op.create_index("ix_assessment_blueprints_employer_id", "assessment_blueprints", ["employer_id"])

    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.add_column(sa.Column("blueprint_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assessment_attempts_blueprint_id",
            "assessment_blueprints",
            ["blueprint_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.drop_constraint("fk_assessment_attempts_blueprint_id", type_="foreignkey")
        batch_op.drop_column("blueprint_id")
    op.drop_index("ix_assessment_blueprints_employer_id", table_name="assessment_blueprints")
    op.drop_table("assessment_blueprints")
    op.drop_index("ix_candidate_profiles_employer_id", table_name="candidate_profiles")
    op.drop_table("candidate_profiles")
    op.drop_index("ix_role_profiles_employer_id", table_name="role_profiles")
    op.drop_table("role_profiles")
