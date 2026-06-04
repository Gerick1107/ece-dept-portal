"""Seed the courses table from bundled JSON (57 ECE courses). Safe to re-run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.course import Course
from app.database.session import SessionLocal

DATA_PATH = Path(__file__).resolve().parent / "data" / "courses.json"


def seed_courses(db: Session) -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing seed data: {DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    inserted = 0
    skipped = 0
    for row in payload:
        code = row["course_code"].strip()
        name = row["course_name"].strip()
        existing = db.scalar(select(Course).where(Course.course_code == code))
        if existing:
            skipped += 1
            continue
        db.add(Course(course_code=code, course_name=name))
        inserted += 1
    db.commit()
    return {"inserted": inserted, "skipped": skipped, "total": len(payload)}


def main() -> None:
    db = SessionLocal()
    try:
        result = seed_courses(db)
        print(f"Courses seed complete: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
