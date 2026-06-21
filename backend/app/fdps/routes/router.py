from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.fdps.models.entities import FacultyFdp
from app.fdps.services.export_service import export_fdps_xlsx
from app.fdps.services.fdp_service import (
    create_fdp,
    delete_fdp,
    get_fdp,
    list_distinct_exact_years,
    list_distinct_years,
    list_faculty_with_fdps,
    list_fdps_filtered,
    update_fdp,
)
from app.utils.faculty_csv_sync import sync_faculty_fdps_csv

router = APIRouter(prefix="/fdps", tags=["fdps"])


class FdpResponse(BaseModel):
    id: int
    faculty_name: str
    year: str
    exact_year: int | None = None
    program: str
    description: str
    no_of_days: int | None = None
    no_of_attendees: int | None = None

    @classmethod
    def from_row(cls, row) -> "FdpResponse":
        return cls(
            id=row.id,
            faculty_name=row.faculty_name,
            year=row.year,
            exact_year=row.exact_year,
            program=row.program,
            description=row.description,
            no_of_days=row.no_of_days,
            no_of_attendees=row.no_of_attendees,
        )


class FdpCreateRequest(BaseModel):
    faculty_name: str = Field(min_length=1, max_length=200)
    year: str = Field(min_length=1, max_length=20)
    exact_year: int | None = None
    program: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    no_of_days: int | None = None
    no_of_attendees: int | None = None


class FdpUpdateRequest(FdpCreateRequest):
    pass


class FdpListResponse(BaseModel):
    items: list[FdpResponse]
    years: list[str]
    exact_years: list[int]
    faculty_names: list[str]


@router.get("/export")
def export_fdps(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    exact_year_from: int | None = None,
    exact_year_to: int | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    program_filter: str | None = Query(default=None, description="NPTEL or MOOC — matches program text"),
):
    names = [n.strip() for n in (faculty_names or "").split(",") if n.strip()] or None
    payload = export_fdps_xlsx(
        db,
        query=query,
        year=year,
        exact_year=exact_year,
        exact_year_from=exact_year_from,
        exact_year_to=exact_year_to,
        year_from=year_from,
        year_to=year_to,
        faculty_names=names,
        program_filter=program_filter,
    )
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=faculty_fdps.xlsx"},
    )


@router.get("", response_model=FdpListResponse)
def list_all_fdps(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    program_filter: str | None = Query(default=None, description="NPTEL or MOOC — matches program text"),
):
    try:
        sync_faculty_fdps_csv(db)
    except Exception:
        pass
    items = list_fdps_filtered(
        db,
        query=query,
        year=year,
        exact_year=exact_year,
        program_filter=program_filter,
    )
    return FdpListResponse(
        items=[FdpResponse.from_row(a) for a in items],
        years=list_distinct_years(db),
        exact_years=list_distinct_exact_years(db),
        faculty_names=list_faculty_with_fdps(db),
    )


@router.post("", response_model=FdpResponse, status_code=status.HTTP_201_CREATED)
def add_fdp(
    body: FdpCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        row = create_fdp(
            db,
            body.faculty_name,
            body.year,
            body.program,
            body.description,
            exact_year=body.exact_year,
            no_of_days=body.no_of_days,
            no_of_attendees=body.no_of_attendees,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FdpResponse.from_row(row)


@router.put("/{fdp_id}", response_model=FdpResponse)
def edit_fdp(
    fdp_id: int,
    body: FdpUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_fdp(db, fdp_id)
    if not row:
        raise HTTPException(status_code=404, detail="FDP not found")
    try:
        row = update_fdp(
            db,
            row,
            body.faculty_name,
            body.year,
            body.program,
            body.description,
            exact_year=body.exact_year,
            no_of_days=body.no_of_days,
            no_of_attendees=body.no_of_attendees,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FdpResponse.from_row(row)


@router.delete("/{fdp_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_fdp(
    fdp_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_fdp(db, fdp_id)
    if not row:
        raise HTTPException(status_code=404, detail="FDP not found")
    delete_fdp(db, row)
