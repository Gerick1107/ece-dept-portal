from __future__ import annotations

import asyncio
import time

from groq import APIError, AuthenticationError, Groq, RateLimitError

from app.config import get_settings

# Default system prompt for CO/PO insight generation. Other call sites pass their own.
_SYSTEM_PROMPT = (
    "You are an academic course improvement advisor for an Electronics and "
    "Communication Engineering department. Provide specific, actionable teaching "
    "and learning recommendations based on CO and PO attainment data."
)
_MAX_RETRIES = 3
_RETRY_SECONDS = 10.0


class LlmError(Exception):
    """Raised for any LLM failure. ``code`` is a stable, machine-readable identifier
    the frontend can branch on (e.g. ``groq_unavailable``, ``local_llm_unavailable``)."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _call_groq_sync(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    settings = get_settings()
    api_key = (settings.groq_api_key or "").strip()
    if not api_key:
        raise LlmError(
            "Cloud (Groq) is not configured. Set GROQ_API_KEY or switch to the Local provider.",
            status_code=503,
            code="groq_unavailable",
        )

    model = (settings.groq_model or "").strip() or "openai/gpt-oss-120b"
    system = system_prompt or _SYSTEM_PROMPT
    for attempt in range(_MAX_RETRIES):
        try:
            client = Groq(api_key=api_key)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = chat_completion.choices[0].message.content
            if not content:
                raise LlmError("No response generated.", code="groq_empty")
            return content
        except RateLimitError:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_SECONDS)
                continue
            raise LlmError(
                "Cloud (Groq) rate limit reached. Please wait a minute and try again.",
                status_code=429,
                code="groq_rate_limit",
            ) from None
        except AuthenticationError:
            raise LlmError(
                "Invalid GROQ_API_KEY. Please check your environment variables.",
                status_code=401,
                code="groq_unavailable",
            ) from None
        except APIError as exc:
            status = getattr(exc, "status_code", None) or 502
            raise LlmError(
                "Could not reach Cloud (Groq) right now. Please try again.",
                status_code=status,
                code="groq_unavailable",
            ) from exc

    raise LlmError("Could not generate a response right now. Please try again.", status_code=502, code="groq_unavailable")


async def generate_groq_text(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """Unified Groq entry point matching the local client's signature."""
    return await asyncio.to_thread(
        _call_groq_sync,
        prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def groq_available() -> tuple[bool, str]:
    """Lightweight readiness check (no network call) for the providers endpoint."""
    settings = get_settings()
    if not (settings.groq_api_key or "").strip():
        return False, "GROQ_API_KEY is not set."
    model = (settings.groq_model or "").strip() or "openai/gpt-oss-120b"
    return True, f"Ready (model: {model})."


# --- Backwards-compatible wrappers (existing call sites still import these) ---
async def generate_llm_text(prompt: str) -> str:
    return await generate_groq_text(prompt)


async def generate_llm_text_with_system(
    prompt: str,
    *,
    system_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    return await generate_groq_text(
        prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens
    )
