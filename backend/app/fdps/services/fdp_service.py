from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.fdps.models.entities import FacultyFdp


def _apply_program_filter(stmt, program_filter: str | None):
    token = (program_filter or "").strip().upper()
    if not token or token == "ALL":
        return stmt
    if token == "NPTEL":
        return stmt.where(FacultyFdp.program.ilike("%NPTEL%"))
    if token in ("MOOC", "MOOG"):
        return stmt.where(
            or_(FacultyFdp.program.ilike("%MOOC%"), FacultyFdp.program.ilike("%MOOG%"))
        )
    return stmt


def list_fdps_filtered(
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
    program_filter: str | None = None,
) -> list[FacultyFdp]:
    stmt = select(FacultyFdp).order_by(
        FacultyFdp.faculty_name.asc(),
        FacultyFdp.exact_year.desc(),
        FacultyFdp.year.desc(),
        FacultyFdp.id.asc(),
    )
    if year:
        stmt = stmt.where(FacultyFdp.year == year.strip())
    if exact_year is not None:
        stmt = stmt.where(FacultyFdp.exact_year == exact_year)
    if exact_year_from is not None:
        stmt = stmt.where(FacultyFdp.exact_year >= exact_year_from)
    if exact_year_to is not None:
        stmt = stmt.where(FacultyFdp.exact_year <= exact_year_to)
    if year_from:
        stmt = stmt.where(FacultyFdp.year >= year_from.strip())
    if year_to:
        stmt = stmt.where(FacultyFdp.year <= year_to.strip())
    if faculty_names:
        names = [n.strip() for n in faculty_names if n and n.strip()]
        if names:
            stmt = stmt.where(FacultyFdp.faculty_name.in_(names))
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            FacultyFdp.faculty_name.ilike(q)
            | FacultyFdp.program.ilike(q)
            | FacultyFdp.description.ilike(q)
        )
    stmt = _apply_program_filter(stmt, program_filter)
    return list(db.scalars(stmt).all())


def list_distinct_years(db: Session) -> list[str]:
    rows = db.scalars(select(FacultyFdp.year).distinct().order_by(FacultyFdp.year.desc())).all()
    return [r for r in rows if r]


def list_distinct_exact_years(db: Session) -> list[int]:
    rows = db.scalars(
        select(FacultyFdp.exact_year)
        .where(FacultyFdp.exact_year.isnot(None))
        .distinct()
        .order_by(FacultyFdp.exact_year.desc())
    ).all()
    return [int(r) for r in rows if r is not None]


def list_faculty_with_fdps(db: Session) -> list[str]:
    rows = db.scalars(
        select(FacultyFdp.faculty_name).distinct().order_by(FacultyFdp.faculty_name.asc())
    ).all()
    return [r for r in rows if r]


def get_fdp(db: Session, fdp_id: int) -> FacultyFdp | None:
    return db.get(FacultyFdp, fdp_id)


def create_fdp(
    db: Session,
    faculty_name: str,
    year: str,
    program: str,
    description: str,
    *,
    exact_year: int | None = None,
    no_of_days: int | None = None,
    no_of_attendees: int | None = None,
) -> FacultyFdp:
    name = faculty_name.strip()
    yr = year.strip()
    prog = program.strip()
    desc = description.strip()
    if not name or not yr or not prog or not desc:
        raise ValueError("Faculty name, year, program, and description are required")
    row = FacultyFdp(
        faculty_name=name,
        year=yr,
        program=prog,
        description=desc,
        exact_year=exact_year,
        no_of_days=no_of_days,
        no_of_attendees=no_of_attendees,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_fdp(
    db: Session,
    row: FacultyFdp,
    faculty_name: str,
    year: str,
    program: str,
    description: str,
    *,
    exact_year: int | None = None,
    no_of_days: int | None = None,
    no_of_attendees: int | None = None,
) -> FacultyFdp:
    name = faculty_name.strip()
    yr = year.strip()
    prog = program.strip()
    desc = description.strip()
    if not name or not yr or not prog or not desc:
        raise ValueError("Faculty name, year, program, and description are required")
    row.faculty_name = name
    row.year = yr
    row.program = prog
    row.description = desc
    row.exact_year = exact_year
    row.no_of_days = no_of_days
    row.no_of_attendees = no_of_attendees
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_fdp(db: Session, row: FacultyFdp) -> None:
    db.delete(row)
    db.commit()
