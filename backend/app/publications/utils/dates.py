"""Lenient parsing of the free-form ``publication_date`` string column.

Google Scholar / SerpAPI return dates in mixed precision — a full date
("2024/03/15" or "2024-03-15"), year+month ("2024/03"), or year-only ("2024").
These helpers normalise those into comparable ``date`` values and report the
precision so callers can tell which rows still need an exact date.
"""
from __future__ import annotations

import re
from datetime import date

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

# 2024-03-15 or 2024/03/15
_YMD_RE = re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b")
# 2024-03 or 2024/03
_YM_RE = re.compile(r"\b(\d{4})[/-](\d{1,2})\b")
# 15 March 2024 / March 15, 2024
_DMY_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?\s+(\d{4})\b", re.IGNORECASE)
_MDY_RE = re.compile(r"\b([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", re.IGNORECASE)
# March 2024
_MY_RE = re.compile(r"\b([A-Za-z]+)\.?\s+(\d{4})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_precision(value: str | None) -> tuple[date | None, str | None]:
    """Return ``(date, precision)`` where precision is 'day' | 'month' | 'year' | None.

    Missing month/day default to 1 so the value is still comparable.
    """
    if not value:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None

    m = _YMD_RE.search(text)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return d, "day"

    m = _DMY_RE.search(text)
    if m and m.group(2).lower() in _MONTHS:
        d = _safe_date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
        if d:
            return d, "day"

    m = _MDY_RE.search(text)
    if m and m.group(1).lower() in _MONTHS:
        d = _safe_date(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
        if d:
            return d, "day"

    m = _YM_RE.search(text)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), 1)
        if d:
            return d, "month"

    m = _MY_RE.search(text)
    if m and m.group(1).lower() in _MONTHS:
        d = _safe_date(int(m.group(2)), _MONTHS[m.group(1).lower()], 1)
        if d:
            return d, "month"

    m = _YEAR_RE.search(text)
    if m:
        d = _safe_date(int(m.group(1)), 1, 1)
        if d:
            return d, "year"

    return None, None


def parse_publication_date(value: str | None) -> date | None:
    """Best-effort comparable date (missing parts default to January 1st)."""
    return parse_precision(value)[0]


def is_partial_date(value: str | None) -> bool:
    """True when the value is missing (or only has year / year-month precision)."""
    _, precision = parse_precision(value)
    return precision != "day"


def extract_year(value: str | None) -> int | None:
    """Return the 4-digit year from a mixed-precision date string, if any."""
    d = parse_publication_date(value)
    return d.year if d is not None else None


def within_range(value: str | None, start: date | None, end: date | None) -> bool:
    """Whether a publication_date string falls within [start, end] (inclusive)."""
    d = parse_publication_date(value)
    if d is None:
        return False
    if start is not None and d < start:
        return False
    if end is not None and d > end:
        return False
    return True
