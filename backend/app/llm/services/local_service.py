"""Local LLM client backed by Ollama (https://ollama.com).

Ollama exposes an OpenAI-compatible API at ``/v1`` so we reuse the OpenAI SDK.
Everything runs on the local machine — no API key, no cost, fully offline.

GPU use is controlled via Ollama ``options.num_gpu`` (set ``LOCAL_LLM_NUM_GPU=-1``
to offload all layers when a GPU is available on the Ollama host).
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from openai import APIConnectionError, APIError, AuthenticationError, NotFoundError, OpenAI

from app.config import get_settings
from app.llm.services.errors import LlmError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an academic course improvement advisor for an Electronics and "
    "Communication Engineering department. Provide specific, actionable teaching "
    "and learning recommendations based on CO and PO attainment data."
)

_API_KEY = "ollama"
_REQUEST_TIMEOUT = 120.0


def _ollama_root(base_url: str) -> str:
    root = (base_url or "").strip().rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    return root or "http://localhost:11434"


def _build_client() -> tuple[OpenAI, str]:
    settings = get_settings()
    base_url = (settings.local_llm_base_url or "").strip() or "http://localhost:11434/v1"
    model = (settings.local_llm_model or "").strip() or "llama3.2:3b"
    client = OpenAI(base_url=base_url, api_key=_API_KEY, timeout=_REQUEST_TIMEOUT)
    return client, model


def _ollama_extra_body() -> dict:
    settings = get_settings()
    options: dict[str, int | str] = {}
    if settings.local_llm_num_gpu is not None:
        options["num_gpu"] = int(settings.local_llm_num_gpu)
    if settings.local_llm_num_ctx:
        options["num_ctx"] = int(settings.local_llm_num_ctx)
    if settings.local_llm_num_thread:
        options["num_thread"] = int(settings.local_llm_num_thread)
    body: dict = {}
    if options:
        body["options"] = options
    keep_alive = (settings.local_llm_keep_alive or "").strip()
    if keep_alive:
        body["keep_alive"] = keep_alive
    return body


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
    extra_body = _ollama_extra_body()
    try:
        kwargs: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra_body:
            kwargs["extra_body"] = extra_body
        completion = client.chat.completions.create(**kwargs)
    except NotFoundError as exc:
        raise _model_not_found() from exc
    except (APIConnectionError, httpx.ConnectError, httpx.TimeoutException) as exc:
        raise _unavailable(type(exc).__name__) from exc
    except AuthenticationError as exc:
        raise _unavailable("auth") from exc
    except APIError as exc:
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


def _gpu_status_message(base_url: str, model: str) -> str:
    """Best-effort GPU layer info from Ollama's running-process API."""
    try:
        resp = httpx.get(f"{_ollama_root(base_url)}/api/ps", timeout=3.0)
        resp.raise_for_status()
        for proc in resp.json().get("models") or []:
            name = proc.get("name") or proc.get("model") or ""
            if name.split(":")[0] == model.split(":")[0] or name == model:
                details = proc.get("details") or {}
                size_vram = details.get("size_vram") or proc.get("size_vram")
                if size_vram:
                    gb = int(size_vram) / (1024**3)
                    return f"Ready (model: {model}, ~{gb:.1f} GB on GPU)."
                return f"Ready (model: {model}, loaded in Ollama)."
    except Exception:
        pass
    settings = get_settings()
    gpu_hint = f", num_gpu={settings.local_llm_num_gpu}" if settings.local_llm_num_gpu else ""
    return f"Ready (model: {model}{gpu_hint}). Ensure Ollama sees your GPU (`ollama ps`)."


def warm_up_model() -> None:
    """Pre-load the model into Ollama (and GPU when configured) to cut first-request latency."""
    settings = get_settings()
    if not settings.local_llm_warmup_on_startup:
        return
    try:
        _call_local_sync("Reply with OK.", system_prompt="Reply with exactly OK.", temperature=0.0, max_tokens=4)
        logger.info("Local LLM warm-up complete (%s).", settings.local_llm_model)
    except LlmError as exc:
        logger.warning("Local LLM warm-up skipped: %s", exc)


def local_available() -> tuple[bool, str]:
    """Check that Ollama is running and the configured model is pulled."""
    settings = get_settings()
    base_url = (settings.local_llm_base_url or "").strip() or "http://localhost:11434/v1"
    model = (settings.local_llm_model or "").strip() or "llama3.2:3b"
    tags_url = f"{_ollama_root(base_url)}/api/tags"
    try:
        resp = httpx.get(tags_url, timeout=3.0)
        resp.raise_for_status()
        models = [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:
        return False, f"Ollama not reachable at {base_url}. Start it with `ollama serve`."

    base_name = model.split(":")[0]
    if any(m == model or m.split(":")[0] == base_name for m in models):
        return True, _gpu_status_message(base_url, model)
    return False, f"Model `{model}` not pulled. Run `ollama pull {model}`."
