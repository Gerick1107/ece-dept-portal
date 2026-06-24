from __future__ import annotations

import csv

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import DATA_ASSETS
from app.course_allocation.models.entities import CourseAllocation, CourseCatalogEntry, CourseCodeAlias
from app.course_allocation.services.course_identity_resolver import (
    collapse_repeated_dept_prefix,
    tokenize_course_codes,
)
from app.utils.faculty_csv_sync import _parse_optional_int


def _yes_no(value: str | None) -> bool:
    return (value or "").strip().lower() in ("yes", "true", "1")


def run_catalog_repoint_migration(db: Session) -> None:
    """Replace fragmented catalog with deduplicated CSV and re-point allocations."""
    catalog_path = DATA_ASSETS / "course_catalog.csv"
    aliases_path = DATA_ASSETS / "course_code_aliases.csv"
    if not catalog_path.exists():
        return

    allocations = list(db.scalars(select(CourseAllocation)).all())
    db.execute(delete(CourseCodeAlias))
    db.execute(delete(CourseCatalogEntry))
    db.flush()

    catalog_by_id: dict[int, CourseCatalogEntry] = {}
    with catalog_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row_id = _parse_optional_int(row.get("id"))
            entry = CourseCatalogEntry(
                course_code=collapse_repeated_dept_prefix(row["course_code"].strip()),
                course_name=row["course_name"].strip(),
                ug_pg=row["ug_pg"].strip(),
                core_elective=row["core_elective"].strip(),
                is_first_year=_yes_no(row.get("is_first_year")),
            )
            if row_id is not None:
                entry.id = row_id
            db.add(entry)
            db.flush()
            if row_id is not None:
                catalog_by_id[row_id] = entry

    variant_to_course: dict[str, CourseCatalogEntry] = {}
    token_to_course: dict[str, CourseCatalogEntry] = {}
    for entry in db.scalars(select(CourseCatalogEntry)).all():
        catalog_by_id[entry.id] = entry
        for tok in tokenize_course_codes(entry.course_code):
            token_to_course[tok] = entry
        variant_to_course[entry.course_code.strip().upper()] = entry

    if aliases_path.exists():
        with aliases_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                course_id = _parse_optional_int(row.get("course_id"))
                if course_id is None:
                    continue
                catalog_entry = catalog_by_id.get(course_id) or db.get(CourseCatalogEntry, course_id)
                if not catalog_entry:
                    continue
                variant_code = collapse_repeated_dept_prefix(row["variant_code"].strip())
                alias = CourseCodeAlias(
                    course_id=catalog_entry.id,
                    variant_code=variant_code,
                    variant_name=(row.get("variant_name") or "").strip() or None,
                )
                row_id = _parse_optional_int(row.get("id"))
                if row_id is not None:
                    alias.id = row_id
                db.add(alias)
                variant_to_course[variant_code.upper()] = catalog_entry
                for tok in tokenize_course_codes(variant_code):
                    token_to_course.setdefault(tok, catalog_entry)

    for alloc in allocations:
        code_key = collapse_repeated_dept_prefix(alloc.course_code).upper()
        catalog_entry = variant_to_course.get(code_key)
        if not catalog_entry:
            for tok in tokenize_course_codes(alloc.course_code):
                catalog_entry = token_to_course.get(tok)
                if catalog_entry:
                    break
        if catalog_entry:
            alloc.course_catalog_id = catalog_entry.id
            alloc.course_code = catalog_entry.course_code
            alloc.course_name = catalog_entry.course_name
            alloc.ug_pg = catalog_entry.ug_pg
            alloc.core_elective = catalog_entry.core_elective
            alloc.is_first_year = catalog_entry.is_first_year

    db.commit()
