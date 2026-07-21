"""Question-paper analysis and generated marks-template regression tests."""

from __future__ import annotations

import asyncio
import io
import json

from openpyxl import load_workbook

from app.copo.services import question_paper_analyzer
from app.copo.services.question_paper_analyzer import generate_component_workbook


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
