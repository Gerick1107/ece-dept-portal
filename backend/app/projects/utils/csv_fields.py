from __future__ import annotations


def parse_csv_field(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def append_csv_value(existing: str | None, new_value: str) -> str:
    cleaned = new_value.strip()
    if not cleaned:
        return existing or ""
    items = parse_csv_field(existing)
    if cleaned not in items:
        items.append(cleaned)
    return ", ".join(items)
