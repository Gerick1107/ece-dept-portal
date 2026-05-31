from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.publications.constants.defaults import FACULTY_CSV_COLUMNS
from app.publications.models import Faculty
from app.publications.schemas import CsvImportSummary
from app.publications.utils.helpers import infer_active_status, normalize_scholar_id


def _parse_optional_year(value: str | None) -> int | None:
    raw = (value or "").strip()
    if not raw:
        return None
    return int(raw)


def _validate_headers(headers: list[str] | None) -> None:
    if not headers:
        raise ValueError("CSV is empty or missing header row")
    normalized = [h.strip() for h in headers]
    missing = [col for col in FACULTY_CSV_COLUMNS if col not in normalized]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")


def import_faculty_csv(db: Session, csv_path: Path) -> CsvImportSummary:
    inserted = 0
    updated = 0
    skipped = 0
    duplicate_rows = 0
    errors: list[str] = []

    seen_ids: set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_headers(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            try:
                scholar_id = normalize_scholar_id(row.get("scholar_id", ""))
                if not scholar_id:
                    skipped += 1
                    errors.append(f"Row {row_number}: scholar_id is required")
                    continue
                if scholar_id in seen_ids:
                    duplicate_rows += 1
                    skipped += 1
                    continue
                seen_ids.add(scholar_id)

                name = (row.get("name") or "").strip()
                join_year = int((row.get("join_year") or "").strip())
                leave_year = _parse_optional_year(row.get("leave_year"))
                faculty = db.scalar(select(Faculty).where(Faculty.scholar_id == scholar_id))
                payload = {
                    "name": name,
                    "designation": (row.get("designation") or "").strip() or None,
                    "department": (row.get("department") or "").strip() or None,
                    "join_year": join_year,
                    "leave_year": leave_year,
                    "photo_url": (row.get("photo_url") or "").strip() or None,
                    "profile_link": (row.get("profile_link") or "").strip() or None,
                    "is_active": infer_active_status(leave_year),
                }
                if faculty:
                    for key, value in payload.items():
                        setattr(faculty, key, value)
                    updated += 1
                else:
                    db.add(
                        Faculty(
                            scholar_id=scholar_id,
                            **payload,
                        )
                    )
                    inserted += 1
            except Exception as exc:
                skipped += 1
                errors.append(f"Row {row_number}: {exc}")

    db.commit()
    return CsvImportSummary(
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        duplicate_rows=duplicate_rows,
        errors=errors,
    )
