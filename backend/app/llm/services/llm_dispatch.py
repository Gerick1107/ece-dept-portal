"""Single dispatch point for every LLM call in the app.

All generative text runs on the local, offline model (Ollama). Call sites
(RAG answering, CO/PO insight generation, document summaries) go through
``generate_text``. No call site should instantiate a provider client directly.
"""
from __future__ import annotations

from app.config import get_settings
from app.llm.services import local_service
from app.llm.services.errors import LlmError

PROVIDERS = ("local",)


def normalize_provider(provider: str | None) -> str:
    """Every provider resolves to ``local``; kept for backward-compatible call sites."""
    return "local"


async def generate_text(
    prompt: str,
    *,
    provider: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    return await local_service.generate_local_text(
        prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens
    )


def provider_status() -> dict:
    """Availability of the local provider for the frontend selector."""
    local_ok, local_msg = local_service.local_available()
    settings = get_settings()
    gpu_layers = settings.local_llm_num_gpu
    return {
        "default": "local",
        "providers": [
            {
                "id": "local",
                "label": "Local (Offline)",
                "available": local_ok,
                "message": local_msg,
                "model": (settings.local_llm_model or "").strip(),
                "num_gpu": gpu_layers,
            },
        ],
    }
