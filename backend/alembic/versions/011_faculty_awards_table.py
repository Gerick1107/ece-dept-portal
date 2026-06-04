"""Create faculty_awards table

Revision ID: 011
Revises: 010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "faculty_awards" in inspector.get_table_names():
        return

    op.create_table(
        "faculty_awards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("faculty_name", sa.String(length=200), nullable=False),
        sa.Column("year", sa.String(length=20), nullable=False),
        sa.Column("award", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faculty_awards_faculty_name", "faculty_awards", ["faculty_name"], unique=False)
    op.create_index("ix_faculty_awards_year", "faculty_awards", ["year"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_faculty_awards_year", table_name="faculty_awards")
    op.drop_index("ix_faculty_awards_faculty_name", table_name="faculty_awards")
    op.drop_table("faculty_awards")
