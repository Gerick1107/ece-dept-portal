from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.moderation.models.entities import QuestionPaper
from app.utils.storage_paths import resolve_storage_path

VALID_SEMESTERS = ("Winter", "Monsoon")


def _papers_dir() -> Path:
    path = Path(get_settings().upload_dir).parent / "moderation-question-papers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_question_paper_file(filename: str, content: bytes) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    dest = _papers_dir() / f"{uuid.uuid4().hex[:10]}_{safe}"
    dest.write_bytes(content)
    return str(dest.resolve())


def list_papers_for_course(
    db: Session,
    course_id: int,
    *,
    year: int | None = None,
    sort: str = "desc",
) -> list[QuestionPaper]:
    stmt = select(QuestionPaper).where(QuestionPaper.course_id == course_id)
    if year is not None:
        stmt = stmt.where(QuestionPaper.year == year)
    order = QuestionPaper.year.desc() if sort == "desc" else QuestionPaper.year.asc()
    stmt = stmt.order_by(order, QuestionPaper.semester.asc())
    return list(db.scalars(stmt).all())


def paper_to_dict(row: QuestionPaper) -> dict:
    return {
        "id": row.id,
        "course_id": row.course_id,
        "faculty_name": row.faculty_name,
        "year": row.year,
        "semester": row.semester,
        "original_filename": row.original_filename,
        "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
    }


def get_paper(db: Session, paper_id: int) -> QuestionPaper | None:
    return db.get(QuestionPaper, paper_id)


def create_paper(
    db: Session,
    *,
    course_id: int,
    faculty_name: str,
    year: int,
    semester: str,
    filename: str,
    content: bytes,
    uploaded_by: int | None,
) -> QuestionPaper:
    if semester not in VALID_SEMESTERS:
        raise ValueError("semester must be Winter or Monsoon")
    if not faculty_name.strip():
        raise ValueError("Faculty name is required")
    if year < 2000 or year > 2100:
        raise ValueError("Enter a valid year")
    storage_path = save_question_paper_file(filename, content)
    row = QuestionPaper(
        course_id=course_id,
        faculty_name=faculty_name.strip(),
        year=year,
        semester=semester,
        original_filename=filename,
        storage_path=storage_path,
        uploaded_by=uploaded_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_paper_file(row: QuestionPaper) -> None:
    path = resolve_storage_path(row.storage_path)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def delete_paper(db: Session, row: QuestionPaper) -> None:
    delete_paper_file(row)
    db.delete(row)
    db.commit()


def list_distinct_years(db: Session, course_id: int) -> list[int]:
    rows = db.scalars(
        select(QuestionPaper.year).where(QuestionPaper.course_id == course_id).distinct()
    ).all()
    return sorted({int(r) for r in rows}, reverse=True)