from __future__ import annotations

import logging
import re
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.copo.services.mapping_service import course_title_matches
from app.database.models.assessment import Assessment, AssessmentCoMapping
from app.database.models.copo import CopoEvaluationRun
from app.database.models.course import Course

logger = logging.getLogger(__name__)


def _resolve_course_id(db: Session, course_title: str) -> int | None:
    courses = db.scalars(select(Course)).all()
    for course in courses:
        label = f"{course.course_code}: {course.course_name}"
        if course_title_matches(course_title, label) or course_title_matches(course_title, course.course_code):
            return course.id
    code_match = re.search(r"(?:ECE|ENG|CSE|CS|EVE|CSER)-?[\d/]+", course_title, re.IGNORECASE)
    if code_match:
        code = code_match.group(0).upper()
        for course in courses:
            if course.course_code.upper() == code:
                return course.id
    return None


def _component_type(name: str) -> str:
    token = re.split(r"[_.\s]+", str(name).strip())[0]
    return token or str(name).strip()


def persist_assessment_co_mappings(
    db: Session,
    run: CopoEvaluationRun,
    *,
    course_title: str,
    semester_label: str | None,
    section_label: str | None,
    intermediate: dict,
) -> None:
    """Replace assessment rows for a completed evaluation run."""
    details = intermediate.get("assessment_co_structure") or []
    if not details:
        return

    course_id = _resolve_course_id(db, course_title)
    if course_id is None:
        logger.warning("Could not resolve course_id for %s — skipping assessment_co_mapping persistence", course_title)
        return

    semester = (semester_label or run.semester_label or "Unknown").strip()
    section = (section_label or run.section_label or "").strip() or None

    db.execute(delete(Assessment).where(Assessment.evaluation_run_id == run.id))

    by_assessment: dict[str, dict] = {}
    for item in details:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        entry = by_assessment.setdefault(
            name,
            {
                "name": name,
                "assessment_type": item.get("assessment_type") or _component_type(name),
                "co_counts": defaultdict(int),
            },
        )
        co_label = str(item.get("co_label") or "").strip()
        if co_label:
            entry["co_counts"][co_label] += int(item.get("question_count") or 1)

    for entry in by_assessment.values():
        assessment = Assessment(
            evaluation_run_id=run.id,
            name=entry["name"],
            assessment_type=entry["assessment_type"],
            course_id=course_id,
            semester=semester,
            section_label=section,
        )
        db.add(assessment)
        db.flush()
        for co_label, question_count in sorted(entry["co_counts"].items()):
            db.add(
                AssessmentCoMapping(
                    assessment_id=assessment.id,
                    course_id=course_id,
                    semester=semester,
                    co_label=co_label,
                    question_count=question_count,
                    weightage=None,
                )
            )


def load_assessment_co_payload(
    db: Session,
    *,
    evaluation_run_id: int | None,
    course_title: str,
    semester_label: str,
    section_label: str | None,
    co_attainment: dict[str, float],
) -> list[dict]:
    """Build per-assessment payload for LLM insights."""
    if evaluation_run_id is None:
        return []

    assessments = db.scalars(
        select(Assessment).where(Assessment.evaluation_run_id == evaluation_run_id).order_by(Assessment.id.asc())
    ).all()
    if not assessments:
        return []

    payload: list[dict] = []
    for assessment in assessments:
        mappings = db.scalars(
            select(AssessmentCoMapping).where(AssessmentCoMapping.assessment_id == assessment.id)
        ).all()
        co_entries = []
        for mapping in mappings:
            co_entries.append(
                {
                    "co_label": mapping.co_label,
                    "question_count": mapping.question_count,
                    "attainment": co_attainment.get(mapping.co_label),
                }
            )
        payload.append(
            {
                "assessment_id": assessment.id,
                "name": assessment.name,
                "type": assessment.assessment_type,
                "semester": semester_label,
                "section_label": section_label,
                "course_title": course_title,
                "cos": co_entries,
            }
        )
    return payload


def build_assessment_co_payload_from_intermediate(
    intermediate: dict,
    *,
    course_title: str,
    semester_label: str,
    section_label: str | None,
    co_attainment: dict[str, float],
) -> list[dict]:
    """Fallback when assessment rows are not persisted in the database."""
    details = intermediate.get("assessment_co_structure") or []
    if details:
        by_name: dict[str, dict] = {}
        for item in details:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            entry = by_name.setdefault(
                name,
                {
                    "name": name,
                    "type": item.get("assessment_type") or _component_type(name),
                    "co_counts": defaultdict(int),
                },
            )
            co_label = str(item.get("co_label") or "").strip()
            if co_label:
                entry["co_counts"][co_label] += int(item.get("question_count") or 1)

        payload: list[dict] = []
        for entry in by_name.values():
            co_entries = [
                {
                    "co_label": co_label,
                    "question_count": count,
                    "attainment": co_attainment.get(co_label),
                }
                for co_label, count in sorted(entry["co_counts"].items())
            ]
            payload.append(
                {
                    "assessment_id": None,
                    "name": entry["name"],
                    "type": entry["type"],
                    "semester": semester_label,
                    "section_label": section_label,
                    "course_title": course_title,
                    "cos": co_entries,
                }
            )
        return payload

    assessment_ids = intermediate.get("assessment_ids") or []
    if not assessment_ids:
        return []

    by_component: dict[str, dict] = defaultdict(lambda: {"question_count": 0, "co_labels": set()})
    for col in assessment_ids:
        base = re.sub(r"\.\d+$", "", str(col).strip())
        base = re.sub(r"_Q\d+$", "", base, flags=re.IGNORECASE)
        by_component[base]["question_count"] += 1

    return [
        {
            "assessment_id": None,
            "name": name,
            "type": _component_type(name),
            "semester": semester_label,
            "section_label": section_label,
            "course_title": course_title,
            "cos": [],
        }
        for name in sorted(by_component)
    ]
