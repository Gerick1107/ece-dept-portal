from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "042_labs_module"
down_revision: Union[str, None] = "041_moderation_module"  # ← set to your actual latest head
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lab_name", sa.String(200), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("total_seats", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allotted_seats", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labs_lab_name", "labs", ["lab_name"])
    op.create_index("ix_labs_faculty_id", "labs", ["faculty_id"])


def downgrade() -> None:
    op.drop_table("labs")