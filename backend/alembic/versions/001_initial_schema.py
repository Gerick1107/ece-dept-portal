"""Initial portal schema

Revision ID: 001
Revises:
Create Date: 2026-05-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("faculty", "hod", "admin", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    upload_status = sa.Enum("uploaded", "processed", "cleared", name="uploadstatus")
    eval_status = sa.Enum("pending", "completed", "failed", "archived", name="evaluationstatus")

    op.create_table(
        "copo_marks_uploads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("status", upload_status, nullable=False),
        sa.Column("parse_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_copo_marks_uploads_user_id"), "copo_marks_uploads", ["user_id"], unique=False)

    op.create_table(
        "copo_evaluation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("marks_upload_id", sa.Integer(), nullable=True),
        sa.Column("course_title", sa.String(length=512), nullable=False),
        sa.Column("mapping_filename", sa.String(length=512), nullable=True),
        sa.Column("evaluation_type", sa.String(length=32), nullable=False),
        sa.Column("status", eval_status, nullable=False),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("comparison_summary", sa.JSON(), nullable=True),
        sa.Column("excel_result_path", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("marks_cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["marks_upload_id"], ["copo_marks_uploads.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_copo_evaluation_runs_public_id"), "copo_evaluation_runs", ["public_id"], unique=True)
    op.create_index(op.f("ix_copo_evaluation_runs_user_id"), "copo_evaluation_runs", ["user_id"], unique=False)

    op.create_table(
        "copo_result_archives",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("archive_path", sa.String(length=1024), nullable=False),
        sa.Column("archive_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["copo_evaluation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_copo_result_archives_evaluation_run_id"),
        "copo_result_archives",
        ["evaluation_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("copo_result_archives")
    op.drop_table("copo_evaluation_runs")
    op.drop_table("copo_marks_uploads")
    op.drop_table("users")
