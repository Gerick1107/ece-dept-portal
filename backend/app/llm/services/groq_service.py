from __future__ import annotations

import asyncio
import time

from groq import APIError, AuthenticationError, Groq, RateLimitError

from app.config import get_settings

_MODEL = "llama-3.3-70b-versatile"
_SYSTEM_PROMPT = (
    "You are an academic course improvement advisor for an Electronics and "
    "Communication Engineering department. Provide specific, actionable teaching "
    "and learning recommendations based on CO and PO attainment data."
)
_MAX_RETRIES = 3
_RETRY_SECONDS = 10.0


class LlmError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


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
        raise LlmError("GROQ_API_KEY not configured", status_code=503)

    system = system_prompt or _SYSTEM_PROMPT
    for attempt in range(_MAX_RETRIES):
        try:
            client = Groq(api_key=api_key)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                model=_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = chat_completion.choices[0].message.content
            if not content:
                raise LlmError("No response generated.")
            return content
        except RateLimitError:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_SECONDS)
                continue
            raise LlmError(
                "AI service rate limit reached. Please wait a minute and try Generate again.",
                status_code=429,
            ) from None
        except AuthenticationError:
            raise LlmError(
                "Invalid GROQ_API_KEY. Please check your environment variables.",
                status_code=401,
            ) from None
        except APIError as exc:
            status = getattr(exc, "status_code", None) or 502
            raise LlmError(
                "Could not generate insights at this time. Please try again.",
                status_code=status,
            ) from exc

    raise LlmError("Could not generate insights at this time. Please try again.", status_code=502)


def _call_groq_sync_legacy(prompt: str) -> str:
    return _call_groq_sync(prompt)


async def generate_llm_text(prompt: str) -> str:
    return await asyncio.to_thread(_call_groq_sync_legacy, prompt)


async def generate_llm_text_with_system(
    prompt: str,
    *,
    system_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    return await asyncio.to_thread(
        _call_groq_sync,
        prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
