from __future__ import annotations

import hashlib
from datetime import datetime


def normalize_scholar_id(raw: str) -> str:
    raw = (raw or "").strip()
    if "user=" in raw:
        return raw.split("user=", 1)[1].split("&", 1)[0].strip()
    return raw


def make_source_hash(title: str, publication_year: int | None) -> str:
    payload = f"{(title or '').strip().lower()}|{publication_year or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_within_tenure(join_year: int, leave_year: int | None, publication_year: int | None) -> bool:
    if publication_year is None:
        return False
    current_year = datetime.utcnow().year
    upper = leave_year if leave_year is not None else current_year
    return join_year <= publication_year <= upper


def infer_active_status(leave_year: int | None) -> bool:
    return leave_year is None
