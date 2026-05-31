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
    "grade": ["grade", "marks", "result"],
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
