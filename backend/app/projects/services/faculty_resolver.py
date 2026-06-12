from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user import User
from app.publications.models.entities import Faculty
from app.utils.name_utils import names_match, strip_name_prefix


def _is_ece_faculty(faculty: Faculty) -> bool:
    dept = (faculty.department or "").upper()
    return "ECE" in dept


def _ece_faculty_rows(db: Session) -> list[Faculty]:
    return [f for f in db.scalars(select(Faculty)).all() if _is_ece_faculty(f)]


@dataclass(frozen=True)
class FacultyMatchResult:
    faculty: Faculty
    matched_via: Literal["guide", "co_guide"]


def match_ece_faculty(db: Session, guide_raw: str, co_guide_raw: str | None) -> FacultyMatchResult | None:
    guide = strip_name_prefix(guide_raw)
    co_guide = strip_name_prefix(co_guide_raw) if co_guide_raw else ""
    rows = _ece_faculty_rows(db)

    for faculty in rows:
        if names_match(guide, faculty.name):
            return FacultyMatchResult(faculty=faculty, matched_via="guide")
    if co_guide:
        for faculty in rows:
            if names_match(co_guide, faculty.name):
                return FacultyMatchResult(faculty=faculty, matched_via="co_guide")
    return None


def resolve_faculty_by_name(db: Session, raw_name: str) -> Faculty:
    name = raw_name.strip()
    if not name:
        raise ValueError("Faculty name is required")
    rows = db.scalars(select(Faculty)).all()

    exact = [f for f in rows if names_match(f.name, name)]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"Ambiguous faculty name '{name}' — multiple matches")

    normalized = strip_name_prefix(name).lower()
    partial = [
        f
        for f in rows
        if normalized in strip_name_prefix(f.name).lower()
        or strip_name_prefix(f.name).lower() in normalized
    ]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise ValueError(f"Faculty '{name}' not found in directory — add faculty first or fix spelling")
    raise ValueError(f"Ambiguous faculty name '{name}' — matches: {', '.join(f.name for f in partial[:5])}")


def faculty_for_user(db: Session, user: User) -> Faculty | None:
    if user.role.value == "admin":
        return None
    normalized = strip_name_prefix(user.full_name).lower()
    for faculty in db.scalars(select(Faculty)).all():
        fn = strip_name_prefix(faculty.name).lower()
        if fn == normalized or normalized in fn or fn in normalized:
            return faculty
    return None
