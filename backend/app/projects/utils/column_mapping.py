from __future__ import annotations

import math
import re
from typing import Any

CANONICAL_FIELDS = {
    "project_title": [
        "project topic",
        "project title",
        "title",
        "topic",
        "project name",
    ],
    "project_type": ["project type", "type", "btp/ip", "category"],
    "faculty": ["faculty", "supervisor", "guide", "faculty name", "project guide"],
    "co_guide": ["co guide", "co-guide", "coguide", "co supervisor", "co-supervisor"],
    "students": ["students", "student", "student names", "student name", "members"],
    "semester": ["semester", "term", "session"],
    "status": ["status", "project status"],
    "credit": ["credit", "credits"],
}


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def map_headers(raw_headers: list[str]) -> dict[str, str]:
    """Map spreadsheet column names to canonical field keys."""
    normalized = {_normalize_header(h): h for h in raw_headers if h and str(h).strip()}
    mapping: dict[str, str] = {}
    for canonical, aliases in CANONICAL_FIELDS.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized:
                mapping[canonical] = normalized[key]
                break
    return mapping


def require_columns(mapping: dict[str, str]) -> list[str]:
    missing = []
    for required in ("project_title", "project_type", "faculty", "semester"):
        if required not in mapping:
            missing.append(required)
    return missing


DEPARTMENT_FIELD_ALIASES = {
    "sr_no": ["sr. no.", "sr no", "serial number", "s.no"],
    "admission_year": ["admission year"],
    "program_definition": ["program definition"],
    "program_specialization": ["program specialization"],
    "semester_file": ["semester"],
    "project_type": ["project type"],
    "course_code": ["course code"],
    "course_name": ["course name"],
    "credit": ["credit", "credits"],
    "student_roll_no": ["student roll number", "student roll no", "roll number"],
    "student_name": ["student name"],
    "guide_name": ["guide name", "guide"],
    "co_guide": ["co-guide", "co guide", "coguide"],
    "title": ["title", "project title", "project topic"],
    "grade": ["grade"],
    "project_status": ["project status", "status"],
}


def map_department_headers(raw_headers: list[str]) -> dict[str, str]:
    normalized = {_normalize_header(h): h for h in raw_headers if h and str(h).strip()}
    mapping: dict[str, str] = {}
    for canonical, aliases in DEPARTMENT_FIELD_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized:
                mapping[canonical] = normalized[key]
                break
    return mapping


DEPARTMENT_REQUIRED_FIELDS = frozenset(
    {"title", "guide_name", "student_roll_no", "student_name", "course_code"}
)


def score_department_header_row(row_values: list) -> int:
    """How many required department columns appear in this row (0–5)."""
    headers = [cell_str(v) for v in row_values]
    mapping = map_department_headers(headers)
    return len(DEPARTMENT_REQUIRED_FIELDS & set(mapping.keys()))


def find_department_header_row_index(raw_frame) -> int | None:
    """
    Locate the header row in sheets that have title/blank rows before column names
    (e.g. row 0 = 'Monsoon 2021', row 2 = actual headers).
    """
    scan_limit = min(25, len(raw_frame))
    best_idx: int | None = None
    best_score = 0
    for idx in range(scan_limit):
        score = score_department_header_row(raw_frame.iloc[idx].tolist())
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_score >= 4:
        return best_idx
    return None


def cell_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value == int(value):
            return str(int(value))
    text = str(value).strip()
    if text.lower() in ("nan", "none", "<na>", "nat"):
        return ""
    return text
