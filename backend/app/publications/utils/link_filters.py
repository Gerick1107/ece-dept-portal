"""Publication URL / venue helpers used by sync, purge, and listing filters."""

from __future__ import annotations

import re
from typing import Any

BLOCKED_LINK_HOSTS = ("repository.iiitd.edu.in",)

# Scholar often lists IIITD theses with venue "IIIT-Delhi, 2025" and a scholar.google
# link — never the repository URL — so URL-only filters miss them.
_IIITD_THESIS_VENUE_RE = re.compile(
    r"\biiit[\s\-]?delhi\b",
    re.IGNORECASE,
)


def _haystack(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip().lower()
        if text:
            parts.append(text)
    return " ".join(parts)


def has_blocked_repository_link(*values: Any) -> bool:
    """True when any provided URL/text references a blocked institutional repository host."""
    joined = _haystack(*values)
    if not joined:
        return False
    return any(host in joined for host in BLOCKED_LINK_HOSTS)


def is_iiitd_repository_thesis_venue(*values: Any) -> bool:
    """True for Scholar thesis venues like ``IIIT-Delhi, 2025`` (not real journals)."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        if not _IIITD_THESIS_VENUE_RE.search(text):
            continue
        # Real journals rarely look like "IIIT-Delhi, 2025" alone.
        if re.fullmatch(r"iiit[\s\-]?delhi\s*,?\s*\d{4}", text, flags=re.IGNORECASE):
            return True
        if re.fullmatch(r"iiit[\s\-]?delhi", text, flags=re.IGNORECASE):
            return True
    return False


def publication_has_blocked_repository_link(publication: Any) -> bool:
    if has_blocked_repository_link(
        getattr(publication, "link", None),
        getattr(publication, "scholar_url", None),
        getattr(publication, "pdf_url", None),
        getattr(publication, "raw_metadata", None),
    ):
        return True
    return is_iiitd_repository_thesis_venue(
        getattr(publication, "journal", None),
        getattr(publication, "conference", None),
        getattr(publication, "book", None),
        getattr(publication, "publisher", None),
    )


def article_has_blocked_repository_link(article: dict[str, Any]) -> bool:
    if has_blocked_repository_link(
        article.get("link"),
        article.get("scholar_url"),
        article.get("pdf_url"),
        article.get("pub_url"),
        article.get("eprint_url"),
        article.get("raw_metadata"),
        article.get("snippet"),
        article.get("summary"),
    ):
        return True
    return is_iiitd_repository_thesis_venue(
        article.get("journal"),
        article.get("conference"),
        article.get("book"),
        article.get("publisher"),
        article.get("venue"),
    )


def venue_is_empty(journal: str | None, conference: str | None, book: str | None) -> bool:
    return not any([(journal or "").strip(), (conference or "").strip(), (book or "").strip()])


def venue_is_preprint_or_unlisted(
    journal: str | None,
    conference: str | None,
    book: str | None,
) -> bool:
    """Match arXiv-like venues or completely empty venue/journal fields."""
    if venue_is_empty(journal, conference, book):
        return True
    joined = _haystack(journal, conference, book)
    return "arxiv" in joined
