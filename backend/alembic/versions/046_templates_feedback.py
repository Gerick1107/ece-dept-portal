"""Custom notification templates + faculty feedback."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "046_templates_feedback"
down_revision: Union[str, None] = "045_course_alloc_ug_pg_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("notification_templates"):
        op.create_table(
            "notification_templates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(64), nullable=False, unique=True),
            sa.Column("label", sa.String(256), nullable=False),
            sa.Column("requirement_type", sa.String(64), nullable=False, unique=True),
            sa.Column("subject", sa.String(512), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_notification_templates_requirement_type", "notification_templates", ["requirement_type"])

    if not _has_table("faculty_feedback"):
        op.create_table(
            "faculty_feedback",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_faculty_feedback_user_id", "faculty_feedback", ["user_id"])
        op.create_index("ix_faculty_feedback_is_resolved", "faculty_feedback", ["is_resolved"])


def downgrade() -> None:
    if _has_table("faculty_feedback"):
        op.drop_table("faculty_feedback")
    if _has_table("notification_templates"):
        op.drop_table("notification_templates")
