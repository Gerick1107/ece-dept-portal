from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.contributions.models.entities import CONTRIBUTION_MODELS
from app.contributions.services.contribution_service import (
    create_contribution,
    delete_contribution,
    get_contribution,
    list_contributions,
    list_distinct_exact_years,
    list_distinct_extra_values,
    list_distinct_years,
    list_faculty_with_records,
    resolve_faculty_for_row,
    update_contribution,
)
from app.contributions.services.export_service import export_contributions_xlsx
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.utils.contribution_faculty_resolver import resolve_faculty_id_required
from app.utils.faculty_csv_sync import sync_contribution_csv, write_contribution_csv

router = APIRouter(prefix="/contributions", tags=["contributions"])

VALID_RESOURCES = set(CONTRIBUTION_MODELS.keys())


def _check_resource(resource: str) -> str:
    if resource not in VALID_RESOURCES:
        raise HTTPException(status_code=404, detail="Unknown contribution resource")
    return resource


class ContributionListResponse(BaseModel):
    items: list[dict[str, Any]]
    years: list[str]
    exact_years: list[int]
    faculty: list[dict[str, Any]]
    extra_filter_values: list[str]
    unmatched_count: int


class ResolveFacultyRequest(BaseModel):
    faculty_id: int


def _row_to_dict(row) -> dict[str, Any]:
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    return data


@router.get("/{resource}/export")
def export_contributions(
    resource: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    exact_year_from: int | None = None,
    exact_year_to: int | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_id: int | None = None,
    extra_filter: str | None = Query(default=None),
):
    resource = _check_resource(resource)
    payload = export_contributions_xlsx(
        db,
        resource,
        query=query,
        year=year,
        exact_year=exact_year,
        exact_year_from=exact_year_from,
        exact_year_to=exact_year_to,
        year_from=year_from,
        year_to=year_to,
        faculty_id=faculty_id,
        extra_filter=extra_filter,
    )
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={resource}.xlsx"},
    )


@router.get("/{resource}", response_model=ContributionListResponse)
def list_all(
    resource: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    faculty_id: int | None = None,
    extra_filter: str | None = Query(default=None),
    unmatched_only: bool = False,
):
    resource = _check_resource(resource)
    try:
        sync_contribution_csv(db, resource)
    except Exception:
        pass
    items = list_contributions(
        db,
        resource,
        query=query,
        year=year,
        exact_year=exact_year,
        faculty_id=faculty_id,
        extra_filter=extra_filter,
        unmatched_only=unmatched_only,
    )
    unmatched = list_contributions(db, resource, unmatched_only=True)
    return ContributionListResponse(
        items=[_row_to_dict(r) for r in items],
        years=list_distinct_years(db, resource),
        exact_years=list_distinct_exact_years(db, resource),
        faculty=list_faculty_with_records(db, resource),
        extra_filter_values=list_distinct_extra_values(db, resource),
        unmatched_count=len(unmatched),
    )


@router.post("/{resource}", status_code=status.HTTP_201_CREATED)
def add_row(
    resource: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    resource = _check_resource(resource)
    faculty_id = body.get("faculty_id")
    if not faculty_id:
        raise HTTPException(status_code=400, detail="faculty_id is required")
    try:
        faculty = resolve_faculty_id_required(db, int(faculty_id))
        row = create_contribution(
            db,
            resource,
            body,
            faculty_id=faculty.id,
            faculty_name=faculty.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    write_contribution_csv(db, resource)
    return _row_to_dict(row)


@router.put("/{resource}/{row_id}")
def edit_row(
    resource: str,
    row_id: int,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    resource = _check_resource(resource)
    row = get_contribution(db, resource, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    faculty_id = body.get("faculty_id")
    if not faculty_id:
        raise HTTPException(status_code=400, detail="faculty_id is required")
    try:
        faculty = resolve_faculty_id_required(db, int(faculty_id))
        row = update_contribution(
            db,
            resource,
            row,
            body,
            faculty_id=faculty.id,
            faculty_name=faculty.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    write_contribution_csv(db, resource)
    return _row_to_dict(row)


@router.post("/{resource}/{row_id}/resolve-faculty")
def resolve_faculty(
    resource: str,
    row_id: int,
    body: ResolveFacultyRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    resource = _check_resource(resource)
    try:
        row = resolve_faculty_for_row(db, row_id, resource, body.faculty_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _row_to_dict(row)


@router.delete("/{resource}/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_row(
    resource: str,
    row_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    resource = _check_resource(resource)
    row = get_contribution(db, resource, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    delete_contribution(db, row)
    write_contribution_csv(db, resource)
