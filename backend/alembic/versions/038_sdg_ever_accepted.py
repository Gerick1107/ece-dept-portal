"""Add sdg_ever_accepted flag for projects that accepted SDGs at least once."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "038_sdg_ever_accepted"
down_revision: Union[str, None] = "037_student_publications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_column("projects", "sdg_ever_accepted"):
        op.add_column(
            "projects",
            sa.Column(
                "sdg_ever_accepted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        # Backfill: any project that currently has confirmed SDGs, or status confirmed.
        op.execute(
            text(
                """
                UPDATE projects
                SET sdg_ever_accepted = 1
                WHERE sdg_review_status = 'confirmed'
                   OR id IN (
                        SELECT DISTINCT project_id
                        FROM project_sdgs
                        WHERE is_confirmed = 1
                   )
                """
            )
        )


def downgrade() -> None:
    if _has_column("projects", "sdg_ever_accepted"):
        op.drop_column("projects", "sdg_ever_accepted")
