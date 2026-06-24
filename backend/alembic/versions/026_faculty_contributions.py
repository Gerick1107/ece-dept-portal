"""Faculty contribution tables; retire faculty_fdps."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "026_faculty_contributions"
down_revision: Union[str, None] = "025_ece_eve_mirror"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _contribution_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("faculty_name", sa.String(200), nullable=False),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True),
        sa.Column("year", sa.String(20), nullable=True),
        sa.Column("exact_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    if not _has_table("faculty_memberships"):
        op.create_table(
            "faculty_memberships",
            *_contribution_columns(),
            sa.Column("society_name", sa.String(500), nullable=False),
            sa.Column("grade_position", sa.String(200), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_faculty_memberships_faculty_name", "faculty_memberships", ["faculty_name"])
        op.create_index("ix_faculty_memberships_faculty_id", "faculty_memberships", ["faculty_id"])

    if not _has_table("faculty_resource_person_events"):
        op.create_table(
            "faculty_resource_person_events",
            *_contribution_columns(),
            sa.Column("program_name", sa.String(500), nullable=False),
            sa.Column("event_date", sa.String(128), nullable=False),
            sa.Column("location", sa.String(500), nullable=False),
            sa.Column("organized_by", sa.String(500), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_faculty_resource_person_events_faculty_name", "faculty_resource_person_events", ["faculty_name"])
        op.create_index("ix_faculty_resource_person_events_faculty_id", "faculty_resource_person_events", ["faculty_id"])
        op.create_index("ix_faculty_resource_person_events_year", "faculty_resource_person_events", ["year"])

    if not _has_table("faculty_mooc_development"):
        op.create_table(
            "faculty_mooc_development",
            *_contribution_columns(),
            sa.Column("course_name", sa.String(500), nullable=False),
            sa.Column("platform", sa.String(200), nullable=False),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_faculty_mooc_development_faculty_name", "faculty_mooc_development", ["faculty_name"])
        op.create_index("ix_faculty_mooc_development_faculty_id", "faculty_mooc_development", ["faculty_id"])

    if not _has_table("department_fdp_events"):
        op.create_table(
            "department_fdp_events",
            *_contribution_columns(),
            sa.Column("program_name", sa.String(500), nullable=False),
            sa.Column("event_date", sa.String(128), nullable=False),
            sa.Column("duration", sa.String(128), nullable=False),
            sa.Column("speaker_affiliation", sa.String(500), nullable=True),
            sa.Column("co_speakers", sa.Text(), nullable=True),
            sa.Column("no_of_attendees", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_department_fdp_events_faculty_name", "department_fdp_events", ["faculty_name"])
        op.create_index("ix_department_fdp_events_faculty_id", "department_fdp_events", ["faculty_id"])
        op.create_index("ix_department_fdp_events_year", "department_fdp_events", ["year"])

    if not _has_table("faculty_student_project_support"):
        op.create_table(
            "faculty_student_project_support",
            *_contribution_columns(),
            sa.Column("event_name", sa.String(500), nullable=False),
            sa.Column("event_date", sa.String(128), nullable=False),
            sa.Column("place", sa.String(500), nullable=False),
            sa.Column("website_link", sa.String(1024), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_faculty_student_project_support_faculty_name", "faculty_student_project_support", ["faculty_name"])
        op.create_index("ix_faculty_student_project_support_faculty_id", "faculty_student_project_support", ["faculty_id"])

    if not _has_table("faculty_collaborations"):
        op.create_table(
            "faculty_collaborations",
            *_contribution_columns(),
            sa.Column("collaboration_type", sa.String(200), nullable=False),
            sa.Column("company_place", sa.String(500), nullable=False),
            sa.Column("duration", sa.String(128), nullable=False),
            sa.Column("outcomes", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_faculty_collaborations_faculty_name", "faculty_collaborations", ["faculty_name"])
        op.create_index("ix_faculty_collaborations_faculty_id", "faculty_collaborations", ["faculty_id"])

    if _has_table("faculty_fdps"):
        op.drop_index("ix_faculty_fdps_program", table_name="faculty_fdps")
        op.drop_index("ix_faculty_fdps_exact_year", table_name="faculty_fdps")
        op.drop_index("ix_faculty_fdps_year", table_name="faculty_fdps")
        op.drop_index("ix_faculty_fdps_faculty_name", table_name="faculty_fdps")
        op.drop_table("faculty_fdps")


def downgrade() -> None:
    if not _has_table("faculty_fdps"):
        op.create_table(
            "faculty_fdps",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("faculty_name", sa.String(200), nullable=False),
            sa.Column("year", sa.String(20), nullable=False),
            sa.Column("exact_year", sa.Integer(), nullable=True),
            sa.Column("program", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("no_of_days", sa.Integer(), nullable=True),
            sa.Column("no_of_attendees", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    for table in [
        "faculty_collaborations",
        "faculty_student_project_support",
        "department_fdp_events",
        "faculty_mooc_development",
        "faculty_resource_person_events",
        "faculty_memberships",
    ]:
        if _has_table(table):
            op.drop_table(table)
