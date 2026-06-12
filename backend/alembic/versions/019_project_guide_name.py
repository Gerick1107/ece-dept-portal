"""Add guide_name column to projects for spreadsheet guide display."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "019_project_guide_name"
down_revision: Union[str, None] = "018_section_affiliations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("projects", "guide_name"):
        op.add_column("projects", sa.Column("guide_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    if _has_column("projects", "guide_name"):
        op.drop_column("projects", "guide_name")
