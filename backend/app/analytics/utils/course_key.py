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


def normalize_programme(programme_label: str | None) -> str | None:
    if programme_label is None:
        return None
    cleaned = programme_label.strip().upper()
    if cleaned in ("UG", "PG", "UG/PG"):
        return cleaned
    return None


def course_display_key(
    course_title: str,
    section_label: str | None = None,
    *,
    programme_label: str | None = None,
    include_programme_variant: bool = False,
) -> str:
    key = course_title
    section = normalize_section(section_label)
    if section:
        key = f"{key} · Section {section}"
    programme = normalize_programme(programme_label)
    if include_programme_variant and programme in ("UG", "PG"):
        key = f"{key} · {programme}"
    return key


def run_display_label(
    semester_label: str,
    *,
    section_label: str | None = None,
    programme_label: str | None = None,
    distinguish_programme: bool = False,
) -> str:
    label = semester_label
    section = normalize_section(section_label)
    if section:
        label = f"{label} · Sec {section}"
    programme = normalize_programme(programme_label)
    if distinguish_programme and programme in ("UG", "PG"):
        label = f"{label} · {programme}"
    return label


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
