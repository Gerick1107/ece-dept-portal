from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.config import BACKEND_ROOT, get_settings

KEY_USAGE_PATH = BACKEND_ROOT / "storage" / "key_usage.json"
SEARCHES_PER_KEY_BUDGET = 250


def load_api_keys() -> list[str]:
    settings = get_settings()
    raw = (os.getenv("SERP_API_KEYS") or "").strip()
    if not raw:
        if settings.serp_api_key:
            return [settings.serp_api_key.strip()]
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else default
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


class SerpApiKeyManager:
    """Rotate SerpAPI keys with per-key search budgets (persisted in storage/key_usage.json)."""

    def __init__(self, api_keys: list[str] | None = None) -> None:
        self.api_keys = api_keys if api_keys is not None else load_api_keys()
        state = _load_json(KEY_USAGE_PATH, {})
        counts = state.get("counts")
        if not isinstance(counts, list) or len(counts) != len(self.api_keys):
            counts = [0] * len(self.api_keys)
        idx = state.get("current_key_index", 0)
        if not isinstance(idx, int) or idx < 0 or idx >= max(len(self.api_keys), 1):
            idx = 0
        self._state: dict[str, Any] = {"current_key_index": idx, "counts": counts}

    def _persist(self) -> None:
        _save_json(KEY_USAGE_PATH, self._state)

    @property
    def exhausted(self) -> bool:
        if not self.api_keys:
            return True
        return self._state["current_key_index"] >= len(self.api_keys)

    def current_key(self) -> str | None:
        if self.exhausted:
            return None
        return self.api_keys[self._state["current_key_index"]]

    def is_key_exhausted(self, status: int | None, err: str | None) -> bool:
        if status in (401, 429):
            return True
        if not err:
            return False
        lower = err.lower()
        return any(
            phrase in lower
            for phrase in (
                "quota",
                "limit exceeded",
                "run out",
                "insufficient",
                "invalid api key",
                "exceeded your",
                "too many requests",
            )
        )

    def rotate(self, reason: str) -> bool:
        idx = self._state["current_key_index"]
        self._state["current_key_index"] = idx + 1
        self._persist()
        return self._state["current_key_index"] < len(self.api_keys)

    def record_use(self) -> None:
        idx = self._state["current_key_index"]
        self._state["counts"][idx] = int(self._state["counts"][idx]) + 1
        self._persist()

    def budget_exceeded(self) -> bool:
        idx = self._state["current_key_index"]
        return int(self._state["counts"][idx]) >= SEARCHES_PER_KEY_BUDGET
