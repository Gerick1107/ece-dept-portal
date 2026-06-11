"""Workflow A: end-of-semester single consolidated Excel upload."""

import os
from typing import Any

from sqlalchemy.orm import Session

from app.copo import repository as copo_repo
from app.copo.download_tokens import issue_download_token
from app.copo.services import evaluation_service
from app.copo.services.file_manager import (
    allowed_file,
    remove_file_if_exists,
    result_filename,
    save_upload,
)
from app.copo.services.parse_scope import build_sanitized_parse_metadata
from app.copo.services.student_parser import build_included_rolls, parse_student_rolls, summarize_scope_selection


async def submit_final_consolidated(
    db: Session,
    user_id: int,
    course_title: str,
    course_file,
    mapping_path: str,
    mapping_filename: str,
    programmes: list[str],
    branches: list[str],
    indirect_attainment: dict[str, float],
    target_value: int = 50,
    semester_label: str | None = None,
    section_label: str | None = None,
    remove_marks_after: bool = False,
    skip_database_save: bool = False,
    preview_upload_id: int | None = None,
) -> dict[str, Any]:
    if not allowed_file(course_file.filename):
        raise ValueError("Invalid file. Only .xlsx consolidated marks files are accepted.")

    path = await save_upload(course_file, "final_consolidated", course_title=course_title)
    parse_preview = parse_student_rolls(path)
    upload = None
    run = None

    if not skip_database_save:
        upload = copo_repo.create_marks_upload(
            db,
            user_id,
            course_file.filename or "course.xlsx",
            path,
            parse_metadata=build_sanitized_parse_metadata(parse_preview),
            course_title=course_title,
            upload_type="final_consolidated",
        )

    included_rolls = build_included_rolls(path, programmes, branches)
    scope = summarize_scope_selection(programmes, branches)

    if not skip_database_save:
        run = copo_repo.create_evaluation_run(
            db,
            user_id,
            course_title,
            evaluation_type="final_consolidated",
            marks_upload_id=upload.id if upload else None,
            mapping_filename=mapping_filename,
            scope_summary=scope,
            semester_label=semester_label,
            section_label=section_label,
            target_value=target_value,
        )

    try:
        payload = evaluation_service.prepare_results_payload(
            path,
            mapping_path,
            course_title,
            included_rolls=included_rolls,
            indirect_attainment=indirect_attainment,
            course_filename=course_file.filename or "course.xlsx",
            mapping_filename=mapping_filename,
            target_value=target_value,
        )
        download_token = None
        excel_path = payload.get("excel_path")
        if excel_path and os.path.exists(excel_path):
            download_token = issue_download_token(excel_path)

        if run:
            copo_repo.complete_evaluation_run(
                db,
                run,
                result_summary={
                    "course_title": payload["course_title"],
                    "course_filename": payload.get("course_filename"),
                    "mapping_filename": mapping_filename,
                    "scope_summary": scope,
                    "semester_label": semester_label,
                    "section_label": section_label,
                    "target_value": target_value,
                    "unique_COs": payload["unique_COs"],
                    "intermediate": payload["intermediate"],
                    "co_warnings": payload.get("co_warnings", []),
                },
                excel_path=excel_path,
            )

        public_id = run.public_id if run else ""
        data_deleted = False

        if remove_marks_after:
            from app.copo.services.cleanup_service import (
                delete_evaluation_sensitive_data,
                hard_delete_upload,
            )

            if run:
                delete_evaluation_sensitive_data(
                    db,
                    run,
                    full_delete=True,
                    delete_excel_report=False,
                )
                data_deleted = True
            else:
                remove_file_if_exists(path)
                remove_file_if_exists(excel_path)
                data_deleted = True
            if preview_upload_id:
                preview = copo_repo.get_marks_upload(db, preview_upload_id, user_id)
                hard_delete_upload(db, preview)
                db.commit()
        elif preview_upload_id:
            from app.copo.services.cleanup_service import hard_delete_upload

            preview = copo_repo.get_marks_upload(db, preview_upload_id, user_id)
            if preview:
                hard_delete_upload(db, preview)
                db.commit()

        return {
            "public_id": public_id,
            "data_deleted": data_deleted,
            "ephemeral": skip_database_save,
            "course_title": payload["course_title"],
            "course_filename": payload.get("course_filename"),
            "mapping_filename": mapping_filename,
            "unique_COs": payload["unique_COs"],
            "intermediate": payload["intermediate"],
            "co_warnings": payload.get("co_warnings", []),
            "download_token": download_token,
            "download_filename": payload.get("download_filename") or result_filename(course_title),
            "parse_preview": parse_preview,
            "scope_summary": scope,
            "marks_cleared": bool(remove_marks_after),
        }
    except Exception as exc:
        if run:
            copo_repo.fail_evaluation_run(db, run, str(exc))
        else:
            remove_file_if_exists(path)
        raise
