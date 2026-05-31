from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user import User
from app.publications.models.entities import Faculty


_HONORIFIC_RE = re.compile(
    r"^(?:prof\.?|professor|dr\.?|mr\.?|ms\.?|mrs\.?|shri\.?|smt\.?)\s+",
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    cleaned = name.strip()
    while True:
        match = _HONORIFIC_RE.match(cleaned)
        if not match:
            break
        cleaned = cleaned[match.end() :].strip()
    return re.sub(r"\s+", " ", cleaned.lower())


def resolve_faculty_by_name(db: Session, raw_name: str) -> Faculty:
    name = raw_name.strip()
    if not name:
        raise ValueError("Faculty name is required")
    normalized = _normalize_name(name)
    rows = db.scalars(select(Faculty)).all()

    def variants(faculty_name: str) -> set[str]:
        base = _normalize_name(faculty_name)
        return {base, f"prof {base}", f"professor {base}", f"dr {base}"}

    exact = [f for f in rows if normalized in variants(f.name) or _normalize_name(f.name) == normalized]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"Ambiguous faculty name '{name}' — multiple matches")

    partial = [
        f
        for f in rows
        if normalized in _normalize_name(f.name) or _normalize_name(f.name) in normalized
    ]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise ValueError(f"Faculty '{name}' not found in directory — add faculty first or fix spelling")
    raise ValueError(f"Ambiguous faculty name '{name}' — matches: {', '.join(f.name for f in partial[:5])}")


def faculty_for_user(db: Session, user: User) -> Faculty | None:
    if user.role.value == "admin":
        return None
    normalized = _normalize_name(user.full_name)
    for faculty in db.scalars(select(Faculty)).all():
        fn = _normalize_name(faculty.name)
        if fn == normalized or normalized in fn or fn in normalized:
            return faculty
    return None
