"""Tests for document PDF metadata extraction."""

from __future__ import annotations

from app.documents.services.pdf_service import parse_senate_header_from_text


def test_parse_senate_header_extracts_meeting_number_and_date():
    text = "36th Senate Meeting Minutes — 20 September 2017\nAgenda item 36.1"
    title, meeting_date = parse_senate_header_from_text(text)
    assert "36" in title
    assert meeting_date == "2017-09-20"
