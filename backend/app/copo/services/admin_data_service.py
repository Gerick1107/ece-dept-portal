"""Admin views and destructive cleanup for CO-PO persisted data."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.copo import repository as copo_repo
from app.copo.services.cleanup_service import (
    delete_admin_evaluation_run,
    delete_evaluation_sensitive_data,
    hard_delete_upload,
    purge_all_copo_data,
)
from app.copo.services.file_manager import remove_file_if_exists
from app.database.models.copo import CopoEvaluationRun, CopoMarksUpload, CopoResultArchive


def list_admin_overview(db: Session) -> dict:
    runs = (
        db.query(CopoEvaluationRun)
        .order_by(CopoEvaluationRun.created_at.desc())
        .limit(200)
        .all()
    )
    uploads = (
        db.query(CopoMarksUpload)
        .order_by(CopoMarksUpload.created_at.desc())
        .limit(200)
        .all()
    )
    archives = (
        db.query(CopoResultArchive)
        .order_by(CopoResultArchive.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "runs": [
            {
                "public_id": r.public_id,
                "user_id": r.user_id,
                "course_title": r.course_title,
                "evaluation_type": r.evaluation_type,
                "status": r.status.value,
                "marks_upload_id": r.marks_upload_id,
                "has_excel": bool(r.excel_result_path),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "uploads": [
            {
                "id": u.id,
                "user_id": u.user_id,
                "upload_type": u.upload_type,
                "course_title": u.course_title,
                "original_filename": u.original_filename,
                "status": u.status.value,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in uploads
        ],
        "archives": [
            {
                "id": a.id,
                "evaluation_run_id": a.evaluation_run_id,
                "evaluation_run_public_id": (a.archive_metadata or {}).get(
                    "evaluation_run_public_id"
                ),
                "archive_path": a.archive_path,
                "archive_metadata": a.archive_metadata,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in archives
        ],
    }


def admin_delete_run(db: Session, public_id: str) -> dict:
    run = copo_repo.get_evaluation_by_public_id(db, public_id)
    if not run:
        return {"run_deleted": False, "removed_files": 0}
    return delete_admin_evaluation_run(db, run)


def admin_delete_upload(db: Session, upload_id: int) -> dict:
    upload = copo_repo.get_marks_upload(db, upload_id)
    if not upload:
        return {"deleted": False}
    removed = 1 if hard_delete_upload(db, upload) else 0
    db.commit()
    return {"deleted": True, "removed_files": removed}


def admin_delete_archive(db: Session, archive_id: int) -> dict:
    archive = db.query(CopoResultArchive).filter(CopoResultArchive.id == archive_id).first()
    if not archive:
        return {"deleted": False}
    remove_file_if_exists(archive.archive_path)
    db.delete(archive)
    db.commit()
    return {"deleted": True}


def admin_archive_run(db: Session, public_id: str, user_id: int | None = None) -> dict:
    """Copy result Excel to archives/ and record in copo_result_archives."""
    run = copo_repo.get_evaluation_by_public_id(db, public_id)
    if not run:
        return {"archived": False, "detail": "Run not found"}
    if user_id is not None and run.user_id != user_id:
        return {"archived": False, "detail": "Not allowed"}
    upload = (
        copo_repo.get_marks_upload(db, run.marks_upload_id, run.user_id)
        if run.marks_upload_id
        else None
    )
    archive = copo_repo.archive_and_clear_marks(db, run, upload)
    if not archive:
        return {"archived": False, "detail": "No result file to archive"}
    return {
        "archived": True,
        "archive_id": archive.id,
        "archive_path": archive.archive_path,
    }
