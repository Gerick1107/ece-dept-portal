from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.labs.services.lab_service import (
    create_lab,
    delete_lab,
    get_lab,
    lab_to_dict,
    list_labs,
    summary_stats,
    update_lab,
)
from app.publications.models.entities import Faculty
from sqlalchemy import select

router = APIRouter(prefix="/labs", tags=["labs"])


class LabRequest(BaseModel):
    lab_name: str = Field(min_length=1, max_length=200)
    location: str | None = None
    faculty_id: int
    total_seats: int = Field(ge=0)
    allotted_seats: int = Field(ge=0)
    remarks: str | None = None


@router.get("")
def get_labs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    faculty_id: int | None = None,
    query: str | None = None,
):
    rows = list_labs(db, faculty_id=faculty_id, query=query)
    return {"items": [lab_to_dict(r) for r in rows], "summary": summary_stats(db)}


@router.get("/faculty-options")
def faculty_options(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    rows = db.scalars(
        select(Faculty).where(Faculty.department.ilike("%ECE%")).order_by(Faculty.name.asc())
    ).all()
    return {"faculty": [{"id": f.id, "name": f.name} for f in rows]}


@router.get("/{lab_id}")
def get_lab_detail(
    lab_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = get_lab(db, lab_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab_to_dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_lab(
    body: LabRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.hod))],
):
    try:
        row = create_lab(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return lab_to_dict(row)


@router.put("/{lab_id}")
def edit_lab(
    lab_id: int,
    body: LabRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.hod))],
):
    row = get_lab(db, lab_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    try:
        row = update_lab(db, row, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return lab_to_dict(row)


@router.delete("/{lab_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lab(
    lab_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_lab(db, lab_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lab not found")
    delete_lab(db, row)