"""Add ece_eve_projects table mirroring projects for ECE/EVE branch filter."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021_ece_eve_projects"
down_revision: Union[str, None] = "020_fix_sanjit_kaul_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ece_eve_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_title", sa.String(length=1024), nullable=False),
        sa.Column("project_type", sa.String(length=50), nullable=False),
        sa.Column("semesters", sa.Text(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("guide_name", sa.String(length=255), nullable=True),
        sa.Column("co_guide", sa.String(length=255), nullable=True),
        sa.Column("course_code", sa.String(length=20), nullable=True),
        sa.Column("course_name", sa.String(length=100), nullable=True),
        sa.Column("admission_year", sa.String(length=20), nullable=True),
        sa.Column("program_definition", sa.String(length=200), nullable=True),
        sa.Column("program_specialization", sa.String(length=200), nullable=True),
        sa.Column("student_roll_nos", sa.Text(), nullable=False),
        sa.Column("student_names", sa.Text(), nullable=False),
        sa.Column("credit", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("upload_batch_id", sa.Integer(), nullable=True),
        sa.Column("sdg_review_status", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["upload_batch_id"], ["project_uploads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ece_eve_projects_project_type", "ece_eve_projects", ["project_type"])
    op.create_index("ix_ece_eve_projects_faculty_id", "ece_eve_projects", ["faculty_id"])
    op.create_index("ix_ece_eve_projects_course_code", "ece_eve_projects", ["course_code"])
    op.create_index("ix_ece_eve_projects_semesters", "ece_eve_projects", ["semesters"], mysql_length=128)
    op.create_index(
        "ix_ece_eve_projects_program_specialization",
        "ece_eve_projects",
        ["program_specialization"],
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO ece_eve_projects (
                project_title, project_type, semesters, faculty_id, guide_name, co_guide,
                course_code, course_name, admission_year, program_definition,
                program_specialization, student_roll_nos, student_names, credit,
                upload_batch_id, sdg_review_status, created_at, updated_at
            )
            SELECT
                project_title, project_type, semesters, faculty_id, guide_name, co_guide,
                course_code, course_name, admission_year, program_definition,
                program_specialization, student_roll_nos, student_names, credit,
                upload_batch_id, sdg_review_status, created_at, updated_at
            FROM projects
            WHERE UPPER(TRIM(program_specialization)) IN ('ECE', 'EVE')
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_ece_eve_projects_program_specialization", table_name="ece_eve_projects")
    op.drop_index("ix_ece_eve_projects_semesters", table_name="ece_eve_projects")
    op.drop_index("ix_ece_eve_projects_course_code", table_name="ece_eve_projects")
    op.drop_index("ix_ece_eve_projects_faculty_id", table_name="ece_eve_projects")
    op.drop_index("ix_ece_eve_projects_project_type", table_name="ece_eve_projects")
    op.drop_table("ece_eve_projects")
