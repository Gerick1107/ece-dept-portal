"""copo_run_analytics_snapshots — preserve result_summary and scope_summary across purge."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_copo_run_analytics"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "copo_run_analytics_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("course_title", sa.String(length=512), nullable=False),
        sa.Column("evaluation_type", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("run_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "preserved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index(
        "ix_copo_run_analytics_snapshots_public_id",
        "copo_run_analytics_snapshots",
        ["public_id"],
        unique=True,
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO copo_run_analytics_snapshots
                (public_id, user_id, course_title, evaluation_type, scope_summary, result_summary, run_created_at)
            SELECT
                public_id, user_id, course_title, evaluation_type, scope_summary, result_summary, created_at
            FROM copo_evaluation_runs
            WHERE result_summary IS NOT NULL OR scope_summary IS NOT NULL
            ON DUPLICATE KEY UPDATE
                scope_summary = VALUES(scope_summary),
                result_summary = VALUES(result_summary),
                run_created_at = VALUES(run_created_at)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_copo_run_analytics_snapshots_public_id", table_name="copo_run_analytics_snapshots")
    op.drop_table("copo_run_analytics_snapshots")
