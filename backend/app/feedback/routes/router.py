from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.feedback.services.feedback_service import (
    create_feedback,
    list_all_feedback,
    list_feedback_for_user,
    set_feedback_resolved,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=3, max_length=10000)


class FeedbackResolve(BaseModel):
    is_resolved: bool


def _serialize(row, *, faculty_name: str | None = None, faculty_email: str | None = None) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "faculty_name": faculty_name,
        "faculty_email": faculty_email,
        "message": row.message,
        "is_resolved": row.is_resolved,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
def list_feedback(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role == UserRole.admin:
        items = [
            _serialize(row, faculty_name=user.full_name, faculty_email=user.email)
            for row, user in list_all_feedback(db)
        ]
    else:
        items = [_serialize(row) for row in list_feedback_for_user(db, current_user.id)]
    return {"items": items}


@router.post("", status_code=201)
def submit_feedback(
    body: FeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Admins manage feedback; they do not submit it here.")
    row = create_feedback(db, user=current_user, message=body.message)
    return _serialize(row)


@router.patch("/{feedback_id}")
def resolve_feedback(
    feedback_id: int,
    body: FeedbackResolve,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = set_feedback_resolved(db, feedback_id=feedback_id, actor=current_user, resolved=body.is_resolved)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return _serialize(row)
