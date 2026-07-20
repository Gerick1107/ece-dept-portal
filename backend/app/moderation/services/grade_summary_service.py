from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.moderation.models.entities import GradeCriterion


def list_grade_criteria(
    db: Session, *, course_code: str | None = None, semester: str | None = None
) -> list[GradeCriterion]:
    stmt = select(GradeCriterion).order_by(GradeCriterion.max_marks.desc())
    if course_code:
        stmt = stmt.where(GradeCriterion.course_code == course_code.strip())
    if semester:
        stmt = stmt.where(GradeCriterion.semester == semester.strip())
    return list(db.scalars(stmt).all())


def create_grade_criterion(db: Session, data: dict) -> GradeCriterion:
    course_code = (data.get("course_code") or "").strip()
    semester = (data.get("semester") or "").strip()
    grade_letter = (data.get("grade_letter") or "").strip()
    if not course_code or not semester or not grade_letter:
        raise ValueError("course_code, semester, and grade_letter are required")
    min_marks = float(data.get("min_marks") or 0)
    max_marks = float(data.get("max_marks") or 0)
    if min_marks > max_marks:
        raise ValueError("min_marks cannot exceed max_marks")
    row = GradeCriterion(
        course_code=course_code,
        semester=semester,
        grade_letter=grade_letter,
        min_marks=min_marks,
        max_marks=max_marks,
        remarks=(data.get("remarks") or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_grade_criterion(db: Session, row: GradeCriterion, data: dict) -> GradeCriterion:
    if "grade_letter" in data and data["grade_letter"]:
        row.grade_letter = data["grade_letter"].strip()
    if "min_marks" in data and data["min_marks"] is not None:
        row.min_marks = float(data["min_marks"])
    if "max_marks" in data and data["max_marks"] is not None:
        row.max_marks = float(data["max_marks"])
    if row.min_marks > row.max_marks:
        raise ValueError("min_marks cannot exceed max_marks")
    if "remarks" in data:
        row.remarks = (data.get("remarks") or "").strip() or None
    db.commit()
    db.refresh(row)
    return row


def delete_grade_criterion(db: Session, row: GradeCriterion) -> None:
    db.delete(row)
    db.commit()


def get_grade_criterion(db: Session, criterion_id: int) -> GradeCriterion | None:
    return db.get(GradeCriterion, criterion_id)