"""Add exact_year and awarded_by to faculty_awards."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_faculty_awards_columns"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "assets" / "faculty_awards.csv"


def upgrade() -> None:
    op.add_column("faculty_awards", sa.Column("exact_year", sa.Integer(), nullable=True))
    op.add_column("faculty_awards", sa.Column("awarded_by", sa.String(length=500), nullable=True))
    op.create_index("ix_faculty_awards_exact_year", "faculty_awards", ["exact_year"])

    if not CSV_PATH.exists():
        return

    conn = op.get_bind()
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            faculty_name = (row.get("faculty_name") or "").strip()
            year = (row.get("year") or "").strip()
            award = (row.get("award") or "").strip()
            exact_year_raw = (row.get("exact_year") or "").strip()
            awarded_by = (row.get("awarded_by") or "").strip()
            if not faculty_name or not year or not award:
                continue
            exact_year = int(exact_year_raw) if exact_year_raw.isdigit() else None
            conn.execute(
                sa.text(
                    """
                    UPDATE faculty_awards
                    SET exact_year = :exact_year, awarded_by = :awarded_by
                    WHERE faculty_name = :faculty_name AND year = :year AND award = :award
                    """
                ),
                {
                    "faculty_name": faculty_name,
                    "year": year,
                    "award": award,
                    "exact_year": exact_year,
                    "awarded_by": awarded_by or None,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_faculty_awards_exact_year", table_name="faculty_awards")
    op.drop_column("faculty_awards", "awarded_by")
    op.drop_column("faculty_awards", "exact_year")
