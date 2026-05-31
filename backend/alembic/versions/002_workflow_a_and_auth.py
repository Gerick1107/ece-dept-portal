"""Workflow A upload metadata and faculty password flags

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "copo_marks_uploads",
        sa.Column("upload_type", sa.String(length=32), nullable=False, server_default="final_consolidated"),
    )
    op.add_column(
        "copo_marks_uploads",
        sa.Column("course_title", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("copo_marks_uploads", "course_title")
    op.drop_column("copo_marks_uploads", "upload_type")
    op.drop_column("users", "must_change_password")
