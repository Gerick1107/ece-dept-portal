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
from app.copo.services.assessment_mapping_service import (
    build_assessment_co_payload_from_intermediate,
    load_assessment_co_payload,
)
from app.database.models.copo import CopoEvaluationRun
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot
from app.database.models.user import User
from app.llm.models.entities import LlmInsightsCache
from app.llm.services.assessment_summary import format_assessment_summary_block, summarize_assessment_ids
from app.llm.services.groq_service import LlmError, generate_llm_text
from app.llm.services.mapping_descriptions import extract_co_descriptions_for_course, extract_po_descriptions

logger = logging.getLogger(__name__)

_PO_PSO_ORDER = [f"PO{i}" for i in range(1, 13)] + ["PSO1", "PSO2", "PSO3"]
PROMPT_VERSION = 7


def _evaluation_run_id(db: Session, public_id: str | None) -> int | None:
    if not public_id:
        return None
    run = db.scalar(select(CopoEvaluationRun).where(CopoEvaluationRun.public_id == public_id))
    return run.id if run else None


def _format_assessment_co_block(assessments: list[dict]) -> str:
    if not assessments:
        return "No assessment-to-CO mapping data is available for this run."
    lines: list[str] = []
    for item in assessments:
        co_parts = []
        for co in item.get("cos") or []:
            attainment = co.get("attainment")
            attainment_txt = f"{attainment:.1f}%" if attainment is not None else "N/A"
            q_count = co.get("question_count")
            q_txt = f", {q_count} question(s)" if q_count is not None else ""
            co_parts.append(f"{co.get('co_label')} (attainment {attainment_txt}{q_txt})")
        co_summary = "; ".join(co_parts) if co_parts else "no CO mappings recorded"
        lines.append(
            f"- Assessment '{item.get('name')}' "
            f"[{item.get('type') or 'type unknown'}] — {co_summary}"
        )
    return "\n".join(lines)


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
        "intermediate": intermediate,
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


def _resolve_assessments_for_run(
    db: Session,
    run: dict,
    *,
    course_title: str,
    semester_label: str,
    section_label: str | None,
    co_attainment: dict[str, float],
) -> list[dict]:
    evaluation_run_id = _evaluation_run_id(db, run.get("public_id"))
    payload = load_assessment_co_payload(
        db,
        evaluation_run_id=evaluation_run_id,
        course_title=course_title,
        semester_label=semester_label,
        section_label=section_label,
        co_attainment=co_attainment,
    )
    if payload:
        return payload
    return build_assessment_co_payload_from_intermediate(
        run.get("intermediate") or {},
        course_title=course_title,
        semester_label=semester_label,
        section_label=section_label,
        co_attainment=co_attainment,
    )


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
    current_co_map = (current.get("co_attainment") or {})
    current_assessments = _resolve_assessments_for_run(
        db,
        current,
        course_title=course_title,
        semester_label=current["semester_label"],
        section_label=section,
        co_attainment=current_co_map,
    )
    previous_assessments: list[dict] = []
    previous_assessment_summary: list[dict] = []
    if previous:
        previous_assessment_summary = summarize_assessment_ids(previous.get("assessment_ids") or [])
        previous_assessments = _resolve_assessments_for_run(
            db,
            previous,
            course_title=course_title,
            semester_label=previous["semester_label"],
            section_label=normalize_section(previous.get("section_label")),
            co_attainment=(previous.get("co_attainment") or {}),
        )

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
        "previous_assessment_summary": previous_assessment_summary,
        "current_assessments": current_assessments,
        "previous_assessments": previous_assessments,
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
    previous_assessment_summary: list[dict] | None = None,
    current_assessments: list[dict] | None = None,
    previous_assessments: list[dict] | None = None,
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
    previous_summary_block = format_assessment_summary_block(previous_assessment_summary or [])
    current_assessment_block = _format_assessment_co_block(current_assessments or [])
    previous_assessment_block = _format_assessment_co_block(previous_assessments or [])

    current_section_txt = _section_label_text(comparison.get("current_section"))
    previous_section_txt = _section_label_text(comparison.get("previous_section"))

    constraints = """
Role and audience:
- The reader is an experienced professor. Do not explain basic CO-attainment concepts.
- Write as a data analyst speaking to a peer.

Strict tone and style rules:
- Use analytical, non-judgmental language.
- Do not use words such as "ineffective", "insufficient", "poor", or any fault-oriented phrasing.
- Ground every claim in explicit numbers from the provided data.
- Do not provide identical recommendations for different COs unless you first explain why their structures are actually the same.
- Do not include generic closing remarks. Every sentence must add specific, data-backed value.
- Do not advise on teaching methods, pedagogy, pace, or time allocation.

Hard forbidden outputs:
- Do not output "consider increasing question coverage" as a standalone recommendation.
- Do not produce any sentence that could be copied unchanged across all COs.
- Do not make claims that cannot be traced to the provided numbers.
- Do not add a generic concluding paragraph that restates earlier points.

Assessment naming rules:
- Use assessment names exactly as provided (for example, Quiz 1, Quiz 2, Midsem, Endsem, Lab, Tutorial).
- Do not invent ordinal names such as "Assessment 1", "Assessment 2".
- If only column-derived names are available, quote those exact names and do not renumber.
"""

    if comparison["has_previous"]:
        comparison_intro = (
            f"Semester A (previous): {comparison['previous_semester']} ({previous_section_txt})\n"
            f"Semester B (current): {comparison['current_semester']} ({current_section_txt})\n"
        )
        return f"""You are an academic attainment analyst for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
Faculty context: {faculty_name}
{comparison_intro}
{constraints}

Course Outcome (CO) descriptions:
{co_desc_block}

CO Attainment Comparison (Semester A vs Semester B):
{co_table}

PO/PSO Attainment Comparison:
{po_table}

Assessment structure summary (Semester A):
{previous_summary_block}

Assessment structure summary (Semester B):
{assessment_block}

Assessment-to-CO mapping with attainment (Semester A):
{previous_assessment_block}

Assessment-to-CO mapping with attainment (Semester B):
{current_assessment_block}

Required output format (use these exact section headings):

## Section 1 — Assessment Structure Comparison (Semester A vs B)
- Compare Semester A and Semester B assessment mix with counts by type.
- Explicitly state additions/removals by assessment type between semesters.
- For each CO, report coverage change across semesters (number of assessment components and question counts).
- Identify COs that lost coverage and COs that gained coverage, then relate each change to attainment delta using exact numbers.

## Section 2 — CO-Level Analysis
- Cover every CO present in the comparison table.
- For each CO, include:
  - attainment in Semester A and Semester B, with delta;
  - total question coverage and component spread in both semesters;
  - interpretation that distinguishes high-coverage decline vs low-coverage decline (do not give the same advice for both);
  - one concrete, structurally justified action tied to specific assessments.
- If recommending a change, name the exact component(s) where it should happen.

## Section 3 — Recommended Assessment Structure for Next Semester
- Provide a concrete plan in this style:
  - Quizzes: ...
  - Midsem: ...
  - Endsem: ...
  - Lab/Tutorial/other existing components: ...
  - New addition (only if justified by data): ...
- Justify each line with a specific finding from Sections 1–2.
- Do not recommend new assessment types unless the provided structure and attainment trends justify it.

## Section 4 — What Held Up
- Mandatory section.
- Report at least one positive or relatively stable finding, if present.
- If all COs declined, identify the CO with the smallest decline and provide a structural reason from the data.

Generate the response using only the data above."""

    co_table_single = "\n".join(
        f"{row['metric']}: current={row['current']:.1f}%"
        for row in comparison["co_comparison"]
        if row.get("current") is not None
    ) or "No CO data."
    comparison_intro = f"Current semester: {comparison['current_semester']} ({current_section_txt})\n"
    return f"""You are an academic attainment analyst for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
Faculty context: {faculty_name}
{comparison_intro}
Only one semester of attainment data is available.
{constraints}

Course Outcome (CO) descriptions:
{co_desc_block}

Current CO attainments:
{co_table_single}

PO/PSO Attainment:
{po_table}

Assessment structure summary:
{assessment_block}

Assessment-to-CO mapping with attainment:
{current_assessment_block}

Required output format (single-semester adaptation):

## Section 1 — Assessment Structure Snapshot
- Summarize counts by assessment type and CO coverage distribution.

## Section 2 — CO-Level Analysis
- For each CO, report attainment plus question/component coverage and a targeted structural action.

## Section 3 — Recommended Assessment Structure for Next Semester
- Provide a concrete assessment plan with per-CO question distribution.
- Add new assessment types only if justified by current structure gaps.

## Section 4 — What Held Up
- Mandatory section.
- Identify at least one strongest or most stable CO from current data and explain the structural basis.

Generate the response using only the data above. Explicitly state that Semester A vs B comparison is unavailable."""


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
        previous_assessment_summary=comparison.get("previous_assessment_summary") or [],
        current_assessments=comparison.get("current_assessments") or [],
        previous_assessments=comparison.get("previous_assessments") or [],
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
