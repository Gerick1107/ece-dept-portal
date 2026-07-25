"""Course allocation: UG/PG type columns, registered students, drop first-year.

Replaces ug_pg + core_elective with separate ug_type and pg_type (Core/Elective/null).
Removes first-year tracking. Adds registered_students (admin-editable, not in Excel).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "045_course_alloc_ug_pg_types"
down_revision: Union[str, None] = "044_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TYPE_VALUES = {"Core", "Elective", "Core/Elective"}


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def _normalize_type(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if cleaned in _TYPE_VALUES:
        return cleaned
    return None


def _split_ug_pg(ug_pg: str | None, core_elective: str | None) -> tuple[str | None, str | None]:
    level = (ug_pg or "").strip().upper()
    ctype = _normalize_type(core_elective)
    if level == "UG":
        return ctype or "Core", None
    if level == "PG":
        return None, ctype or "Core"
    if level in ("UG/PG", "UGPG"):
        return ctype or "Elective", ctype or "Elective"
    # Unknown — keep both empty rather than inventing data
    return None, None


def _migrate_table(table: str) -> None:
    bind = op.get_bind()
    if not _has_column(table, "ug_type"):
        op.add_column(table, sa.Column("ug_type", sa.String(32), nullable=True))
    if not _has_column(table, "pg_type"):
        op.add_column(table, sa.Column("pg_type", sa.String(32), nullable=True))
    if table == "course_allocations" and not _has_column(table, "registered_students"):
        op.add_column(table, sa.Column("registered_students", sa.Integer(), nullable=True))

    if _has_column(table, "ug_pg") and _has_column(table, "core_elective"):
        rows = bind.execute(text(f"SELECT id, ug_pg, core_elective FROM {table}")).fetchall()
        for row_id, ug_pg, core_elective in rows:
            ug_type, pg_type = _split_ug_pg(ug_pg, core_elective)
            bind.execute(
                text(f"UPDATE {table} SET ug_type = :ug, pg_type = :pg WHERE id = :id"),
                {"ug": ug_type, "pg": pg_type, "id": row_id},
            )

    for col in ("ug_pg", "core_elective", "is_first_year", "first_year_course_name"):
        if _has_column(table, col):
            op.drop_column(table, col)


def _rewrite_csv(path: Path, *, is_allocation: bool) -> None:
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    if "ug_type" in fieldnames:
        return
    out_fields = []
    for f in fieldnames:
        if f in ("ug_pg", "core_elective", "is_first_year", "first_year_course_name"):
            continue
        out_fields.append(f)
        if f == "course_name":
            out_fields.extend(["ug_type", "pg_type"])
            if is_allocation:
                out_fields.append("registered_students")
    if "ug_type" not in out_fields:
        # Fallback if course_name missing
        out_fields = [f for f in fieldnames if f not in ("ug_pg", "core_elective", "is_first_year", "first_year_course_name")]
        insert_at = 1
        out_fields[insert_at:insert_at] = ["ug_type", "pg_type"] + (["registered_students"] if is_allocation else [])

    new_rows = []
    for row in rows:
        ug_type, pg_type = _split_ug_pg(row.get("ug_pg"), row.get("core_elective"))
        new_row = {k: row.get(k, "") for k in out_fields if k not in ("ug_type", "pg_type", "registered_students")}
        new_row["ug_type"] = ug_type or ""
        new_row["pg_type"] = pg_type or ""
        if is_allocation:
            new_row["registered_students"] = row.get("registered_students", "") or ""
        new_rows.append(new_row)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(new_rows)


def upgrade() -> None:
    _migrate_table("course_catalog")
    _migrate_table("course_allocations")

    # Keep on-disk CSV assets in sync so csv_sync does not reintroduce old columns.
    root = Path(__file__).resolve().parents[3]  # repo root (…/NPortal)
    assets = root / "data" / "assets"
    _rewrite_csv(assets / "course_catalog.csv", is_allocation=False)
    _rewrite_csv(assets / "course_allocations.csv", is_allocation=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("course_allocations", "course_catalog"):
        if not _has_column(table, "ug_pg"):
            op.add_column(table, sa.Column("ug_pg", sa.String(16), nullable=False, server_default="UG"))
        if not _has_column(table, "core_elective"):
            op.add_column(table, sa.Column("core_elective", sa.String(32), nullable=False, server_default="Core"))
        if not _has_column(table, "is_first_year"):
            op.add_column(
                table,
                sa.Column("is_first_year", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if table == "course_allocations" and not _has_column(table, "first_year_course_name"):
            op.add_column(table, sa.Column("first_year_course_name", sa.String(256), nullable=True))

        if _has_column(table, "ug_type"):
            rows = bind.execute(text(f"SELECT id, ug_type, pg_type FROM {table}")).fetchall()
            for row_id, ug_type, pg_type in rows:
                has_ug = bool(ug_type)
                has_pg = bool(pg_type)
                if has_ug and has_pg:
                    ug_pg = "UG/PG"
                    ce = ug_type if ug_type == pg_type else "Core/Elective"
                elif has_pg:
                    ug_pg = "PG"
                    ce = pg_type or "Core"
                else:
                    ug_pg = "UG"
                    ce = ug_type or "Core"
                bind.execute(
                    text(f"UPDATE {table} SET ug_pg = :ug_pg, core_elective = :ce WHERE id = :id"),
                    {"ug_pg": ug_pg, "ce": ce, "id": row_id},
                )

        for col in ("ug_type", "pg_type"):
            if _has_column(table, col):
                op.drop_column(table, col)
    if _has_column("course_allocations", "registered_students"):
        op.drop_column("course_allocations", "registered_students")
