"""Rename existing ECE Faculty Meet meetings by their document title/type.

For every ECE Faculty Meet, this reads the PDF (minutes preferred, else agenda),
asks the local LLM for the official meeting type (e.g. "Moderation Meeting"),
and updates ``meeting_title`` accordingly.

Date-based indexing is preserved: before changing the title, the current date is
saved into the ``meeting_date`` column (parsed from the old title if that column
is empty), so RAG date routing keeps working after the rename.

Only ECE Faculty Meets are touched — Senate / AAC / PGC / UGC are left as-is.

Usage:
    python scripts/retitle_ece_faculty_meets.py [--dry-run] [--limit N]

Requires the local LLM (Ollama) to be running.
"""
from __future__ import annotations

import argparse
import asyncio
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
from app.documents.services.meeting_title_service import derive_meeting_title
from app.documents.services.pdf_service import extract_pdf_pages
from app.documents.services.rag_service import detect_date_hint


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


def _read_pdf_text(meeting: Meeting) -> str:
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
    return "\n".join(text for _, text in pages[:2])


async def _process(meeting: Meeting) -> str | None:
    text = _read_pdf_text(meeting)
    if not text.strip():
        return None
    return await derive_meeting_title(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retitle ECE Faculty Meets by document type.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving.")
    parser.add_argument("--limit", type=int, default=None, help="Max meetings to process.")
    args = parser.parse_args()

    db = SessionLocal()
    changed = 0
    skipped = 0
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
            # Preserve the date for indexing before touching the title.
            if not meeting.meeting_date:
                iso = _iso_from_hint(detect_date_hint(meeting.meeting_title or ""))
                if iso:
                    meeting.meeting_date = iso

            new_title = asyncio.run(_process(meeting))
            if not new_title or new_title == meeting.meeting_title:
                skipped += 1
                continue

            print(f"[{meeting.year}] '{meeting.meeting_title}' -> '{new_title}' (date={meeting.meeting_date})")
            if not args.dry_run:
                meeting.meeting_title = new_title
                db.commit()
            changed += 1
    finally:
        db.close()

    print()
    print("=== ECE FACULTY MEET RETITLE COMPLETE ===")
    print(f"Renamed: {changed}")
    print(f"Skipped (no text / unchanged): {skipped}")
    if args.dry_run:
        print("(dry run — no changes saved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
