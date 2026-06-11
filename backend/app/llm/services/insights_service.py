from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.services.copo_service import _resolve_row_section, _resolve_semester_label
from app.analytics.utils.copo_parser import parse_copo_result_summary
from app.analytics.utils.course_key import course_display_key, normalize_section
from app.analytics.utils.semester import semester_sort_key
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot
from app.database.models.user import User
from app.llm.models.entities import LlmInsightsCache
from app.llm.services.assessment_summary import format_assessment_summary_block, summarize_assessment_ids
from app.llm.services.groq_service import LlmError, generate_llm_text
from app.llm.services.mapping_descriptions import extract_co_descriptions_for_course, extract_po_descriptions

logger = logging.getLogger(__name__)

_PO_PSO_ORDER = [f"PO{i}" for i in range(1, 13)] + ["PSO1", "PSO2", "PSO3"]
PROMPT_VERSION = 3


def _parse_run(row: CopoRunAnalyticsSnapshot) -> dict | None:
    parsed = parse_copo_result_summary(row.result_summary)
    if not parsed:
        return None
    intermediate = (row.result_summary or {}).get("intermediate") or {}
    assessment_ids = intermediate.get("assessment_ids") or []
    section = _resolve_row_section(row)
    run_at = row.run_created_at
    return {
        "public_id": row.public_id,
        "course_title": row.course_title,
        "course_key": course_display_key(row.course_title, section),
        "section_label": section,
        "semester_label": _resolve_semester_label(row),
        "run_created_at": run_at.isoformat() if run_at else None,
        "user_id": row.user_id,
        "assessment_ids": assessment_ids if isinstance(assessment_ids, list) else [],
        **parsed,
    }


def _snapshot_query(db: Session, _user: User):
    return list(
        db.scalars(
            select(CopoRunAnalyticsSnapshot).order_by(CopoRunAnalyticsSnapshot.run_created_at.asc())
        ).all()
    )


def _section_matches(run_section: str | None, requested: str | None) -> bool:
    return normalize_section(run_section) == normalize_section(requested)


def _find_run(
    runs: list[dict],
    *,
    semester_label: str,
    section_label: str | None = None,
) -> dict | None:
    matches = [
        r
        for r in runs
        if r["semester_label"] == semester_label and _section_matches(r.get("section_label"), section_label)
    ]
    if not matches:
        return None
    return max(matches, key=lambda r: r.get("run_created_at") or "")


def _latest_per_semester_section(runs: list[dict]) -> dict[tuple[str, str | None], dict]:
    grouped: dict[tuple[str, str | None], list[dict]] = defaultdict(list)
    for run in runs:
        grouped[(run["semester_label"], normalize_section(run.get("section_label")))].append(run)
    latest: dict[tuple[str, str | None], dict] = {}
    for key, sem_runs in grouped.items():
        latest[key] = max(sem_runs, key=lambda r: r.get("run_created_at") or "")
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


def _filter_runs_for_course(
    all_runs: list[dict],
    *,
    course_title: str,
    section_label: str | None = None,
) -> list[dict]:
    return [
        r
        for r in all_runs
        if r["course_title"] == course_title and _section_matches(r.get("section_label"), section_label)
    ]


def list_insight_courses(db: Session, user: User) -> list[dict]:
    all_parsed = [parsed for row in _snapshot_query(db, user) if (parsed := _parse_run(row))]
    by_course: dict[tuple[str, str | None], list[dict]] = defaultdict(list)
    for run in all_parsed:
        by_course[(run["course_title"], normalize_section(run.get("section_label")))].append(run)

    courses: list[dict] = []
    for (title, section), runs in by_course.items():
        per_key = _latest_per_semester_section(runs)
        sems = sorted({k[0] for k in per_key}, key=semester_sort_key)
        if not sems:
            continue
        latest_sem = sems[-1]
        latest = per_key[(latest_sem, section)]
        courses.append(
            {
                "course_title": title,
                "course_key": course_display_key(title, section),
                "section_label": section,
                "semester_count": len(sems),
                "semesters": sems,
                "latest_semester": latest["semester_label"],
                "latest_run_id": latest["public_id"],
            }
        )
    return sorted(courses, key=lambda c: c["course_key"])


def get_course_options(db: Session, user: User, course_title: str, section_label: str | None = None) -> dict:
    all_parsed = [parsed for row in _snapshot_query(db, user) if (parsed := _parse_run(row))]
    runs = _filter_runs_for_course(
        all_parsed,
        course_title=course_title,
        section_label=section_label,
    )
    if not runs:
        raise ValueError("No attainment snapshots found for this course")
    per_key = _latest_per_semester_section(runs)
    semesters = sorted({k[0] for k in per_key}, key=semester_sort_key)
    return {
        "course_title": course_title,
        "section_label": normalize_section(section_label),
        "semesters": semesters,
        "sections": sorted(
            {
                normalize_section(r.get("section_label"))
                for r in all_parsed
                if r["course_title"] == course_title and normalize_section(r.get("section_label"))
            }
        ),
    }


def get_course_comparison(
    db: Session,
    user: User,
    course_title: str,
    *,
    current_semester: str | None = None,
    current_section: str | None = None,
    previous_semester: str | None = None,
    previous_section: str | None = None,
) -> dict:
    all_parsed = [parsed for row in _snapshot_query(db, user) if (parsed := _parse_run(row))]
    section = normalize_section(current_section)
    runs = _filter_runs_for_course(all_parsed, course_title=course_title, section_label=section)
    if not runs:
        raise ValueError("No attainment snapshots found for this course")

    per_key = _latest_per_semester_section(runs)
    semesters = sorted({k[0] for k in per_key}, key=semester_sort_key)

    if current_semester:
        current = _find_run(runs, semester_label=current_semester, section_label=section)
        if not current:
            raise ValueError("No run found for the selected current semester and section")
    else:
        latest_sem = semesters[-1]
        current = per_key[(latest_sem, section)]

    previous = None
    if previous_semester:
        if previous_section is None:
            prev_section = section
        elif not str(previous_section).strip():
            prev_section = None
        else:
            prev_section = normalize_section(previous_section)
        previous = _find_run(
            _filter_runs_for_course(all_parsed, course_title=course_title, section_label=prev_section),
            semester_label=previous_semester,
            section_label=prev_section,
        )
    elif len(semesters) >= 2:
        prev_sem = semesters[semesters.index(current["semester_label"]) - 1]
        previous = per_key.get((prev_sem, section))

    co_descriptions, co_desc_available, _co_src = extract_co_descriptions_for_course(course_title)
    assessment_summary = summarize_assessment_ids(current.get("assessment_ids") or [])

    return {
        "course_title": course_title,
        "course_key": course_display_key(course_title, section),
        "section_label": section,
        "has_previous": previous is not None,
        "current_semester": current["semester_label"],
        "previous_semester": previous["semester_label"] if previous else None,
        "current_section": section,
        "previous_section": normalize_section(previous.get("section_label")) if previous else None,
        "current_run_id": current["public_id"],
        "previous_run_id": previous["public_id"] if previous else None,
        "co_comparison": _comparison_rows(previous, current, "co_attainment"),
        "po_comparison": _comparison_rows(previous, current, "po_attainment", sort_po=True),
        "insufficient_history": previous is None,
        "co_descriptions_available": co_desc_available and bool(co_descriptions),
        "assessment_summary": assessment_summary,
        "available_semesters": semesters,
        "available_sections": sorted(
            {
                normalize_section(r.get("section_label"))
                for r in all_parsed
                if r["course_title"] == course_title and normalize_section(r.get("section_label"))
            }
        ),
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


def _section_label_text(section: str | None) -> str:
    return f"Section {section}" if section else "No section"


def build_llm_prompt(
    *,
    course_title: str,
    faculty_name: str,
    comparison: dict,
    co_descriptions: dict[str, str],
    co_descriptions_available: bool,
    po_descriptions: dict[str, str],
    assessment_summary: list[dict],
) -> str:
    if co_descriptions_available and co_descriptions:
        co_desc_block = "\n".join(co_descriptions[k] for k in sorted(co_descriptions))
    else:
        co_desc_block = (
            "CO identifiers only (no descriptions configured): "
            + ", ".join(row["metric"] for row in comparison["co_comparison"] if row.get("current") is not None)
        )

    po_desc_block = "\n".join(
        po_descriptions.get(k, k) for k in _PO_PSO_ORDER if k in po_descriptions
    ) or "PO descriptions: Standard PO1-PO12 as per NBA guidelines."
    pso_lines = [po_descriptions[k] for k in ("PSO1", "PSO2", "PSO3") if k in po_descriptions]
    pso_desc_block = "\n".join(pso_lines) if pso_lines else ""

    co_table = _format_comparison_lines(comparison["co_comparison"])
    po_table = _format_comparison_lines(comparison["po_comparison"])
    assessment_block = format_assessment_summary_block(assessment_summary)

    current_section_txt = _section_label_text(comparison.get("current_section"))
    previous_section_txt = _section_label_text(comparison.get("previous_section"))

    if comparison["has_previous"]:
        comparison_intro = (
            f"Current: {comparison['current_semester']} ({current_section_txt})\n"
            f"Previous: {comparison['previous_semester']} ({previous_section_txt})\n"
        )
        task_block = """Based on the data above:
1. For each CO that has DECLINED compared to the previous semester, identify likely academic/pedagogical reasons specific to that CO's topic, and suggest 3-4 concrete teaching or learning strategies the faculty can adopt next semester to improve attainment for that specific CO.
2. For each CO that has IMPROVED, briefly note what may be working well and how to sustain it.
3. Based on PO/PSO attainment trends, suggest any overall course delivery improvements.
4. Keep suggestions specific to the CO topics — do not give generic advice.
5. Format your response with a clear heading for each CO, followed by a final Overall Recommendations section.

Based on the PO/PSO attainment data above:
6. Identify which Programme Outcomes have declined and suggest course-level interventions that could improve student performance on those POs. Be specific about which teaching activities, assessments, or learning experiences map to each declining PO.
7. If PSO data is available, analyse PSO trends and suggest programme-specific improvements.
8. Note any POs that are consistently strong across both semesters.

Based on the assessment structure above and the CO/PO attainment trends:
9. Evaluate whether the current assessment structure is appropriate for the number of COs being assessed.
10. Suggest whether any component types should be added, removed, or reweighted (connect suggestions to CO/PO performance).
11. For components with a high number of questions, suggest whether reducing question count might improve assessment quality without reducing coverage.
12. For components with very few questions, suggest whether increasing question count could provide more reliable attainment measurement.
13. If a component type is entirely missing that could benefit learning outcomes, suggest adding it.
14. Keep all suggestions grounded in the attainment data shown above."""
    else:
        co_table_single = "\n".join(
            f"{row['metric']}: current={row['current']:.1f}%"
            for row in comparison["co_comparison"]
            if row.get("current") is not None
        ) or "No CO data."
        comparison_intro = (
            f"Current: {comparison['current_semester']} ({current_section_txt})\n"
        )
        co_table = co_table_single
        po_table = _format_comparison_lines(comparison["po_comparison"])
        return f"""You are an academic course improvement advisor for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
{comparison_intro}
Only one semester of data is available for this course/section. Current CO attainments:
{co_table_single}

Course Outcome (CO) descriptions for this course:
{co_desc_block}

Programme Outcome (PO) descriptions:
{po_desc_block}

PO/PSO Attainment:
{po_table}
{f"PSO descriptions:{chr(10)}{pso_desc_block}{chr(10)}" if pso_desc_block else ""}
Assessment Structure for This Course (latest semester):
{assessment_block}

Note: CO-to-assessment mappings are not available; analyse assessment structure from a pedagogical and workload perspective.

Based on typical attainment targets of 60%, suggest teaching and learning strategies to improve attainment for any COs currently below target. Format with clear headings per CO and an Overall Recommendations section."""

    assessment_section = ""
    if assessment_summary:
        assessment_section = f"""
Assessment Structure for This Course (latest semester):
{assessment_block}

Note: CO-to-assessment mappings are not available; analyse assessment structure from a pedagogical and workload perspective.
"""

    return f"""You are an academic course improvement advisor for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
{comparison_intro}
Course Outcome (CO) descriptions for this course:
{co_desc_block}

Programme Outcome (PO) descriptions:
{po_desc_block}
{f"Programme Specific Outcome (PSO) descriptions:{chr(10)}{pso_desc_block}{chr(10)}" if pso_desc_block else ""}
CO Attainment Comparison:
{co_table}

PO/PSO Attainment Comparison:
{po_table}
{assessment_section}
{task_block}"""


def _run_identifier(
    course_title: str,
    semester: str,
    section_label: str | None = None,
    *,
    previous_semester: str | None = None,
    previous_section: str | None = None,
) -> str:
    section = normalize_section(section_label) or "none"
    if previous_semester:
        prev_section = normalize_section(previous_section) or "none"
        return (
            f"{course_title}_{semester}_{section}_vs_{previous_semester}_{prev_section}"
        ).replace(" ", "_")
    return f"{course_title}_{semester}_{section}".replace(" ", "_")


def _get_cache(db: Session, run_identifier: str) -> LlmInsightsCache | None:
    return db.scalar(select(LlmInsightsCache).where(LlmInsightsCache.run_id == run_identifier))


def get_cached_insights(
    db: Session,
    user: User,
    course_title: str,
    *,
    current_semester: str | None = None,
    current_section: str | None = None,
    previous_semester: str | None = None,
    previous_section: str | None = None,
) -> dict:
    comparison = get_course_comparison(
        db,
        user,
        course_title,
        current_semester=current_semester,
        current_section=current_section,
        previous_semester=previous_semester,
        previous_section=previous_section,
    )
    run_identifier = _run_identifier(
        course_title,
        comparison["current_semester"],
        comparison.get("current_section"),
        previous_semester=comparison.get("previous_semester"),
        previous_section=comparison.get("previous_section"),
    )
    cached = _get_cache(db, run_identifier)
    valid_cache = cached if cached and cached.prompt_version == PROMPT_VERSION else None
    return {
        "course_title": course_title,
        "run_id": comparison["current_run_id"],
        "comparison": comparison,
        "insights": valid_cache.llm_response if valid_cache else None,
        "generated_at": valid_cache.generated_at.isoformat() if valid_cache and valid_cache.generated_at else None,
        "cached": valid_cache is not None,
    }


async def generate_insights(
    db: Session,
    user: User,
    *,
    course_title: str,
    run_id: str | None = None,
    regenerate: bool = False,
    current_semester: str | None = None,
    current_section: str | None = None,
    previous_semester: str | None = None,
    previous_section: str | None = None,
) -> dict:
    comparison = get_course_comparison(
        db,
        user,
        course_title,
        current_semester=current_semester,
        current_section=current_section,
        previous_semester=previous_semester,
        previous_section=previous_section,
    )
    if run_id and comparison["current_run_id"] != run_id:
        raise ValueError("run_id does not match the selected semester/section run for this course")

    run_identifier = _run_identifier(
        course_title,
        comparison["current_semester"],
        comparison.get("current_section"),
        previous_semester=comparison.get("previous_semester"),
        previous_section=comparison.get("previous_section"),
    )
    snapshot_run_id = comparison["current_run_id"]

    if not regenerate:
        cached = _get_cache(db, run_identifier)
        if cached and cached.prompt_version == PROMPT_VERSION:
            return {
                "course_title": course_title,
                "run_id": snapshot_run_id,
                "comparison": comparison,
                "insights": cached.llm_response,
                "generated_at": cached.generated_at.isoformat() if cached.generated_at else None,
                "cached": True,
            }

    co_descriptions, co_desc_available, co_source = extract_co_descriptions_for_course(course_title)
    po_descriptions, po_source = extract_po_descriptions()
    assessment_summary = comparison.get("assessment_summary") or []
    logger.info(
        "LLM prompt sources — CO: %s | PO: %s | assessments: %d types",
        co_source or "NOT FOUND — omitted from prompt",
        po_source,
        len(assessment_summary),
    )
    prompt = build_llm_prompt(
        course_title=course_title,
        faculty_name=user.full_name,
        comparison=comparison,
        co_descriptions=co_descriptions,
        co_descriptions_available=co_desc_available,
        po_descriptions=po_descriptions,
        assessment_summary=assessment_summary,
    )

    try:
        llm_response = await generate_llm_text(prompt)
    except LlmError:
        raise

    existing = _get_cache(db, run_identifier)
    if existing:
        existing.prompt_used = prompt
        existing.llm_response = llm_response
        existing.course_id = course_title
        existing.run_id = run_identifier
        existing.generated_at = datetime.utcnow()
        existing.prompt_version = PROMPT_VERSION
    else:
        db.add(
            LlmInsightsCache(
                run_id=run_identifier,
                course_id=course_title,
                prompt_used=prompt,
                llm_response=llm_response,
                prompt_version=PROMPT_VERSION,
            )
        )
    db.commit()
    cached = _get_cache(db, run_identifier)
    return {
        "course_title": course_title,
        "run_id": snapshot_run_id,
        "comparison": comparison,
        "insights": llm_response,
        "generated_at": cached.generated_at.isoformat() if cached and cached.generated_at else None,
        "cached": False,
    }
