import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.copo.services.file_manager import archive_result_file, remove_file_if_exists
from app.database.models.copo import (
    CopoEvaluationRun,
    CopoMarksUpload,
    CopoResultArchive,
    EvaluationStatus,
    UploadStatus,
)


def create_percentage_results_upload(
    db: Session,
    user_id: int,
    excel_path: str,
    *,
    course_title: str | None = None,
    source_upload_id: int | None = None,
) -> CopoMarksUpload:
    """Register a compare/bulk generated percentage workbook under uploads/."""
    filename = Path(excel_path).name
    metadata: dict = {"generated_by": "compare_evaluation"}
    if source_upload_id is not None:
        metadata["source_upload_id"] = source_upload_id
    return create_marks_upload(
        db,
        user_id,
        filename,
        excel_path,
        parse_metadata=metadata,
        course_title=course_title,
        upload_type="percentage_results",
    )


def create_marks_upload(
    db: Session,
    user_id: int,
    filename: str,
    storage_path: str,
    parse_metadata: dict | None,
    course_title: str | None = None,
    upload_type: str = "final_consolidated",
) -> CopoMarksUpload:
    record = CopoMarksUpload(
        user_id=user_id,
        upload_type=upload_type,
        course_title=course_title,
        original_filename=filename,
        storage_path=storage_path,
        parse_metadata=parse_metadata,
        status=UploadStatus.uploaded,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_marks_upload(db: Session, upload_id: int, user_id: int | None = None) -> CopoMarksUpload | None:
    q = db.query(CopoMarksUpload).filter(CopoMarksUpload.id == upload_id)
    if user_id is not None:
        q = q.filter(CopoMarksUpload.user_id == user_id)
    return q.first()


def create_evaluation_run(
    db: Session,
    user_id: int,
    course_title: str,
    evaluation_type: str,
    marks_upload_id: int | None = None,
    mapping_filename: str | None = None,
    scope_summary: str | None = None,
    semester_label: str | None = None,
    target_value: int = 50,
) -> CopoEvaluationRun:
    run = CopoEvaluationRun(
        public_id=uuid.uuid4().hex,
        user_id=user_id,
        marks_upload_id=marks_upload_id,
        course_title=course_title,
        evaluation_type=evaluation_type,
        mapping_filename=mapping_filename,
        scope_summary=scope_summary,
        semester_label=semester_label,
        target_value=target_value,
        status=EvaluationStatus.pending,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def complete_evaluation_run(
    db: Session,
    run: CopoEvaluationRun,
    result_summary: dict,
    excel_path: str | None,
    comparison_summary: dict | None = None,
) -> CopoEvaluationRun:
    from app.copo.services.analytics_snapshot_service import upsert_run_analytics_snapshot

    run.status = EvaluationStatus.completed
    run.result_summary = result_summary
    run.comparison_summary = comparison_summary
    run.excel_result_path = excel_path
    if result_summary and result_summary.get("semester_label"):
        run.semester_label = str(result_summary["semester_label"])
    db.commit()
    db.refresh(run)
    upsert_run_analytics_snapshot(db, run)
    db.commit()
    return run


def fail_evaluation_run(db: Session, run: CopoEvaluationRun, error: str) -> None:
    run.status = EvaluationStatus.failed
    run.error_message = error
    db.commit()


def get_evaluation_by_public_id(db: Session, public_id: str) -> CopoEvaluationRun | None:
    return db.query(CopoEvaluationRun).filter(CopoEvaluationRun.public_id == public_id).first()


def clear_marks_for_upload(db: Session, upload: CopoMarksUpload) -> None:
    """Remove marks file from disk; clear path and parse metadata (no roll lists kept)."""
    remove_file_if_exists(upload.storage_path)
    upload.status = UploadStatus.cleared
    upload.cleared_at = datetime.now(timezone.utc)
    upload.storage_path = ""
    upload.parse_metadata = None
    db.commit()


def archive_and_clear_marks(
    db: Session, run: CopoEvaluationRun, upload: CopoMarksUpload | None
) -> CopoResultArchive | None:
    if not run.excel_result_path:
        return None
    archive_path = archive_result_file(
        run.excel_result_path, run.public_id, course_title=run.course_title
    )
    archive = CopoResultArchive(
        evaluation_run_id=run.id,
        archive_path=archive_path,
        archive_metadata={
            "course_title": run.course_title,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "evaluation_run_public_id": run.public_id,
        },
    )
    db.add(archive)
    run.status = EvaluationStatus.archived
    if upload and upload.status != UploadStatus.cleared:
        clear_marks_for_upload(db, upload)
        run.marks_cleared_at = datetime.now(timezone.utc)
    run.excel_result_path = None
    db.commit()
    db.refresh(archive)
    return archive
