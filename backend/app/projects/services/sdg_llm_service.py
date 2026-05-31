from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod

import httpx

from app.config import get_settings


class SdgLlmProvider(ABC):
    @abstractmethod
    def suggest_sdgs(self, project_title: str, project_type: str) -> list[dict]:
        """Return list of {sdg_number, confidence}."""

    def suggest_sdgs_with_retry(self, project_title: str, project_type: str) -> list[dict]:
        settings = get_settings()
        last_error: Exception | None = None
        for attempt in range(settings.sdg_max_retries):
            try:
                return self.suggest_sdgs(project_title, project_type)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    wait = settings.sdg_request_delay_seconds * (2**attempt)
                    time.sleep(wait)
                    continue
                raise
            except Exception as exc:
                last_error = exc
                if attempt + 1 < settings.sdg_max_retries:
                    time.sleep(settings.sdg_request_delay_seconds)
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("SDG suggestion failed after retries")


class GeminiSdgProvider(SdgLlmProvider):
    def suggest_sdgs(self, project_title: str, project_type: str) -> list[dict]:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured in backend/.env")
        prompt = _build_prompt(project_title, project_type)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, params={"key": settings.gemini_api_key}, json=payload)
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise ValueError("Gemini returned no candidates — check API key and model name")
        text = candidates[0]["content"]["parts"][0]["text"]
        return _parse_llm_json(text)


class OpenRouterSdgProvider(SdgLlmProvider):
    def suggest_sdgs(self, project_title: str, project_type: str) -> list[dict]:
        settings = get_settings()
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured in backend/.env")
        prompt = _build_prompt(project_title, project_type)
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
        return _parse_llm_json(text)


def get_sdg_provider() -> SdgLlmProvider:
    settings = get_settings()
    if settings.sdg_llm_provider.lower() == "openrouter":
        return OpenRouterSdgProvider()
    return GeminiSdgProvider()


def suggest_project_sdgs(project_title: str, project_type: str) -> list[dict]:
    return get_sdg_provider().suggest_sdgs_with_retry(project_title, project_type)


def _build_prompt(project_title: str, project_type: str) -> str:
    return (
        "You classify academic BTP/IP projects against UN Sustainable Development Goals (SDGs 1-17).\n"
        f"Project type: {project_type}\n"
        f"Project title: {project_title}\n\n"
        "Respond with ONLY valid JSON array, no markdown. Each item:\n"
        '{"sdg_number": <int 1-17>, "confidence": <float 0-1>}\n'
        "Suggest 1-4 most relevant SDGs."
    )


def _parse_llm_json(text: str) -> list[dict]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\[[\s\S]*\]", cleaned)
    if not match:
        raise ValueError("LLM response did not contain a JSON array")
    raw = json.loads(match.group(0))
    results: list[dict] = []
    for item in raw:
        num = int(item.get("sdg_number", item.get("sdg", 0)))
        if 1 <= num <= 17:
            conf = float(item.get("confidence", 0.7))
            results.append({"sdg_number": num, "confidence": max(0.0, min(1.0, conf))})
    return results
