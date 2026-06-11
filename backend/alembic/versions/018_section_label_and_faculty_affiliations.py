"""Add section_label to CO-PO runs and faculty affiliations tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "018_section_affiliations"
down_revision: Union[str, None] = "017_llm_prompt_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def upgrade() -> None:
    if not _has_column("copo_evaluation_runs", "section_label"):
        op.add_column(
            "copo_evaluation_runs",
            sa.Column("section_label", sa.String(length=32), nullable=True),
        )
    if not _has_column("copo_run_analytics_snapshots", "section_label"):
        op.add_column(
            "copo_run_analytics_snapshots",
            sa.Column("section_label", sa.String(length=32), nullable=True),
        )

    if not _has_table("affiliations"):
        op.create_table(
            "affiliations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=512), nullable=False),
            sa.Column("url", sa.String(length=1024), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", "url", name="uq_affiliation_name_url"),
        )
    if _has_table("affiliations") and not _has_index("affiliations", "ix_affiliations_category"):
        op.create_index("ix_affiliations_category", "affiliations", ["category"])

    if not _has_table("faculty_affiliations"):
        op.create_table(
            "faculty_affiliations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("faculty_id", sa.Integer(), nullable=False),
            sa.Column("affiliation_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["affiliation_id"], ["affiliations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("faculty_id", "affiliation_id", name="uq_faculty_affiliation"),
        )
    if _has_table("faculty_affiliations") and not _has_index(
        "faculty_affiliations", "ix_faculty_affiliations_faculty_id"
    ):
        op.create_index("ix_faculty_affiliations_faculty_id", "faculty_affiliations", ["faculty_id"])


def downgrade() -> None:
    if _has_table("faculty_affiliations"):
        if _has_index("faculty_affiliations", "ix_faculty_affiliations_faculty_id"):
            op.drop_index("ix_faculty_affiliations_faculty_id", table_name="faculty_affiliations")
        op.drop_table("faculty_affiliations")
    if _has_table("affiliations"):
        if _has_index("affiliations", "ix_affiliations_category"):
            op.drop_index("ix_affiliations_category", table_name="affiliations")
        op.drop_table("affiliations")
    if _has_column("copo_run_analytics_snapshots", "section_label"):
        op.drop_column("copo_run_analytics_snapshots", "section_label")
    if _has_column("copo_evaluation_runs", "section_label"):
        op.drop_column("copo_evaluation_runs", "section_label")
