"""BTP projects schema overhaul for department Excel format

Revision ID: 009
Revises: 008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("projects")}

    if "semesters" not in columns:
        op.add_column("projects", sa.Column("semesters", sa.Text(), nullable=True))
    if "student_roll_nos" not in columns:
        op.add_column("projects", sa.Column("student_roll_nos", sa.Text(), nullable=True))
    if "student_names" not in columns:
        op.add_column("projects", sa.Column("student_names", sa.Text(), nullable=True))
    if "course_code" not in columns:
        op.add_column("projects", sa.Column("course_code", sa.String(length=20), nullable=True))
    if "course_name" not in columns:
        op.add_column("projects", sa.Column("course_name", sa.String(length=100), nullable=True))
    if "admission_year" not in columns:
        op.add_column("projects", sa.Column("admission_year", sa.String(length=20), nullable=True))
    if "program_definition" not in columns:
        op.add_column("projects", sa.Column("program_definition", sa.String(length=200), nullable=True))
    if "program_specialization" not in columns:
        op.add_column("projects", sa.Column("program_specialization", sa.String(length=200), nullable=True))

    if "semester" in columns:
        bind.execute(
            sa.text(
                "UPDATE projects SET semesters = semester WHERE semesters IS NULL OR semesters = ''"
            )
        )
        op.drop_index("ix_projects_semester", table_name="projects")
        op.drop_column("projects", "semester")

    bind.execute(
        sa.text(
            """
            UPDATE projects p
            SET student_names = (
                SELECT GROUP_CONCAT(ps.student_name ORDER BY ps.id SEPARATOR ', ')
                FROM project_students ps
                WHERE ps.project_id = p.id
            )
            WHERE (p.student_names IS NULL OR p.student_names = '')
            """
        )
    )
    bind.execute(
        sa.text(
            "UPDATE projects SET student_roll_nos = '' WHERE student_roll_nos IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE projects SET student_names = '' WHERE student_names IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE projects SET semesters = '' WHERE semesters IS NULL"
        )
    )

    op.alter_column("projects", "semesters", existing_type=sa.Text(), nullable=False)
    op.alter_column("projects", "student_roll_nos", existing_type=sa.Text(), nullable=False)
    op.alter_column("projects", "student_names", existing_type=sa.Text(), nullable=False)

    if "status" in columns:
        index_names = {idx["name"] for idx in inspector.get_indexes("projects")}
        if "ix_projects_status" in index_names:
            op.drop_index("ix_projects_status", table_name="projects")
        op.drop_column("projects", "status")

    op.alter_column(
        "projects",
        "project_type",
        existing_type=sa.String(length=16),
        type_=sa.String(length=50),
        existing_nullable=False,
    )

    op.create_index("ix_projects_course_code", "projects", ["course_code"], unique=False)
    op.create_index("ix_projects_semesters", "projects", ["semesters"], unique=False, mysql_length=128)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("projects")}

    if "ix_projects_course_code" in {idx["name"] for idx in inspector.get_indexes("projects")}:
        op.drop_index("ix_projects_course_code", table_name="projects")
    if "ix_projects_semesters" in {idx["name"] for idx in inspector.get_indexes("projects")}:
        op.drop_index("ix_projects_semesters", table_name="projects")

    if "semester" not in columns:
        op.add_column("projects", sa.Column("semester", sa.String(length=128), nullable=True))
        bind.execute(sa.text("UPDATE projects SET semester = semesters"))
        op.alter_column("projects", "semester", existing_type=sa.String(length=128), nullable=False)
        op.create_index("ix_projects_semester", "projects", ["semester"], unique=False)

    if "status" not in columns:
        op.add_column(
            "projects",
            sa.Column("status", sa.String(length=64), nullable=False, server_default="Pending"),
        )
        op.create_index("ix_projects_status", "projects", ["status"], unique=False)

    for col in (
        "semesters",
        "student_roll_nos",
        "student_names",
        "course_code",
        "course_name",
        "admission_year",
        "program_definition",
        "program_specialization",
    ):
        if col in columns:
            op.drop_column("projects", col)

    op.alter_column(
        "projects",
        "project_type",
        existing_type=sa.String(length=50),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
