from __future__ import annotations

import uuid
from pathlib import Path

from app.config import get_settings


def ensure_projects_upload_dir() -> Path:
    settings = get_settings()
    path = Path(settings.projects_upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_project_upload(filename: str, content: bytes) -> tuple[str, str]:
    directory = ensure_projects_upload_dir()
    safe = Path(filename).name.replace(" ", "_")
    stored = f"{uuid.uuid4().hex[:8]}_{safe}"
    full = directory / stored
    full.write_bytes(content)
    return str(full.resolve()), stored
