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
    exact_year: int | None = None,
    exact_year_from: int | None = None,
    exact_year_to: int | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_names: list[str] | None = None,
) -> list[FacultyAward]:
    stmt = select(FacultyAward).order_by(
        FacultyAward.faculty_name.asc(),
        FacultyAward.exact_year.desc(),
        FacultyAward.year.desc(),
        FacultyAward.id.asc(),
    )
    if year:
        stmt = stmt.where(FacultyAward.year == year.strip())
    if exact_year is not None:
        stmt = stmt.where(FacultyAward.exact_year == exact_year)
    if exact_year_from is not None:
        stmt = stmt.where(FacultyAward.exact_year >= exact_year_from)
    if exact_year_to is not None:
        stmt = stmt.where(FacultyAward.exact_year <= exact_year_to)
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


def list_distinct_exact_years(db: Session) -> list[int]:
    rows = db.scalars(
        select(FacultyAward.exact_year)
        .where(FacultyAward.exact_year.isnot(None))
        .distinct()
        .order_by(FacultyAward.exact_year.desc())
    ).all()
    return [int(r) for r in rows if r is not None]


def list_faculty_with_awards(db: Session) -> list[str]:
    rows = db.scalars(
        select(FacultyAward.faculty_name).distinct().order_by(FacultyAward.faculty_name.asc())
    ).all()
    return [r for r in rows if r]


def get_award(db: Session, award_id: int) -> FacultyAward | None:
    return db.get(FacultyAward, award_id)


def create_award(
    db: Session,
    faculty_name: str,
    year: str,
    award: str,
    *,
    exact_year: int | None = None,
    awarded_by: str | None = None,
) -> FacultyAward:
    name = faculty_name.strip()
    yr = year.strip()
    text = award.strip()
    if not name or not yr or not text:
        raise ValueError("Faculty name, year, and award are required")
    row = FacultyAward(
        faculty_name=name,
        year=yr,
        award=text,
        exact_year=exact_year,
        awarded_by=(awarded_by.strip() if awarded_by else None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_award(
    db: Session,
    row: FacultyAward,
    faculty_name: str,
    year: str,
    award: str,
    *,
    exact_year: int | None = None,
    awarded_by: str | None = None,
) -> FacultyAward:
    name = faculty_name.strip()
    yr = year.strip()
    text = award.strip()
    if not name or not yr or not text:
        raise ValueError("Faculty name, year, and award are required")
    row.faculty_name = name
    row.year = yr
    row.award = text
    row.exact_year = exact_year
    row.awarded_by = awarded_by.strip() if awarded_by else None
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_award(db: Session, row: FacultyAward) -> None:
    db.delete(row)
    db.commit()
