"""Meetings with dual agenda/minutes files."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "027_meetings_dual_files"
down_revision: Union[str, None] = "026_faculty_contributions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_table("meetings"):
        op.create_table(
            "meetings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("document_type", sa.String(32), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("meeting_title", sa.String(512), nullable=False),
            sa.Column("meeting_date", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_meetings_document_type", "meetings", ["document_type"])
        op.create_index("ix_meetings_year", "meetings", ["year"])

    if not _has_table("meeting_files"):
        op.create_table(
            "meeting_files",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("file_role", sa.String(16), nullable=False),
            sa.Column("file_name", sa.String(512), nullable=False),
            sa.Column("file_path", sa.String(1024), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("meeting_id", "file_role", name="uq_meeting_file_role"),
        )
        op.create_index("ix_meeting_files_meeting_id", "meeting_files", ["meeting_id"])

    if _has_table("document_chunks") and not _has_column("document_chunks", "meeting_file_id"):
        op.add_column(
            "document_chunks",
            sa.Column("meeting_file_id", sa.Integer(), nullable=True),
        )

    bind = op.get_bind()
    if _has_table("portal_documents") and _has_table("meetings"):
        existing_meetings = bind.execute(text("SELECT COUNT(*) FROM meetings")).scalar()
        if not existing_meetings:
            rows = bind.execute(
                text(
                    "SELECT id, document_type, year, title, meeting_date, file_name, file_path, description "
                    "FROM portal_documents ORDER BY id"
                )
            ).fetchall()
            for row in rows:
                doc_id, doc_type, year, title, meeting_date, file_name, file_path, description = row
                result = bind.execute(
                    text(
                        "INSERT INTO meetings (document_type, year, meeting_title, meeting_date) "
                        "VALUES (:dt, :yr, :title, :md)"
                    ),
                    {"dt": doc_type, "yr": year, "title": title, "md": meeting_date},
                )
                meeting_id = result.lastrowid
                bind.execute(
                    text(
                        "INSERT INTO meeting_files (meeting_id, file_role, file_name, file_path, description) "
                        "VALUES (:mid, 'minutes', :fn, :fp, :desc)"
                    ),
                    {"mid": meeting_id, "fn": file_name, "fp": file_path, "desc": description},
                )
                if _has_column("document_chunks", "meeting_file_id") and _has_column("document_chunks", "document_id"):
                    bind.execute(
                        text(
                            "UPDATE document_chunks SET meeting_file_id = "
                            "(SELECT id FROM meeting_files WHERE meeting_id = :mid AND file_role = 'minutes') "
                            "WHERE document_id = :did"
                        ),
                        {"mid": meeting_id, "did": doc_id},
                    )

    if _has_table("document_chunks") and _has_column("document_chunks", "document_id"):
        if _has_column("document_chunks", "meeting_file_id"):
            op.alter_column("document_chunks", "meeting_file_id", existing_type=sa.Integer(), nullable=False)
        fks = inspect(bind).get_foreign_keys("document_chunks")
        for fk in fks:
            if "document_id" in (fk.get("constrained_columns") or []):
                op.drop_constraint(fk["name"], "document_chunks", type_="foreignkey")
        op.drop_column("document_chunks", "document_id")

    if _has_table("portal_documents"):
        op.drop_table("portal_documents")


def downgrade() -> None:
    pass
