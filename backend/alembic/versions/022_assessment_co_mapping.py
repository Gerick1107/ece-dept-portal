"""Add assessments and assessment_co_mapping for LLM insights CO linkage."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

down_revision: Union[str, None] = "021_ece_eve_projects"
revision: str = "022_assessment_co_mapping"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("assessment_type", sa.String(length=64), nullable=True),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("semester", sa.String(length=50), nullable=False),
        sa.Column("section_label", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"], ["copo_evaluation_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessments_evaluation_run_id", "assessments", ["evaluation_run_id"])
    op.create_index("ix_assessments_course_id", "assessments", ["course_id"])

    op.create_table(
        "assessment_co_mapping",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("semester", sa.String(length=50), nullable=False),
        sa.Column("co_label", sa.String(length=50), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=True),
        sa.Column("weightage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_co_mapping_assessment_id", "assessment_co_mapping", ["assessment_id"])
    op.create_index("ix_assessment_co_mapping_course_id", "assessment_co_mapping", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_assessment_co_mapping_course_id", table_name="assessment_co_mapping")
    op.drop_index("ix_assessment_co_mapping_assessment_id", table_name="assessment_co_mapping")
    op.drop_table("assessment_co_mapping")
    op.drop_index("ix_assessments_course_id", table_name="assessments")
    op.drop_index("ix_assessments_evaluation_run_id", table_name="assessments")
    op.drop_table("assessments")
