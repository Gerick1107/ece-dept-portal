from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database.models.user import User, UserRole
from app.notifications.models.entities import Notification, NotificationAttachment, NotificationRecipient
from app.utils.email_service import send_email

NOTIFICATIONS_DIR = Path(get_settings().upload_dir).parent / "notifications"


def ensure_notifications_dir() -> Path:
    NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    return NOTIFICATIONS_DIR


async def save_attachments(notification_id: int, files: list[UploadFile]) -> list[NotificationAttachment]:
    ensure_notifications_dir()
    saved: list[NotificationAttachment] = []
    for upload in files:
        if not upload.filename:
            continue
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in upload.filename)
        dest = NOTIFICATIONS_DIR / f"n{notification_id}_{uuid.uuid4().hex[:8]}_{safe}"
        content = await upload.read()
        dest.write_bytes(content)
        saved.append(
            NotificationAttachment(
                notification_id=notification_id,
                original_filename=upload.filename,
                storage_path=str(dest.resolve()),
                mime_type=upload.content_type,
                file_size=len(content),
            )
        )
    return saved


def _recipient_users(db: Session, user_ids: list[int] | None) -> list[User]:
    if user_ids:
        return list(
            db.scalars(
                select(User).where(
                    User.id.in_(user_ids),
                    User.is_active.is_(True),
                    User.role.in_([UserRole.faculty, UserRole.hod]),
                )
            ).all()
        )
    return list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.role.in_([UserRole.faculty, UserRole.hod]),
            )
        ).all()
    )


async def create_and_send_notification(
    db: Session,
    *,
    admin_user_id: int,
    title: str,
    message: str,
    recipient_user_ids: list[int] | None,
    attachment_files: list[UploadFile] | None = None,
) -> Notification:
    notification = Notification(
        created_by_user_id=admin_user_id,
        title=title.strip(),
        message=message.strip(),
    )
    db.add(notification)
    db.flush()

    saved_atts = await save_attachments(notification.id, attachment_files or [])
    for att in saved_atts:
        db.add(att)
    db.flush()

    users = _recipient_users(db, recipient_user_ids)
    recipient_rows: list[tuple[NotificationRecipient, User]] = []
    for user in users:
        recipient = NotificationRecipient(notification_id=notification.id, user_id=user.id)
        db.add(recipient)
        recipient_rows.append((recipient, user))
    db.flush()

    settings = get_settings()
    for recipient, user in recipient_rows:
        if not user:
            recipient.email_status = "skipped"
            continue
        if not settings.smtp_enabled:
            recipient.email_status = "skipped"
            recipient.email_error = "SMTP disabled"
            continue
        body_html = f"<p>{message.replace(chr(10), '<br>')}</p>"
        if saved_atts:
            body_html += "<p><em>Attachments are available in the portal.</em></p>"
        ok = send_email(
            user.email,
            f"[ECE Portal] {title}",
            message,
            body_html,
        )
        recipient.email_status = "sent" if ok else "failed"
        if not ok:
            recipient.email_error = "SMTP send failed"

    db.commit()
    db.refresh(notification)
    return notification


def list_user_notifications(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(
        select(NotificationRecipient)
        .where(NotificationRecipient.user_id == user_id)
        .options(
            joinedload(NotificationRecipient.notification).joinedload(Notification.attachments)
        )
        .order_by(NotificationRecipient.created_at.desc())
    ).unique().all()

    out: list[dict] = []
    for rec in rows:
        n = rec.notification
        out.append(
            {
                "id": rec.id,
                "notification_id": n.id,
                "title": n.title,
                "message": n.message,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "is_read": rec.read_at is not None,
                "read_at": rec.read_at.isoformat() if rec.read_at else None,
                "attachments": [
                    {
                        "id": a.id,
                        "filename": a.original_filename,
                        "mime_type": a.mime_type,
                        "file_size": a.file_size,
                    }
                    for a in n.attachments
                ],
            }
        )
    return out


def unread_count(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(NotificationRecipient)
            .where(NotificationRecipient.user_id == user_id, NotificationRecipient.read_at.is_(None))
        )
        or 0
    )


def mark_read(db: Session, user_id: int, recipient_id: int) -> bool:
    rec = db.scalar(
        select(NotificationRecipient).where(
            NotificationRecipient.id == recipient_id,
            NotificationRecipient.user_id == user_id,
        )
    )
    if not rec:
        return False
    if rec.read_at is None:
        rec.read_at = datetime.now(timezone.utc)
        db.commit()
    return True


def mark_all_read(db: Session, user_id: int) -> int:
    rows = list(
        db.scalars(
            select(NotificationRecipient).where(
                NotificationRecipient.user_id == user_id,
                NotificationRecipient.read_at.is_(None),
            )
        ).all()
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        row.read_at = now
    db.commit()
    return len(rows)


def get_attachment_for_user(db: Session, user_id: int, attachment_id: int) -> NotificationAttachment | None:
    att = db.get(NotificationAttachment, attachment_id)
    if not att:
        return None
    rec = db.scalar(
        select(NotificationRecipient).where(
            NotificationRecipient.notification_id == att.notification_id,
            NotificationRecipient.user_id == user_id,
        )
    )
    if not rec:
        return None
    if not att.storage_path or not os.path.exists(att.storage_path):
        return None
    return att


def list_admin_notifications(db: Session) -> list[dict]:
    notifications = db.scalars(
        select(Notification).options(joinedload(Notification.recipients)).order_by(Notification.created_at.desc())
    ).unique().all()
    out = []
    for n in notifications:
        total = len(n.recipients)
        read = sum(1 for r in n.recipients if r.read_at)
        emailed = sum(1 for r in n.recipients if r.email_status == "sent")
        failed = sum(1 for r in n.recipients if r.email_status == "failed")
        out.append(
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "recipient_count": total,
                "read_count": read,
                "email_sent_count": emailed,
                "email_failed_count": failed,
            }
        )
    return out


def get_admin_notification_detail(db: Session, notification_id: int) -> dict | None:
    n = db.scalar(
        select(Notification)
        .where(Notification.id == notification_id)
        .options(joinedload(Notification.recipients), joinedload(Notification.attachments))
    )
    if not n:
        return None
    user_map = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_([r.user_id for r in n.recipients]))).all()
    }
    return {
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "attachments": [
            {"id": a.id, "filename": a.original_filename, "mime_type": a.mime_type, "file_size": a.file_size}
            for a in n.attachments
        ],
        "recipients": [
            {
                "user_id": r.user_id,
                "name": user_map.get(r.user_id).full_name if user_map.get(r.user_id) else "—",
                "email": user_map.get(r.user_id).email if user_map.get(r.user_id) else "—",
                "read_at": r.read_at.isoformat() if r.read_at else None,
                "email_status": r.email_status,
                "email_error": r.email_error,
            }
            for r in n.recipients
        ],
    }
