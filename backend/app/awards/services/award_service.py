from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.awards.models.entities import FacultyAward


def list_awards(
    db: Session,
    *,
    query: str | None = None,
    year: str | None = None,
) -> list[FacultyAward]:
    return list_awards_filtered(db, query=query, year=year)


def list_awards_filtered(
    db: Session,
    *,
    query: str | None = None,
    year: str | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_names: list[str] | None = None,
) -> list[FacultyAward]:
    stmt = select(FacultyAward).order_by(
        FacultyAward.faculty_name.asc(), FacultyAward.year.desc(), FacultyAward.id.asc()
    )
    if year:
        stmt = stmt.where(FacultyAward.year == year.strip())
    if year_from:
        stmt = stmt.where(FacultyAward.year >= year_from.strip())
    if year_to:
        stmt = stmt.where(FacultyAward.year <= year_to.strip())
    if faculty_names:
        names = [n.strip() for n in faculty_names if n and n.strip()]
        if names:
            stmt = stmt.where(FacultyAward.faculty_name.in_(names))
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            FacultyAward.faculty_name.ilike(q) | FacultyAward.award.ilike(q)
        )
    return list(db.scalars(stmt).all())


def list_distinct_years(db: Session) -> list[str]:
    rows = db.scalars(select(FacultyAward.year).distinct().order_by(FacultyAward.year.desc())).all()
    return [r for r in rows if r]


def list_faculty_with_awards(db: Session) -> list[str]:
    rows = db.scalars(
        select(FacultyAward.faculty_name).distinct().order_by(FacultyAward.faculty_name.asc())
    ).all()
    return [r for r in rows if r]


def get_award(db: Session, award_id: int) -> FacultyAward | None:
    return db.get(FacultyAward, award_id)


def create_award(db: Session, faculty_name: str, year: str, award: str) -> FacultyAward:
    name = faculty_name.strip()
    yr = year.strip()
    text = award.strip()
    if not name or not yr or not text:
        raise ValueError("Faculty name, year, and award are required")
    row = FacultyAward(faculty_name=name, year=yr, award=text)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_award(db: Session, row: FacultyAward, faculty_name: str, year: str, award: str) -> FacultyAward:
    name = faculty_name.strip()
    yr = year.strip()
    text = award.strip()
    if not name or not yr or not text:
        raise ValueError("Faculty name, year, and award are required")
    row.faculty_name = name
    row.year = yr
    row.award = text
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_award(db: Session, row: FacultyAward) -> None:
    db.delete(row)
    db.commit()
