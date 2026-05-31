"""Publications module schema

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faculty",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("scholar_id", sa.String(length=64), nullable=False),
        sa.Column("join_year", sa.Integer(), nullable=False),
        sa.Column("leave_year", sa.Integer(), nullable=True),
        sa.Column("photo_url", sa.String(length=1024), nullable=True),
        sa.Column("profile_link", sa.String(length=1024), nullable=True),
        sa.Column("total_citations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("h_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("i10_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_faculty_department"), "faculty", ["department"], unique=False)
    op.create_index(op.f("ix_faculty_is_active"), "faculty", ["is_active"], unique=False)
    op.create_index(op.f("ix_faculty_join_year"), "faculty", ["join_year"], unique=False)
    op.create_index(op.f("ix_faculty_leave_year"), "faculty", ["leave_year"], unique=False)
    op.create_index(op.f("ix_faculty_name"), "faculty", ["name"], unique=False)
    op.create_index(op.f("ix_faculty_scholar_id"), "faculty", ["scholar_id"], unique=True)

    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("journal_or_conference", sa.String(length=512), nullable=True),
        sa.Column("publisher", sa.String(length=512), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("publication_type", sa.String(length=128), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("scholar_url", sa.String(length=1024), nullable=True),
        sa.Column("pdf_url", sa.String(length=1024), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("is_iiitd_publication", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publications_doi"), "publications", ["doi"], unique=False)
    op.create_index(op.f("ix_publications_is_iiitd_publication"), "publications", ["is_iiitd_publication"], unique=False)
    op.create_index(op.f("ix_publications_journal_or_conference"), "publications", ["journal_or_conference"], unique=False)
    op.create_index(op.f("ix_publications_publication_type"), "publications", ["publication_type"], unique=False)
    op.create_index(op.f("ix_publications_publication_year"), "publications", ["publication_year"], unique=False)
    op.create_index(op.f("ix_publications_source_hash"), "publications", ["source_hash"], unique=True)

    op.create_table(
        "publication_faculty",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("publication_id", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_id"], ["publications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_id", "faculty_id", name="uq_publication_faculty"),
    )
    op.create_index(op.f("ix_publication_faculty_faculty_id"), "publication_faculty", ["faculty_id"], unique=False)
    op.create_index(op.f("ix_publication_faculty_publication_id"), "publication_faculty", ["publication_id"], unique=False)

    op.create_table(
        "scrape_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("new_publications_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scrape_logs_faculty_id"), "scrape_logs", ["faculty_id"], unique=False)
    op.create_index(op.f("ix_scrape_logs_status"), "scrape_logs", ["status"], unique=False)

    op.create_table(
        "blocked_publications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blocked_publications_source_hash"), "blocked_publications", ["source_hash"], unique=True)

    op.create_table(
        "publication_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("publication_id", sa.Integer(), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publication_audit_logs_action"), "publication_audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_publication_audit_logs_publication_id"), "publication_audit_logs", ["publication_id"], unique=False)
    op.create_index(op.f("ix_publication_audit_logs_source_hash"), "publication_audit_logs", ["source_hash"], unique=False)


def downgrade() -> None:
    op.drop_table("publication_audit_logs")
    op.drop_table("blocked_publications")
    op.drop_table("scrape_logs")
    op.drop_table("publication_faculty")
    op.drop_table("publications")
    op.drop_table("faculty")
