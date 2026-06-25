"""Helpers to pair agenda/minutes files into a single logical meeting.

A meeting is identified by its ordinal number ("32nd", "41th", "36 th", ...)
parsed from the file name. Agenda and minutes PDFs that share the same
document type, year and meeting number belong to the same meeting and are
shown together in the portal.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.documents.models.entities import (
    DOCUMENT_TYPE_AAC,
    DOCUMENT_TYPE_ECE_FACULTY_MEET,
    DOCUMENT_TYPE_PGC,
    DOCUMENT_TYPE_SENATE,
    DOCUMENT_TYPE_UGC,
)

# Matches "32nd", "41th" (common typo), "36 th" (stray space) etc.
_ORDINAL_RE = re.compile(r"\b(\d{1,3})\s*(?:st|nd|rd|th)\b", re.IGNORECASE)
_ID_SUFFIX_RE = re.compile(r"-\d{2,}-\d+$", re.IGNORECASE)

_TYPE_LABEL: dict[str, str] = {
    DOCUMENT_TYPE_SENATE: "Senate",
    DOCUMENT_TYPE_AAC: "AAC",
    DOCUMENT_TYPE_PGC: "PGC",
    DOCUMENT_TYPE_UGC: "UGC",
    DOCUMENT_TYPE_ECE_FACULTY_MEET: "ECE Faculty",
}


def parse_meeting_number(filename: str) -> int | None:
    """Return the leading ordinal meeting number from a file name, if any."""
    stem = Path(filename).stem.replace("_", " ")
    match = _ORDINAL_RE.search(stem)
    if match:
        return int(match.group(1))
    return None


def meeting_identity(filename: str) -> int | str:
    """Stable identity for pairing agenda/minutes of the same meeting.

    Prefer the ordinal number when present. Otherwise fall back to a
    normalized stem (e.g. ``aac meeting`` for ``AAC Meeting-25-393773``).
    """
    stem = Path(filename).stem.replace("_", " ")
    number = parse_meeting_number(stem)
    if number is not None:
        return number
    lowered = stem.lower()
    if "minutes of" in lowered:
        match = _ORDINAL_RE.search(stem)
        if match:
            return int(match.group(1))
    normalized = _ID_SUFFIX_RE.sub("", stem).strip().lower()
    return normalized or "unknown"


def meeting_key(document_type: str, year: int, identity: int | str) -> tuple[str, int, int | str]:
    """Stable grouping key for agenda/minutes belonging to the same meeting."""
    return (document_type, year, identity)


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_meeting_title(
    document_type: str,
    *,
    identity: int | str,
    year: int,
    fallback: str | None = None,
) -> str:
    """Generate a clean, human-readable meeting title."""
    label = _TYPE_LABEL.get(document_type, "Meeting")
    if document_type == DOCUMENT_TYPE_ECE_FACULTY_MEET:
        if fallback:
            return fallback
        return f"ECE Faculty Meeting ({year})"
    if isinstance(identity, int):
        return f"{_ordinal(identity)} {label} Meeting"
    if fallback:
        return fallback
    return f"{label} Meeting ({year})"
