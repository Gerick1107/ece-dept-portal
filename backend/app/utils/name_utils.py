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


def _name_tokens_ordered(name: str) -> list[str]:
    return [t for t in strip_name_prefix(name).lower().split() if t]


def _is_initial(token: str) -> bool:
    return len(token.rstrip(".")) == 1


def _token_matches(a: str, b: str) -> bool:
    if a == b:
        return True
    a_core = a.rstrip(".")
    b_core = b.rstrip(".")
    if _is_initial(a_core) and b_core.startswith(a_core):
        return True
    if _is_initial(b_core) and a_core.startswith(b_core):
        return True
    return False


def _is_subsequence_match(short: list[str], long: list[str]) -> bool:
    if not short:
        return False
    idx = 0
    for token in long:
        if _token_matches(short[idx], token):
            idx += 1
            if idx == len(short):
                return True
    return False


def names_match(a: str, b: str) -> bool:
    """
    Match faculty names allowing optional middle names and initials.

    Examples:
    - "Vivek Ashok Bohara" matches "Vivek Bohara"
    - "Sanjit Krishnan Kaul" matches "Sanjit Kaul"
    - "Dr. Sanjit K" matches "Sanjit Krishnan Kaul"
    """
    parts_a = _name_tokens_ordered(a)
    parts_b = _name_tokens_ordered(b)
    if not parts_a or not parts_b:
        return False
    if parts_a == parts_b:
        return True
    short, long = (parts_a, parts_b) if len(parts_a) <= len(parts_b) else (parts_b, parts_a)
    if len(short) == 1:
        return len(long) == 1 and short[0] == long[0]
    if not _token_matches(short[0], long[0]):
        return False
    return _is_subsequence_match(short, long)
