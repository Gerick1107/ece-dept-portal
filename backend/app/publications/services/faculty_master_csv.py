"""Keep faculty_master.csv in sync when faculty are created/updated via the UI."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_ASSETS
from app.publications.constants.defaults import FACULTY_CSV_COLUMNS
from app.publications.models import Faculty

FACULTY_MASTER_CSV = DATA_ASSETS / "faculty_master.csv"


def faculty_master_csv_path() -> Path:
    DATA_ASSETS.mkdir(parents=True, exist_ok=True)
    return FACULTY_MASTER_CSV


def _row_from_faculty(faculty: Faculty) -> dict[str, str]:
    return {
        "id": str(faculty.id),
        "name": faculty.name or "",
        "designation": faculty.designation or "",
        "department": faculty.department or "",
        "scholar_id": faculty.scholar_id or "",
        "join_year": "" if faculty.join_year is None else str(faculty.join_year),
        "leave_year": "" if faculty.leave_year is None else str(faculty.leave_year),
        "photo_url": faculty.photo_url or "",
        "profile_link": faculty.profile_link or "",
    }


def rewrite_faculty_master_csv(db: Session, csv_path: Path | None = None) -> Path:
    path = csv_path or faculty_master_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = db.scalars(select(Faculty).order_by(Faculty.id.asc())).all()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FACULTY_CSV_COLUMNS))
        writer.writeheader()
        for faculty in rows:
            writer.writerow(_row_from_faculty(faculty))
    return path


def upsert_faculty_master_csv_row(faculty: Faculty, csv_path: Path | None = None) -> Path:
    """Insert or update one faculty row in faculty_master.csv (create file if missing)."""
    path = csv_path or faculty_master_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                existing.append({col: (row.get(col) or "") for col in FACULTY_CSV_COLUMNS})

    payload = _row_from_faculty(faculty)
    replaced = False
    for idx, row in enumerate(existing):
        if (row.get("scholar_id") or "").strip() == faculty.scholar_id or (
            row.get("id") or ""
        ).strip() == str(faculty.id):
            existing[idx] = payload
            replaced = True
            break
    if not replaced:
        existing.append(payload)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FACULTY_CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(existing)
    return path
