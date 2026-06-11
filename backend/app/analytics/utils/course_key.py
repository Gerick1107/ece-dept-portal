"""Helpers for course + optional section identity in analytics and LLM insights."""

from __future__ import annotations


def normalize_section(section_label: str | None) -> str | None:
    if section_label is None:
        return None
    cleaned = section_label.strip()
    if not cleaned:
        return None
    upper = cleaned.upper()
    if upper.startswith("SECTION "):
        cleaned = cleaned[8:].strip()
    return cleaned.upper()


def course_display_key(course_title: str, section_label: str | None = None) -> str:
    section = normalize_section(section_label)
    if section:
        return f"{course_title} · Section {section}"
    return course_title


def resolve_section_label(
    *,
    section_label: str | None = None,
    result_summary: dict | None = None,
) -> str | None:
    if section_label:
        return normalize_section(section_label)
    if isinstance(result_summary, dict) and result_summary.get("section_label"):
        return normalize_section(str(result_summary["section_label"]))
    return None
