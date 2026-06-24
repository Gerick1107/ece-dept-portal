"""Faculty requirement tracker + notification requirement_type."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "028_faculty_requirements"
down_revision: Union[str, None] = "027_meetings_dual_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("notifications", "requirement_type"):
        op.add_column("notifications", sa.Column("requirement_type", sa.String(64), nullable=True))

    if not _has_table("faculty_requirements"):
        op.create_table(
            "faculty_requirements",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("faculty_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("requirement_type", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="grey"),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_notification_id", sa.Integer(), sa.ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("reminder_interval_minutes", sa.Integer(), nullable=True),
            sa.Column("next_reminder_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("faculty_user_id", "requirement_type", name="uq_faculty_requirement"),
        )
        op.create_index("ix_faculty_requirements_user", "faculty_requirements", ["faculty_user_id"])


def downgrade() -> None:
    if _has_table("faculty_requirements"):
        op.drop_table("faculty_requirements")
    if _has_column("notifications", "requirement_type"):
        op.drop_column("notifications", "requirement_type")
