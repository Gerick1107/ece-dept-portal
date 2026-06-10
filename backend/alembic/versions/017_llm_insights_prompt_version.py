"""Add prompt_version to llm_insights_cache for cache invalidation on prompt changes."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_llm_prompt_version"
down_revision: Union[str, None] = "016_llm_insights_run_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_insights_cache",
        sa.Column("prompt_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("llm_insights_cache", "prompt_version")
