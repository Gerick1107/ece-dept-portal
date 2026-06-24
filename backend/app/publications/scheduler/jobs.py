from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.publications.services.gap_fill_service import run_gap_fill_all

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _get_or_create_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def _monthly_sync_job() -> None:
    summary = run_gap_fill_all()
    if summary.failed_faculty:
        logger.warning("Monthly gap-fill failures: %s", summary.failed_faculty)


def _requirement_reminder_job() -> None:
    from app.database.models.user import User
    from app.database.session import SessionLocal
    from app.notifications.models.entities import Notification, NotificationRecipient
    from app.notifications.services.requirement_service import REQUIREMENT_LABELS, advance_reminder, due_reminders
    from app.utils.email_service import send_email

    settings = get_settings()
    db = SessionLocal()
    sent = 0
    try:
        for row in due_reminders(db):
            try:
                user = db.get(User, row.faculty_user_id)
                if not user or not user.is_active:
                    advance_reminder(db, row)
                    continue

                label = REQUIREMENT_LABELS.get(row.requirement_type, row.requirement_type)
                title = f"Reminder: {label}"
                message = (
                    f"Dear {user.full_name},\n\n"
                    f"This is a reminder to complete: {label}.\n\n"
                    f"Please log in to the ECE Portal."
                )
                html = f"<p>{message.replace(chr(10), '<br>')}</p>"

                if settings.smtp_enabled:
                    ok = send_email(user.email, f"[ECE Portal] {title}", message, html)
                    if not ok:
                        logger.warning("Requirement reminder email failed for %s", user.email)
                else:
                    # Local/dev fallback: portal notification when SMTP is not configured.
                    notification = Notification(
                        title=title,
                        message=message,
                        created_by_user_id=None,
                    )
                    db.add(notification)
                    db.flush()
                    recipient = NotificationRecipient(
                        notification_id=notification.id,
                        user_id=user.id,
                        email_status="skipped",
                        email_error="SMTP disabled — portal reminder only",
                    )
                    db.add(recipient)
                    db.flush()

                advance_reminder(db, row)
                sent += 1
            except Exception:
                logger.exception("Requirement reminder failed for faculty_requirement id=%s", row.id)
                db.rollback()
    finally:
        db.close()

    if sent:
        logger.info("Processed %d requirement reminder(s)", sent)


def ensure_requirement_reminder_scheduler_started() -> BackgroundScheduler | None:
    settings = get_settings()
    if not settings.enable_requirement_reminders:
        return None

    scheduler = _get_or_create_scheduler()
    poll_minutes = max(1, settings.requirement_reminder_poll_minutes)
    scheduler.add_job(
        _requirement_reminder_job,
        trigger="interval",
        minutes=poll_minutes,
        id="requirement_reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("Requirement reminder scheduler active (poll every %s minute(s))", poll_minutes)
    return scheduler


def ensure_scheduler_started() -> BackgroundScheduler | None:
    settings = get_settings()
    if not settings.enable_scheduler:
        return None

    scheduler = _get_or_create_scheduler()
    scheduler.add_job(
        _monthly_sync_job,
        trigger="cron",
        day=1,
        hour=2,
        minute=0,
        id="publications_monthly_sync",
        replace_existing=True,
    )
    return scheduler


def scheduler_status() -> dict:
    if not _scheduler:
        return {"running": False, "jobs": []}
    settings = get_settings()
    return {
        "running": _scheduler.running,
        "jobs": [job.id for job in _scheduler.get_jobs()],
        "requirement_reminders_enabled": settings.enable_requirement_reminders,
        "requirement_reminder_poll_minutes": settings.requirement_reminder_poll_minutes,
    }
