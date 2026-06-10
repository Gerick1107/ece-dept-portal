from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.services.copo_service import _resolve_semester_label
from app.analytics.utils.copo_parser import parse_copo_result_summary
from app.analytics.utils.semester import semester_sort_key
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot
from app.database.models.user import User, UserRole
from app.llm.models.entities import LlmInsightsCache
from app.llm.services.groq_service import LlmError, generate_llm_text
from app.llm.services.mapping_descriptions import extract_co_descriptions_for_course, extract_po_descriptions

_PO_PSO_ORDER = [f"PO{i}" for i in range(1, 13)] + ["PSO1", "PSO2", "PSO3"]
_ATTAINMENT_TARGET = 60.0


def _parse_run(row: CopoRunAnalyticsSnapshot) -> dict | None:
    parsed = parse_copo_result_summary(row.result_summary)
    if not parsed:
        return None
    run_at = row.run_created_at
    return {
        "public_id": row.public_id,
        "course_title": row.course_title,
        "semester_label": _resolve_semester_label(row),
        "run_created_at": run_at.isoformat() if run_at else None,
        "user_id": row.user_id,
        **parsed,
    }


def _snapshot_query(db: Session, user: User):
    stmt = select(CopoRunAnalyticsSnapshot).order_by(CopoRunAnalyticsSnapshot.run_created_at.asc())
    if user.role not in (UserRole.admin, UserRole.hod):
        stmt = stmt.where(CopoRunAnalyticsSnapshot.user_id == user.id)
    return list(db.scalars(stmt).all())


def _latest_per_semester(runs: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        grouped[run["semester_label"]].append(run)
    latest: dict[str, dict] = {}
    for semester, sem_runs in grouped.items():
        latest[semester] = max(sem_runs, key=lambda r: r.get("run_created_at") or "")
    return latest


def _metric_keys(prev: dict | None, curr: dict, field: str) -> list[str]:
    keys: set[str] = set()
    if prev:
        keys.update((prev.get(field) or {}).keys())
    keys.update((curr.get(field) or {}).keys())
    if field == "co_attainment":
        keys.update(curr.get("unique_cos") or [])
    return sorted(keys, key=lambda k: (0, int(k.replace("CO", ""))) if k.upper().startswith("CO") else (1, k))


def _comparison_rows(
    prev: dict | None,
    curr: dict,
    field: str,
    *,
    sort_po: bool = False,
) -> list[dict]:
    prev_map = (prev or {}).get(field) or {}
    curr_map = curr.get(field) or {}
    keys = _metric_keys(prev, curr, field)
    if sort_po:
        keys = [k for k in _PO_PSO_ORDER if k in keys] + [k for k in keys if k not in _PO_PSO_ORDER]
    rows: list[dict] = []
    for key in keys:
        previous_val = prev_map.get(key)
        current_val = curr_map.get(key)
        delta = None
        trend = "neutral"
        if previous_val is not None and current_val is not None:
            delta = round(current_val - previous_val, 2)
            if delta > 0:
                trend = "up"
            elif delta < 0:
                trend = "down"
        rows.append(
            {
                "metric": key,
                "previous": previous_val,
                "current": current_val,
                "delta": delta,
                "trend": trend,
            }
        )
    return rows


def list_insight_courses(db: Session, user: User) -> list[dict]:
    by_course: dict[str, list[dict]] = defaultdict(list)
    for row in _snapshot_query(db, user):
        parsed = _parse_run(row)
        if parsed:
            by_course[parsed["course_title"]].append(parsed)

    courses: list[dict] = []
    for title, runs in by_course.items():
        per_sem = _latest_per_semester(runs)
        sems = sorted(per_sem.keys(), key=semester_sort_key)
        if not sems:
            continue
        latest = per_sem[sems[-1]]
        courses.append(
            {
                "course_title": title,
                "semester_count": len(sems),
                "latest_semester": latest["semester_label"],
                "latest_run_id": latest["public_id"],
            }
        )
    return sorted(courses, key=lambda c: c["course_title"])


def get_course_comparison(db: Session, user: User, course_title: str) -> dict:
    rows = [r for r in _snapshot_query(db, user) if r.course_title == course_title]
    runs = [parsed for r in rows if (parsed := _parse_run(r))]
    if not runs:
        raise ValueError("No attainment snapshots found for this course")

    per_sem = _latest_per_semester(runs)
    semesters = sorted(per_sem.keys(), key=semester_sort_key)
    current = per_sem[semesters[-1]]
    previous = per_sem[semesters[-2]] if len(semesters) >= 2 else None

    return {
        "course_title": course_title,
        "has_previous": previous is not None,
        "current_semester": current["semester_label"],
        "previous_semester": previous["semester_label"] if previous else None,
        "current_run_id": current["public_id"],
        "co_comparison": _comparison_rows(previous, current, "co_attainment"),
        "po_comparison": _comparison_rows(previous, current, "po_attainment", sort_po=True),
        "insufficient_history": len(semesters) < 2,
    }


def _format_comparison_lines(rows: list[dict]) -> str:
    lines: list[str] = []
    for row in rows:
        prev = row.get("previous")
        curr = row.get("current")
        delta = row.get("delta")
        if curr is None:
            continue
        status = "UNCHANGED"
        if delta is not None:
            if delta > 0:
                status = "IMPROVED"
            elif delta < 0:
                status = "DECLINED"
        prev_txt = f"{prev:.1f}%" if prev is not None else "N/A"
        delta_txt = f"{delta:+.1f}%" if delta is not None else "N/A"
        lines.append(
            f"{row['metric']}: previous={prev_txt}, current={curr:.1f}%, delta={delta_txt} [{status}]"
        )
    return "\n".join(lines) or "No attainment data available."


def build_llm_prompt(
    *,
    course_title: str,
    faculty_name: str,
    comparison: dict,
    co_descriptions: dict[str, str],
    po_descriptions: dict[str, str],
) -> str:
    co_desc_block = "\n".join(co_descriptions.values()) if co_descriptions else (
        "CO descriptions: Not available for this course."
    )
    po_desc_block = "\n".join(
        po_descriptions.get(k, k) for k in _PO_PSO_ORDER if k in po_descriptions
    ) if po_descriptions else "PO descriptions: Standard PO1-PO12 as per NBA guidelines."

    co_table = _format_comparison_lines(comparison["co_comparison"])
    po_table = _format_comparison_lines(comparison["po_comparison"])

    if comparison["has_previous"]:
        comparison_intro = (
            f"Current semester: {comparison['current_semester']}\n"
            f"Previous semester: {comparison['previous_semester']}\n"
        )
        task_block = """Based on the data above:
1. For each CO that has DECLINED compared to the previous semester, identify likely academic/pedagogical reasons specific to that CO's topic, and suggest 3-4 concrete teaching or learning strategies the faculty can adopt next semester to improve attainment for that specific CO.
2. For each CO that has IMPROVED, briefly note what may be working well and how to sustain it.
3. Based on PO/PSO attainment trends, suggest any overall course delivery improvements.
4. Keep suggestions specific to the CO topics — do not give generic advice.
5. Format your response with a clear heading for each CO, followed by a final Overall Recommendations section."""
    else:
        co_table_single = "\n".join(
            f"{row['metric']}: current={row['current']:.1f}%"
            for row in comparison["co_comparison"]
            if row.get("current") is not None
        ) or "No CO data."
        comparison_intro = f"Current semester: {comparison['current_semester']}\n"
        co_table = co_table_single
        po_table = _format_comparison_lines(comparison["po_comparison"])
        return f"""You are an academic course improvement advisor for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
{comparison_intro}
Only one semester of data is available for this course. Current CO attainments:
{co_table_single}

Course Outcome (CO) descriptions for this course:
{co_desc_block}

Programme Outcome (PO) descriptions:
{po_desc_block}

PO/PSO Attainment:
{po_table}

Based on typical attainment targets of 60%, suggest teaching and learning strategies to improve attainment for any COs currently below target. Format with clear headings per CO and an Overall Recommendations section."""

    return f"""You are an academic course improvement advisor for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
{comparison_intro}
Course Outcome (CO) descriptions for this course:
{co_desc_block}

Programme Outcome (PO) descriptions:
{po_desc_block}

CO Attainment Comparison:
{co_table}

PO/PSO Attainment Comparison:
{po_table}

{task_block}"""


def _run_identifier(course_title: str, semester: str) -> str:
    return f"{course_title}_{semester}".replace(" ", "_")


def _get_cache(db: Session, course_title: str, run_identifier: str) -> LlmInsightsCache | None:
    return db.scalar(
        select(LlmInsightsCache).where(
            LlmInsightsCache.course_id == course_title,
            LlmInsightsCache.run_id == run_identifier,
        )
    )


def get_cached_insights(db: Session, user: User, course_title: str) -> dict:
    """Return cached LLM text only — never calls the LLM API."""
    comparison = get_course_comparison(db, user, course_title)
    run_identifier = _run_identifier(course_title, comparison["current_semester"])
    cached = _get_cache(db, course_title, run_identifier)
    return {
        "course_title": course_title,
        "run_id": comparison["current_run_id"],
        "comparison": comparison,
        "insights": cached.llm_response if cached else None,
        "generated_at": cached.generated_at.isoformat() if cached and cached.generated_at else None,
        "cached": cached is not None,
    }


async def generate_insights(
    db: Session,
    user: User,
    *,
    course_title: str,
    run_id: str | None = None,
    regenerate: bool = False,
) -> dict:
    comparison = get_course_comparison(db, user, course_title)
    if run_id and comparison["current_run_id"] != run_id:
        raise ValueError("run_id does not match the latest semester run for this course")

    run_identifier = _run_identifier(course_title, comparison["current_semester"])
    snapshot_run_id = comparison["current_run_id"]

    if not regenerate:
        cached = _get_cache(db, course_title, run_identifier)
        if cached:
            return {
                "course_title": course_title,
                "run_id": snapshot_run_id,
                "comparison": comparison,
                "insights": cached.llm_response,
                "generated_at": cached.generated_at.isoformat() if cached.generated_at else None,
                "cached": True,
            }

    co_descriptions = extract_co_descriptions_for_course(course_title)
    po_descriptions = extract_po_descriptions()
    prompt = build_llm_prompt(
        course_title=course_title,
        faculty_name=user.full_name,
        comparison=comparison,
        co_descriptions=co_descriptions,
        po_descriptions=po_descriptions,
    )

    try:
        llm_response = await generate_llm_text(prompt)
    except LlmError:
        raise

    existing = _get_cache(db, course_title, run_identifier)
    if existing:
        existing.prompt_used = prompt
        existing.llm_response = llm_response
        existing.course_id = course_title
        existing.run_id = run_identifier
        existing.generated_at = datetime.utcnow()
    else:
        db.add(
            LlmInsightsCache(
                run_id=run_identifier,
                course_id=course_title,
                prompt_used=prompt,
                llm_response=llm_response,
            )
        )
    db.commit()
    cached = _get_cache(db, course_title, run_identifier)
    return {
        "course_title": course_title,
        "run_id": snapshot_run_id,
        "comparison": comparison,
        "insights": llm_response,
        "generated_at": cached.generated_at.isoformat() if cached and cached.generated_at else None,
        "cached": False,
    }
