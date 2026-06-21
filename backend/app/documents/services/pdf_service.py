from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_MEETING_HEADER_RE = re.compile(
    r"(?P<number>\d+)(?:st|nd|rd|th)?\s+Senate(?:[\s-]+Meeting)?[\s-]+Minutes.*?"
    r"(?P<day>\d{1,2})[\s,]+(?P<month>[A-Za-z]+)[\s,]+(?P<year>\d{4})",
    re.IGNORECASE | re.DOTALL,
)
_FILENAME_TITLE_RE = re.compile(
    r"(?P<number>\d+)(?:st|nd|rd|th)?\s+Senate[\s-]+Minutes",
    re.IGNORECASE,
)
_DATE_DAY_FIRST_RE = re.compile(
    r"(?P<day>\d{1,2})[\s,]+(?P<month>[A-Za-z]+)[\s,]+(?P<year>\d{4})",
    re.IGNORECASE,
)
_DATE_MONTH_FIRST_RE = re.compile(
    r"(?P<month>[A-Za-z]+)[\s,]+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})",
    re.IGNORECASE,
)
_MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


@dataclass
class ExtractedPdfMeta:
    title: str
    meeting_date: str | None
    pages: list[tuple[int, str]]


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append((index, text))
    return pages


def _format_meeting_date(day: str, month: str, year: str) -> str | None:
    month_num = _MONTHS.get(month.lower())
    if not month_num:
        return None
    return f"{year}-{month_num}-{day.zfill(2)}"


def parse_date_from_text(text: str) -> str | None:
    """Find a calendar date in free text or filenames."""
    normalized = text.replace("\n", " ")
    for pattern in (_DATE_DAY_FIRST_RE, _DATE_MONTH_FIRST_RE):
        match = pattern.search(normalized)
        if not match:
            continue
        parsed = _format_meeting_date(match.group("day"), match.group("month"), match.group("year"))
        if parsed:
            return parsed
    return None


def parse_title_from_filename(filename: str) -> str | None:
    stem = Path(filename).stem.replace("_", " ")
    match = _FILENAME_TITLE_RE.search(stem)
    if not match:
        return None
    number = match.group("number")
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(int(number) % 10 if int(number) % 100 not in (11, 12, 13) else 0, "th")
    return f"{number}{suffix} Senate Minutes"


def parse_senate_header_from_text(text: str) -> tuple[str, str | None]:
    normalized = text.replace("\n", " ")
    match = _MEETING_HEADER_RE.search(normalized)
    if match:
        number = match.group("number")
        title = f"{number}th Senate Minutes"
        meeting_date = _format_meeting_date(match.group("day"), match.group("month"), match.group("year"))
        return title, meeting_date
    meeting_date = parse_date_from_text(normalized)
    title_match = _FILENAME_TITLE_RE.search(normalized)
    if title_match:
        number = title_match.group("number")
        return f"{number}th Senate Minutes", meeting_date
    return "Senate Minutes", meeting_date


def extract_pdf_metadata(path: Path, *, fallback_title: str | None = None) -> ExtractedPdfMeta:
    pages = extract_pdf_pages(path)
    first_page = pages[0][1] if pages else ""
    sample_text = "\n".join(text for _, text in pages[:2])
    title, meeting_date = parse_senate_header_from_text(first_page)

    filename_title = parse_title_from_filename(path.name)
    if title == "Senate Minutes" and filename_title:
        title = filename_title
    elif title == "Senate Minutes" and fallback_title:
        title = fallback_title

    if not meeting_date:
        meeting_date = parse_date_from_text(path.stem) or parse_date_from_text(sample_text)

    return ExtractedPdfMeta(title=title, meeting_date=meeting_date, pages=pages)
