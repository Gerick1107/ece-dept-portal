from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.publications.services.gap_fill_service import run_gap_fill_all

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _monthly_sync_job() -> None:
    summary = run_gap_fill_all()
    if summary.failed_faculty:
        logger.warning("Monthly gap-fill failures: %s", summary.failed_faculty)


def ensure_scheduler_started() -> BackgroundScheduler | None:
    global _scheduler
    settings = get_settings()
    if not settings.enable_scheduler:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _monthly_sync_job,
        trigger="cron",
        day=1,
        hour=2,
        minute=0,
        id="publications_monthly_sync",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def scheduler_status() -> dict:
    if not _scheduler:
        return {"running": False, "jobs": []}
    return {
        "running": _scheduler.running,
        "jobs": [job.id for job in _scheduler.get_jobs()],
    }
