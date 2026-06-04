from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.awards.services.award_service import (
    create_award,
    delete_award,
    get_award,
    list_awards,
    list_distinct_years,
    list_faculty_with_awards,
    update_award,
)
from app.awards.services.export_service import export_awards_xlsx
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/awards", tags=["awards"])


class AwardResponse(BaseModel):
    id: int
    faculty_name: str
    year: str
    award: str

    model_config = {"from_attributes": True}


class AwardCreateRequest(BaseModel):
    faculty_name: str = Field(min_length=1, max_length=200)
    year: str = Field(min_length=1, max_length=20)
    award: str = Field(min_length=1)


class AwardUpdateRequest(AwardCreateRequest):
    pass


class AwardListResponse(BaseModel):
    items: list[AwardResponse]
    years: list[str]
    faculty_names: list[str]


@router.get("/export")
def export_awards(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    year: str | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    faculty_names: str | None = Query(
        default=None,
        description="Comma-separated faculty names to include",
    ),
):
    names = [n.strip() for n in (faculty_names or "").split(",") if n.strip()] or None
    payload = export_awards_xlsx(
        db,
        query=query,
        year=year,
        year_from=year_from,
        year_to=year_to,
        faculty_names=names,
    )
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=faculty_awards.xlsx"},
    )


@router.get("", response_model=AwardListResponse)
def list_all_awards(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    year: str | None = None,
):
    items = list_awards(db, query=query, year=year)
    return AwardListResponse(
        items=[AwardResponse.model_validate(a) for a in items],
        years=list_distinct_years(db),
        faculty_names=list_faculty_with_awards(db),
    )


@router.post("", response_model=AwardResponse, status_code=status.HTTP_201_CREATED)
def add_award(
    body: AwardCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        row = create_award(db, body.faculty_name, body.year, body.award)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AwardResponse.model_validate(row)


@router.put("/{award_id}", response_model=AwardResponse)
def edit_award(
    award_id: int,
    body: AwardUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_award(db, award_id)
    if not row:
        raise HTTPException(status_code=404, detail="Award not found")
    try:
        row = update_award(db, row, body.faculty_name, body.year, body.award)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AwardResponse.model_validate(row)


@router.delete("/{award_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_award(
    award_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_award(db, award_id)
    if not row:
        raise HTTPException(status_code=404, detail="Award not found")
    delete_award(db, row)
