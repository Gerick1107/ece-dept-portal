from __future__ import annotations

import re

_CANONICAL_COURSE_NAMES = {
    "btech project": "B.Tech Project",
    "b tech project": "B.Tech Project",
    "b.tech project": "B.Tech Project",
    "b.tech. project": "B.Tech Project",
    "independent project": "Independent Project",
    "independent study": "Independent Study",
    "undergraduate research": "Undergraduate Research",
}


def _normalize_key(value: str) -> str:
    return re.sub(r"[\s.]+", " ", value.strip().lower())


def normalize_course_name(raw: str) -> str:
    if not raw or not raw.strip():
        return raw
    key = _normalize_key(raw)
    if key in _CANONICAL_COURSE_NAMES:
        return _CANONICAL_COURSE_NAMES[key]
    for variant, canonical in _CANONICAL_COURSE_NAMES.items():
        if _normalize_key(variant) == key:
            return canonical
    return raw.strip()
