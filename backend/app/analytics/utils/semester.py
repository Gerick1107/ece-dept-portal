"""Derive IIITD semester labels from timestamps."""

from __future__ import annotations

from datetime import datetime


def semester_label_from_date(value: datetime | None) -> str:
    if value is None:
        return "Unknown"
    month = value.month
    year = value.year
    if month in (1, 2, 3, 4, 5):
        return f"Winter {year}"
    if month in (7, 8, 9, 10, 11):
        return f"Monsoon {year}"
    return f"Summer {year}"


def parse_semester_tag(tag: str) -> tuple[str, int] | None:
    """Parse 'Monsoon 2024' → ('Monsoon', 2024)."""
    parts = tag.strip().split()
    if len(parts) < 2:
        return None
    term = parts[0].capitalize()
    try:
        year = int(parts[-1])
    except ValueError:
        return None
    if term not in ("Monsoon", "Winter", "Summer"):
        return None
    return term, year


def semester_sort_key(tag: str) -> tuple[int, int]:
    """True chronological order key.

    Within a calendar year the terms run Winter (Jan–May) → Summer (May–Jul)
    → Monsoon (Aug–Dec), so e.g. Winter 2023 precedes Monsoon 2023. This also
    yields academic-year grouping: Monsoon 2022 → Winter 2023, then
    Monsoon 2023 → Winter 2024, and so on.
    """
    parsed = parse_semester_tag(tag)
    if not parsed:
        return (0, 0)
    term, year = parsed
    order = {"Winter": 1, "Summer": 2, "Monsoon": 3}
    return (year, order.get(term, 0))
