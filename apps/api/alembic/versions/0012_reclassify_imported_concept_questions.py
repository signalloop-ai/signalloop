"""Reclassify imported concept questions.

Revision ID: 0012_concept_question_types
Revises: 0011_question_package_status
Create Date: 2026-07-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0012_concept_question_types"
down_revision: Union[str, None] = "0011_question_package_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE question_bank_questions
        SET question_type = 'technical_concept'
        WHERE generated_by = 'source_import'
          AND source_id IN (
              SELECT id FROM question_sources
              WHERE source_id IN (
                  'alexey_data_science_interviews',
                  'lydia_js_questions',
                  'sudheerj_react_questions',
                  'trimstray_sysadmin_skills'
              )
          )
        """
    )
    op.execute(
        """
        UPDATE question_bank_questions
        SET question_type = 'technical_concept'
        WHERE generated_by = 'source_import'
          AND source_id IN (
              SELECT id FROM question_sources
              WHERE source_id = 'h5bp_frontend_questions'
          )
          AND CAST(provenance AS TEXT) LIKE '%javascript-questions.md%'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE question_bank_questions
        SET question_type = 'communication'
        WHERE question_type = 'technical_concept'
          AND generated_by = 'source_import'
          AND source_id IN (
              SELECT id FROM question_sources
              WHERE source_id IN ('lydia_js_questions', 'sudheerj_react_questions')
          )
        """
    )
    op.execute(
        """
        UPDATE question_bank_questions
        SET question_type = 'communication'
        WHERE question_type = 'technical_concept'
          AND generated_by = 'source_import'
          AND source_id IN (
              SELECT id FROM question_sources
              WHERE source_id = 'h5bp_frontend_questions'
          )
          AND CAST(provenance AS TEXT) LIKE '%javascript-questions.md%'
        """
    )
    op.execute(
        """
        UPDATE question_bank_questions
        SET question_type = 'tradeoff_judgment'
        WHERE question_type = 'technical_concept'
          AND generated_by = 'source_import'
          AND source_id IN (
              SELECT id FROM question_sources
              WHERE source_id = 'alexey_data_science_interviews'
          )
        """
    )
    op.execute(
        """
        UPDATE question_bank_questions
        SET question_type = 'system_design'
        WHERE question_type = 'technical_concept'
          AND generated_by = 'source_import'
          AND source_id IN (
              SELECT id FROM question_sources
              WHERE source_id = 'trimstray_sysadmin_skills'
          )
        """
    )
