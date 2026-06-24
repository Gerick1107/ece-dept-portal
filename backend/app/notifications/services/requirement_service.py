from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user import User, UserRole
from app.notifications.models.entities import REQUIREMENT_TYPES, FacultyRequirement

REQUIREMENT_LABELS = {
    "course_upcoming_sem": "Upcoming semester course(s)",
    "yearly_report": "Yearly report",
    "new_awards": "New awards since last asked",
    "new_fdps": "New FDPs since last asked",
    "verify_sdgs": "Verify SDGs (BTP/IP)",
    "copo_attainment": "CO-PO attainment (prev. semester)",
}


def upsert_requirement_on_send(
    db: Session,
    *,
    user_id: int,
    requirement_type: str,
    notification_id: int,
    reminder_interval_minutes: int | None,
) -> FacultyRequirement:
    now = datetime.now(timezone.utc)
    row = db.scalar(
        select(FacultyRequirement).where(
            FacultyRequirement.faculty_user_id == user_id,
            FacultyRequirement.requirement_type == requirement_type,
        )
    )
    if not row:
        row = FacultyRequirement(faculty_user_id=user_id, requirement_type=requirement_type)
        db.add(row)
    row.status = "red"
    row.requested_at = now
    row.read_at = None
    row.fulfilled_at = None
    row.source_notification_id = notification_id
    if reminder_interval_minutes and reminder_interval_minutes > 0:
        row.reminder_enabled = True
        row.reminder_interval_minutes = reminder_interval_minutes
        row.next_reminder_at = now + timedelta(minutes=reminder_interval_minutes)
    else:
        row.reminder_enabled = False
        row.reminder_interval_minutes = None
        row.next_reminder_at = None
    row.updated_at = now
    return row


def mark_requirement_read(db: Session, user_id: int, requirement_type: str) -> None:
    row = db.scalar(
        select(FacultyRequirement).where(
            FacultyRequirement.faculty_user_id == user_id,
            FacultyRequirement.requirement_type == requirement_type,
        )
    )
    if not row or row.status != "red":
        return
    now = datetime.now(timezone.utc)
    row.status = "yellow"
    row.read_at = now
    row.updated_at = now


def mark_requirement_fulfilled(db: Session, user_id: int, requirement_type: str) -> None:
    row = db.scalar(
        select(FacultyRequirement).where(
            FacultyRequirement.faculty_user_id == user_id,
            FacultyRequirement.requirement_type == requirement_type,
        )
    )
    if not row:
        return
    now = datetime.now(timezone.utc)
    row.status = "green"
    row.fulfilled_at = now
    row.reminder_enabled = False
    row.next_reminder_at = None
    row.updated_at = now


def set_requirement_status(db: Session, user_id: int, requirement_type: str, status: str) -> FacultyRequirement | None:
    if status not in ("grey", "red", "yellow", "green"):
        raise ValueError("Invalid status")
    row = db.scalar(
        select(FacultyRequirement).where(
            FacultyRequirement.faculty_user_id == user_id,
            FacultyRequirement.requirement_type == requirement_type,
        )
    )
    now = datetime.now(timezone.utc)
    if not row:
        row = FacultyRequirement(faculty_user_id=user_id, requirement_type=requirement_type, status=status)
        db.add(row)
    else:
        row.status = status
        row.updated_at = now
        if status == "green":
            row.fulfilled_at = now
            row.reminder_enabled = False
            row.next_reminder_at = None
        elif status == "grey":
            row.reminder_enabled = False
            row.next_reminder_at = None
            row.fulfilled_at = None
    db.commit()
    db.refresh(row)
    return row


def list_requirement_matrix(db: Session) -> list[dict]:
    users = list(
        db.scalars(
            select(User)
            .where(User.is_active.is_(True), User.role.in_([UserRole.faculty, UserRole.hod]))
            .order_by(User.full_name)
        ).all()
    )
    reqs = {
        (r.faculty_user_id, r.requirement_type): r
        for r in db.scalars(select(FacultyRequirement)).all()
    }
    out = []
    for user in users:
        cells = {}
        for rt in REQUIREMENT_TYPES:
            row = reqs.get((user.id, rt))
            cells[rt] = {
                "status": row.status if row else "grey",
                "requested_at": row.requested_at.isoformat() if row and row.requested_at else None,
                "read_at": row.read_at.isoformat() if row and row.read_at else None,
                "fulfilled_at": row.fulfilled_at.isoformat() if row and row.fulfilled_at else None,
                "reminder_enabled": row.reminder_enabled if row else False,
            }
        out.append({"user_id": user.id, "name": user.full_name, "email": user.email, "cells": cells})
    return out


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def due_reminders(db: Session) -> list[FacultyRequirement]:
    now = datetime.now(timezone.utc)
    rows = list(
        db.scalars(
            select(FacultyRequirement).where(
                FacultyRequirement.reminder_enabled.is_(True),
                FacultyRequirement.next_reminder_at.isnot(None),
                FacultyRequirement.status.in_(["red", "yellow"]),
            )
        ).all()
    )
    return [r for r in rows if r.next_reminder_at and _coerce_utc(r.next_reminder_at) <= now]


def advance_reminder(db: Session, row: FacultyRequirement) -> None:
    now = datetime.now(timezone.utc)
    row.last_reminder_sent_at = now
    if row.reminder_interval_minutes:
        row.next_reminder_at = now + timedelta(minutes=row.reminder_interval_minutes)
    row.updated_at = now
    db.commit()
