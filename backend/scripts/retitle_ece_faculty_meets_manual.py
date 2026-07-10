"""Rename existing ECE Faculty Meets by their document title/type WITHOUT any LLM.

Every ECE Faculty Meet PDF opens with a line like
``Minutes of <TITLE> held on <date>``. This script reads that line and derives a
clean meeting title from it. The vast majority are regular faculty meetings
(``ECE FM`` -> "ECE Faculty Meeting"); the special ones (workshops, moderation
meetings, alumni meets, director visits, etc.) are curated in ``OVERRIDES`` below
after manually reviewing each PDF.

Date-based indexing is preserved: ``meeting_date`` is never cleared, and if it is
somehow empty it is re-derived from the old title before the rename.

Only ECE Faculty Meets are touched — Senate / AAC / PGC / UGC are left as-is.
No local LLM / Ollama is required.

Usage:
    python scripts/retitle_ece_faculty_meets_manual.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database.session import SessionLocal
from app.documents.models.entities import DOCUMENT_TYPE_ECE_FACULTY_MEET, Meeting
from app.documents.services.file_manager import resolve_document_path
from app.documents.services.pdf_service import extract_pdf_pages
from app.documents.services.rag_service import detect_date_hint

DEFAULT_TITLE = "ECE Faculty Meeting"

# Curated titles for the meetings that are NOT ordinary faculty meetings.
# Keyed by meeting id after manually reading the first page of each PDF.
OVERRIDES: dict[int, str] = {
    267: "ECE Program Review - Signal Processing",
    280: "ECE Departmental Meeting with Director",
    289: "ECE Department Visit",
    290: "Workshop for M.Tech CPS and M.Tech ML",
    291: "Meeting for M.Tech CSP Revamp",
    292: "Meeting for M.Tech CSP Revamp",
    298: "Workshop on Launching M.Tech in ECE (Machine Learning)",
    306: "Workshop on Launching M.Tech in ECE (Machine Learning)",
    307: "Workshop on Launching M.Tech in ECE (Cyber Physical Systems)",
    308: "Meeting for M.Tech CSP Revamp",
    312: "Visit to Electropreneur Park",
    313: "Meeting for CoE LED Lighting",
    318: "Meeting for Secure Digital Platform",
    319: "ECE Alumni Meet",
    320: "Second Workshop for B.Tech EE-VDT",
    323: "First Workshop for B.Tech EE-VDT",
    324: "Academic Audit",
    325: "Meeting with Director",
    328: "Meeting for INAE Award Nomination",
    341: "Meeting with Director",
    347: "ECE Graduating Batch Meeting",
    348: "ECE Moderation Meeting",
    352: "ECE Moderation Meeting",
    353: "ECE Follow Up - Faculty Meeting",
    355: "ECE Second Follow Up - Faculty Meeting",
}

# Any first-line phrase that reduces to one of these is a normal faculty meeting.
_FM_RE = re.compile(r"^(the\s+)?ece\s*fm$", re.IGNORECASE)
_TITLE_RE = re.compile(r"minutes\s*of\s*(.+?)\s*held\s*on", re.IGNORECASE | re.DOTALL)


def _read_first_page(meeting: Meeting) -> str:
    files = {f.file_role: f for f in meeting.files}
    chosen = files.get("minutes") or files.get("agenda") or (meeting.files[0] if meeting.files else None)
    if chosen is None:
        return ""
    path = resolve_document_path(chosen.file_path)
    if not path.exists():
        return ""
    try:
        pages = extract_pdf_pages(path)
    except Exception:
        return ""
    return pages[0][1] if pages else ""


def _derive_title(text: str) -> str:
    """Best-effort deterministic title from the PDF's opening line."""
    head = " ".join(text.split())[:400]
    match = _TITLE_RE.search(head)
    if match:
        candidate = match.group(1).strip().strip("\u201c\u201d\"' ")
        candidate = re.sub(r"^the\s+", "", candidate, flags=re.IGNORECASE).strip()
        if _FM_RE.match(candidate) or re.fullmatch(r"ece\s*fm", candidate, re.IGNORECASE):
            return DEFAULT_TITLE
    # Regardless of phrasing, if the header mentions "ECE FM" it is a faculty meeting.
    if re.search(r"ece\s*fm", head, re.IGNORECASE):
        return DEFAULT_TITLE
    return DEFAULT_TITLE


def _iso_from_hint(hint: dict | None) -> str | None:
    if not hint or not hint.get("year"):
        return None
    year = hint["year"]
    month = hint.get("month")
    day = hint.get("day")
    if month and day:
        return f"{year:04d}-{month:02d}-{day:02d}"
    if month:
        return f"{year:04d}-{month:02d}"
    return f"{year:04d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Retitle ECE Faculty Meets (no LLM).")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving.")
    parser.add_argument("--limit", type=int, default=None, help="Max meetings to process.")
    args = parser.parse_args()

    db = SessionLocal()
    changed = 0
    unchanged = 0
    try:
        stmt = (
            select(Meeting)
            .options(joinedload(Meeting.files))
            .where(Meeting.document_type == DOCUMENT_TYPE_ECE_FACULTY_MEET)
            .order_by(Meeting.year.asc(), Meeting.id.asc())
        )
        meetings = list(db.scalars(stmt).unique().all())
        if args.limit is not None:
            meetings = meetings[: args.limit]

        for meeting in meetings:
            # Preserve the date index before touching the title.
            if not meeting.meeting_date:
                iso = _iso_from_hint(detect_date_hint(meeting.meeting_title or ""))
                if iso:
                    meeting.meeting_date = iso

            if meeting.id in OVERRIDES:
                new_title = OVERRIDES[meeting.id]
            else:
                new_title = _derive_title(_read_first_page(meeting))

            if new_title == meeting.meeting_title:
                unchanged += 1
                continue

            print(f"[{meeting.year}] #{meeting.id} '{meeting.meeting_title}' -> '{new_title}' (date={meeting.meeting_date})")
            if not args.dry_run:
                meeting.meeting_title = new_title
            changed += 1

        if not args.dry_run:
            db.commit()
    finally:
        db.close()

    print()
    print("=== ECE FACULTY MEET RETITLE (deterministic) ===")
    print(f"Renamed: {changed}")
    print(f"Unchanged: {unchanged}")
    if args.dry_run:
        print("(dry run — no changes saved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
