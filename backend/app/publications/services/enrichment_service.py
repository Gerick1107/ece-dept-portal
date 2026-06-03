from __future__ import annotations

import json
import logging
import time
from urllib.parse import parse_qs, urlparse

import httpx

from app.publications.models import Publication
from app.publications.services.serpapi_keys import SerpApiKeyManager
from app.publications.utils.metadata_backfill import apply_metadata_to_publication

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"
REQUEST_DELAY_SECONDS = 1.0


def extract_citation_for_view(scholar_url: str | None) -> str | None:
    if not scholar_url:
        return None
    parsed = urlparse(scholar_url)
    values = parse_qs(parsed.query).get("citation_for_view")
    if not values:
        return None
    value = values[0].strip()
    return value or None


def fetch_citation_metadata(
    client: httpx.Client,
    citation_id: str,
    api_key: str,
) -> tuple[dict | None, int | None, str | None]:
    params = {
        "engine": "google_scholar_author",
        "view_op": "view_citation",
        "citation_id": citation_id,
        "api_key": api_key,
    }
    try:
        response = client.get(SERPAPI_URL, params=params)
    except httpx.HTTPError as exc:
        return None, None, str(exc)

    status = response.status_code
    try:
        payload = response.json()
    except ValueError:
        return None, status, f"non-JSON response (HTTP {status})"

    if status in (401, 429):
        err = payload.get("error") if isinstance(payload, dict) else response.text
        return None, status, str(err)

    if status >= 400:
        err = payload.get("error") if isinstance(payload, dict) else response.text
        return None, status, f"HTTP {status}: {err}"

    if not isinstance(payload, dict):
        return None, status, "unexpected payload format"

    if payload.get("error"):
        return None, status, str(payload["error"])

    citation = payload.get("citation")
    if not isinstance(citation, dict):
        return None, status, "missing citation object in response"

    return citation, status, None


def enrich_publication(
    publication: Publication,
    *,
    client: httpx.Client,
    key_manager: SerpApiKeyManager,
) -> bool:
    """
    Fetch view_citation metadata for one publication, store raw JSON, apply schema fields.
    Returns True if enrichment succeeded or was skipped safely, False if keys exhausted.
    """
    citation_for_view = extract_citation_for_view(publication.scholar_url)
    if not citation_for_view:
        publication.raw_metadata = "{}"
        return True

    while not key_manager.exhausted:
        if key_manager.budget_exceeded():
            if not key_manager.rotate(f"reached budget on key {key_manager._state['current_key_index']}"):
                return False
            continue

        api_key = key_manager.current_key()
        if not api_key:
            return False

        citation, http_status, err = fetch_citation_metadata(client, citation_for_view, api_key)
        if key_manager.is_key_exhausted(http_status, err):
            if not key_manager.rotate(f"API error ({http_status}: {err})"):
                return False
            continue

        if citation is None:
            logger.warning(
                "Enrichment failed publication_id=%s: %s",
                publication.id,
                err,
            )
            return True

        key_manager.record_use()
        publication.raw_metadata = json.dumps(citation, ensure_ascii=False)
        apply_metadata_to_publication(publication, citation)
        time.sleep(REQUEST_DELAY_SECONDS)
        return True

    return False
