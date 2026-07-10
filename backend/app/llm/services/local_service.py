"""Local LLM client backed by Ollama (https://ollama.com).

Ollama exposes an OpenAI-compatible API at ``/v1`` so we reuse the OpenAI SDK.
Everything runs on the local machine — no API key, no cost, fully offline.

The model must be pulled first, e.g. ``ollama pull llama3.2:3b``. See README.
"""
from __future__ import annotations

import asyncio

import httpx
from openai import APIConnectionError, APIError, AuthenticationError, NotFoundError, OpenAI

from app.config import get_settings
from app.llm.services.errors import LlmError

_SYSTEM_PROMPT = (
    "You are an academic course improvement advisor for an Electronics and "
    "Communication Engineering department. Provide specific, actionable teaching "
    "and learning recommendations based on CO and PO attainment data."
)

# Ollama ignores the api_key, but the OpenAI SDK requires a non-empty string.
_API_KEY = "ollama"
_REQUEST_TIMEOUT = 120.0


def _build_client() -> tuple[OpenAI, str]:
    settings = get_settings()
    base_url = (settings.local_llm_base_url or "").strip() or "http://localhost:11434/v1"
    model = (settings.local_llm_model or "").strip() or "llama3.2:3b"
    client = OpenAI(base_url=base_url, api_key=_API_KEY, timeout=_REQUEST_TIMEOUT)
    return client, model


def _unavailable(detail: str) -> LlmError:
    settings = get_settings()
    model = (settings.local_llm_model or "llama3.2:3b").strip()
    return LlmError(
        f"Local LLM (Ollama) isn't reachable. Start it with `ollama serve` and make sure "
        f"`{model}` is pulled (`ollama pull {model}`). [{detail}]",
        status_code=503,
        code="local_llm_unavailable",
    )


def _model_not_found() -> LlmError:
    settings = get_settings()
    model = (settings.local_llm_model or "llama3.2:3b").strip()
    return LlmError(
        f"Local model `{model}` is not pulled. Run `ollama pull {model}`.",
        status_code=503,
        code="local_llm_unavailable",
    )


def _call_local_sync(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    client, model = _build_client()
    system = system_prompt or _SYSTEM_PROMPT
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except NotFoundError as exc:
        raise _model_not_found() from exc
    except (APIConnectionError, httpx.ConnectError, httpx.TimeoutException) as exc:
        raise _unavailable(type(exc).__name__) from exc
    except AuthenticationError as exc:  # shouldn't happen with Ollama, but be safe
        raise _unavailable("auth") from exc
    except APIError as exc:
        # Ollama returns 404 in the message body when the model isn't pulled.
        if "not found" in str(exc).lower() or "no such model" in str(exc).lower():
            raise _model_not_found() from exc
        raise _unavailable(getattr(exc, "message", "") or str(exc)) from exc

    content = completion.choices[0].message.content if completion.choices else None
    if not content:
        raise LlmError("Local model returned an empty response.", status_code=502, code="local_llm_unavailable")
    return content


async def generate_local_text(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    return await asyncio.to_thread(
        _call_local_sync,
        prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def local_available() -> tuple[bool, str]:
    """Check that Ollama is running and the configured model is pulled.

    Uses the native ``/api/tags`` endpoint (derived from the configured base URL) so
    the providers endpoint can report a clear, actionable status without a generation.
    """
    settings = get_settings()
    base_url = (settings.local_llm_base_url or "").strip() or "http://localhost:11434/v1"
    model = (settings.local_llm_model or "").strip() or "llama3.2:3b"
    tags_url = base_url.rstrip("/")
    if tags_url.endswith("/v1"):
        tags_url = tags_url[: -len("/v1")]
    tags_url = f"{tags_url}/api/tags"
    try:
        resp = httpx.get(tags_url, timeout=3.0)
        resp.raise_for_status()
        models = [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:
        return False, f"Ollama not reachable at {base_url}. Start it with `ollama serve`."

    # Ollama tags include the tag suffix (e.g. "llama3.2:3b"); match leniently.
    base_name = model.split(":")[0]
    if any(m == model or m.split(":")[0] == base_name for m in models):
        return True, f"Ready (model: {model})."
    return False, f"Model `{model}` not pulled. Run `ollama pull {model}`."
