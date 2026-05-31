"""Build API-safe parse/scope payloads (counts only — no roll lists)."""

from __future__ import annotations

PROGRAMME_LABELS = {
    "UG": "UG (Undergraduate)",
    "PG": "PG / M.Tech (MT prefix)",
    "PhD": "PhD (PhD prefix)",
    "Other": "Other",
}


def programme_label(prog: str) -> str:
    return PROGRAMME_LABELS.get(prog, prog)


def build_parse_api_payload(parse_result: dict) -> dict:
    """
    Convert parse_student_rolls() output to API response fields.
    Default selection: ALL detected programmes and ALL branches.
    """
    programmes = parse_result.get("programmes") or {}
    branches = parse_result.get("branches") or {}
    default_programmes = list(programmes.keys())
    default_branches = list(branches.keys())
    has_branch_data = bool(branches)

    return {
        "cos": parse_result.get("cos") or [],
        "programmes": programmes,
        "branches": branches,
        "total_students": int(parse_result.get("total_students") or 0),
        "has_branch_data": has_branch_data,
        "default_programmes": default_programmes,
        "default_branches": default_branches,
        "parse_message": "File analyzed successfully",
    }


def build_sanitized_parse_metadata(parse_result: dict) -> dict:
    """Persist only aggregate scope metadata — never roll lists."""
    payload = build_parse_api_payload(parse_result)
    return {
        "cos": payload["cos"],
        "programmes": payload["programmes"],
        "branches": payload["branches"],
        "total_students": payload["total_students"],
        "has_branch_data": payload["has_branch_data"],
    }
