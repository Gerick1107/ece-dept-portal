from __future__ import annotations

from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.projects.models.entities import Project, ProjectSdg, ProjectUpload
from app.projects.schemas.project import (
    ImportSummary,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    SdgEditRequest,
)
from app.projects.services.admin_data_service import delete_project_upload, list_project_uploads, purge_all_projects
from app.projects.services.export_service import export_projects_csv, export_projects_excel, export_projects_pdf
from app.projects.services.import_service import build_template_bytes, import_projects_file
from app.projects.services.project_service import (
    ProjectSearchFilters,
    confirm_sdgs,
    create_project,
    delete_project,
    edit_confirmed_sdgs,
    get_sdg_catalog,
    project_to_dict,
    reject_sdgs,
    search_projects,
    update_project,
)
from app.projects.services.sdg_queue import enqueue_sdg_tags, sdg_llm_enabled, tag_project_now

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/settings")
def project_module_settings(_: Annotated[User, Depends(get_current_user)]):
    return {"enable_sdg_llm": sdg_llm_enabled()}


def _filters_from_query(
    query: str | None = None,
    faculty_id: int | None = None,
    project_type: str | None = None,
    semester: str | None = None,
    student_name: str | None = None,
    sdg: int | None = None,
    status: str | None = None,
    credit: str | None = None,
    grade: str | None = None,
    confirmed_sdg_only: bool = True,
) -> ProjectSearchFilters:
    return ProjectSearchFilters(
        query=query,
        faculty_id=faculty_id,
        project_type=project_type,
        semester=semester,
        student_name=student_name,
        sdg_number=sdg,
        status=status,
        credit=credit,
        grade=grade,
        confirmed_sdg_only=confirmed_sdg_only,
    )


def _load_project(db: Session, project_id: int) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(
            joinedload(Project.students),
            joinedload(Project.sdg_links).joinedload(ProjectSdg.sdg),
            joinedload(Project.faculty),
        )
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=ProjectListResponse)
@router.get("/search", response_model=ProjectListResponse)
def list_or_search_projects(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    query: str | None = None,
    faculty_id: int | None = None,
    project_type: str | None = None,
    semester: str | None = None,
    student_name: str | None = None,
    sdg: int | None = None,
    status: str | None = None,
    credit: str | None = None,
    grade: str | None = None,
    confirmed_sdg_only: bool = False,
):
    filters = _filters_from_query(
        query, faculty_id, project_type, semester, student_name, sdg, status, credit, grade, confirmed_sdg_only
    )
    rows, total = search_projects(db, filters, page, page_size)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(project_to_dict(db, p)) for p in rows],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/sdgs/catalog")
def sdg_catalog(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    return [
        {"id": s.id, "sdg_number": s.sdg_number, "sdg_name": s.sdg_name, "description": s.description}
        for s in get_sdg_catalog(db)
    ]


@router.get("/template")
def download_import_template(_: Annotated[User, Depends(get_current_user)]):
    payload = build_template_bytes()
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=btp_ip_import_template.xlsx"},
    )


@router.post("/import", response_model=ImportSummary)
async def import_projects(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
    file: UploadFile = File(...),
    auto_sdg: bool = Query(default=True),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, or .xls files are accepted")
    content = await file.read()
    try:
        result = import_projects_file(db, content, file.filename or "upload.xlsx", user.id, auto_sdg=auto_sdg)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportSummary(**result)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def add_project(
    body: ProjectCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        project = create_project(db, body)
        enqueue_sdg_tags([project.id])
        project = _load_project(db, project.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectResponse.model_validate(project_to_dict(db, project))


@router.put("/{project_id}", response_model=ProjectResponse)
def edit_project(
    project_id: int,
    body: ProjectUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    project = _load_project(db, project_id)
    try:
        project = update_project(db, project, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectResponse.model_validate(project_to_dict(db, project))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    project = _load_project(db, project_id)
    delete_project(db, project)


@router.post("/{project_id}/generate-sdgs", response_model=ProjectResponse)
def generate_sdgs(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    _assert_sdg_access()
    project = _load_project(db, project_id)
    try:
        tag_project_now(db, project)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Gemini rate limit reached — wait a minute and try again.",
            ) from exc
        raise HTTPException(status_code=502, detail="SDG service error") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    project = _load_project(db, project_id)
    return ProjectResponse.model_validate(project_to_dict(db, project))


@router.post("/{project_id}/accept-sdgs", response_model=ProjectResponse)
def accept_sdgs(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    _assert_sdg_access()
    project = _load_project(db, project_id)
    project = confirm_sdgs(db, project)
    return ProjectResponse.model_validate(project_to_dict(db, project))


@router.post("/{project_id}/reject-sdgs", response_model=ProjectResponse)
def reject_sdg_suggestions(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    _assert_sdg_access()
    project = _load_project(db, project_id)
    project = reject_sdgs(db, project)
    return ProjectResponse.model_validate(project_to_dict(db, project))


@router.post("/{project_id}/edit-sdgs", response_model=ProjectResponse)
def edit_sdgs(
    project_id: int,
    body: SdgEditRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    _assert_sdg_access()
    project = _load_project(db, project_id)
    try:
        project = edit_confirmed_sdgs(db, project, body.sdg_numbers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectResponse.model_validate(project_to_dict(db, project))


@router.get("/export")
def export_projects(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    format: str = Query(default="xlsx", pattern="^(csv|xlsx|pdf)$"),
    query: str | None = None,
    faculty_id: int | None = None,
    project_type: str | None = None,
    semester: str | None = None,
    student_name: str | None = None,
    sdg: int | None = None,
    status: str | None = None,
    credit: str | None = None,
    grade: str | None = None,
    confirmed_sdg_only: bool = True,
):
    filters = _filters_from_query(
        query, faculty_id, project_type, semester, student_name, sdg, status, credit, grade, confirmed_sdg_only
    )
    if format == "csv":
        payload = export_projects_csv(db, filters)
        return Response(
            content=payload,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=projects.csv"},
        )
    if format == "pdf":
        payload = export_projects_pdf(db, filters)
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=projects.pdf"},
        )
    payload = export_projects_excel(db, filters)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=projects.xlsx"},
    )


@router.get("/admin/uploads")
def admin_list_uploads(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return {"project_uploads": list_project_uploads(db)}


@router.get("/admin/uploads/{upload_id}/download")
def admin_download_upload(
    upload_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = db.get(ProjectUpload, upload_id)
    if not row or not Path(row.filepath).exists():
        raise HTTPException(status_code=404, detail="Upload file not found")
    return FileResponse(row.filepath, filename=row.filename)


@router.post("/admin/purge-all")
def admin_purge_all_projects(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return purge_all_projects(db)


@router.delete("/admin/uploads/{upload_id}")
def admin_delete_upload(
    upload_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    result = delete_project_upload(db, upload_id)
    if not result.get("deleted"):
        raise HTTPException(status_code=404, detail="Upload not found")
    return result


def _assert_sdg_access() -> None:
    """Any authenticated portal user may review SDGs (faculty, HOD, admin)."""
    return
