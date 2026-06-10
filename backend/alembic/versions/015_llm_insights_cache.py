"""llm_insights_cache table for Gemini CO-PO recommendations."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_llm_insights_cache"
down_revision: Union[str, None] = "014_faculty_awards_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_insights_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=512), nullable=False),
        sa.Column("prompt_used", sa.Text(), nullable=True),
        sa.Column("llm_response", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_llm_insights_cache_run_id", "llm_insights_cache", ["run_id"])
    op.create_index("ix_llm_insights_cache_course_id", "llm_insights_cache", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_insights_cache_course_id", table_name="llm_insights_cache")
    op.drop_index("ix_llm_insights_cache_run_id", table_name="llm_insights_cache")
    op.drop_table("llm_insights_cache")
