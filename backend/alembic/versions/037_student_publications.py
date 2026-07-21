"""Alembic: student publications table."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "037_student_publications"
down_revision: Union[str, None] = "036_publication_manual_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("student_publications"):
        op.create_table(
            "student_publications",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(length=1024), nullable=False),
            sa.Column("authors", sa.Text(), nullable=True),
            sa.Column("publication_year", sa.Integer(), nullable=True),
            sa.Column("extra_fields", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_student_publications_title", "student_publications", ["title"])
        op.create_index(
            "ix_student_publications_publication_year",
            "student_publications",
            ["publication_year"],
        )


def downgrade() -> None:
    if _has_table("student_publications"):
        op.drop_index("ix_student_publications_publication_year", table_name="student_publications")
        op.drop_index("ix_student_publications_title", table_name="student_publications")
        op.drop_table("student_publications")
