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
