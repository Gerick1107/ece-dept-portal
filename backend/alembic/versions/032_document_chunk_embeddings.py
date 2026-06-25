"""Add embedding_json column to document_chunks for semantic RAG retrieval."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "032_document_chunk_embeddings"
down_revision: Union[str, None] = "031_notification_replies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("document_chunks", "embedding_json"):
        op.add_column("document_chunks", sa.Column("embedding_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_column("document_chunks", "embedding_json"):
        op.drop_column("document_chunks", "embedding_json")
