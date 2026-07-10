"""Derive a concise, human meeting title from an ECE Faculty Meet PDF.

ECE Faculty Meet PDFs are named by type in real life (Moderation Meeting,
Faculty Meeting, Curriculum Review Meeting, …) rather than by an ordinal number.
This uses the local LLM to read the document text and return that official
title. Date-based indexing is unaffected: callers keep the meeting_date column,
so RAG date routing still works even after the title changes.
"""
from __future__ import annotations

import re

from app.llm.services.llm_dispatch import generate_text

_SYSTEM_PROMPT = (
    "You label official university department meeting documents. Given the opening "
    "text of a meeting agenda or minutes, reply with ONLY the short official name of "
    "the meeting type (for example: 'Moderation Meeting', 'Faculty Meeting', "
    "'Curriculum Review Meeting', 'Board of Studies Meeting'). Use Title Case. Do not "
    "add the date, department name, ordinal numbers, quotes, or any explanation."
)

_MAX_TITLE_LEN = 120


def _clean(title: str) -> str | None:
    text = (title or "").strip().strip("\"'").splitlines()[0].strip() if title else ""
    # Drop a trailing "Meeting" duplication and stray punctuation.
    text = re.sub(r"\s+", " ", text).strip(" .:-")
    if not text or len(text) > _MAX_TITLE_LEN:
        return None
    # Reject obviously non-title junk (e.g. a full sentence).
    if len(text.split()) > 8:
        return None
    return text


async def derive_meeting_title(pdf_text: str) -> str | None:
    """Return a concise meeting-type title from PDF text, or None if it can't be determined."""
    excerpt = (pdf_text or "").strip()
    if not excerpt:
        return None
    prompt = (
        "Opening text of a meeting document:\n\n"
        f"{excerpt[:1800]}\n\n"
        "Official meeting type name:"
    )
    try:
        raw = await generate_text(
            prompt,
            provider="local",
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=24,
        )
    except Exception:
        return None
    return _clean(raw)
