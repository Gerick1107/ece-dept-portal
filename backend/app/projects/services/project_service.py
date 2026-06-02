from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.projects.models.entities import Project, ProjectSdg, ProjectStudent, Sdg
from app.projects.schemas.project import ProjectCreate, ProjectUpdate
from app.publications.models.entities import Faculty


class ProjectSearchFilters:
    def __init__(
        self,
        *,
        query: str | None = None,
        faculty_id: int | None = None,
        project_type: str | None = None,
        semester: str | None = None,
        student_name: str | None = None,
        sdg_number: int | None = None,
        status: str | None = None,
        credit: str | None = None,
        confirmed_sdg_only: bool = False,
    ):
        self.query = query
        self.faculty_id = faculty_id
        self.project_type = project_type.upper() if project_type else None
        self.semester = semester
        self.student_name = student_name
        self.sdg_number = sdg_number
        self.status = status
        self.credit = credit
        self.confirmed_sdg_only = confirmed_sdg_only


def _normalize_type(value: str) -> str:
    """Accept BTP, IP, BTP Design, Independent Project, etc."""
    upper = value.strip().upper()
    if not upper:
        raise ValueError("project_type is required")
    if "BTP" in upper:
        return "BTP"
    if "IP" in upper or "INDEPENDENT" in upper:
        return "IP"
    raise ValueError(f"project_type must be BTP or IP (got {value!r})")


def _set_students(db: Session, project: Project, names: list[str]) -> None:
    db.execute(delete(ProjectStudent).where(ProjectStudent.project_id == project.id))
    for name in names:
        cleaned = name.strip()
        if cleaned:
            db.add(ProjectStudent(project_id=project.id, student_name=cleaned))


def project_to_dict(db: Session, project: Project) -> dict:
    faculty = db.get(Faculty, project.faculty_id)
    suggested: list[dict] = []
    confirmed: list[dict] = []
    for link in project.sdg_links:
        sdg = link.sdg or db.get(Sdg, link.sdg_id)
        if not sdg:
            continue
        entry = {
            "id": sdg.id,
            "sdg_number": sdg.sdg_number,
            "sdg_name": sdg.sdg_name,
            "is_confirmed": link.is_confirmed,
            "confidence_score": link.confidence_score,
        }
        if link.is_confirmed:
            confirmed.append(entry)
        else:
            suggested.append(entry)
    return {
        "id": project.id,
        "project_title": project.project_title,
        "project_type": project.project_type,
        "semester": project.semester,
        "faculty_id": project.faculty_id,
        "faculty_name": faculty.name if faculty else "",
        "co_guide": project.co_guide,
        "status": project.status,
        "credit": project.credit,
        "students": [s.student_name for s in project.students],
        "sdg_review_status": project.sdg_review_status,
        "suggested_sdgs": suggested,
        "confirmed_sdgs": confirmed,
        "upload_batch_id": project.upload_batch_id,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def search_projects(
    db: Session,
    filters: ProjectSearchFilters,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Project], int]:
    stmt = select(Project).options(
        joinedload(Project.students),
        joinedload(Project.sdg_links).joinedload(ProjectSdg.sdg),
        joinedload(Project.faculty),
    )
    if filters.faculty_id:
        stmt = stmt.where(Project.faculty_id == filters.faculty_id)
    if filters.project_type:
        stmt = stmt.where(Project.project_type == filters.project_type)
    if filters.semester:
        stmt = stmt.where(Project.semester.ilike(f"%{filters.semester.strip()}%"))
    if filters.status:
        stmt = stmt.where(Project.status.ilike(f"%{filters.status.strip()}%"))
    if filters.credit:
        stmt = stmt.where(Project.credit.ilike(f"%{filters.credit.strip()}%"))
    if filters.query:
        q = f"%{filters.query.strip()}%"
        stmt = stmt.where(
            or_(
                Project.project_title.ilike(q),
                Project.co_guide.ilike(q),
            )
        )
    if filters.student_name:
        sn = f"%{filters.student_name.strip()}%"
        stmt = stmt.where(
            Project.id.in_(select(ProjectStudent.project_id).where(ProjectStudent.student_name.ilike(sn)))
        )
    if filters.sdg_number:
        sdg_sub = select(Sdg.id).where(Sdg.sdg_number == filters.sdg_number).scalar_subquery()
        link_q = select(ProjectSdg.project_id).where(ProjectSdg.sdg_id == sdg_sub)
        if filters.confirmed_sdg_only:
            link_q = link_q.where(ProjectSdg.is_confirmed.is_(True))
        stmt = stmt.where(Project.id.in_(link_q))

    count_stmt = select(func.count(Project.id))
    if filters.faculty_id:
        count_stmt = count_stmt.where(Project.faculty_id == filters.faculty_id)
    if filters.project_type:
        count_stmt = count_stmt.where(Project.project_type == filters.project_type)
    if filters.semester:
        count_stmt = count_stmt.where(Project.semester.ilike(f"%{filters.semester.strip()}%"))
    if filters.status:
        count_stmt = count_stmt.where(Project.status.ilike(f"%{filters.status.strip()}%"))
    if filters.credit:
        count_stmt = count_stmt.where(Project.credit.ilike(f"%{filters.credit.strip()}%"))
    if filters.query:
        q = f"%{filters.query.strip()}%"
        count_stmt = count_stmt.where(or_(Project.project_title.ilike(q), Project.co_guide.ilike(q)))
    if filters.student_name:
        sn = f"%{filters.student_name.strip()}%"
        count_stmt = count_stmt.where(
            Project.id.in_(select(ProjectStudent.project_id).where(ProjectStudent.student_name.ilike(sn)))
        )
    if filters.sdg_number:
        sdg_sub = select(Sdg.id).where(Sdg.sdg_number == filters.sdg_number).scalar_subquery()
        link_q = select(ProjectSdg.project_id).where(ProjectSdg.sdg_id == sdg_sub)
        if filters.confirmed_sdg_only:
            link_q = link_q.where(ProjectSdg.is_confirmed.is_(True))
        count_stmt = count_stmt.where(Project.id.in_(link_q))
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Project.id.asc()).offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(rows), int(total)


def create_project(db: Session, body: ProjectCreate, upload_batch_id: int | None = None) -> Project:
    faculty = db.get(Faculty, body.faculty_id)
    if not faculty:
        raise ValueError("faculty_id not found")
    project = Project(
        project_title=body.project_title.strip(),
        project_type=_normalize_type(body.project_type),
        semester=body.semester.strip(),
        faculty_id=body.faculty_id,
        co_guide=body.co_guide.strip() if body.co_guide else None,
        status=body.status or "Pending",
        credit=body.credit,
        upload_batch_id=upload_batch_id,
        sdg_review_status="none",
    )
    db.add(project)
    db.flush()
    _set_students(db, project, body.students)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, body: ProjectUpdate) -> Project:
    if body.project_title is not None:
        project.project_title = body.project_title.strip()
    if body.project_type is not None:
        project.project_type = _normalize_type(body.project_type)
    if body.semester is not None:
        project.semester = body.semester.strip()
    if body.faculty_id is not None:
        if not db.get(Faculty, body.faculty_id):
            raise ValueError("faculty_id not found")
        project.faculty_id = body.faculty_id
    if body.co_guide is not None:
        project.co_guide = body.co_guide.strip() or None
    if body.status is not None:
        project.status = body.status
    if body.credit is not None:
        project.credit = body.credit
    if body.students is not None:
        _set_students(db, project, body.students)
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()


def clear_sdg_links(db: Session, project_id: int, *, confirmed_only: bool | None = None) -> None:
    stmt = delete(ProjectSdg).where(ProjectSdg.project_id == project_id)
    if confirmed_only is True:
        stmt = stmt.where(ProjectSdg.is_confirmed.is_(True))
    elif confirmed_only is False:
        stmt = stmt.where(ProjectSdg.is_confirmed.is_(False))
    db.execute(stmt)


def apply_sdg_suggestions(db: Session, project: Project, suggestions: list[dict]) -> None:
    clear_sdg_links(db, project.id, confirmed_only=False)
    existing_confirmed_ids = set(
        db.scalars(
            select(ProjectSdg.sdg_id).where(
                ProjectSdg.project_id == project.id,
                ProjectSdg.is_confirmed.is_(True),
            )
        ).all()
    )

    deduped_by_sdg: dict[int, float | None] = {}
    for item in suggestions:
        try:
            sdg_number = int(item.get("sdg_number"))
        except (TypeError, ValueError):
            continue
        confidence_raw = item.get("confidence")
        confidence = float(confidence_raw) if confidence_raw is not None else None
        prev = deduped_by_sdg.get(sdg_number)
        if prev is None or (confidence is not None and confidence > prev):
            deduped_by_sdg[sdg_number] = confidence

    added = 0
    for sdg_number, confidence in deduped_by_sdg.items():
        sdg = db.scalar(select(Sdg).where(Sdg.sdg_number == sdg_number))
        if not sdg or sdg.id in existing_confirmed_ids:
            # Keep confirmed mappings intact; don't reinsert duplicate links.
            continue
        added += 1
        db.add(
            ProjectSdg(
                project_id=project.id,
                sdg_id=sdg.id,
                is_confirmed=False,
                confidence_score=confidence,
            )
        )
    if added > 0:
        project.sdg_review_status = "pending_review"
    elif existing_confirmed_ids:
        project.sdg_review_status = "confirmed"
    else:
        project.sdg_review_status = "none"
    db.commit()


def confirm_sdgs(db: Session, project: Project) -> Project:
    for link in project.sdg_links:
        if not link.is_confirmed:
            link.is_confirmed = True
    project.sdg_review_status = "confirmed"
    db.commit()
    db.refresh(project)
    return project


def reject_sdgs(db: Session, project: Project) -> Project:
    clear_sdg_links(db, project.id, confirmed_only=False)
    project.sdg_review_status = "rejected"
    db.commit()
    db.refresh(project)
    return project


def edit_confirmed_sdgs(db: Session, project: Project, sdg_numbers: list[int]) -> Project:
    clear_sdg_links(db, project.id)
    unique = sorted(set(sdg_numbers))
    for num in unique:
        if not 1 <= num <= 17:
            raise ValueError(f"Invalid SDG number: {num}")
        sdg = db.scalar(select(Sdg).where(Sdg.sdg_number == num))
        if sdg:
            db.add(ProjectSdg(project_id=project.id, sdg_id=sdg.id, is_confirmed=True, confidence_score=None))
    project.sdg_review_status = "confirmed" if unique else "none"
    db.commit()
    db.refresh(project)
    return project


def get_sdg_catalog(db: Session) -> list[Sdg]:
    return list(db.scalars(select(Sdg).order_by(Sdg.sdg_number)).all())
