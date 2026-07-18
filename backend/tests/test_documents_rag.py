"""Tests for document RAG routing and lexical retrieval scoring."""

from __future__ import annotations

from app.documents.services.rag_service import (
    _lexical_score,
    _content_tokens,
    detect_meeting_number,
    detect_routing_date_hint,
    detect_ece_title_hints,
)


def test_detect_meeting_number_requires_meeting_context():
    assert detect_meeting_number("What was decided in meeting 22?") == 22
    assert detect_meeting_number("Summarize the 36th Senate meeting") == 36
    assert detect_meeting_number("Tell me about the 12th AAC meeting outcomes") == 12
    # Pasted topic text with ordinals/dates must NOT pin a meeting number
    assert detect_meeting_number("held on 15th May 2023 the committee approved TA allotment") is None
    assert detect_meeting_number("for 3rd year BTech students the eligibility criteria") is None


def test_routing_date_ignores_bare_year_in_topic_paste():
    assert detect_routing_date_hint("curriculum changes approved in 2023 for ECE") is None
    assert detect_routing_date_hint("ECE FM meeting on 08 May 2026") == {
        "year": 2026,
        "month": 5,
        "day": 8,
    }
    assert detect_routing_date_hint("faculty meeting May 2024") == {
        "year": 2024,
        "month": 5,
        "day": None,
    }


def test_ece_title_hints_require_meeting_word():
    assert detect_ece_title_hints("when was curriculum revision discussed?") == []
    assert detect_ece_title_hints("summarize the moderation meeting") == ["moderation"]
    assert "research" not in detect_ece_title_hints("research proposal funding norms")


def test_lexical_score_boosts_copy_paste_phrase():
    phrase = "TA allotment eligibility criteria for MTech students"
    chunk = f"Agenda item 12.3 — The senate approved the {phrase} with effect from Monsoon 2024."
    score = _lexical_score(phrase, chunk, _content_tokens(phrase))
    assert score >= 1.5
    weak = _lexical_score("unrelated quantum optics picnic", chunk, _content_tokens("unrelated quantum optics picnic"))
    assert weak < score
