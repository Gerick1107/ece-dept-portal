from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.models.user import User, UserRole
from app.feedback.models.entities import FacultyFeedback
from app.utils.email_service import send_email

settings = get_settings()


def create_feedback(db: Session, *, user: User, message: str) -> FacultyFeedback:
    row = FacultyFeedback(user_id=user.id, message=message.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    _notify_admins_and_hod(db, user, row)
    return row


def list_feedback_for_user(db: Session, user_id: int) -> list[FacultyFeedback]:
    return list(
        db.scalars(
            select(FacultyFeedback)
            .where(FacultyFeedback.user_id == user_id)
            .order_by(FacultyFeedback.created_at.desc())
        ).all()
    )


def list_all_feedback(db: Session) -> list[tuple[FacultyFeedback, User]]:
    rows = list(
        db.scalars(select(FacultyFeedback).order_by(FacultyFeedback.created_at.desc())).all()
    )
    users = {u.id: u for u in db.scalars(select(User)).all()}
    return [(r, users[r.user_id]) for r in rows if r.user_id in users]


def set_feedback_resolved(
    db: Session, *, feedback_id: int, actor: User, resolved: bool
) -> FacultyFeedback | None:
    row = db.get(FacultyFeedback, feedback_id)
    if not row:
        return None
    row.is_resolved = resolved
    row.resolved_at = datetime.now(timezone.utc) if resolved else None
    row.resolved_by_user_id = actor.id if resolved else None
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def _notify_admins_and_hod(db: Session, faculty: User, row: FacultyFeedback) -> None:
    recipients = list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.profile_removed.is_(False),
                User.role.in_([UserRole.admin, UserRole.hod]),
            )
        ).all()
    )
    portal = settings.portal_frontend_url.rstrip("/")
    subject = "ECE Department Smart Portal — New faculty feedback"
    body = (
        f"Faculty {faculty.full_name} ({faculty.email}) left feedback on the portal.\n\n"
        f"Submitted: {row.created_at}\n\n"
        f"Please review it under Feedback: {portal}/feedback\n"
    )
    for user in recipients:
        if user.id == faculty.id:
            continue
        send_email(user.email, subject, body)
