from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.documents.models.entities import (
    DOCUMENT_TYPE_AAC,
    DOCUMENT_TYPE_ALL,
    DOCUMENT_TYPE_ECE_FACULTY_MEET,
    DOCUMENT_TYPE_PGC,
    DOCUMENT_TYPE_SENATE,
    DOCUMENT_TYPE_UGC,
)

DOCUMENT_TYPE_DIRS: dict[str, str] = {
    DOCUMENT_TYPE_SENATE: "senate-minutes",
    DOCUMENT_TYPE_ECE_FACULTY_MEET: "ece-faculty-meets",
    DOCUMENT_TYPE_AAC: "aac-meetings",
    DOCUMENT_TYPE_UGC: "ugc-meetings",
    DOCUMENT_TYPE_PGC: "pgc-meetings",
}

SLUG_TO_TYPE: dict[str, str] = {
    "senate": DOCUMENT_TYPE_SENATE,
    "senate-meetings": DOCUMENT_TYPE_SENATE,
    "ece-faculty-meets": DOCUMENT_TYPE_ECE_FACULTY_MEET,
    "ece-faculty-meetings": DOCUMENT_TYPE_ECE_FACULTY_MEET,
    "aac-meetings": DOCUMENT_TYPE_AAC,
    "ugc-meetings": DOCUMENT_TYPE_UGC,
    "pgc-meetings": DOCUMENT_TYPE_PGC,
    "all-meetings": DOCUMENT_TYPE_ALL,
}


def ensure_documents_dirs() -> Path:
    root = Path(get_settings().documents_dir)
    for subdir in DOCUMENT_TYPE_DIRS.values():
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


def subdir_for_type(document_type: str) -> str:
    return DOCUMENT_TYPE_DIRS.get(document_type, "documents")


def resolve_document_path(stored_path: str | Path) -> Path:
    """Resolve a stored document path to the current documents directory.

    Stored ``file_path`` values are absolute paths from whichever machine ingested
    the PDF (e.g. a Windows path baked into a DB dump that is later read inside a
    Linux container, or a friend's differently-named project folder). If the path
    exists as-is, it is used unchanged; otherwise it is re-anchored under the
    configured ``documents_dir`` using the known document-type subdir so the same
    DB works across machines without rewriting stored paths.
    """
    raw = str(stored_path)
    direct = Path(raw)
    if direct.exists():
        return direct

    root = Path(get_settings().documents_dir)
    # Normalize separators so Windows paths split correctly when running on Linux.
    parts = [p for p in raw.replace("\\", "/").split("/") if p]
    known = set(DOCUMENT_TYPE_DIRS.values())
    for i, part in enumerate(parts):
        if part in known:
            return root.joinpath(*parts[i:])
    # Fallback: re-anchor on the last "documents" segment if present.
    if "documents" in parts:
        last = len(parts) - 1 - parts[::-1].index("documents")
        return root.joinpath(*parts[last + 1:])
    return direct
