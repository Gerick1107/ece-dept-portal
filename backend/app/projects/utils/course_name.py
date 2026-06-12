from __future__ import annotations

import re

_CANONICAL_SUFFIXES = [
    "btech project",
    "independent project",
    "independent study",
    "undergraduate research",
    "mtech capstone project",
    "mtech minor project",
    "mtech scholarly paper",
    "mtech thesis",
    "phd thesis",
]

_CANONICAL_DISPLAY = {
    "btech project": "B.Tech Project",
    "independent project": "Independent Project",
    "independent study": "Independent Study",
    "undergraduate research": "Undergraduate Research",
    "mtech capstone project": "M.Tech Capstone Project",
    "mtech minor project": "M.Tech Minor Project",
    "mtech scholarly paper": "M.Tech Scholarly Paper",
    "mtech thesis": "M.Tech Thesis",
    "phd thesis": "Ph.D. Thesis",
}


def _normalize_key(value: str) -> str:
    without_dots = re.sub(r"\.", "", value.strip().lower())
    return re.sub(r"\s+", " ", without_dots).strip()


def normalize_course_name(raw: str) -> str:
    if not raw or not raw.strip():
        return raw
    key = _normalize_key(raw)
    is_progress = key.endswith(" progress")
    base_key = key[: -len(" progress")].strip() if is_progress else key
    canonical = _CANONICAL_DISPLAY.get(base_key)
    if canonical:
        return f"{canonical} Progress" if is_progress else canonical
    return raw.strip()


def course_name_filter_key(value: str) -> str:
    """Stable key for grouping equivalent course-name filter options."""
    return _normalize_key(value).removesuffix(" progress")
