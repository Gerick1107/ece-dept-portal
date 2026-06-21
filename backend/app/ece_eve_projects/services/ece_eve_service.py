from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import String, delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.ece_eve_projects.models.entities import EceEveProject
from app.projects.models.entities import Project
from app.publications.models.entities import Faculty

ECE_EVE_BRANCHES = frozenset({"ECE", "EVE"})


def _is_ece_eve_branch(program_specialization: str | None) -> bool:
    if not program_specialization:
        return False
    return program_specialization.strip().upper() in ECE_EVE_BRANCHES


def _project_to_ece_eve_row(project: Project) -> EceEveProject:
    return EceEveProject(
        project_title=project.project_title,
        project_type=project.project_type,
        semesters=project.semesters,
        faculty_id=project.faculty_id,
        guide_name=project.guide_name,
        co_guide=project.co_guide,
        course_code=project.course_code,
        course_name=project.course_name,
        admission_year=project.admission_year,
        program_definition=project.program_definition,
        program_specialization=project.program_specialization,
        student_roll_nos=project.student_roll_nos,
        student_names=project.student_names,
        credit=project.credit,
        upload_batch_id=project.upload_batch_id,
        sdg_review_status=project.sdg_review_status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def purge_ece_eve_projects(db: Session) -> dict:
    """Delete all ECE/EVE projects, dependent rows, mirror table, and orphan upload files."""
    from pathlib import Path

    from app.projects.models.entities import Project, ProjectSdg, ProjectStudent, ProjectUpload

    branch_filter = func.upper(func.trim(Project.program_specialization)).in_(tuple(ECE_EVE_BRANCHES))
    ece_eve_ids = list(db.scalars(select(Project.id).where(branch_filter)).all())

    removed_files = 0
    if not ece_eve_ids:
        db.execute(delete(EceEveProject))
        db.commit()
        return {"purged": True, "removed_files": 0}

    upload_batch_ids = {
        bid
        for bid in db.scalars(
            select(Project.upload_batch_id).where(
                Project.id.in_(ece_eve_ids),
                Project.upload_batch_id.isnot(None),
            )
        ).all()
        if bid
    }
    uploads_to_delete: list[int] = []
    for batch_id in upload_batch_ids:
        other_count = db.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.upload_batch_id == batch_id, ~Project.id.in_(ece_eve_ids))
        )
        if other_count:
            continue
        upload = db.get(ProjectUpload, batch_id)
        if not upload:
            continue
        path = Path(upload.filepath)
        if path.exists():
            try:
                path.unlink()
                removed_files += 1
            except OSError:
                pass
        uploads_to_delete.append(batch_id)

    db.query(ProjectSdg).filter(ProjectSdg.project_id.in_(ece_eve_ids)).delete(synchronize_session=False)
    db.query(ProjectStudent).filter(ProjectStudent.project_id.in_(ece_eve_ids)).delete(synchronize_session=False)
    db.query(Project).filter(Project.id.in_(ece_eve_ids)).delete(synchronize_session=False)
    if uploads_to_delete:
        db.query(ProjectUpload).filter(ProjectUpload.id.in_(uploads_to_delete)).delete(synchronize_session=False)
    db.execute(delete(EceEveProject))
    db.commit()
    return {"purged": True, "removed_files": removed_files}


def refresh_ece_eve_projects(db: Session) -> int:
    """Rebuild ece_eve_projects from projects where branch is ECE or EVE."""
    db.execute(delete(EceEveProject))
    rows = db.scalars(
        select(Project).where(
            func.upper(func.trim(Project.program_specialization)).in_(tuple(ECE_EVE_BRANCHES))
        )
    ).all()
    for project in rows:
        db.add(_project_to_ece_eve_row(project))
    db.commit()
    return len(rows)


class EceEveProjectFilters:
    def __init__(
        self,
        *,
        branch: str | None = None,
        year: str | None = None,
        project_type: str | None = None,
        query: str | None = None,
        faculty_id: int | None = None,
        semesters: list[str] | None = None,
        course_codes: list[str] | None = None,
        course_name: str | None = None,
        co_guide: str | None = None,
        credit: str | None = None,
    ):
        self.branch = branch.strip().upper() if branch and branch.strip().lower() != "both" else None
        self.year = year.strip() if year else None
        self.project_type = project_type.strip() if project_type else None
        self.query = query.strip() if query else None
        self.faculty_id = faculty_id
        self.semesters = semesters or []
        self.course_codes = [c.strip().upper() for c in (course_codes or []) if c.strip()]
        self.course_name = course_name.strip() if course_name else None
        self.co_guide = co_guide.strip() if co_guide else None
        self.credit = credit.strip() if credit else None


def search_ece_eve_projects(
    db: Session,
    filters: EceEveProjectFilters,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[EceEveProject], int]:
    q = select(EceEveProject).options(joinedload(EceEveProject.faculty))
    if filters.branch:
        q = q.where(func.upper(func.trim(EceEveProject.program_specialization)) == filters.branch)
    else:
        q = q.where(
            func.upper(func.trim(EceEveProject.program_specialization)).in_(tuple(ECE_EVE_BRANCHES))
        )
    if filters.year:
        q = q.where(
            or_(
                EceEveProject.admission_year == filters.year,
                EceEveProject.semesters.ilike(f"%{filters.year}%"),
            )
        )
    if filters.project_type:
        q = q.where(EceEveProject.project_type == filters.project_type)
    if filters.faculty_id:
        q = q.where(EceEveProject.faculty_id == filters.faculty_id)
    if filters.semesters:
        q = q.where(or_(*[EceEveProject.semesters.ilike(f"%{tag}%") for tag in filters.semesters]))
    if filters.course_codes:
        q = q.where(func.upper(func.coalesce(EceEveProject.course_code, "")).in_(filters.course_codes))
    if filters.course_name:
        q = q.where(EceEveProject.course_name == filters.course_name)
    if filters.co_guide:
        q = q.where(EceEveProject.co_guide == filters.co_guide)
    if filters.credit:
        q = q.where(func.cast(EceEveProject.credit, String) == filters.credit)
    if filters.query:
        like = f"%{filters.query}%"
        q = q.where(
            or_(
                EceEveProject.project_title.ilike(like),
                EceEveProject.student_names.ilike(like),
                EceEveProject.student_roll_nos.ilike(like),
                EceEveProject.guide_name.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.order_by(EceEveProject.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return list(rows), int(total)


def project_row_to_dict(row: EceEveProject) -> dict:
    faculty = row.faculty
    return {
        "id": row.id,
        "project_title": row.project_title,
        "project_type": row.project_type,
        "semesters": row.semesters,
        "faculty_id": row.faculty_id,
        "guide_name": row.guide_name or (faculty.name if faculty else None),
        "co_guide": row.co_guide,
        "course_code": row.course_code,
        "course_name": row.course_name,
        "admission_year": row.admission_year,
        "program_definition": row.program_definition,
        "program_specialization": row.program_specialization,
        "student_roll_nos": row.student_roll_nos,
        "student_names": row.student_names,
        "credit": float(row.credit) if row.credit is not None else None,
        "faculty_name": faculty.name if faculty else None,
        "sdg_review_status": row.sdg_review_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_ece_eve_analytics(db: Session, *, branch: str | None = None) -> dict:
    filters = EceEveProjectFilters(branch=branch or "both")
    q = select(EceEveProject).options(joinedload(EceEveProject.faculty))
    if filters.branch:
        q = q.where(func.upper(func.trim(EceEveProject.program_specialization)) == filters.branch)
    else:
        q = q.where(
            func.upper(func.trim(EceEveProject.program_specialization)).in_(tuple(ECE_EVE_BRANCHES))
        )
    rows = db.scalars(q).unique().all()

    by_branch: dict[str, int] = {}
    by_semester: dict[str, int] = {}
    by_type: dict[str, int] = {}
    supervisor_counts: dict[str, int] = {}

    for row in rows:
        branch_key = (row.program_specialization or "Unknown").strip().upper()
        by_branch[branch_key] = by_branch.get(branch_key, 0) + 1
        semester_tags = [p.strip() for p in str(row.semesters or "").split(",") if p.strip()]
        if not semester_tags:
            semester_tags = ["Unknown"]
        for tag in semester_tags:
            by_semester[tag] = by_semester.get(tag, 0) + 1
        type_key = row.project_type or "Unknown"
        by_type[type_key] = by_type.get(type_key, 0) + 1
        guide = row.guide_name or (row.faculty.name if row.faculty else "Unknown")
        supervisor_counts[guide] = supervisor_counts.get(guide, 0) + 1

    return {
        "total_count": len(rows),
        "by_branch": [{"branch": k, "count": v} for k, v in sorted(by_branch.items())],
        "by_semester": [{"semester": k, "count": v} for k, v in sorted(by_semester.items())],
        "by_type": [{"project_type": k, "count": v} for k, v in sorted(by_type.items())],
        "supervisor_distribution": [
            {"supervisor": k, "count": v}
            for k, v in sorted(supervisor_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def list_ece_eve_filter_options(db: Session) -> dict:
    semester_rows = db.scalars(select(EceEveProject.semesters).where(EceEveProject.semesters.is_not(None))).all()
    semesters: set[str] = set()
    for raw in semester_rows:
        for part in str(raw).split(","):
            tag = part.strip()
            if tag:
                semesters.add(tag)

    course_codes = sorted(
        {
            str(v).strip().upper()
            for v in db.scalars(select(EceEveProject.course_code).where(EceEveProject.course_code.is_not(None))).all()
            if str(v).strip()
        }
    )
    course_names = sorted(
        {
            str(v).strip()
            for v in db.scalars(select(EceEveProject.course_name).where(EceEveProject.course_name.is_not(None))).all()
            if str(v).strip()
        }
    )
    co_guides = sorted(
        {
            str(v).strip()
            for v in db.scalars(select(EceEveProject.co_guide).where(EceEveProject.co_guide.is_not(None))).all()
            if str(v).strip()
        }
    )
    guides = db.scalars(
        select(Faculty).where(Faculty.department.ilike("%ECE%")).order_by(Faculty.name.asc())
    ).all()
    return {
        "semesters": sorted(semesters),
        "course_codes": course_codes,
        "course_names": course_names,
        "co_guides": co_guides,
        "guides": [{"id": g.id, "name": g.name} for g in guides],
        "project_types": ["Thesis", "IP/IS/UR"],
    }


def export_ece_eve_csv(db: Session, filters: EceEveProjectFilters) -> bytes:
    rows, _ = search_ece_eve_projects(db, filters, page=1, page_size=100000)
    frame = pd.DataFrame([project_row_to_dict(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["project_title"])
    return frame.to_csv(index=False).encode("utf-8")


def export_ece_eve_excel(db: Session, filters: EceEveProjectFilters) -> bytes:
    rows, _ = search_ece_eve_projects(db, filters, page=1, page_size=100000)
    frame = pd.DataFrame([project_row_to_dict(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["project_title"])
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="ece_eve_projects")
    return buf.getvalue()


def export_ece_eve_pdf(db: Session, filters: EceEveProjectFilters, title: str = "ECE/EVE Projects") -> bytes:
    rows, _ = search_ece_eve_projects(db, filters, page=1, page_size=100000)
    data = [
        ["Branch", "Title", "Type", "Semester", "Guide", "Co-Guide", "Course", "Students"],
    ]
    for row in rows[:500]:
        p = project_row_to_dict(row)
        data.append(
            [
                p.get("program_specialization") or "-",
                p.get("project_title") or "-",
                p.get("project_type") or "-",
                p.get("semesters") or "-",
                p.get("guide_name") or "-",
                p.get("co_guide") or "-",
                p.get("course_code") or "-",
                p.get("student_names") or "-",
            ]
        )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 8)]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buf.getvalue()
