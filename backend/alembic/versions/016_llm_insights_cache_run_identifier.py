"""Widen llm_insights_cache keys for course_title + run_identifier lookup."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_llm_insights_run_id"
down_revision: Union[str, None] = "015_llm_insights_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "llm_insights_cache",
        "run_id",
        existing_type=sa.String(length=64),
        type_=sa.String(length=256),
        existing_nullable=False,
    )
    op.alter_column(
        "llm_insights_cache",
        "course_id",
        existing_type=sa.String(length=512),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "llm_insights_cache",
        "run_id",
        existing_type=sa.String(length=256),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
