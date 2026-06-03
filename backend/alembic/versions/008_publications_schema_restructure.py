"""Restructure publications: new venue/patent columns, drop legacy fields

Revision ID: 008
Revises: 007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS: list[tuple[str, sa.Column]] = [
    ("link", sa.Column("link", sa.String(length=2000), nullable=True)),
    ("publication_date", sa.Column("publication_date", sa.String(length=50), nullable=True)),
    ("pages", sa.Column("pages", sa.String(length=100), nullable=True)),
    ("conference", sa.Column("conference", sa.Text(), nullable=True)),
    ("journal", sa.Column("journal", sa.String(length=500), nullable=True)),
    ("book", sa.Column("book", sa.Text(), nullable=True)),
    ("volume", sa.Column("volume", sa.String(length=50), nullable=True)),
    ("issue", sa.Column("issue", sa.String(length=50), nullable=True)),
    ("is_patent", sa.Column("is_patent", sa.Boolean(), nullable=False, server_default=sa.false())),
    ("inventors", sa.Column("inventors", sa.Text(), nullable=True)),
    ("patent_office", sa.Column("patent_office", sa.String(length=100), nullable=True)),
    ("patent_number", sa.Column("patent_number", sa.String(length=200), nullable=True)),
    ("application_number", sa.Column("application_number", sa.String(length=200), nullable=True)),
]

_DROP_COLUMNS = ("journal_or_conference", "publication_type", "abstract", "doi")

_INDEXES_ON_DROP_COLUMNS = (
    "ix_publications_doi",
    "ix_publications_journal_or_conference",
    "ix_publications_publication_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("publications")}
    indexes = {idx["name"] for idx in inspector.get_indexes("publications")}

    for name, column in _NEW_COLUMNS:
        if name not in columns:
            op.add_column("publications", column)

    for index_name in _INDEXES_ON_DROP_COLUMNS:
        if index_name in indexes:
            op.drop_index(index_name, table_name="publications")

    columns = {col["name"] for col in sa.inspect(bind).get_columns("publications")}
    for name in _DROP_COLUMNS:
        if name in columns:
            op.drop_column("publications", name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("publications")}

    if "journal_or_conference" not in columns:
        op.add_column("publications", sa.Column("journal_or_conference", sa.String(length=512), nullable=True))
    if "publication_type" not in columns:
        op.add_column("publications", sa.Column("publication_type", sa.String(length=128), nullable=True))
    if "abstract" not in columns:
        op.add_column("publications", sa.Column("abstract", sa.Text(), nullable=True))
    if "doi" not in columns:
        op.add_column("publications", sa.Column("doi", sa.String(length=255), nullable=True))

    indexes = {idx["name"] for idx in inspector.get_indexes("publications")}
    if "ix_publications_doi" not in indexes:
        op.create_index("ix_publications_doi", "publications", ["doi"], unique=False)
    if "ix_publications_journal_or_conference" not in indexes:
        op.create_index(
            "ix_publications_journal_or_conference",
            "publications",
            ["journal_or_conference"],
            unique=False,
        )
    if "ix_publications_publication_type" not in indexes:
        op.create_index("ix_publications_publication_type", "publications", ["publication_type"], unique=False)

    columns = {col["name"] for col in sa.inspect(bind).get_columns("publications")}
    for name, _ in reversed(_NEW_COLUMNS):
        if name in columns:
            op.drop_column("publications", name)
