from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.analytics.utils.semester import semester_sort_key
from app.projects.models.entities import Project
from app.publications.models.entities import Faculty

_STOP_WORDS = frozenset(
    "a an the and or of in on for to with by from at is are was were be been being "
    "using based study design analysis system implementation via into over under "
    "iiitd iiit delhi project thesis".split()
)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def _split_semesters(value: str) -> list[str]:
    return _split_csv(value)


def _is_thesis(project_type: str) -> bool:
    return project_type.strip().lower() == "thesis"


def _matches_project_type(project_type: str, filter_type: str | None) -> bool:
    if not filter_type or filter_type.lower() == "all":
        return True
    pt = project_type.strip().lower()
    ft = filter_type.strip().lower()
    if ft == "thesis":
        return pt == "thesis"
    if ft in ("ip", "ip/is/ur", "ip/is", "is", "ur"):
        return pt != "thesis"
    return ft in pt or pt in ft


def _top_keywords(titles: list[str], limit: int = 20) -> list[dict]:
    counter: Counter[str] = Counter()
    for title in titles:
        words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", title.lower())
        for w in words:
            if w not in _STOP_WORDS and not w.isdigit():
                counter[w] += 1
    return [{"keyword": k, "count": v} for k, v in counter.most_common(limit)]


def get_projects_analytics(
    db: Session,
    *,
    semesters: list[str] | None = None,
    project_type: str | None = None,
    course_name: str | None = None,
    faculty_id: int | None = None,
    specialization: str | None = None,
) -> dict:
    stmt = select(Project).options(joinedload(Project.faculty))
    projects = list(db.scalars(stmt).unique().all())

    semester_filter = {s.strip() for s in (semesters or []) if s.strip()}
    filtered: list[Project] = []
    for p in projects:
        if not _matches_project_type(p.project_type, project_type):
            continue
        if course_name and (p.course_name or "").lower().find(course_name.lower()) < 0:
            continue
        if faculty_id and p.faculty_id != faculty_id:
            continue
        if specialization and (p.program_specialization or "").lower().find(specialization.lower()) < 0:
            continue
        if semester_filter:
            tags = set(_split_semesters(p.semesters))
            if not tags.intersection(semester_filter):
                continue
        filtered.append(p)

    all_rolls: set[str] = set()
    guides: set[str] = set()
    co_guide_count = 0
    thesis_count = 0
    ip_count = 0

    per_semester: dict[str, dict[str, int]] = {}
    course_code_counts: Counter[str] = Counter()
    guide_counts: Counter[str] = Counter()
    co_guide_counts: Counter[str] = Counter()
    spec_counts: Counter[str] = Counter()
    multi_semester_buckets: dict[str, int] = {}
    credit_by_type: dict[str, Counter[float]] = {"Thesis": Counter(), "IP/IS/UR": Counter()}
    sdg_status: Counter[str] = Counter()
    titles: list[str] = []

    for p in filtered:
        rolls = _split_csv(p.student_roll_nos)
        all_rolls.update(rolls)
        guide_name = p.faculty.name if p.faculty else f"Faculty #{p.faculty_id}"
        guides.add(guide_name)
        guide_counts[guide_name] += 1
        if p.co_guide:
            co_guide_count += 1
            co_guide_counts[p.co_guide] += 1
        if _is_thesis(p.project_type):
            thesis_count += 1
            type_key = "Thesis"
        else:
            ip_count += 1
            type_key = "IP/IS/UR"
        if p.course_code:
            course_code_counts[p.course_code] += 1
        if p.program_specialization:
            spec_counts[p.program_specialization] += 1
        sem_tags = _split_semesters(p.semesters)
        bucket = "1 semester"
        if len(sem_tags) == 2:
            bucket = "2 semesters"
        elif len(sem_tags) >= 3:
            bucket = "3+ semesters"
        multi_semester_buckets[bucket] = multi_semester_buckets.get(bucket, 0) + 1
        for tag in sem_tags:
            per_semester.setdefault(tag, {"Thesis": 0, "IP/IS/UR": 0})
            per_semester[tag][type_key] += 1
        if p.credit is not None:
            credit_by_type[type_key][float(p.credit)] += 1
        sdg_status[p.sdg_review_status or "none"] += 1
        titles.append(p.project_title)

    semester_timeline = sorted(per_semester.keys(), key=semester_sort_key)
    semester_chart = [
        {
            "semester": s,
            "thesis": per_semester[s]["Thesis"],
            "ip_is_ur": per_semester[s]["IP/IS/UR"],
            "total": per_semester[s]["Thesis"] + per_semester[s]["IP/IS/UR"],
        }
        for s in semester_timeline
    ]

    faculty_load = []
    all_faculty_names = sorted(set(guide_counts) | set(co_guide_counts))
    for name in all_faculty_names:
        faculty_load.append(
            {
                "faculty_name": name,
                "as_guide": guide_counts.get(name, 0),
                "as_co_guide": co_guide_counts.get(name, 0),
                "total": guide_counts.get(name, 0) + co_guide_counts.get(name, 0),
            }
        )
    faculty_load.sort(key=lambda x: x["total"], reverse=True)

    faculty_options = [
        {"id": f.id, "name": f.name}
        for f in db.scalars(select(Faculty).where(Faculty.department.ilike("%ECE%")).order_by(Faculty.name)).all()
    ]

    return {
        "kpis": {
            "total_projects": len(filtered),
            "unique_students": len(all_rolls),
            "unique_guides": len(guides),
            "with_co_guide": co_guide_count,
            "thesis_count": thesis_count,
            "ip_is_ur_count": ip_count,
        },
        "semester_chart": semester_chart,
        "course_code_distribution": [
            {"course_code": k, "count": v} for k, v in course_code_counts.most_common()
        ],
        "faculty_load": faculty_load,
        "specialization_distribution": [{"name": k, "count": v} for k, v in spec_counts.most_common()],
        "multi_semester_distribution": [
            {"bucket": k, "count": v} for k, v in multi_semester_buckets.items()
        ],
        "credit_distribution": {
            "Thesis": [{"credit": k, "count": v} for k, v in sorted(credit_by_type["Thesis"].items())],
            "IP/IS/UR": [{"credit": k, "count": v} for k, v in sorted(credit_by_type["IP/IS/UR"].items())],
        },
        "sdg_review_status": [{"status": k, "count": v} for k, v in sdg_status.items()],
        "top_keywords": _top_keywords(titles),
        "filter_options": {
            "semesters": semester_timeline,
            "faculty": faculty_options,
            "course_codes": [code for code, _ in course_code_counts.most_common()],
        },
    }
