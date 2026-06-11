from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.utils.copo_parser import parse_copo_result_summary
from app.analytics.utils.course_key import course_display_key, normalize_section, resolve_section_label
from app.analytics.utils.semester import semester_label_from_date, semester_sort_key
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_semester_label(row: CopoRunAnalyticsSnapshot) -> str:
    if row.semester_label:
        return row.semester_label
    summary = row.result_summary if isinstance(row.result_summary, dict) else {}
    if summary.get("semester_label"):
        return str(summary["semester_label"])
    return semester_label_from_date(row.run_created_at)


def _resolve_row_section(row: CopoRunAnalyticsSnapshot) -> str | None:
    return resolve_section_label(
        section_label=row.section_label,
        result_summary=row.result_summary if isinstance(row.result_summary, dict) else None,
    )


def get_copo_analytics(
    db: Session,
    *,
    course_title: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    stmt = select(CopoRunAnalyticsSnapshot).order_by(CopoRunAnalyticsSnapshot.run_created_at.asc())
    rows = list(db.scalars(stmt).all())

    from_dt = _parse_dt(from_date)
    to_dt = _parse_dt(to_date)

    runs: list[dict] = []
    for row in rows:
        section = _resolve_row_section(row)
        display_key = course_display_key(row.course_title, section)
        if course_title and course_title.lower() not in display_key.lower():
            continue
        run_at = row.run_created_at
        if from_dt and run_at and run_at < from_dt:
            continue
        if to_dt and run_at and run_at > to_dt:
            continue
        parsed = parse_copo_result_summary(row.result_summary)
        if not parsed:
            continue
        semester = _resolve_semester_label(row)
        section_suffix = f" · Sec {section}" if section else ""
        run_key = f"{semester}{section_suffix} · {row.public_id[:8]}"
        runs.append(
            {
                "public_id": row.public_id,
                "course_title": row.course_title,
                "course_key": display_key,
                "section_label": section,
                "scope_summary": row.scope_summary,
                "semester_label": semester,
                "run_key": run_key,
                "run_created_at": run_at.isoformat() if run_at else None,
                **parsed,
            }
        )

    by_course: dict[str, list[dict]] = {}
    for run in runs:
        by_course.setdefault(run["course_key"], []).append(run)

    for title in by_course:
        by_course[title].sort(
            key=lambda r: (semester_sort_key(r["semester_label"]), r.get("run_created_at") or "")
        )

    courses = []
    for title, course_runs in sorted(by_course.items()):
        courses.append(
            {
                "course_title": course_runs[0]["course_title"],
                "course_key": title,
                "section_label": course_runs[0].get("section_label"),
                "runs": course_runs,
                "latest_run": course_runs[-1] if course_runs else None,
            }
        )

    latest_co_vals: list[float] = []
    latest_po_vals: list[float] = []
    for course_runs in by_course.values():
        if not course_runs:
            continue
        latest = course_runs[-1]
        latest_co_vals.extend(latest["co_attainment"].values())
        latest_po_vals.extend(latest["po_attainment"].values())

    def _avg(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "kpis": {
            "total_courses": len(by_course),
            "total_runs": len(runs),
            "avg_co_attainment": _avg(latest_co_vals),
            "avg_po_attainment": _avg(latest_po_vals),
        },
        "course_titles": sorted(by_course.keys()),
        "courses": courses,
    }


def get_copo_run_analytics(db: Session, public_id: str) -> dict | None:
    """Parsed snapshot for a single evaluation run (used by Generator dashboard charts)."""
    row = db.scalar(
        select(CopoRunAnalyticsSnapshot).where(CopoRunAnalyticsSnapshot.public_id == public_id)
    )
    if not row:
        return None
    parsed = parse_copo_result_summary(row.result_summary)
    if not parsed:
        return None
    section = _resolve_row_section(row)
    return {
        "public_id": row.public_id,
        "course_title": row.course_title,
        "course_key": course_display_key(row.course_title, section),
        "section_label": section,
        "semester_label": _resolve_semester_label(row),
        **parsed,
    }
