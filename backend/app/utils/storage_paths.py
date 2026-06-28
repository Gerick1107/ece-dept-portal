"""Resolve stored file paths to the current ``storage/`` directory.

Like documents, uploaded files (notification attachments, project import sheets)
store an absolute path from the machine that created them. A DB dump taken on
Windows therefore holds ``C:\\...\\storage\\...`` paths that don't exist inside the
Linux container. This re-anchors such paths under the running instance's storage
root so migrated records keep working without rewriting the database.
"""
from __future__ import annotations

from pathlib import Path

from app.config import get_settings

_STORAGE_ANCHOR = "storage"


def storage_root() -> Path:
    # upload_dir is "<root>/storage/uploads"; its parent is the storage root.
    return Path(get_settings().upload_dir).parent


def resolve_storage_path(stored_path: str | Path) -> Path:
    """Return a usable path for a stored storage file, re-anchoring if needed."""
    raw = str(stored_path)
    direct = Path(raw)
    if direct.exists():
        return direct

    parts = [p for p in raw.replace("\\", "/").split("/") if p]
    if _STORAGE_ANCHOR in parts:
        idx = len(parts) - 1 - parts[::-1].index(_STORAGE_ANCHOR)
        return storage_root().joinpath(*parts[idx + 1:])
    return direct
