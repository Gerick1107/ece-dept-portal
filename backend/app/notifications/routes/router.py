from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.utils.storage_paths import resolve_storage_path
from app.notifications.services.notification_service import (
    create_and_send_notification,
    get_admin_notification_detail,
    get_attachment_for_user,
    get_reply_attachment_for_admin,
    get_reply_attachment_for_user,
    list_admin_notifications,
    list_user_notifications,
    mark_all_read,
    mark_read,
    submit_notification_reply,
    unread_count,
)
from app.notifications.services.requirement_service import (
    REQUIREMENT_LABELS,
    list_requirement_matrix,
    set_requirement_status,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class RequirementStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=32)


@router.get("/unread-count")
def get_unread_count(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {"count": unread_count(db, current_user.id)}


@router.get("")
def my_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {"items": list_user_notifications(db, current_user.id), "unread_count": unread_count(db, current_user.id)}


@router.post("/{recipient_id}/reply")
async def reply_to_notification(
    recipient_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    message: str = Form(...),
    attachment: UploadFile | None = File(default=None),
):
    try:
        reply = await submit_notification_reply(
            db,
            user_id=current_user.id,
            recipient_id=recipient_id,
            message=message,
            attachment_files=[attachment] if attachment and attachment.filename else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": reply.id,
        "message": reply.message,
        "created_at": reply.created_at.isoformat() if reply.created_at else None,
        "attachment_count": len(reply.attachments),
    }


@router.get("/reply-attachments/{attachment_id}/download")
def download_reply_attachment(
    attachment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    att = get_reply_attachment_for_user(db, current_user.id, attachment_id)
    if not att:
        att = get_reply_attachment_for_admin(db, attachment_id) if current_user.role == UserRole.admin else None
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(
        resolve_storage_path(att.storage_path),
        filename=att.original_filename,
        media_type=att.mime_type or "application/octet-stream",
    )


@router.post("/{recipient_id}/read")
def read_notification(
    recipient_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not mark_read(db, current_user.id, recipient_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"read": True}


@router.post("/read-all")
def read_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {"marked": mark_all_read(db, current_user.id)}


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    att = get_attachment_for_user(db, current_user.id, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(
        resolve_storage_path(att.storage_path),
        filename=att.original_filename,
        media_type=att.mime_type or "application/octet-stream",
    )


@router.get("/admin/list")
def admin_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return {"items": list_admin_notifications(db)}


@router.get("/admin/users")
def admin_recipient_options(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True), User.role.in_([UserRole.faculty, UserRole.hod]))
        .order_by(User.full_name)
    ).all()
    return {
        "users": [{"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role.value} for u in users]
    }


@router.get("/admin/requirements")
def admin_requirements_matrix(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return {"labels": REQUIREMENT_LABELS, "rows": list_requirement_matrix(db)}


@router.put("/admin/requirements/{user_id}/{requirement_type}")
def admin_set_requirement_status(
    user_id: int,
    requirement_type: str,
    body: RequirementStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    try:
        row = set_requirement_status(db, user_id, requirement_type, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": row.status if row else body.status}


@router.post("/admin/send")
async def admin_send(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.admin))],
    title: str = Form(...),
    message: str = Form(...),
    recipient_user_ids: str = Form(""),
    requirement_type: str = Form(""),
    reminder_interval_minutes: int = Form(0),
    attachments: list[UploadFile] = File(default=[]),
):
    ids = [int(x.strip()) for x in recipient_user_ids.split(",") if x.strip().isdigit()] or None
    req_type = requirement_type.strip() or None
    reminder = reminder_interval_minutes if reminder_interval_minutes > 0 else None
    notification = await create_and_send_notification(
        db,
        admin_user_id=current_user.id,
        title=title,
        message=message,
        recipient_user_ids=ids,
        attachment_files=[f for f in (attachments or []) if f.filename],
        requirement_type=req_type,
        reminder_interval_minutes=reminder,
    )
    return {
        "id": notification.id,
        "recipient_count": len(notification.recipients),
        "title": notification.title,
    }


@router.get("/admin/{notification_id}")
def admin_detail(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    detail = get_admin_notification_detail(db, notification_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Notification not found")
    return detail
