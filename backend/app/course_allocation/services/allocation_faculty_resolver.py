from __future__ import annotations

import csv
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_ASSETS
from app.course_allocation.models.entities import FacultyNameAlias
from app.publications.models.entities import Faculty
from app.utils.contribution_faculty_resolver import (
    FacultyResolveFailure,
    FacultyResolveResult,
    _normalize_name,
    resolve_faculty_id,
)

logger = logging.getLogger(__name__)

_PLACEHOLDER_CACHE: set[str] | None = None
_ALIAS_VARIANT_TO_CANONICAL: dict[str, str] = {}


def _load_placeholder_values() -> set[str]:
    global _PLACEHOLDER_CACHE
    if _PLACEHOLDER_CACHE is not None:
        return _PLACEHOLDER_CACHE
    values: set[str] = {"", "na", "n/a"}
    path = DATA_ASSETS / "non_faculty_placeholders.csv"
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                raw = (row.get("placeholder_value") or "").strip()
                if raw and raw != "(blank)":
                    values.add(_normalize_name(raw))
    _PLACEHOLDER_CACHE = values
    return values


def is_placeholder_name(raw_name: str) -> bool:
    name = (raw_name or "").strip()
    if not name:
        return True
    norm = _normalize_name(name)
    placeholders = _load_placeholder_values()
    if norm in placeholders:
        return True
    if norm.startswith("discontinued"):
        return True
    if "not being offered" in norm:
        return True
    if norm in ("cse", "cse faculty"):
        return True
    return False


def refresh_alias_cache(db: Session) -> None:
    global _ALIAS_VARIANT_TO_CANONICAL
    rows = db.scalars(select(FacultyNameAlias)).all()
    _ALIAS_VARIANT_TO_CANONICAL = {
        _normalize_name(r.variant_name): r.canonical_name.strip() for r in rows if r.variant_name
    }


def resolve_allocation_faculty(db: Session, raw_name: str) -> FacultyResolveResult | FacultyResolveFailure | None:
    if is_placeholder_name(raw_name):
        return None
    norm = _normalize_name(raw_name)
    if norm in _ALIAS_VARIANT_TO_CANONICAL:
        canonical = _ALIAS_VARIANT_TO_CANONICAL[norm]
        for faculty in db.scalars(select(Faculty)).all():
            if _normalize_name(faculty.name) == _normalize_name(canonical):
                return FacultyResolveResult(
                    faculty_id=faculty.id,
                    matched_name=faculty.name,
                    confidence="alias",
                    raw_name=raw_name,
                )
        result = resolve_faculty_id(db, canonical)
        if isinstance(result, FacultyResolveResult):
            return FacultyResolveResult(
                faculty_id=result.faculty_id,
                matched_name=result.matched_name,
                confidence="alias",
                raw_name=raw_name,
            )
    result = resolve_faculty_id(db, raw_name)
    if isinstance(result, FacultyResolveFailure):
        logger.warning("Unmatched allocation faculty name: '%s'", raw_name)
    return result


def add_faculty_alias(db: Session, variant_name: str, faculty_id: int) -> FacultyNameAlias:
    from app.course_allocation.services.csv_sync import write_aliases_csv

    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        raise ValueError("Faculty not found")
    variant = variant_name.strip()
    existing = db.scalar(select(FacultyNameAlias).where(FacultyNameAlias.variant_name == variant))
    if existing:
        existing.canonical_name = faculty.name
        existing.faculty_id = faculty.id
        row = existing
    else:
        row = FacultyNameAlias(variant_name=variant, canonical_name=faculty.name, faculty_id=faculty.id)
        db.add(row)
    db.commit()
    db.refresh(row)
    refresh_alias_cache(db)
    write_aliases_csv(db)
    return row
