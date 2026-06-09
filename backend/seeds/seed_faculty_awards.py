"""Seed faculty_awards from bundled JSON. Safe to re-run (skips duplicates)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.awards.models.entities import FacultyAward
from app.database.session import SessionLocal

DATA_PATH = Path(__file__).resolve().parent / "data" / "faculty_awards.json"


def seed_faculty_awards(db: Session) -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing seed data: {DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    inserted = 0
    skipped = 0
    for row in payload:
        faculty_name = row["faculty_name"].strip()
        year = row["year"].strip()
        award = row["award"].strip()
        existing = db.scalar(
            select(FacultyAward).where(
                FacultyAward.faculty_name == faculty_name,
                FacultyAward.year == year,
                FacultyAward.award == award,
            )
        )
        exact_year = row.get("exact_year")
        awarded_by = (row.get("awarded_by") or "").strip() or None
        if existing:
            if exact_year is not None and existing.exact_year != exact_year:
                existing.exact_year = int(exact_year)
            if awarded_by and existing.awarded_by != awarded_by:
                existing.awarded_by = awarded_by
            skipped += 1
            continue
        db.add(
            FacultyAward(
                faculty_name=faculty_name,
                year=year,
                award=award,
                exact_year=int(exact_year) if exact_year is not None else None,
                awarded_by=awarded_by,
            )
        )
        inserted += 1
    db.commit()  # includes backfills on skipped duplicate rows
    return {"inserted": inserted, "skipped": skipped, "total": len(payload)}


def main() -> None:
    db = SessionLocal()
    try:
        result = seed_faculty_awards(db)
        print(f"Faculty awards seed complete: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
