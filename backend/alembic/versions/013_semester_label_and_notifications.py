"""semester_label on CO-PO tables + notifications module."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012_copo_run_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "copo_evaluation_runs",
        sa.Column("semester_label", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "copo_run_analytics_snapshots",
        sa.Column("semester_label", sa.String(length=32), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE copo_evaluation_runs
            SET semester_label = JSON_UNQUOTE(JSON_EXTRACT(result_summary, '$.semester_label'))
            WHERE semester_label IS NULL
              AND result_summary IS NOT NULL
              AND JSON_EXTRACT(result_summary, '$.semester_label') IS NOT NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE copo_run_analytics_snapshots s
            INNER JOIN copo_evaluation_runs r ON r.public_id = s.public_id
            SET s.semester_label = COALESCE(r.semester_label, s.semester_label)
            """
        )
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "notification_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notification_recipients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("email_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id", "user_id", name="uq_notification_recipient"),
    )
    op.create_index("ix_notification_recipients_user_id", "notification_recipients", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_recipients_user_id", table_name="notification_recipients")
    op.drop_table("notification_recipients")
    op.drop_table("notification_attachments")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_column("copo_run_analytics_snapshots", "semester_label")
    op.drop_column("copo_evaluation_runs", "semester_label")
