from __future__ import annotations


class LlmError(Exception):
    """Raised for any LLM failure. ``code`` is a stable, machine-readable identifier
    the frontend can branch on (e.g. ``local_llm_unavailable``)."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
