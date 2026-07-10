from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import FacultyScope, get_current_user, get_faculty_scope, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.ece_eve_projects.services.ece_eve_service import (
    EceEveProjectFilters,
    export_ece_eve_csv,
    export_ece_eve_excel,
    export_ece_eve_pdf,
    get_ece_eve_analytics,
    list_ece_eve_filter_options,
    project_row_to_dict,
    purge_ece_eve_projects,
    search_ece_eve_projects,
)

router = APIRouter(prefix="/ece-eve-projects", tags=["ece-eve-projects"])


@router.post("/admin/purge-all")
def admin_purge_ece_eve_projects(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return purge_ece_eve_projects(db)


@router.get("")
def list_ece_eve_projects(
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    branch: str | None = Query(default=None, description="ECE, EVE, or omit for both"),
    faculty_id: int | None = None,
    guide_name: str | None = None,
    student_name: str | None = None,
    student_roll_no: str | None = None,
    semesters: str | None = None,
    course_codes: str | None = None,
    course_name: str | None = None,
    co_guide: str | None = None,
    credit: str | None = None,
    year: str | None = None,
    project_type: str | None = None,
    query: str | None = None,
):
    if not scope.see_all:
        faculty_id = scope.faculty_id if scope.faculty_id is not None else -1
    semester_list = [s.strip() for s in (semesters or "").split(",") if s.strip()]
    code_list = [s.strip() for s in (course_codes or "").split(",") if s.strip()]
    filters = EceEveProjectFilters(
        branch=branch,
        year=year,
        project_type=project_type,
        query=query,
        faculty_id=faculty_id,
        guide_name=guide_name,
        student_name=student_name,
        student_roll_no=student_roll_no,
        semesters=semester_list,
        course_codes=code_list,
        course_name=course_name,
        co_guide=co_guide,
        credit=credit,
    )
    rows, total = search_ece_eve_projects(db, filters, page, page_size)
    return {
        "items": [project_row_to_dict(row) for row in rows],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/analytics")
def ece_eve_projects_analytics(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    branch: str | None = Query(default=None, description="ECE, EVE, or omit for both"),
):
    return get_ece_eve_analytics(db, branch=branch)


@router.get("/filters")
def ece_eve_project_filters(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return list_ece_eve_filter_options(db)


@router.get("/export")
def export_ece_eve_projects(
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[FacultyScope, Depends(get_faculty_scope)],
    format: str = Query(default="xlsx", pattern="^(csv|xlsx|pdf)$"),
    branch: str | None = Query(default=None),
    faculty_id: int | None = None,
    guide_name: str | None = None,
    student_name: str | None = None,
    student_roll_no: str | None = None,
    semesters: str | None = None,
    course_codes: str | None = None,
    course_name: str | None = None,
    co_guide: str | None = None,
    credit: str | None = None,
    year: str | None = None,
    project_type: str | None = None,
    query: str | None = None,
):
    if not scope.see_all:
        faculty_id = scope.faculty_id if scope.faculty_id is not None else -1
    filters = EceEveProjectFilters(
        branch=branch,
        year=year,
        project_type=project_type,
        query=query,
        faculty_id=faculty_id,
        guide_name=guide_name,
        student_name=student_name,
        student_roll_no=student_roll_no,
        semesters=[s.strip() for s in (semesters or "").split(",") if s.strip()],
        course_codes=[s.strip() for s in (course_codes or "").split(",") if s.strip()],
        course_name=course_name,
        co_guide=co_guide,
        credit=credit,
    )
    if format == "csv":
        payload = export_ece_eve_csv(db, filters)
        return Response(
            content=payload,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ece_eve_projects.csv"},
        )
    if format == "pdf":
        payload = export_ece_eve_pdf(db, filters)
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ece_eve_projects.pdf"},
        )
    payload = export_ece_eve_excel(db, filters)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ece_eve_projects.xlsx"},
    )
