"""Manual publication edits, books flag, and repository-link purge support."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "036_publication_manual_overrides"
down_revision: Union[str, None] = "035_publication_custom_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REPO_HOST = "repository.iiitd.edu.in"


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("publications", "manual_overrides"):
        op.add_column("publications", sa.Column("manual_overrides", sa.Text(), nullable=True))
    if not _has_column("publications", "is_manual_book"):
        op.add_column(
            "publications",
            sa.Column("is_manual_book", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_publications_is_manual_book", "publications", ["is_manual_book"])

    # Purge existing repository.iiitd.edu.in publications and tombstone them so sync
    # cannot re-insert them later.
    bind = op.get_bind()
    rows = bind.execute(
        text(
            """
            SELECT id, source_hash, title
            FROM publications
            WHERE LOWER(COALESCE(link, '')) LIKE :pat
               OR LOWER(COALESCE(scholar_url, '')) LIKE :pat
               OR LOWER(COALESCE(pdf_url, '')) LIKE :pat
            """
        ),
        {"pat": f"%{_REPO_HOST}%"},
    ).fetchall()

    for pub_id, source_hash, title in rows:
        exists = bind.execute(
            text("SELECT 1 FROM blocked_publications WHERE source_hash = :h LIMIT 1"),
            {"h": source_hash},
        ).fetchone()
        if not exists:
            bind.execute(
                text(
                    """
                    INSERT INTO blocked_publications (source_hash, title, reason)
                    VALUES (:h, :t, :r)
                    """
                ),
                {
                    "h": source_hash,
                    "t": (title or "")[:1024] or None,
                    "r": "blocked_repository_iiitd",
                },
            )
        bind.execute(
            text(
                """
                INSERT INTO publication_audit_logs (action, publication_id, source_hash, details)
                VALUES ('purge_repository_link', :pid, :h, :d)
                """
            ),
            {
                "pid": pub_id,
                "h": source_hash,
                "d": f"Removed {_REPO_HOST} publication",
            },
        )
        bind.execute(
            text("DELETE FROM publication_faculty WHERE publication_id = :pid"),
            {"pid": pub_id},
        )
        bind.execute(text("DELETE FROM publications WHERE id = :pid"), {"pid": pub_id})


def downgrade() -> None:
    if _has_column("publications", "is_manual_book"):
        op.drop_index("ix_publications_is_manual_book", table_name="publications")
        op.drop_column("publications", "is_manual_book")
    if _has_column("publications", "manual_overrides"):
        op.drop_column("publications", "manual_overrides")
