"""Tests for document PDF metadata extraction."""

from __future__ import annotations

from app.documents.services.pdf_service import (
    parse_date_from_text,
    parse_senate_header_from_text,
    parse_title_from_filename,
)


def test_parse_senate_header_extracts_meeting_number_and_date():
    text = "36th Senate Meeting Minutes — 20 September 2017\nAgenda item 36.1"
    title, meeting_date = parse_senate_header_from_text(text)
    assert "36" in title
    assert meeting_date == "2017-09-20"


def test_parse_senate_header_handles_hyphenated_minutes_title():
    text = "36th Senate-Minutes-20 September 2017"
    title, meeting_date = parse_senate_header_from_text(text)
    assert "36" in title
    assert meeting_date == "2017-09-20"


def test_parse_date_from_text_supports_month_first_format():
    assert parse_date_from_text("held on September 20, 2017 with members present") == "2017-09-20"


def test_parse_title_and_date_from_filename():
    filename = "36th Senate-Minutes-20 September 2017-Updated (1).pdf"
    assert parse_title_from_filename(filename) == "36th Senate Minutes"
    assert parse_date_from_text(filename) == "2017-09-20"
