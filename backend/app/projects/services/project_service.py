from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.projects.models.entities import Project, ProjectSdg, ProjectStudent, Sdg
from app.projects.schemas.project import ProjectCreate, ProjectUpdate
from app.projects.utils.course_name import normalize_course_name
from app.projects.utils.csv_fields import append_csv_value, parse_csv_field
from app.publications.models.entities import Faculty
from app.utils.name_utils import strip_name_prefix


class ProjectSearchFilters:
    def __init__(
        self,
        *,
        query: str | None = None,
        faculty_id: int | None = None,
        project_type: str | None = None,
        semesters: list[str] | None = None,
        course_codes: list[str] | None = None,
        course_name: str | None = None,
        co_guide: str | None = None,
        student_name: str | None = None,
        student_roll_no: str | None = None,
        sdg_number: int | None = None,
        credit: str | None = None,
        confirmed_sdg_only: bool = False,
        scope_faculty_id: int | None = None,
        scope_faculty_name: str | None = None,
    ):
        self.query = query
        self.faculty_id = faculty_id
        self.project_type = project_type.strip() if project_type else None
        self.semesters = semesters or []
        self.course_codes = course_codes or []
        self.course_name = course_name
        self.co_guide = co_guide
        self.student_name = student_name
        self.student_roll_no = student_roll_no
        self.sdg_number = sdg_number
        self.credit = credit
        self.confirmed_sdg_only = confirmed_sdg_only
        # Per-faculty visibility scope: restricts results to projects the faculty
        # is involved in as EITHER guide (faculty_id) OR co-guide (name match).
        # When set with an id but no resolvable name, only the guide side applies.
        self.scope_faculty_id = scope_faculty_id
        self.scope_faculty_name = scope_faculty_name


def _normalize_type(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("project_type is required")
    return cleaned


def _sync_students_from_names(db: Session, project: Project) -> None:
    db.execute(delete(ProjectStudent).where(ProjectStudent.project_id == project.id))
    for name in parse_csv_field(project.student_names):
        db.add(ProjectStudent(project_id=project.id, student_name=name))


def find_merge_candidate(
    db: Session,
    title: str,
    guide_clean: str,
    course_code: str,
) -> Project | None:
    title_key = title.strip().lower()
    guide_key = strip_name_prefix(guide_clean).lower()
    code_key = (course_code or "").strip().upper()
    rows = db.scalars(
        select(Project).options(joinedload(Project.faculty)).order_by(Project.id.asc())
    ).unique().all()
    for project in rows:
        stored_guide = project.guide_name or (project.faculty.name if project.faculty else "")
        stored_key = strip_name_prefix(stored_guide).lower()
        if (
            project.project_title.strip().lower() == title_key
            and stored_key == guide_key
            and (project.course_code or "").strip().upper() == code_key
        ):
            return project
    return None


def merge_project(
    project: Project,
    *,
    semester_tag: str,
    student_roll_no: str,
    student_name: str,
) -> Project:
    project.semesters = append_csv_value(project.semesters, semester_tag)
    if student_roll_no:
        project.student_roll_nos = append_csv_value(project.student_roll_nos, student_roll_no)
    if student_name:
        project.student_names = append_csv_value(project.student_names, student_name)
    project.updated_at = datetime.utcnow()
    return project


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
    credit_val = project.credit
    if credit_val is not None:
        credit_val = float(credit_val)
    return {
        "id": project.id,
        "project_title": project.project_title,
        "project_type": project.project_type,
        "semesters": project.semesters,
        "faculty_id": project.faculty_id,
        "faculty_name": strip_name_prefix(project.guide_name or (faculty.name if faculty else "")),
        "guide_name": strip_name_prefix(project.guide_name) if project.guide_name else None,
        "co_guide": project.co_guide,
        "course_code": project.course_code,
        "course_name": normalize_course_name(project.course_name) if project.course_name else None,
        "admission_year": project.admission_year,
        "program_definition": project.program_definition,
        "program_specialization": project.program_specialization,
        "student_roll_nos": project.student_roll_nos,
        "student_names": project.student_names,
        "credit": credit_val,
        "students": parse_csv_field(project.student_names),
        "student_rolls": parse_csv_field(project.student_roll_nos),
        "sdg_review_status": project.sdg_review_status,
        "sdg_ever_accepted": bool(getattr(project, "sdg_ever_accepted", False)),
        "suggested_sdgs": suggested,
        "confirmed_sdgs": confirmed,
        "upload_batch_id": project.upload_batch_id,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _apply_filters(stmt, filters: ProjectSearchFilters):
    # Per-faculty scope (guide OR co-guide) — applied first so it always narrows.
    if filters.scope_faculty_id is not None or filters.scope_faculty_name:
        conditions = []
        if filters.scope_faculty_id is not None:
            conditions.append(Project.faculty_id == filters.scope_faculty_id)
        if filters.scope_faculty_name:
            name = strip_name_prefix(filters.scope_faculty_name.strip())
            if name:
                conditions.append(Project.co_guide.ilike(f"%{name}%"))
                conditions.append(Project.guide_name.ilike(f"%{name}%"))
        stmt = stmt.where(or_(*conditions)) if conditions else stmt.where(Project.id == -1)
    if filters.faculty_id:
        stmt = stmt.where(Project.faculty_id == filters.faculty_id)
    if filters.project_type:
        stmt = stmt.where(Project.project_type.ilike(f"%{filters.project_type.strip()}%"))
    if filters.course_name:
        target = normalize_course_name(filters.course_name.strip())
        stmt = stmt.where(Project.course_name == target)
    if filters.course_codes:
        codes = [c.strip().upper() for c in filters.course_codes if c.strip()]
        if codes:
            stmt = stmt.where(func.upper(Project.course_code).in_(codes))
    if filters.semesters:
        for tag in filters.semesters:
            cleaned = tag.strip()
            if cleaned:
                stmt = stmt.where(Project.semesters.ilike(f"%{cleaned}%"))
    if filters.co_guide:
        cg = f"%{strip_name_prefix(filters.co_guide.strip())}%"
        stmt = stmt.where(Project.co_guide.ilike(cg))
    if filters.credit:
        try:
            credit_val = float(filters.credit.strip())
            stmt = stmt.where(Project.credit == credit_val)
        except ValueError:
            pass
    if filters.query:
        q = f"%{filters.query.strip()}%"
        stmt = stmt.join(Faculty, Project.faculty_id == Faculty.id).where(
            or_(
                Project.project_title.ilike(q),
                Project.guide_name.ilike(q),
                Project.co_guide.ilike(q),
                Project.student_names.ilike(q),
                Project.student_roll_nos.ilike(q),
                Faculty.name.ilike(q),
            )
        )
    if filters.student_name:
        sn = f"%{filters.student_name.strip()}%"
        stmt = stmt.where(Project.student_names.ilike(sn))
    if filters.student_roll_no:
        sr = f"%{filters.student_roll_no.strip()}%"
        stmt = stmt.where(Project.student_roll_nos.ilike(sr))
    if filters.sdg_number:
        sdg_sub = select(Sdg.id).where(Sdg.sdg_number == filters.sdg_number).scalar_subquery()
        link_q = select(ProjectSdg.project_id).where(ProjectSdg.sdg_id == sdg_sub)
        if filters.confirmed_sdg_only:
            link_q = link_q.where(ProjectSdg.is_confirmed.is_(True))
        stmt = stmt.where(Project.id.in_(link_q))
    return stmt


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
    stmt = _apply_filters(stmt, filters)

    count_stmt = select(func.count(Project.id))
    count_stmt = _apply_filters(count_stmt, filters)
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
        semesters=body.semesters.strip(),
        faculty_id=body.faculty_id,
        guide_name=strip_name_prefix(body.guide_name) if body.guide_name else None,
        co_guide=strip_name_prefix(body.co_guide) if body.co_guide else None,
        course_code=body.course_code.strip() if body.course_code else None,
        course_name=normalize_course_name(body.course_name) if body.course_name else None,
        admission_year=body.admission_year,
        program_definition=body.program_definition,
        program_specialization=body.program_specialization,
        student_roll_nos=body.student_roll_nos.strip() if body.student_roll_nos else "",
        student_names=body.student_names.strip() if body.student_names else "",
        credit=body.credit,
        upload_batch_id=upload_batch_id,
        sdg_review_status="none",
    )
    db.add(project)
    db.flush()
    _sync_students_from_names(db, project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, body: ProjectUpdate) -> Project:
    if body.project_title is not None:
        project.project_title = body.project_title.strip()
    if body.project_type is not None:
        project.project_type = _normalize_type(body.project_type)
    if body.semesters is not None:
        project.semesters = body.semesters.strip()
    if body.faculty_id is not None:
        if not db.get(Faculty, body.faculty_id):
            raise ValueError("faculty_id not found")
        project.faculty_id = body.faculty_id
    if body.guide_name is not None:
        project.guide_name = strip_name_prefix(body.guide_name) if body.guide_name else None
    if body.co_guide is not None:
        project.co_guide = strip_name_prefix(body.co_guide) if body.co_guide else None
    if body.course_code is not None:
        project.course_code = body.course_code.strip() or None
    if body.course_name is not None:
        project.course_name = normalize_course_name(body.course_name) if body.course_name else None
    if body.admission_year is not None:
        project.admission_year = body.admission_year
    if body.program_definition is not None:
        project.program_definition = body.program_definition
    if body.program_specialization is not None:
        project.program_specialization = body.program_specialization
    if body.student_roll_nos is not None:
        project.student_roll_nos = body.student_roll_nos.strip()
    if body.student_names is not None:
        project.student_names = body.student_names.strip()
        _sync_students_from_names(db, project)
    if body.credit is not None:
        project.credit = body.credit
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


def confirm_sdgs(db: Session, project: Project, sdg_numbers: list[int]) -> Project:
    """Confirm only the SDGs selected in the review UI."""
    return edit_confirmed_sdgs(db, project, sdg_numbers)


def reject_sdgs(db: Session, project: Project) -> Project:
    clear_sdg_links(db, project.id)
    project.sdg_review_status = "rejected"
    db.commit()
    db.refresh(project)
    return project


def edit_confirmed_sdgs(db: Session, project: Project, sdg_numbers: list[int]) -> Project:
    old_confidence: dict[int, float | None] = {}
    for link in project.sdg_links:
        if link.sdg:
            old_confidence[link.sdg.sdg_number] = link.confidence_score
    clear_sdg_links(db, project.id)
    unique = sorted(set(sdg_numbers))
    for num in unique:
        if not 1 <= num <= 17:
            raise ValueError(f"Invalid SDG number: {num}")
        sdg = db.scalar(select(Sdg).where(Sdg.sdg_number == num))
        if sdg:
            db.add(
                ProjectSdg(
                    project_id=project.id,
                    sdg_id=sdg.id,
                    is_confirmed=True,
                    confidence_score=old_confidence.get(num),
                )
            )
    project.sdg_review_status = "confirmed" if unique else "none"
    if unique:
        project.sdg_ever_accepted = True
    db.commit()
    db.refresh(project)
    return project


def get_sdg_catalog(db: Session) -> list[Sdg]:
    return list(db.scalars(select(Sdg).order_by(Sdg.sdg_number)).all())


def list_distinct_course_codes(db: Session) -> list[str]:
    rows = db.scalars(
        select(Project.course_code)
        .where(Project.course_code.isnot(None), Project.course_code != "")
        .distinct()
        .order_by(Project.course_code.asc())
    ).all()
    return [r for r in rows if r]


def list_distinct_course_names(db: Session) -> list[str]:
    rows = db.scalars(
        select(Project.course_name)
        .where(Project.course_name.isnot(None), Project.course_name != "")
        .distinct()
        .order_by(Project.course_name.asc())
    ).all()
    return sorted({normalize_course_name(r) for r in rows if r})
