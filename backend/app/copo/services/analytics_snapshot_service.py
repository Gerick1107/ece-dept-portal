"""Preserve CO-PO run summaries for long-term analysis."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.copo import CopoEvaluationRun
from app.database.models.copo_analytics import CopoRunAnalyticsSnapshot


def upsert_run_analytics_snapshot(db: Session, run: CopoEvaluationRun) -> None:
    if not run.result_summary and not run.scope_summary:
        return
    existing = db.scalar(
        select(CopoRunAnalyticsSnapshot).where(CopoRunAnalyticsSnapshot.public_id == run.public_id)
    )
    if existing:
        existing.user_id = run.user_id
        existing.course_title = run.course_title
        existing.evaluation_type = run.evaluation_type
        existing.scope_summary = run.scope_summary
        existing.semester_label = run.semester_label or (run.result_summary or {}).get("semester_label")
        existing.result_summary = run.result_summary
        existing.run_created_at = run.created_at
    else:
        db.add(
            CopoRunAnalyticsSnapshot(
                public_id=run.public_id,
                user_id=run.user_id,
                course_title=run.course_title,
                evaluation_type=run.evaluation_type,
                scope_summary=run.scope_summary,
                semester_label=run.semester_label or (run.result_summary or {}).get("semester_label"),
                result_summary=run.result_summary,
                run_created_at=run.created_at,
            )
        )
    db.flush()


def preserve_all_run_snapshots(db: Session) -> int:
    runs = db.query(CopoEvaluationRun).all()
    count = 0
    for run in runs:
        if run.result_summary or run.scope_summary:
            upsert_run_analytics_snapshot(db, run)
            count += 1
    db.commit()
    return count
