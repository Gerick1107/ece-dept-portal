"""Link portal users to a faculty directory record for per-faculty data scoping."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "034_user_faculty_link"
down_revision: Union[str, None] = "033_budget_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("users", "faculty_id"):
        op.add_column(
            "users",
            sa.Column(
                "faculty_id",
                sa.Integer(),
                sa.ForeignKey("faculty.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_users_faculty_id", "users", ["faculty_id"])


def downgrade() -> None:
    if _has_column("users", "faculty_id"):
        op.drop_index("ix_users_faculty_id", table_name="users")
        op.drop_column("users", "faculty_id")
