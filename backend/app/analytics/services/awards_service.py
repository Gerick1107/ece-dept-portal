from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.utils.award_categories import classify_award
from app.awards.models.entities import FacultyAward


def get_awards_analytics(
    db: Session,
    *,
    faculty_names: list[str] | None = None,
    years: list[str] | None = None,
    exact_years: list[int] | None = None,
    categories: list[str] | None = None,
) -> dict:
    rows = list(db.scalars(select(FacultyAward).order_by(FacultyAward.year, FacultyAward.faculty_name)).all())

    faculty_filter = {n.strip() for n in (faculty_names or []) if n.strip()}
    year_filter = {y.strip() for y in (years or []) if y.strip()}
    exact_year_filter = {int(y) for y in (exact_years or []) if y is not None}
    category_filter = {c.strip() for c in (categories or []) if c.strip()}

    enriched: list[dict] = []
    for row in rows:
        category = classify_award(row.award)
        if faculty_filter and row.faculty_name not in faculty_filter:
            continue
        if year_filter and row.year not in year_filter:
            continue
        if exact_year_filter and (row.exact_year is None or row.exact_year not in exact_year_filter):
            continue
        if category_filter and category not in category_filter:
            continue
        enriched.append(
            {
                "id": row.id,
                "faculty_name": row.faculty_name,
                "year": row.year,
                "exact_year": row.exact_year,
                "awarded_by": row.awarded_by,
                "award": row.award,
                "category": category,
            }
        )

    faculty_counts: Counter[str] = Counter()
    year_counts: Counter[int] = Counter()
    category_counts: Counter[str] = Counter()
    faculty_category: dict[str, Counter[str]] = defaultdict(Counter)
    heatmap: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for item in enriched:
        faculty_counts[item["faculty_name"]] += 1
        if item["exact_year"] is not None:
            year_counts[item["exact_year"]] += 1
        category_counts[item["category"]] += 1
        faculty_category[item["faculty_name"]][item["category"]] += 1
        if item["exact_year"] is not None:
            heatmap[item["faculty_name"]][str(item["exact_year"])] += 1

    top_faculty = faculty_counts.most_common(1)[0] if faculty_counts else None
    top_year = year_counts.most_common(1)[0] if year_counts else None
    top_category = category_counts.most_common(1)[0] if category_counts else None

    faculty_chart = []
    for name, count in faculty_counts.most_common():
        by_cat = faculty_category[name]
        faculty_chart.append(
            {
                "faculty_name": name,
                "total": count,
                "by_category": dict(by_cat),
            }
        )

    years_sorted = sorted(year_counts.keys())
    year_chart = [
        {
            "year": str(y),
            "exact_year": y,
            "total": year_counts[y],
            "by_category": {
                cat: sum(1 for e in enriched if e["exact_year"] == y and e["category"] == cat)
                for cat in category_counts
            },
        }
        for y in years_sorted
    ]

    cumulative = 0
    for entry in year_chart:
        cumulative += entry["total"]
        entry["cumulative"] = cumulative

    return {
        "kpis": {
            "total_awards": len(enriched),
            "faculty_with_awards": len(faculty_counts),
            "top_faculty": {"name": top_faculty[0], "count": top_faculty[1]} if top_faculty else None,
            "top_year": {"year": top_year[0], "count": top_year[1]} if top_year else None,
            "top_category": {"category": top_category[0], "count": top_category[1]} if top_category else None,
        },
        "items": enriched,
        "faculty_chart": faculty_chart,
        "year_chart": year_chart,
        "category_distribution": [{"category": k, "count": v} for k, v in category_counts.most_common()],
        "heatmap": {
            "faculty_names": sorted(heatmap.keys()),
            "years": [str(y) for y in years_sorted],
            "cells": [
                {"faculty_name": f, "year": str(y), "count": heatmap[f][str(y)]}
                for f in sorted(heatmap.keys())
                for y in years_sorted
            ],
        },
        "filter_options": {
            "faculty_names": sorted(faculty_counts.keys()),
            "years": [str(y) for y in years_sorted],
            "exact_years": years_sorted,
            "categories": sorted(category_counts.keys()),
        },
    }
