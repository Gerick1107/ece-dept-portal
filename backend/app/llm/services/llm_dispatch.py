"""Single dispatch point for every LLM call in the app.

Call sites (RAG answering, CO/PO insight generation, document summaries) go through
``generate_text`` and pass the user-selected ``provider``. No call site should
instantiate a provider client directly.
"""
from __future__ import annotations

from app.config import get_settings
from app.llm.services import groq_service, local_service
from app.llm.services.groq_service import LlmError

PROVIDERS = ("groq", "local")


def normalize_provider(provider: str | None) -> str:
    p = (provider or "").strip().lower()
    if p in PROVIDERS:
        return p
    return (get_settings().default_llm_provider or "groq").strip().lower() if not p else p


async def generate_text(
    prompt: str,
    *,
    provider: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    chosen = normalize_provider(provider)
    if chosen == "local":
        return await local_service.generate_local_text(
            prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens
        )
    if chosen == "groq":
        return await groq_service.generate_groq_text(
            prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens
        )
    raise LlmError(f"Unknown LLM provider '{provider}'.", status_code=400, code="unknown_provider")


def provider_status() -> dict:
    """Availability of each provider for the frontend selector."""
    groq_ok, groq_msg = groq_service.groq_available()
    local_ok, local_msg = local_service.local_available()
    settings = get_settings()
    return {
        "default": normalize_provider(None),
        "providers": [
            {
                "id": "groq",
                "label": "Cloud (Groq)",
                "available": groq_ok,
                "message": groq_msg,
                "model": (settings.groq_model or "").strip(),
            },
            {
                "id": "local",
                "label": "Local (Offline)",
                "available": local_ok,
                "message": local_msg,
                "model": (settings.local_llm_model or "").strip(),
            },
        ],
    }
