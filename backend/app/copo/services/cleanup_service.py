"""
Cascade deletion for CO-PO evaluation data.

Privacy: removes uploaded marks workbooks, result Excel files, archives, and DB rows.
See docs/STORAGE.md for folder/archive behaviour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.copo import repository as copo_repo
from app.copo.services.file_manager import remove_file_if_exists
from app.database.models.copo import CopoEvaluationRun, CopoMarksUpload, CopoResultArchive


def hard_delete_upload(db: Session, upload: CopoMarksUpload | None) -> bool:
    """Fully remove an upload row and its file from disk."""
    if not upload:
        return False
    remove_file_if_exists(upload.storage_path)
    db.delete(upload)
    return True


def delete_sibling_marks_uploads(
    db: Session,
    user_id: int,
    course_title: str | None,
    original_filename: str | None,
    exclude_ids: set[int] | None = None,
    *,
    within_hours: int = 24,
) -> int:
    """
    Remove orphan or duplicate marks uploads from the same workflow
    (e.g. parse-students preview row + final-consolidated row).
    """
    exclude_ids = exclude_ids or set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    q = db.query(CopoMarksUpload).filter(CopoMarksUpload.user_id == user_id)
    candidates = q.all()
    removed = 0
    for upload in candidates:
        if upload.id in exclude_ids:
            continue
        if upload.created_at and upload.created_at.replace(tzinfo=timezone.utc) < cutoff:
            continue
        match = False
        if course_title and upload.course_title and upload.course_title.strip() == course_title.strip():
            match = True
        if original_filename and upload.original_filename == original_filename:
            match = True
        if not match:
            continue
        if hard_delete_upload(db, upload):
            removed += 1
    return removed


def clear_marks_upload_sensitive_data(db: Session, upload) -> None:
    """Remove marks file from disk and mark upload cleared; strip parse_metadata."""
    if not upload:
        return
    remove_file_if_exists(upload.storage_path)
    upload.parse_metadata = None
    copo_repo.clear_marks_for_upload(db, upload)


def delete_admin_evaluation_run(db: Session, run: CopoEvaluationRun) -> dict[str, int | bool]:
    """
    Admin delete from Data & Archives: remove the live result file and evaluation run row only.

    Marks uploads and archived report copies are left intact.
    """
    removed_files = 0
    if run.excel_result_path:
        remove_file_if_exists(run.excel_result_path)
        removed_files += 1
        run.excel_result_path = None

    public_id = run.public_id
    linked_archives = (
        db.query(CopoResultArchive)
        .filter(CopoResultArchive.evaluation_run_id == run.id)
        .all()
    )
    for archive in linked_archives:
        meta = dict(archive.archive_metadata or {})
        meta["evaluation_run_public_id"] = public_id
        archive.archive_metadata = meta
        archive.evaluation_run_id = None

    db.flush()
    db.delete(run)
    db.commit()
    return {"removed_files": removed_files, "run_deleted": True}


def delete_evaluation_sensitive_data(
    db: Session,
    run: CopoEvaluationRun,
    *,
    full_delete: bool = False,
    delete_excel_report: bool = False,
) -> dict[str, int | bool]:
    """
    Remove sensitive artifacts for an evaluation run.

    full_delete=True (checkbox after success or manual delete):
      - marks upload file for this run hard-deleted from DB
      - excel result file, archive copies, evaluation run row

    full_delete=False (legacy partial — unused by UI after Week 1 refinements):
      - marks cleared only, run retained
    """
    removed_files = 0
    upload = None
    exclude_ids: set[int] = set()
    if run.marks_upload_id:
        exclude_ids.add(run.marks_upload_id)
        upload = copo_repo.get_marks_upload(db, run.marks_upload_id)

    if upload and (full_delete or upload.status.value != "cleared"):
        if full_delete:
            if hard_delete_upload(db, upload):
                removed_files += 1
        else:
            clear_marks_upload_sensitive_data(db, upload)
            removed_files += 1
            run.marks_cleared_at = run.marks_cleared_at or upload.cleared_at

    if delete_excel_report or full_delete:
        if run.excel_result_path:
            remove_file_if_exists(run.excel_result_path)
            removed_files += 1
            run.excel_result_path = None

    if full_delete:
        for archive in list(run.archives or []):
            remove_file_if_exists(archive.archive_path)
            removed_files += 1
            db.delete(archive)

        upload_id = run.marks_upload_id
        db.delete(run)
        db.flush()
        if upload_id:
            leftover = copo_repo.get_marks_upload(db, upload_id)
            if leftover:
                if hard_delete_upload(db, leftover):
                    removed_files += 1
        db.commit()
        return {"removed_files": removed_files, "run_deleted": True}

    db.commit()
    return {"removed_files": removed_files, "run_deleted": False}


def _sweep_results_directory() -> int:
    """Remove generated result workbooks under storage/results (orphans included)."""
    import logging
    from pathlib import Path

    from app.config import get_settings

    logger = logging.getLogger(__name__)
    results_dir = Path(get_settings().results_dir)
    if not results_dir.exists():
        return 0
    removed = 0
    for child in results_dir.iterdir():
        if not child.is_file():
            continue
        if not child.name.endswith("_CO_PO_Percentage_Results.xlsx"):
            continue
        try:
            child.unlink()
            removed += 1
        except OSError as exc:
            logger.warning("Could not delete result file %s: %s", child, exc)
    return removed


def purge_all_copo_data(db: Session) -> dict[str, int]:
    """Admin-only: remove every CO-PO upload, run, archive, and linked files."""
    from app.copo.services.analytics_snapshot_service import preserve_all_run_snapshots

    snapshots_preserved = preserve_all_run_snapshots(db)
    removed_files = 0
    for archive in db.query(CopoResultArchive).all():
        remove_file_if_exists(archive.archive_path)
        removed_files += 1
        db.delete(archive)
    for run in db.query(CopoEvaluationRun).all():
        if run.excel_result_path:
            remove_file_if_exists(run.excel_result_path)
            removed_files += 1
        db.delete(run)
    for upload in db.query(CopoMarksUpload).all():
        remove_file_if_exists(upload.storage_path)
        removed_files += 1
        db.delete(upload)
    db.commit()
    removed_files += _sweep_results_directory()
    return {
        "removed_files": removed_files,
        "runs_deleted": True,
        "analytics_snapshots_preserved": snapshots_preserved,
    }
