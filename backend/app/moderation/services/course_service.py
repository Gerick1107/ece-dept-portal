from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.moderation.models.entities import ModerationCourse, QuestionPaper


def list_courses(db: Session, *, query: str | None = None, faculty: str | None = None) -> list[ModerationCourse]:
    stmt = select(ModerationCourse).order_by(ModerationCourse.course_code.asc())
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(or_(ModerationCourse.course_code.ilike(q), ModerationCourse.course_name.ilike(q)))
    if faculty:
        f = f"%{faculty.strip()}%"
        stmt = stmt.where(
            ModerationCourse.id.in_(
                select(QuestionPaper.course_id).where(QuestionPaper.faculty_name.ilike(f))
            )
        )
    return list(db.scalars(stmt).unique().all())


def get_course(db: Session, course_id: int) -> ModerationCourse | None:
    return db.get(ModerationCourse, course_id)


def course_to_dict(row: ModerationCourse) -> dict:
    """Build the API dict directly from the loaded relationship — no extra query."""
    papers = row.papers
    faculty_names = sorted({p.faculty_name for p in papers if p.faculty_name})
    return {
        "id": row.id,
        "course_code": row.course_code,
        "course_name": row.course_name,
        "paper_count": len(papers),
        "faculty_names": faculty_names,
    }


def create_course(db: Session, data: dict) -> ModerationCourse:
    code = (data.get("course_code") or "").strip()
    name = (data.get("course_name") or "").strip()
    if not code or not name:
        raise ValueError("Course code and name are required")
    existing = db.scalar(select(ModerationCourse).where(ModerationCourse.course_code == code))
    if existing:
        raise ValueError(f"Course code '{code}' already exists")
    row = ModerationCourse(course_code=code, course_name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_course(db: Session, row: ModerationCourse, data: dict) -> ModerationCourse:
    if data.get("course_code"):
        row.course_code = data["course_code"].strip()
    if data.get("course_name"):
        row.course_name = data["course_name"].strip()
    db.commit()
    db.refresh(row)
    return row


def delete_course(db: Session, row: ModerationCourse) -> None:
    from app.moderation.services.question_paper_service import delete_paper_file

    for paper in list(row.papers):
        delete_paper_file(paper)
    db.delete(row)
    db.commit()