from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models.course import Course


def list_courses(db: Session) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.course_code.asc())).all())


def course_display_label(course: Course) -> str:
    return f"{course.course_code}: {course.course_name}"


def create_course(db: Session, course_code: str, course_name: str) -> Course:
    code = course_code.strip()
    name = course_name.strip()
    if not code or not name:
        raise ValueError("Course code and course name are required")
    existing = db.scalar(select(Course).where(Course.course_code == code))
    if existing:
        raise ValueError(f"Course code '{code}' already exists")
    course = Course(course_code=code, course_name=name)
    db.add(course)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(f"Course code '{code}' already exists") from exc
    db.refresh(course)
    return course
