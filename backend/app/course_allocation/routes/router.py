from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.course_allocation.services.allocation_service import (
    course_history,
    courses_dashboard_summary,
    create_allocation,
    dashboard_summary,
    delete_allocation,
    faculty_history,
    get_allocation,
    list_allocations_view,
    list_catalog,
    list_courses_view,
    resolve_allocation_faculty_row,
    update_allocation,
    update_catalog_entry,
)
from app.course_allocation.services.csv_sync import sync_all_course_allocation_csv, write_allocations_csv
from app.course_allocation.services.export_service import export_allocations_xlsx, export_courses_xlsx
from app.course_allocation.services.semester_service import effective_current_semester
from app.course_allocation.services.xlsx_upload_service import parse_allocation_xlsx, preview_upload
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/course-allocation", tags=["course-allocation"])


class ResolveFacultyRequest(BaseModel):
    faculty_id: int


@router.get("/current-semester")
def current_semester(_: Annotated[User, Depends(get_current_user)]):
    return {"semester": effective_current_semester()}


@router.get("/dashboard-summary")
def summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    semester: str | None = None,
):
    sem = semester or effective_current_semester()
    return dashboard_summary(db, sem)


@router.get("")
def list_view(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    scope: str | None = None,
    query: str | None = None,
    ug_pg: str | None = None,
    core_elective: str | None = None,
    first_year_only: bool = False,
):
    try:
        sync_all_course_allocation_csv(db)
    except Exception:
        pass
    if not scope:
        scope = effective_current_semester()
    return list_allocations_view(
        db,
        scope=scope,
        query=query,
        ug_pg=ug_pg,
        core_elective=core_elective,
        first_year_only=first_year_only,
    )


@router.get("/export")
def export_view(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    scope: str | None = None,
    query: str | None = None,
    ug_pg: str | None = None,
    core_elective: str | None = None,
    first_year_only: bool = False,
):
    if not scope:
        scope = effective_current_semester()
    payload = export_allocations_xlsx(
        db,
        scope=scope,
        query=query,
        ug_pg=ug_pg,
        core_elective=core_elective,
        first_year_only=first_year_only,
    )
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=course_allocations.xlsx"},
    )


@router.get("/faculty/{faculty_id}")
def faculty_detail(
    faculty_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    data = faculty_history(db, faculty_id)
    if not data:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return data


@router.get("/courses/dashboard-summary")
def courses_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    semester: str | None = None,
):
    sem = semester or effective_current_semester()
    return courses_dashboard_summary(db, sem)


@router.get("/courses")
def courses_list_view(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    scope: str | None = None,
    query: str | None = None,
    ug_pg: str | None = None,
    core_elective: str | None = None,
    first_year_only: bool = False,
):
    try:
        sync_all_course_allocation_csv(db)
    except Exception:
        pass
    if not scope:
        scope = effective_current_semester()
    return list_courses_view(
        db,
        scope=scope,
        query=query,
        ug_pg=ug_pg,
        core_elective=core_elective,
        first_year_only=first_year_only,
    )


@router.get("/courses/export")
def courses_export_view(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    scope: str | None = None,
    query: str | None = None,
    ug_pg: str | None = None,
    core_elective: str | None = None,
    first_year_only: bool = False,
):
    if not scope:
        scope = effective_current_semester()
    payload = export_courses_xlsx(
        db,
        scope=scope,
        query=query,
        ug_pg=ug_pg,
        core_elective=core_elective,
        first_year_only=first_year_only,
    )
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=course_wise_allocations.xlsx"},
    )


@router.get("/courses/{course_catalog_id}")
def course_detail(
    course_catalog_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    data = course_history(db, course_catalog_id)
    if not data:
        raise HTTPException(status_code=404, detail="Course not found")
    return data


@router.get("/catalog")
def catalog_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    try:
        sync_all_course_allocation_csv(db)
    except Exception:
        pass
    entries = list_catalog(db)
    return {
        "items": [
            {
                "id": e.id,
                "course_code": e.course_code,
                "course_name": e.course_name,
                "ug_pg": e.ug_pg,
                "core_elective": e.core_elective,
                "is_first_year": e.is_first_year,
            }
            for e in entries
        ]
    }


@router.put("/catalog/{entry_id}")
def catalog_edit(
    entry_id: int,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.course_allocation.models.entities import CourseCatalogEntry

    entry = db.get(CourseCatalogEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    try:
        row = update_catalog_entry(db, entry, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": row.id,
        "course_code": row.course_code,
        "course_name": row.course_name,
        "ug_pg": row.ug_pg,
        "core_elective": row.core_elective,
        "is_first_year": row.is_first_year,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def add_allocation(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        row = create_allocation(db, body)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row.id}


@router.put("/{row_id}")
def edit_allocation(
    row_id: int,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_allocation(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Allocation not found")
    try:
        row = update_allocation(db, row, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row.id}


@router.post("/{row_id}/resolve-faculty")
def resolve_faculty(
    row_id: int,
    body: ResolveFacultyRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        row = resolve_allocation_faculty_row(db, row_id, body.faculty_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row.id, "faculty_id": row.faculty_id}


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_allocation(
    row_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_allocation(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Allocation not found")
    delete_allocation(db, row)


@router.post("/upload/preview")
async def upload_preview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed")
    payload = await file.read()
    tmp = Path(tempfile.gettempdir()) / f"alloc_{uuid.uuid4().hex}.xlsx"
    tmp.write_bytes(payload)
    try:
        sync_all_course_allocation_csv(db)
    except Exception:
        pass
    try:
        return preview_upload(tmp, db)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_commit(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed")
    payload = await file.read()
    tmp = Path(tempfile.gettempdir()) / f"alloc_{uuid.uuid4().hex}.xlsx"
    tmp.write_bytes(payload)
    try:
        parsed = parse_allocation_xlsx(tmp)
        created = 0
        for row_data in parsed:
            create_allocation(db, row_data)
            created += 1
        return {"created": created}
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
