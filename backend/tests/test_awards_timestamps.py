"""Regression tests for faculty awards timestamp formatting."""

from __future__ import annotations

from datetime import datetime, timezone


def _format_ts(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def test_award_timestamp_formatting_renders_real_values_not_placeholder():
    created = datetime(2026, 6, 4, 18, 46, 33, tzinfo=timezone.utc)
    updated = datetime(2026, 6, 4, 13, 28, 21, tzinfo=timezone.utc)
    assert _format_ts(created) == "2026-06-04 18:46:33"
    assert _format_ts(updated) == "2026-06-04 13:28:21"
    assert "###" not in (_format_ts(created) or "")
