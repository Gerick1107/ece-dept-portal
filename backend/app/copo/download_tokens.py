import time
import uuid

from app.config import get_settings

settings = get_settings()
_DOWNLOAD_TOKENS: dict[str, dict] = {}


def issue_download_token(excel_path: str) -> str:
    token = uuid.uuid4().hex
    _DOWNLOAD_TOKENS[token] = {"created_at": time.time(), "excel_path": excel_path}
    return token


def pop_download_path(token: str) -> str | None:
    entry = _DOWNLOAD_TOKENS.pop(token, None)
    if not entry:
        return None
    if (time.time() - entry["created_at"]) > settings.file_max_age_seconds:
        return None
    return entry.get("excel_path")


def cleanup_stale_tokens() -> None:
    now = time.time()
    stale = [
        k
        for k, v in _DOWNLOAD_TOKENS.items()
        if (now - v.get("created_at", now)) > settings.file_max_age_seconds
    ]
    for k in stale:
        _DOWNLOAD_TOKENS.pop(k, None)
