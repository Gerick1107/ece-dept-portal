from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.analytics.utils.semester import semester_sort_key
from app.projects.models.entities import Project, ProjectSdg
from app.projects.services.project_service import confirm_sdgs, project_to_dict
from app.projects.utils.csv_fields import parse_csv_field

logger = logging.getLogger(__name__)

SDG_AUTO_ACCEPT_THRESHOLD = 0.5


def _project_semester_tags(project: Project) -> list[str]:
    return [t.strip() for t in parse_csv_field(project.semesters) if t.strip()]


def _is_pending_review(project: Project) -> bool:
    if project.sdg_review_status == "pending_review":
        return True
    if project.sdg_review_status != "none":
        return False
    return any(not link.is_confirmed for link in project.sdg_links)


def _project_in_semester_range(project: Project, from_semester: str, to_semester: str) -> bool:
    from_key = semester_sort_key(from_semester)
    to_key = semester_sort_key(to_semester)
    lo = from_key if from_key <= to_key else to_key
    hi = to_key if from_key <= to_key else from_key
    for tag in _project_semester_tags(project):
        key = semester_sort_key(tag)
        if lo <= key <= hi:
            return True
    return False


def _default_accept_numbers(project: Project) -> list[int]:
    nums: list[int] = []
    for link in project.sdg_links:
        if link.is_confirmed:
            continue
        sdg = link.sdg
        if not sdg:
            continue
        score = link.confidence_score
        if score is not None and score >= SDG_AUTO_ACCEPT_THRESHOLD:
            nums.append(sdg.sdg_number)
    return sorted(set(nums))


def preview_bulk_accept_sdgs(
    db: Session,
    *,
    faculty_id: int,
    from_semester: str,
    to_semester: str,
) -> dict:
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.faculty_id == faculty_id)
            .options(
                joinedload(Project.sdg_links).joinedload(ProjectSdg.sdg),
                joinedload(Project.faculty),
            )
        ).unique().all()
    )
    matching = []
    for project in projects:
        if not _is_pending_review(project):
            continue
        if not _project_in_semester_range(project, from_semester, to_semester):
            continue
        sdg_numbers = _default_accept_numbers(project)
        if not sdg_numbers:
            continue
        matching.append(
            {
                "id": project.id,
                "project_title": project.project_title,
                "semesters": _project_semester_tags(project),
                "sdg_numbers": sdg_numbers,
            }
        )
    return {
        "faculty_id": faculty_id,
        "from_semester": from_semester,
        "to_semester": to_semester,
        "count": len(matching),
        "projects": matching,
    }


def bulk_accept_sdgs(
    db: Session,
    *,
    faculty_id: int,
    from_semester: str,
    to_semester: str,
    actor_email: str | None = None,
) -> dict:
    preview = preview_bulk_accept_sdgs(
        db,
        faculty_id=faculty_id,
        from_semester=from_semester,
        to_semester=to_semester,
    )
    accepted_ids: list[int] = []
    for item in preview["projects"]:
        project = db.scalar(
            select(Project)
            .where(Project.id == item["id"])
            .options(joinedload(Project.sdg_links).joinedload(ProjectSdg.sdg))
        )
        if not project or not _is_pending_review(project):
            continue
        confirm_sdgs(db, project, item["sdg_numbers"])
        accepted_ids.append(project.id)

    logger.info(
        "Bulk SDG accept: faculty_id=%s range=%s..%s accepted=%s by=%s at=%s",
        faculty_id,
        from_semester,
        to_semester,
        len(accepted_ids),
        actor_email or "unknown",
        datetime.utcnow().isoformat(),
    )
    return {
        "accepted_count": len(accepted_ids),
        "accepted_project_ids": accepted_ids,
        "faculty_id": faculty_id,
        "from_semester": from_semester,
        "to_semester": to_semester,
        "accepted_at": datetime.utcnow().isoformat(),
        "accepted_by": actor_email,
    }
