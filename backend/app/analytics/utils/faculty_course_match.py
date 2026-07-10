"""Match CO-PO run snapshots to a faculty via their course allocations.

Historical CO-PO evaluation runs were created by an admin account, so filtering
snapshots purely by ``user_id`` hides everything from faculty logins. Instead we
link a snapshot to a faculty when the **course code** embedded in the snapshot's
title (e.g. ``ECE-356/556: Statistical ML``) matches a course the faculty taught
(``course_allocations.course_code`` like ``CSE342/ECE356``) in the same semester.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.course_allocation.models.entities import CourseAllocation

_PREFIX_NUM_RE = re.compile(r"^\s*([A-Z]{2,4})\s*-?\s*(\d{2,4})")
_BARE_NUM_RE = re.compile(r"^\s*(\d{2,4})")


def _norm_semester(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def extract_core_codes(text: str | None) -> set[str]:
    """Extract canonical course codes (e.g. ``{'ECE356', 'ECE556'}``) from a code
    string or a snapshot title, inheriting the department prefix across
    slash-separated numbers (``ECE-356/556`` -> ECE356, ECE556)."""
    if not text:
        return set()
    # For titles like "ECE-548: Advanced Digital Communication" only the part
    # before the first colon holds course codes; plain codes have no colon.
    head = str(text).split(":", 1)[0].upper()
    codes: set[str] = set()
    current_prefix: str | None = None
    for part in re.split(r"[,/]", head):
        part = part.strip()
        if not part:
            continue
        m = _PREFIX_NUM_RE.match(part)
        if m:
            current_prefix = m.group(1)
            codes.add(f"{m.group(1)}{m.group(2)}")
            continue
        m2 = _BARE_NUM_RE.match(part)
        if m2 and current_prefix:
            codes.add(f"{current_prefix}{m2.group(1)}")
    return codes


def faculty_course_semester_keys(db: Session, faculty_id: int) -> set[tuple[str, str]]:
    """Set of ``(course_code, normalized_semester)`` pairs a faculty has taught."""
    rows = db.execute(
        select(CourseAllocation.course_code, CourseAllocation.semester).where(
            CourseAllocation.faculty_id == faculty_id,
            CourseAllocation.is_faculty_placeholder.is_(False),
        )
    ).all()
    keys: set[tuple[str, str]] = set()
    for course_code, semester in rows:
        sem = _norm_semester(semester)
        for code in extract_core_codes(course_code):
            keys.add((code, sem))
    return keys


def snapshot_matches_faculty(
    course_title: str | None,
    semester_label: str | None,
    allowed_keys: set[tuple[str, str]],
) -> bool:
    """Whether a snapshot's course/semester is one the faculty taught."""
    if not allowed_keys:
        return False
    sem = _norm_semester(semester_label)
    for code in extract_core_codes(course_title):
        if (code, sem) in allowed_keys:
            return True
    return False
