"""Faculty faculty_fdps table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023_faculty_fdps"
down_revision: Union[str, None] = "022_assessment_co_mapping"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faculty_fdps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("faculty_name", sa.String(length=200), nullable=False),
        sa.Column("year", sa.String(length=20), nullable=False),
        sa.Column("exact_year", sa.Integer(), nullable=True),
        sa.Column("program", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("no_of_days", sa.Integer(), nullable=True),
        sa.Column("no_of_attendees", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faculty_fdps_faculty_name", "faculty_fdps", ["faculty_name"])
    op.create_index("ix_faculty_fdps_year", "faculty_fdps", ["year"])
    op.create_index("ix_faculty_fdps_exact_year", "faculty_fdps", ["exact_year"])
    op.create_index("ix_faculty_fdps_program", "faculty_fdps", ["program"])


def downgrade() -> None:
    op.drop_index("ix_faculty_fdps_program", table_name="faculty_fdps")
    op.drop_index("ix_faculty_fdps_exact_year", table_name="faculty_fdps")
    op.drop_index("ix_faculty_fdps_year", table_name="faculty_fdps")
    op.drop_index("ix_faculty_fdps_faculty_name", table_name="faculty_fdps")
    op.drop_table("faculty_fdps")
