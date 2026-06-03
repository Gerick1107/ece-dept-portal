from __future__ import annotations

import time
from typing import Any

import httpx

SERPAPI_AUTHOR_URL = "https://serpapi.com/search"
PAGE_SIZE = 20
REQUEST_DELAY_SECONDS = 1.0


class SerpApiError(Exception):
    """Raised when SerpAPI returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _parse_profile_metrics(cited_by: dict[str, Any] | None) -> dict[str, int]:
    metrics = {"total_citations": 0, "h_index": 0, "i10_index": 0}
    table = (cited_by or {}).get("table") or []
    if len(table) > 0:
        citations = table[0].get("citations") or {}
        metrics["total_citations"] = int(citations.get("all") or 0)
    if len(table) > 1:
        h_index = table[1].get("h_index") or {}
        metrics["h_index"] = int(h_index.get("all") or 0)
    if len(table) > 2:
        i10_index = table[2].get("i10_index") or {}
        metrics["i10_index"] = int(i10_index.get("all") or 0)
    return metrics


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    year_raw = article.get("year")
    try:
        year = int(year_raw) if year_raw else None
    except (TypeError, ValueError):
        year = None

    venue = (article.get("publication") or "").strip() or None
    cited_by = article.get("cited_by") or {}
    citation_count = 0
    if isinstance(cited_by, dict):
        citation_count = int(cited_by.get("value") or 0)

    return {
        "title": (article.get("title") or "").strip(),
        "authors": (article.get("authors") or "").strip() or None,
        "publication_year": year,
        "journal": venue,
        "publisher": None,
        "citation_count": citation_count,
        "link": article.get("link"),
        "is_patent": False,
        "scholar_url": article.get("link"),
        "pdf_url": None,
    }


def _raise_for_serpapi_response(response: httpx.Response, payload: dict[str, Any]) -> None:
    if response.status_code == 401:
        raise SerpApiError("SerpAPI authentication failed (401): invalid API key", 401)
    if response.status_code == 429:
        raise SerpApiError("SerpAPI rate limit exceeded (429)", 429)
    if response.status_code == 422:
        raise SerpApiError(f"SerpAPI invalid request (422): {payload.get('error', response.text)}", 422)
    if response.status_code >= 400:
        raise SerpApiError(
            f"SerpAPI HTTP error ({response.status_code}): {payload.get('error', response.text)}",
            response.status_code,
        )
    if payload.get("error"):
        raise SerpApiError(f"SerpAPI error: {payload['error']}")


def _fetch_author_page(
    client: httpx.Client,
    scholar_id: str,
    api_key: str,
    start: int,
) -> dict[str, Any]:
    params = {
        "engine": "google_scholar_author",
        "author_id": scholar_id,
        "api_key": api_key,
        "start": start,
    }
    response = client.get(SERPAPI_AUTHOR_URL, params=params)
    try:
        payload = response.json()
    except ValueError as exc:
        raise SerpApiError(
            f"SerpAPI returned non-JSON response (HTTP {response.status_code}): {response.text[:300]}",
            response.status_code,
        ) from exc

    if not isinstance(payload, dict):
        raise SerpApiError("SerpAPI returned unexpected payload format")

    _raise_for_serpapi_response(response, payload)
    return payload


def scrape_faculty_serpapi(scholar_id: str, api_key: str) -> dict[str, Any]:
    """
    Fetch all articles for a Google Scholar author via SerpAPI.

    Returns:
        {
            "profile_metrics": {"total_citations", "h_index", "i10_index"},
            "articles": [<normalized publication dicts>],
        }
    """
    if not scholar_id:
        raise ValueError("scholar_id is required")
    if not api_key:
        raise SerpApiError("SERP_API_KEY is not configured", 401)

    all_articles: list[dict[str, Any]] = []
    profile_metrics = {"total_citations": 0, "h_index": 0, "i10_index": 0}

    with httpx.Client(timeout=60.0) as client:
        start = 0
        while True:
            payload = _fetch_author_page(client, scholar_id, api_key, start)
            if start == 0:
                profile_metrics = _parse_profile_metrics(payload.get("cited_by"))

            page_articles = payload.get("articles") or []
            if not page_articles:
                break

            for article in page_articles:
                if isinstance(article, dict):
                    all_articles.append(_normalize_article(article))

            if len(page_articles) < PAGE_SIZE:
                break

            start += PAGE_SIZE
            time.sleep(REQUEST_DELAY_SECONDS)

    return {
        "profile_metrics": profile_metrics,
        "articles": all_articles,
    }
