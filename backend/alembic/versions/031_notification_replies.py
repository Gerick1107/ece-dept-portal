"""Notification faculty replies with optional attachments."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "031_notification_replies"
down_revision: Union[str, None] = "030_fixes_and_additions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def upgrade() -> None:
    if not _has_table("notification_replies"):
        op.create_table(
            "notification_replies",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("recipient_id", sa.Integer(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["recipient_id"], ["notification_recipients.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notification_replies_recipient_id", "notification_replies", ["recipient_id"])

    if not _has_table("notification_reply_attachments"):
        op.create_table(
            "notification_reply_attachments",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("reply_id", sa.Integer(), nullable=False),
            sa.Column("original_filename", sa.String(length=512), nullable=False),
            sa.Column("storage_path", sa.String(length=1024), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["reply_id"], ["notification_replies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    if _has_table("notification_reply_attachments"):
        op.drop_table("notification_reply_attachments")
    if _has_table("notification_replies"):
        op.drop_index("ix_notification_replies_recipient_id", table_name="notification_replies")
        op.drop_table("notification_replies")
