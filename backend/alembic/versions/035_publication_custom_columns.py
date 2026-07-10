"""Admin-defined custom publication columns + per-publication custom_fields JSON."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "035_publication_custom_columns"
down_revision: Union[str, None] = "034_user_faculty_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def _has_table(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_column("publications", "custom_fields"):
        op.add_column("publications", sa.Column("custom_fields", sa.Text(), nullable=True))

    if not _has_table("publication_custom_columns"):
        op.create_table(
            "publication_custom_columns",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("key", sa.String(length=64), nullable=False),
            sa.Column("label", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_keys", sa.Text(), nullable=True),
            sa.Column("crossref_field", sa.String(length=64), nullable=True),
            sa.Column("use_llm", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_publication_custom_columns_key",
            "publication_custom_columns",
            ["key"],
            unique=True,
        )
        op.create_index(
            "ix_publication_custom_columns_enabled",
            "publication_custom_columns",
            ["enabled"],
        )


def downgrade() -> None:
    if _has_table("publication_custom_columns"):
        op.drop_index("ix_publication_custom_columns_enabled", table_name="publication_custom_columns")
        op.drop_index("ix_publication_custom_columns_key", table_name="publication_custom_columns")
        op.drop_table("publication_custom_columns")
    if _has_column("publications", "custom_fields"):
        op.drop_column("publications", "custom_fields")
