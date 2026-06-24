from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

from app.config import get_settings

SEMESTER_PIN: str | None = "Monsoon 2026"


def detect_current_semester(today: date | None = None) -> str:
    today = today or date.today()
    month, year = today.month, today.year
    if month >= 8:
        return f"Monsoon {year}"
    if month <= 5:
        return f"Winter {year}"
    return f"Monsoon {year}"


def effective_current_semester() -> str:
    if SEMESTER_PIN:
        return SEMESTER_PIN
    return detect_current_semester()


def parse_semester(semester: str) -> tuple[str, int]:
    parts = semester.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid semester: {semester}")
    return parts[0], int(parts[1])


def academic_year_for_semester(semester: str) -> str:
    term, year = parse_semester(semester)
    if term.lower() == "monsoon":
        return f"{year}-{str(year + 1)[-2:]}"
    return f"{year - 1}-{str(year)[-2:]}"


def parse_academic_year(ay: str) -> tuple[int, int] | None:
    """Parse YYYY-YY or YYYY-YYYY academic year labels."""
    raw = ay.strip()
    m_short = re.match(r"^(\d{4})-(\d{2})$", raw)
    if m_short:
        start = int(m_short.group(1))
        end_short = int(m_short.group(2))
        if end_short == (start + 1) % 100:
            return start, start + 1
        return None
    m_long = re.match(r"^(\d{4})-(\d{4})$", raw)
    if m_long:
        start = int(m_long.group(1))
        end = int(m_long.group(2))
        if end == start + 1:
            return start, end
    return None


def semesters_for_academic_year(ay: str) -> list[str]:
    parsed = parse_academic_year(ay)
    if not parsed:
        return []
    start, end = parsed
    return [f"Monsoon {start}", f"Winter {end}"]


def scope_semesters(scope: str | None) -> list[str] | None:
    if not scope or scope.strip().lower() in ("all", ""):
        return None
    stripped = scope.strip()
    if parse_academic_year(stripped):
        return semesters_for_academic_year(stripped)
    return [stripped]
