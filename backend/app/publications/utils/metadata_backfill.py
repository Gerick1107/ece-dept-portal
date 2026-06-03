"""Apply SerpAPI view_citation JSON to publication column fields."""
from __future__ import annotations

from typing import Any

from app.publications.models import Publication

_COLUMN_LIMITS: dict[str, int] = {
    "title": 1024,
    "link": 2000,
    "pdf_url": 1024,
    "publication_date": 50,
    "pages": 100,
    "journal": 500,
    "volume": 50,
    "issue": 50,
    "patent_office": 100,
    "patent_number": 200,
    "application_number": 200,
    "publisher": 512,
}


def clean_metadata_str(value: Any, field: str | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if field and field in _COLUMN_LIMITS:
        text = text[: _COLUMN_LIMITS[field]]
    return text


def is_patent_metadata(meta: dict[str, Any]) -> bool:
    return any(key in meta for key in ("patent_office", "patent_number", "application_number"))


def citation_total_from_metadata(meta: dict[str, Any]) -> int | None:
    total_citations = meta.get("total_citations")
    if not isinstance(total_citations, dict):
        return None
    cited_by = total_citations.get("cited_by")
    if not isinstance(cited_by, dict):
        return None
    total = cited_by.get("total")
    if total is None:
        return None
    try:
        return int(total)
    except (TypeError, ValueError):
        return None


def pdf_url_from_metadata(meta: dict[str, Any]) -> str | None:
    resources = meta.get("resources")
    if not isinstance(resources, list) or not resources:
        return None
    first = resources[0]
    if not isinstance(first, dict):
        return None
    return clean_metadata_str(first.get("link"), "pdf_url")


def build_updates_from_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    patent = is_patent_metadata(meta)
    updates: dict[str, Any] = {"is_patent": patent}

    title = clean_metadata_str(meta.get("title"), "title")
    if title:
        updates["title"] = title

    authors = meta.get("authors")
    if authors is not None:
        updates["authors"] = clean_metadata_str(authors)
    elif patent and meta.get("inventors") is not None:
        updates["authors"] = clean_metadata_str(meta.get("inventors"))

    if meta.get("publisher") is not None:
        updates["publisher"] = clean_metadata_str(meta.get("publisher"), "publisher")

    citation = citation_total_from_metadata(meta)
    if citation is not None:
        updates["citation_count"] = citation

    updates["pdf_url"] = pdf_url_from_metadata(meta)

    for field in ("link", "publication_date", "pages", "volume", "issue"):
        if field in meta:
            updates[field] = clean_metadata_str(meta.get(field), field)

    if patent:
        for field in ("inventors", "patent_office", "patent_number", "application_number"):
            if field in meta:
                updates[field] = clean_metadata_str(meta.get(field), field)
    else:
        for field in ("journal", "conference", "book"):
            if field in meta:
                updates[field] = clean_metadata_str(meta.get(field), field)

    return updates


def apply_metadata_to_publication(publication: Publication, meta: dict[str, Any]) -> None:
    for key, value in build_updates_from_metadata(meta).items():
        setattr(publication, key, value)
