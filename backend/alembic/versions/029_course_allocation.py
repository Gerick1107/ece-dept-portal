"""Course allocation module tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "029_course_allocation"
down_revision: Union[str, None] = "028_faculty_requirements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if not _has_table("course_catalog"):
        op.create_table(
            "course_catalog",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("course_code", sa.String(256), nullable=False),
            sa.Column("course_name", sa.Text(), nullable=False),
            sa.Column("ug_pg", sa.String(16), nullable=False),
            sa.Column("core_elective", sa.String(32), nullable=False),
            sa.Column("is_first_year", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("course_code"),
        )
        op.create_index("ix_course_catalog_course_code", "course_catalog", ["course_code"])

    if not _has_table("faculty_name_aliases"):
        op.create_table(
            "faculty_name_aliases",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("variant_name", sa.String(200), nullable=False),
            sa.Column("canonical_name", sa.String(200), nullable=False),
            sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("variant_name"),
        )
        op.create_index("ix_faculty_name_aliases_variant_name", "faculty_name_aliases", ["variant_name"])

    if not _has_table("course_allocations"):
        op.create_table(
            "course_allocations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("faculty_name", sa.String(200), nullable=False),
            sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True),
            sa.Column("semester", sa.String(32), nullable=False),
            sa.Column("academic_year", sa.String(16), nullable=False),
            sa.Column("course_code", sa.String(256), nullable=False),
            sa.Column("course_name", sa.Text(), nullable=False),
            sa.Column("ug_pg", sa.String(16), nullable=False),
            sa.Column("core_elective", sa.String(32), nullable=False),
            sa.Column("is_first_year", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("first_year_course_name", sa.String(256), nullable=True),
            sa.Column("source", sa.String(32), nullable=False, server_default="historical"),
            sa.Column("is_faculty_placeholder", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_course_allocations_semester", "course_allocations", ["semester"])
        op.create_index("ix_course_allocations_faculty_id", "course_allocations", ["faculty_id"])
        op.create_index("ix_course_allocations_academic_year", "course_allocations", ["academic_year"])


def downgrade() -> None:
    for table in ("course_allocations", "faculty_name_aliases", "course_catalog"):
        if _has_table(table):
            op.drop_table(table)
