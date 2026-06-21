"""Re-runnable CSV ↔ DB sync for faculty_awards and faculty_fdps."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_ASSETS

T = TypeVar("T")


def _parse_optional_int(value: str | None) -> int | None:
    raw = (value or "").strip()
    if not raw or raw == "###":
        return None
    return int(raw) if raw.isdigit() else None


def _csv_ids(rows: list[dict[str, str]]) -> set[int]:
    ids: set[int] = set()
    for row in rows:
        raw = (row.get("id") or "").strip()
        if raw.isdigit():
            ids.add(int(raw))
    return ids


def _delete_csv_removed_rows(db: Session, model, csv_ids: set[int]) -> None:
    """Remove DB rows whose id fell within the CSV id range but are no longer in the file."""
    if not csv_ids:
        return
    max_id = max(csv_ids)
    rows = db.scalars(select(model.id).where(model.id <= max_id)).all()
    for row_id in rows:
        if row_id not in csv_ids:
            row = db.get(model, row_id)
            if row:
                db.delete(row)


def sync_csv_rows(
    db: Session,
    csv_path: Path,
    *,
    model,
    natural_key: Callable[[dict[str, str]], tuple | None],
    find_existing: Callable[[Session, tuple], T | None],
    find_by_id: Callable[[Session, int], T | None],
    build_row: Callable[[dict[str, str]], T],
    apply_row: Callable[[T, dict[str, str]], bool],
) -> None:
    if not csv_path.exists():
        return

    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    csv_ids = _csv_ids(rows)
    _delete_csv_removed_rows(db, model, csv_ids)

    for row in rows:
        key = natural_key(row)
        if not key:
            continue
        row_id = _parse_optional_int(row.get("id"))
        existing = find_by_id(db, row_id) if row_id else None
        if not existing:
            existing = find_existing(db, key)
        if existing:
            apply_row(existing, row)
            continue
        db.add(build_row(row))
    db.commit()


def sync_faculty_awards_csv(db: Session, csv_path: Path | None = None) -> None:
    from app.awards.models.entities import FacultyAward

    path = csv_path or (DATA_ASSETS / "faculty_awards.csv")

    def natural_key(row: dict[str, str]) -> tuple | None:
        faculty_name = (row.get("faculty_name") or "").strip()
        year = (row.get("year") or "").strip()
        award = (row.get("award") or "").strip()
        if not faculty_name or not year or not award:
            return None
        return (faculty_name, year, award)

    def find_existing(db: Session, key: tuple) -> FacultyAward | None:
        faculty_name, year, award = key
        return db.scalar(
            select(FacultyAward).where(
                FacultyAward.faculty_name == faculty_name,
                FacultyAward.year == year,
                FacultyAward.award == award,
            )
        )

    def find_by_id(db: Session, row_id: int) -> FacultyAward | None:
        return db.get(FacultyAward, row_id)

    def build_row(row: dict[str, str]) -> FacultyAward:
        row_id = _parse_optional_int(row.get("id"))
        entity = FacultyAward(
            faculty_name=row["faculty_name"].strip(),
            year=row["year"].strip(),
            award=row["award"].strip(),
            exact_year=_parse_optional_int(row.get("exact_year")),
            awarded_by=(row.get("awarded_by") or "").strip() or None,
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: FacultyAward, row: dict[str, str]) -> bool:
        changed = False
        exact_year = _parse_optional_int(row.get("exact_year"))
        awarded_by = (row.get("awarded_by") or "").strip() or None
        if exact_year is not None and existing.exact_year != exact_year:
            existing.exact_year = exact_year
            changed = True
        if awarded_by and existing.awarded_by != awarded_by:
            existing.awarded_by = awarded_by
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=FacultyAward,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


def sync_faculty_fdps_csv(db: Session, csv_path: Path | None = None) -> None:
    from app.fdps.models.entities import FacultyFdp

    path = csv_path or (DATA_ASSETS / "faculty_fdps.csv")

    def natural_key(row: dict[str, str]) -> tuple | None:
        faculty_name = (row.get("faculty_name") or "").strip()
        year = (row.get("year") or "").strip()
        program = (row.get("program") or "").strip()
        description = (row.get("description") or "").strip()
        if not faculty_name or not year or not program or not description:
            return None
        return (faculty_name, year, program, description)

    def find_existing(db: Session, key: tuple) -> FacultyFdp | None:
        faculty_name, year, program, description = key
        return db.scalar(
            select(FacultyFdp).where(
                FacultyFdp.faculty_name == faculty_name,
                FacultyFdp.year == year,
                FacultyFdp.program == program,
                FacultyFdp.description == description,
            )
        )

    def find_by_id(db: Session, row_id: int) -> FacultyFdp | None:
        return db.get(FacultyFdp, row_id)

    def build_row(row: dict[str, str]) -> FacultyFdp:
        row_id = _parse_optional_int(row.get("id"))
        entity = FacultyFdp(
            faculty_name=row["faculty_name"].strip(),
            year=row["year"].strip(),
            exact_year=_parse_optional_int(row.get("exact_year")),
            program=row["program"].strip(),
            description=row["description"].strip(),
            no_of_days=_parse_optional_int(row.get("no_of_days")),
            no_of_attendees=_parse_optional_int(row.get("no_of_attendees")),
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: FacultyFdp, row: dict[str, str]) -> bool:
        changed = False
        exact_year = _parse_optional_int(row.get("exact_year"))
        no_of_days = _parse_optional_int(row.get("no_of_days"))
        no_of_attendees = _parse_optional_int(row.get("no_of_attendees"))
        if exact_year is not None and existing.exact_year != exact_year:
            existing.exact_year = exact_year
            changed = True
        if no_of_days is not None and existing.no_of_days != no_of_days:
            existing.no_of_days = no_of_days
            changed = True
        if no_of_attendees is not None and existing.no_of_attendees != no_of_attendees:
            existing.no_of_attendees = no_of_attendees
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=FacultyFdp,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )
