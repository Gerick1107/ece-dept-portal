"""Question-paper analysis and generated marks-template regression tests."""

from __future__ import annotations

import asyncio
import io
import json

from openpyxl import load_workbook

from app.copo.services import question_paper_analyzer
from app.copo.services.question_paper_analyzer import (
    AnalyzedQuestion,
    generate_component_workbook,
    redistribute_sibling_marks,
)


def test_analyzer_rejects_co_without_source_evidence(monkeypatch):
    response = {
        "component_name": "Quiz",
        "paper_total_marks": 10,
        "questions": [
            {
                "label": "Q1",
                "co_labels": ["CO4"],
                "co_evidence": "CO4",
                "max_marks": 10,
                "is_bonus": False,
            }
        ],
    }

    async def fake_generate_text(*args, **kwargs):
        return json.dumps(response)

    monkeypatch.setattr(question_paper_analyzer, "_generate_analysis_text", fake_generate_text)
    result = asyncio.run(
        question_paper_analyzer.analyze_question_paper_text(
            "Q1. Explain the circuit operation. [10 marks]"
        )
    )

    assert result["questions"][0]["co_labels"] == []
    assert result["questions"][0]["co_label"] == ""
    assert result["warnings"] == [
        "No COs found for: Q1. Manually edit/add CO mappings before downloading."
    ]


def test_generated_workbook_scales_bonus_but_excludes_it_from_total():
    payload = generate_component_workbook(
        component_name="Quiz",
        paper_total_marks=40,
        weightage=20,
        questions=[
            {"label": "Q1", "co_labels": ["CO1"], "max_marks": 40, "is_bonus": False},
            {"label": "Bonus", "co_labels": [], "max_marks": 5, "is_bonus": True},
        ],
    )

    worksheet = load_workbook(io.BytesIO(payload), data_only=True).active
    assert worksheet["C4"].value == 20
    assert worksheet["D4"].value == 2.5
    assert worksheet["E4"].value == 20


def test_equal_split_when_part_marks_missing(monkeypatch):
    """MTH-style: parent worth 10, parts a/b with no printed marks → 5 each."""
    response = {
        "component_name": "EndSem",
        "paper_total_marks": 40,
        "questions": [
            {
                "label": "Q1",
                "co_labels": [],
                "co_evidence": "",
                "max_marks": 10,
                "is_bonus": False,
                "parts": [
                    {"label": "Q1a", "co_labels": [], "co_evidence": "", "max_marks": 0},
                    {"label": "Q1b", "co_labels": [], "co_evidence": "", "max_marks": 0},
                ],
            },
            {
                "label": "Q2",
                "co_labels": [],
                "co_evidence": "",
                "max_marks": 10,
                "is_bonus": False,
                "parts": [
                    {"label": "Q2a", "co_labels": [], "co_evidence": "", "max_marks": 0},
                    {"label": "Q2b", "co_labels": [], "co_evidence": "", "max_marks": 0},
                ],
            },
            {
                "label": "Q3",
                "co_labels": [],
                "co_evidence": "",
                "max_marks": 10,
                "is_bonus": False,
                "parts": [
                    {"label": "Q3a", "co_labels": [], "co_evidence": "", "max_marks": 0},
                    {"label": "Q3b", "co_labels": [], "co_evidence": "", "max_marks": 0},
                    {"label": "Q3c", "co_labels": [], "co_evidence": "", "max_marks": 0},
                ],
            },
            {
                "label": "Q4",
                "co_labels": [],
                "co_evidence": "",
                "max_marks": 10,
                "is_bonus": False,
                "parts": [
                    {"label": "Q4a", "co_labels": [], "co_evidence": "", "max_marks": 0},
                    {"label": "Q4b", "co_labels": [], "co_evidence": "", "max_marks": 0},
                ],
            },
        ],
    }

    async def fake_generate_text(*args, **kwargs):
        return json.dumps(response)

    monkeypatch.setattr(question_paper_analyzer, "_generate_analysis_text", fake_generate_text)
    result = asyncio.run(question_paper_analyzer.analyze_question_paper_text("Each question is worth 10 marks. Maximum Marks: 40."))

    by_label = {q["label"]: q["max_marks"] for q in result["questions"]}
    assert by_label["Q1a"] == 5.0
    assert by_label["Q1b"] == 5.0
    assert by_label["Q3a"] == 3.33
    assert by_label["Q3b"] == 3.33
    assert by_label["Q3c"] == 3.34
    assert sum(q["max_marks"] for q in result["questions"]) == 40.0


def test_uses_printed_part_marks_when_present(monkeypatch):
    response = {
        "component_name": "EndSem",
        "paper_total_marks": 5,
        "questions": [
            {
                "label": "Q2",
                "co_labels": ["CO2"],
                "co_evidence": "[Q2] [CO2]",
                "max_marks": 5,
                "is_bonus": False,
                "parts": [
                    {"label": "Q2a", "co_labels": [], "co_evidence": "", "max_marks": 1},
                    {"label": "Q2b", "co_labels": [], "co_evidence": "", "max_marks": 2},
                    {"label": "Q2c", "co_labels": [], "co_evidence": "", "max_marks": 2},
                ],
            }
        ],
    }

    async def fake_generate_text(*args, **kwargs):
        return json.dumps(response)

    monkeypatch.setattr(question_paper_analyzer, "_generate_analysis_text", fake_generate_text)
    result = asyncio.run(
        question_paper_analyzer.analyze_question_paper_text(
            "[Q2] [CO2]: (a) [1 Mark] (b) [2 Marks] (c) [2 Marks]"
        )
    )

    by_label = {q["label"]: q for q in result["questions"]}
    assert by_label["Q2a"]["max_marks"] == 1.0
    assert by_label["Q2b"]["max_marks"] == 2.0
    assert by_label["Q2c"]["max_marks"] == 2.0
    # Parts inherit parent CO when paper only labels the parent header.
    assert by_label["Q2a"]["co_labels"] == ["CO2"]


def test_redistribute_when_llm_copies_parent_total_onto_each_part():
    questions = [
        AnalyzedQuestion("Q1a", [], 10),
        AnalyzedQuestion("Q1b", [], 10),
        AnalyzedQuestion("Q2a", [], 10),
        AnalyzedQuestion("Q2b", [], 10),
        AnalyzedQuestion("Q3a", [], 10),
        AnalyzedQuestion("Q3b", [], 10),
        AnalyzedQuestion("Q3c", [], 10),
        AnalyzedQuestion("Q4a", [], 10),
        AnalyzedQuestion("Q4b", [], 10),
    ]
    fixed = redistribute_sibling_marks(questions, paper_total_marks=40)
    assert sum(q.max_marks for q in fixed) == 40.0
    assert fixed[0].max_marks == 5.0
    assert fixed[4].max_marks == 3.33
