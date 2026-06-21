from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_MEETING_HEADER_RE = re.compile(
    r"(?P<number>\d+)(?:st|nd|rd|th)?\s+Senate.*?Minutes.*?(?P<day>\d{1,2})\s+"
    r"(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})",
    re.IGNORECASE | re.DOTALL,
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


def parse_senate_header_from_text(text: str) -> tuple[str, str | None]:
    match = _MEETING_HEADER_RE.search(text.replace("\n", " "))
    if not match:
        return "Senate Minutes", None
    number = match.group("number")
    day = match.group("day").zfill(2)
    month = _MONTHS.get(match.group("month").lower(), "01")
    year = match.group("year")
    title = f"{number}th Senate Minutes"
    meeting_date = f"{year}-{month}-{day}"
    return title, meeting_date


def extract_pdf_metadata(path: Path, *, fallback_title: str | None = None) -> ExtractedPdfMeta:
    pages = extract_pdf_pages(path)
    first_page = pages[0][1] if pages else ""
    title, meeting_date = parse_senate_header_from_text(first_page)
    if title == "Senate Minutes" and fallback_title:
        title = fallback_title
    return ExtractedPdfMeta(title=title, meeting_date=meeting_date, pages=pages)
