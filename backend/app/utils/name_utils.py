from __future__ import annotations

import re

_PREFIX_RE = re.compile(r"^(Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s*", re.IGNORECASE)


def strip_name_prefix(name: str) -> str:
    cleaned = name.strip()
    while True:
        match = _PREFIX_RE.match(cleaned)
        if not match:
            break
        cleaned = cleaned[match.end() :].strip()
    return cleaned


def names_match(a: str, b: str) -> bool:
    return strip_name_prefix(a).lower() == strip_name_prefix(b).lower()
