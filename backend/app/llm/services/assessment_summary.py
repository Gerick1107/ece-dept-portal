"""Summarize assessment components from CO-PO evaluation run data."""

from __future__ import annotations

import re
from collections import defaultdict


def _component_base(name: str) -> str:
    s = str(name).strip()
    m = re.match(r"^(.+?)\.\d+$", s)
    if m:
        return m.group(1)
    m = re.match(r"^(.+?)_Q\d+$", s, re.IGNORECASE)
    if m:
        return m.group(1)
    return s


def _component_type(name: str) -> str:
    base = _component_base(name)
    token = re.split(r"[_.\s]+", base)[0]
    return token or base


def summarize_assessment_ids(assessment_ids: list[str]) -> list[dict]:
    """Group assessment column labels into component types with counts."""
    if not assessment_ids:
        return []

    by_component: dict[str, list[str]] = defaultdict(list)
    for col in assessment_ids:
        by_component[_component_base(col)].append(col)

    type_stats: dict[str, dict] = defaultdict(lambda: {"component_count": 0, "total_questions": 0})
    for comp_name, cols in by_component.items():
        comp_type = _component_type(comp_name)
        type_stats[comp_type]["component_count"] += 1
        type_stats[comp_type]["total_questions"] += len(cols)

    return [
        {
            "component_type": comp_type,
            "component_count": stats["component_count"],
            "total_questions": stats["total_questions"],
        }
        for comp_type, stats in sorted(type_stats.items())
    ]


def format_assessment_summary_block(summary: list[dict]) -> str:
    if not summary:
        return "No assessment structure data available for this course run."
    lines = []
    for item in summary:
        lines.append(
            f"- {item['component_type']}: {item['component_count']} component(s), "
            f"{item['total_questions']} total question column(s)"
        )
    return "\n".join(lines)
