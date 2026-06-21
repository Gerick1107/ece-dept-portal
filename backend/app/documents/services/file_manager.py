from __future__ import annotations

from pathlib import Path

from app.config import get_settings

SENATE_SUBDIR = "senate-minutes"
ECE_MEETS_SUBDIR = "ece-faculty-meets"


def ensure_documents_dirs() -> Path:
    """Ensure tracked document subfolders exist (PDFs are gitignored)."""
    root = Path(get_settings().documents_dir)
    for name in (SENATE_SUBDIR, ECE_MEETS_SUBDIR):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
