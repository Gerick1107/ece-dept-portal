from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.publications.models.entities import Publication


def _pub_type(row: Publication) -> str:
    if row.is_patent:
        return "Patent"
    if row.book:
        return "Book"
    if row.journal:
        return "Journal"
    if row.conference:
        return "Conference"
    return "Other"


def get_publications_analytics(
    db: Session,
    *,
    year: int | None = None,
    pub_type: str | None = None,
    is_patent: bool | None = None,
) -> dict:
    rows = list(db.scalars(select(Publication).order_by(Publication.publication_year.desc())).all())

    filtered: list[Publication] = []
    for row in rows:
        if year is not None and row.publication_year != year:
            continue
        if is_patent is not None and bool(row.is_patent) != is_patent:
            continue
        ptype = _pub_type(row)
        if pub_type and pub_type.lower() != "all" and ptype.lower() != pub_type.lower():
            continue
        filtered.append(row)

    citations = [int(row.citation_count or 0) for row in filtered]
    iiitd_count = sum(1 for row in filtered if row.is_iiitd_publication)

    per_year: dict[int, Counter[str]] = {}
    type_counts: Counter[str] = Counter()
    venue_counts: dict[str, Counter[str]] = {
        "conference": Counter(),
        "journal": Counter(),
        "publisher": Counter(),
    }
    citation_buckets = Counter({"0": 0, "1-10": 0, "11-50": 0, "51-100": 0, "100+": 0})
    iiitd_split = {"iiitd": iiitd_count, "external": len(filtered) - iiitd_count}

    for row in filtered:
        ptype = _pub_type(row)
        type_counts[ptype] += 1
        yr = row.publication_year or 0
        per_year.setdefault(yr, Counter())[ptype] += 1
        if row.conference:
            venue_counts["conference"][row.conference] += 1
        if row.journal:
            venue_counts["journal"][row.journal] += 1
        if row.publisher:
            venue_counts["publisher"][row.publisher] += 1
        c = int(row.citation_count or 0)
        if c == 0:
            citation_buckets["0"] += 1
        elif c <= 10:
            citation_buckets["1-10"] += 1
        elif c <= 50:
            citation_buckets["11-50"] += 1
        elif c <= 100:
            citation_buckets["51-100"] += 1
        else:
            citation_buckets["100+"] += 1

    top_cited = sorted(
        [
            {
                "title": row.title,
                "authors": row.authors,
                "year": row.publication_year,
                "venue": row.journal or row.conference or row.publisher or "—",
                "citations": int(row.citation_count or 0),
            }
            for row in filtered
        ],
        key=lambda x: x["citations"],
        reverse=True,
    )[:20]

    year_chart = [
        {
            "year": y,
            "journal": per_year[y].get("Journal", 0),
            "conference": per_year[y].get("Conference", 0),
            "book": per_year[y].get("Book", 0),
            "patent": per_year[y].get("Patent", 0),
            "total": sum(per_year[y].values()),
        }
        for y in sorted(per_year.keys())
    ]

    return {
        "kpis": {
            "total_publications": len(filtered),
            "total_patents": type_counts.get("Patent", 0),
            "total_citations": sum(citations),
            "iiitd_publications": iiitd_count,
            "avg_citations": round(sum(citations) / len(citations), 2) if citations else 0,
        },
        "is_empty": len(filtered) == 0,
        "year_chart": year_chart,
        "type_distribution": [{"type": k, "count": v} for k, v in type_counts.items()],
        "top_venues": {
            "conference": [{"name": k, "count": v} for k, v in venue_counts["conference"].most_common(10)],
            "journal": [{"name": k, "count": v} for k, v in venue_counts["journal"].most_common(10)],
            "publisher": [{"name": k, "count": v} for k, v in venue_counts["publisher"].most_common(10)],
        },
        "citation_distribution": [{"bucket": k, "count": v} for k, v in citation_buckets.items()],
        "iiitd_split": iiitd_split,
        "top_cited": top_cited,
    }
