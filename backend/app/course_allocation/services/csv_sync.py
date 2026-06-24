from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_ASSETS
from app.course_allocation.models.entities import CourseAllocation, CourseCatalogEntry, CourseCodeAlias, FacultyNameAlias
from app.course_allocation.services.allocation_faculty_resolver import (
    is_placeholder_name,
    refresh_alias_cache,
    resolve_allocation_faculty,
)
from app.utils.contribution_faculty_resolver import FacultyResolveResult
from app.utils.faculty_csv_sync import _parse_optional_int, sync_csv_rows


def _yes_no(value: str | None) -> bool:
    return (value or "").strip().lower() in ("yes", "true", "1")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


ALLOCATION_FIELDS = [
    "id",
    "faculty_name",
    "semester",
    "academic_year",
    "course_code",
    "course_name",
    "ug_pg",
    "core_elective",
    "is_first_year",
    "first_year_course_name",
    "source",
    "is_faculty_placeholder",
    "created_at",
    "updated_at",
]

CATALOG_FIELDS = [
    "id",
    "course_code",
    "course_name",
    "ug_pg",
    "core_elective",
    "is_first_year",
    "created_at",
    "updated_at",
]

ALIAS_FIELDS = ["id", "variant_name", "canonical_name", "created_at", "updated_at"]

CODE_ALIAS_FIELDS = ["id", "course_id", "variant_code", "variant_name", "created_at", "updated_at"]


def sync_faculty_name_aliases_csv(db: Session) -> None:
    path = DATA_ASSETS / "faculty_name_aliases.csv"

    def natural_key(row: dict[str, str]) -> tuple | None:
        v = (row.get("variant_name") or "").strip()
        if not v:
            return None
        return (v,)

    def find_existing(db: Session, key: tuple):
        return db.scalar(select(FacultyNameAlias).where(FacultyNameAlias.variant_name == key[0]))

    def find_by_id(db: Session, row_id: int):
        return db.get(FacultyNameAlias, row_id)

    def build_row(row: dict[str, str]) -> FacultyNameAlias:
        row_id = _parse_optional_int(row.get("id"))
        entity = FacultyNameAlias(
            variant_name=row["variant_name"].strip(),
            canonical_name=row["canonical_name"].strip(),
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: FacultyNameAlias, row: dict[str, str]) -> bool:
        changed = False
        cn = row["canonical_name"].strip()
        if existing.canonical_name != cn:
            existing.canonical_name = cn
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=FacultyNameAlias,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )
    refresh_alias_cache(db)


def sync_course_catalog_csv(db: Session) -> None:
    path = DATA_ASSETS / "course_catalog.csv"

    def natural_key(row: dict[str, str]) -> tuple | None:
        code = (row.get("course_code") or "").strip()
        if not code:
            return None
        return (code,)

    def find_existing(db: Session, key: tuple):
        return db.scalar(select(CourseCatalogEntry).where(CourseCatalogEntry.course_code == key[0]))

    def find_by_id(db: Session, row_id: int):
        return db.get(CourseCatalogEntry, row_id)

    def build_row(row: dict[str, str]) -> CourseCatalogEntry:
        row_id = _parse_optional_int(row.get("id"))
        entity = CourseCatalogEntry(
            course_code=row["course_code"].strip(),
            course_name=row["course_name"].strip(),
            ug_pg=row["ug_pg"].strip(),
            core_elective=row["core_elective"].strip(),
            is_first_year=_yes_no(row.get("is_first_year")),
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: CourseCatalogEntry, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("course_name", "ug_pg", "core_elective"):
            val = row[attr].strip()
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        fy = _yes_no(row.get("is_first_year"))
        if existing.is_first_year != fy:
            existing.is_first_year = fy
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=CourseCatalogEntry,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


def sync_course_code_aliases_csv(db: Session) -> None:
    path = DATA_ASSETS / "course_code_aliases.csv"
    if not path.exists():
        return

    def natural_key(row: dict[str, str]) -> tuple | None:
        v = (row.get("variant_code") or "").strip()
        if not v:
            return None
        return (v,)

    def find_existing(db: Session, key: tuple):
        return db.scalar(select(CourseCodeAlias).where(CourseCodeAlias.variant_code == key[0]))

    def find_by_id(db: Session, row_id: int):
        return db.get(CourseCodeAlias, row_id)

    def build_row(row: dict[str, str]) -> CourseCodeAlias:
        row_id = _parse_optional_int(row.get("id"))
        course_id = _parse_optional_int(row.get("course_id"))
        entity = CourseCodeAlias(
            course_id=course_id or 0,
            variant_code=row["variant_code"].strip(),
            variant_name=(row.get("variant_name") or "").strip() or None,
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: CourseCodeAlias, row: dict[str, str]) -> bool:
        changed = False
        course_id = _parse_optional_int(row.get("course_id"))
        if course_id is not None and existing.course_id != course_id:
            existing.course_id = course_id
            changed = True
        vn = (row.get("variant_name") or "").strip() or None
        if existing.variant_name != vn:
            existing.variant_name = vn
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=CourseCodeAlias,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


def repoint_allocations_to_catalog(db: Session) -> None:
    from app.course_allocation.services.course_identity_resolver import (
        collapse_repeated_dept_prefix,
        tokenize_course_codes,
    )

    catalog_entries = list(db.scalars(select(CourseCatalogEntry)).all())
    aliases = list(db.scalars(select(CourseCodeAlias)).all())
    variant_to_course: dict[str, CourseCatalogEntry] = {}
    token_to_course: dict[str, CourseCatalogEntry] = {}
    id_to_entry = {e.id: e for e in catalog_entries}
    for entry in catalog_entries:
        variant_to_course[entry.course_code.upper()] = entry
        for tok in tokenize_course_codes(entry.course_code):
            token_to_course[tok] = entry
    for alias in aliases:
        entry = id_to_entry.get(alias.course_id)
        if not entry:
            continue
        variant_to_course[collapse_repeated_dept_prefix(alias.variant_code).upper()] = entry
        for tok in tokenize_course_codes(alias.variant_code):
            token_to_course.setdefault(tok, entry)

    changed = False
    for alloc in db.scalars(select(CourseAllocation)).all():
        code_key = collapse_repeated_dept_prefix(alloc.course_code).upper()
        entry = variant_to_course.get(code_key)
        if not entry:
            for tok in tokenize_course_codes(alloc.course_code):
                entry = token_to_course.get(tok)
                if entry:
                    break
        if entry:
            if alloc.course_catalog_id != entry.id or alloc.course_code != entry.course_code:
                alloc.course_catalog_id = entry.id
                alloc.course_code = entry.course_code
                alloc.course_name = entry.course_name
                alloc.ug_pg = entry.ug_pg
                alloc.core_elective = entry.core_elective
                alloc.is_first_year = entry.is_first_year
                changed = True
    if changed:
        db.commit()


def sync_course_allocations_csv(db: Session) -> None:
    refresh_alias_cache(db)
    path = DATA_ASSETS / "course_allocations.csv"

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        sem = (row.get("semester") or "").strip()
        code = (row.get("course_code") or "").strip()
        name = (row.get("course_name") or "").strip()
        if not sem or not code:
            return None
        return (fn, sem, code, name)

    def find_existing(db: Session, key: tuple):
        fn, sem, code, name = key
        return db.scalar(
            select(CourseAllocation).where(
                CourseAllocation.faculty_name == fn,
                CourseAllocation.semester == sem,
                CourseAllocation.course_code == code,
                CourseAllocation.course_name == name,
            )
        )

    def find_by_id(db: Session, row_id: int):
        return db.get(CourseAllocation, row_id)

    def _apply_faculty(entity: CourseAllocation, faculty_name: str, placeholder: bool) -> None:
        entity.is_faculty_placeholder = placeholder
        if placeholder:
            entity.faculty_id = None
            return
        resolved = resolve_allocation_faculty(db, faculty_name)
        entity.faculty_id = resolved.faculty_id if isinstance(resolved, FacultyResolveResult) else None

    def build_row(row: dict[str, str]) -> CourseAllocation:
        row_id = _parse_optional_int(row.get("id"))
        faculty_name = (row.get("faculty_name") or "").strip()
        placeholder = _yes_no(row.get("is_faculty_placeholder")) or is_placeholder_name(faculty_name)
        entity = CourseAllocation(
            faculty_name=faculty_name,
            semester=row["semester"].strip(),
            academic_year=row["academic_year"].strip(),
            course_code=row["course_code"].strip(),
            course_name=row["course_name"].strip(),
            ug_pg=row["ug_pg"].strip(),
            core_elective=row["core_elective"].strip(),
            is_first_year=_yes_no(row.get("is_first_year")),
            first_year_course_name=(row.get("first_year_course_name") or "").strip() or None,
            source=(row.get("source") or "historical").strip(),
            is_faculty_placeholder=placeholder,
        )
        _apply_faculty(entity, faculty_name, placeholder)
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: CourseAllocation, row: dict[str, str]) -> bool:
        changed = False
        faculty_name = (row.get("faculty_name") or "").strip()
        placeholder = _yes_no(row.get("is_faculty_placeholder")) or is_placeholder_name(faculty_name)
        for attr in (
            "semester",
            "academic_year",
            "course_code",
            "course_name",
            "ug_pg",
            "core_elective",
            "source",
        ):
            val = row[attr].strip()
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        fy = _yes_no(row.get("is_first_year"))
        if existing.is_first_year != fy:
            existing.is_first_year = fy
            changed = True
        fycn = (row.get("first_year_course_name") or "").strip() or None
        if existing.first_year_course_name != fycn:
            existing.first_year_course_name = fycn
            changed = True
        if existing.faculty_name != faculty_name:
            existing.faculty_name = faculty_name
            changed = True
        if existing.is_faculty_placeholder != placeholder:
            existing.is_faculty_placeholder = placeholder
            changed = True
        fid_before = existing.faculty_id
        _apply_faculty(existing, faculty_name, placeholder)
        if existing.faculty_id != fid_before:
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=CourseAllocation,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


def sync_all_course_allocation_csv(db: Session) -> None:
    sync_faculty_name_aliases_csv(db)
    sync_course_catalog_csv(db)
    sync_course_code_aliases_csv(db)
    sync_course_allocations_csv(db)
    repoint_allocations_to_catalog(db)


def write_allocations_csv(db: Session) -> None:
    rows = db.scalars(select(CourseAllocation).order_by(CourseAllocation.id)).all()
    data = [
        {
            "id": str(r.id),
            "faculty_name": r.faculty_name,
            "semester": r.semester,
            "academic_year": r.academic_year,
            "course_code": r.course_code,
            "course_name": r.course_name,
            "ug_pg": r.ug_pg,
            "core_elective": r.core_elective,
            "is_first_year": "Yes" if r.is_first_year else "No",
            "first_year_course_name": r.first_year_course_name or "",
            "source": r.source,
            "is_faculty_placeholder": "Yes" if r.is_faculty_placeholder else "No",
            "created_at": "",
            "updated_at": "",
        }
        for r in rows
    ]
    _write_csv(DATA_ASSETS / "course_allocations.csv", ALLOCATION_FIELDS, data)


def write_catalog_csv(db: Session) -> None:
    rows = db.scalars(select(CourseCatalogEntry).order_by(CourseCatalogEntry.id)).all()
    data = [
        {
            "id": str(r.id),
            "course_code": r.course_code,
            "course_name": r.course_name,
            "ug_pg": r.ug_pg,
            "core_elective": r.core_elective,
            "is_first_year": "Yes" if r.is_first_year else "No",
            "created_at": "",
            "updated_at": "",
        }
        for r in rows
    ]
    _write_csv(DATA_ASSETS / "course_catalog.csv", CATALOG_FIELDS, data)


def write_code_aliases_csv(db: Session) -> None:
    rows = db.scalars(select(CourseCodeAlias).order_by(CourseCodeAlias.id)).all()
    data = [
        {
            "id": str(r.id),
            "course_id": str(r.course_id),
            "variant_code": r.variant_code,
            "variant_name": r.variant_name or "",
            "created_at": "",
            "updated_at": "",
        }
        for r in rows
    ]
    _write_csv(DATA_ASSETS / "course_code_aliases.csv", CODE_ALIAS_FIELDS, data)


def write_aliases_csv(db: Session) -> None:
    rows = db.scalars(select(FacultyNameAlias).order_by(FacultyNameAlias.id)).all()
    data = [
        {
            "id": str(r.id),
            "variant_name": r.variant_name,
            "canonical_name": r.canonical_name,
            "created_at": "",
            "updated_at": "",
        }
        for r in rows
    ]
    _write_csv(DATA_ASSETS / "faculty_name_aliases.csv", ALIAS_FIELDS, data)
