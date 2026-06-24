"""Course catalog dedup, new contribution tables, allocation re-pointing."""

from __future__ import annotations

import csv
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "030_fixes_and_additions"
down_revision: str | None = "029_course_allocation"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("course_allocations", "course_catalog_id"):
        op.add_column(
            "course_allocations",
            sa.Column("course_catalog_id", sa.Integer(), sa.ForeignKey("course_catalog.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_course_allocations_course_catalog_id", "course_allocations", ["course_catalog_id"])

    if not _has_table("course_code_aliases"):
        op.create_table(
            "course_code_aliases",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("course_catalog.id", ondelete="CASCADE"), nullable=False),
            sa.Column("variant_code", sa.String(256), nullable=False),
            sa.Column("variant_name", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_course_code_aliases_course_id", "course_code_aliases", ["course_id"])
        op.create_index("ix_course_code_aliases_variant_code", "course_code_aliases", ["variant_code"])

    if not _has_table("faculty_services"):
        op.create_table(
            "faculty_services",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("faculty_name", sa.String(200), nullable=False),
            sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True),
            sa.Column("year", sa.String(20), nullable=True),
            sa.Column("exact_year", sa.Integer(), nullable=True),
            sa.Column("scope", sa.String(32), nullable=False),
            sa.Column("role_title", sa.String(500), nullable=False),
            sa.Column("organization", sa.String(500), nullable=True),
            sa.Column("start_date", sa.String(32), nullable=True),
            sa.Column("end_date", sa.String(32), nullable=True),
            sa.Column("duration_text", sa.String(128), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_faculty_services_faculty_name", "faculty_services", ["faculty_name"])
        op.create_index("ix_faculty_services_scope", "faculty_services", ["scope"])

    if not _has_table("phd_students"):
        op.create_table(
            "phd_students",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("faculty_name", sa.String(200), nullable=False),
            sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True),
            sa.Column("as_of_year", sa.Integer(), nullable=True),
            sa.Column("students_graduated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ongoing_phd_students", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_phd_students_faculty_name", "phd_students", ["faculty_name"])

    bind = op.get_bind()
    from sqlalchemy.orm import sessionmaker

    from app.course_allocation.services.catalog_migration_service import run_catalog_repoint_migration
    from app.utils.faculty_csv_sync import sync_faculty_services_csv, sync_phd_students_csv

    Session = sessionmaker(bind=bind)
    db = Session()
    try:
        run_catalog_repoint_migration(db)
        sync_faculty_services_csv(db)
        sync_phd_students_csv(db)
    finally:
        db.close()


def downgrade() -> None:
    if _has_table("phd_students"):
        op.drop_table("phd_students")
    if _has_table("faculty_services"):
        op.drop_table("faculty_services")
    if _has_table("course_code_aliases"):
        op.drop_table("course_code_aliases")
    if _has_column("course_allocations", "course_catalog_id"):
        op.drop_index("ix_course_allocations_course_catalog_id", table_name="course_allocations")
        op.drop_column("course_allocations", "course_catalog_id")
