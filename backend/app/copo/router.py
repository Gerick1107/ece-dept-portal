import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.config import get_settings, DATA_ASSETS
from app.copo import repository as copo_repo
from app.copo.download_tokens import issue_download_token, pop_download_path
from app.utils.storage_paths import resolve_storage_path
from app.copo.schemas import (
    AdminDataOverviewResponse,
    AdminPurgeResponse,
    BulkEvaluateRequest,
    BulkResultResponse,
    ClearUploadsResponse,
    CompareEvaluateRequest,
    CompareResultResponse,
    CourseCosResponse,
    CourseNamesResponse,
    EvaluateRequest,
    EvaluationResultResponse,
    ComparisonSetup,
    DeleteEvaluationDataResponse,
    MarksTemplateComponentsResponse,
    MarksTemplateGenerateRequest,
    ParseStudentsResponse,
    QuestionPaperAnalyzeResponse,
    QuestionPaperGenerateRequest,
)
from app.copo.services import evaluation_service, mapping_service
from app.copo.services.file_manager import (
    allowed_file,
    cleanup_upload_directory,
    remove_file_if_exists,
    result_filename,
    save_upload,
)
from app.copo.services.mapping_service import resolve_mapping_path
from app.copo.services.student_parser import build_included_rolls, summarize_scope_selection
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/copo", tags=["copo"])
settings = get_settings()


@router.get("/course-names", response_model=CourseNamesResponse)
def get_course_names(db: Annotated[Session, Depends(get_db)]):
    from app.courses.services.course_service import course_display_label, list_courses

    db_courses = list_courses(db)
    if db_courses:
        return CourseNamesResponse(courses=[course_display_label(c) for c in db_courses])

    path = settings.resolved_mapping_path
    if not os.path.exists(path):
        raise HTTPException(
            status_code=500,
            detail=f"CO-PO mapping file not found at {path}. Place mapping Excel in data/assets/ or seed courses.",
        )
    names = mapping_service.extract_course_names(path)
    return CourseNamesResponse(courses=names)


@router.post("/course-names", response_model=CourseNamesResponse)
async def post_course_names(mapping_file: UploadFile = File(...)):
    if not allowed_file(mapping_file.filename):
        raise HTTPException(status_code=400, detail="Invalid mapping file")
    path = await save_upload(mapping_file, "tmp_mapping")
    try:
        names = mapping_service.extract_course_names(path)
    finally:
        remove_file_if_exists(path)
    return CourseNamesResponse(courses=names)


@router.post("/final-submit", response_model=EvaluationResultResponse)
async def final_submit(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    course_title: str = Form(...),
    course_file: UploadFile = File(...),
    use_default_mapping: bool = Form(True),
    mapping_type: str = Form("UG"),
    mapping_file: UploadFile | None = File(None),
    programmes: list[str] = Form(default=[]),
    branches: list[str] = Form(default=[]),
    indirect_attainment_json: str = Form("{}"),
    target_value: int = Form(50),
    remove_marks_after: bool = Form(False),
    skip_database_save: bool = Form(False),
    preview_upload_id: int = Form(0),
    semester_term: str = Form(...),
    semester_year: str = Form(...),
    section_label: str = Form(""),
):
    """
    Faculty: one end-of-semester consolidated Excel → parse → CO/PO → report.
    Replaces separate parse-then-evaluate for the primary faculty path.
    """
    import json

    from app.copo.services.workflow_a import submit_final_consolidated

    indirect_attainment = json.loads(indirect_attainment_json or "{}")
    mapping_path = settings.resolved_mapping_path
    mapping_filename = os.path.basename(mapping_path)
    tmp_mapping = None
    if not use_default_mapping and mapping_file:
        if not allowed_file(mapping_file.filename):
            raise HTTPException(status_code=400, detail="Invalid mapping file")
        tmp_mapping = await save_upload(mapping_file, "custom_mapping")
        mapping_path = tmp_mapping
        mapping_filename = mapping_file.filename or mapping_filename
    elif str(mapping_type).upper() == "PG":
        mapping_path = settings.resolved_pg_mapping_path
        mapping_filename = os.path.basename(mapping_path)

    term = semester_term.strip().capitalize()
    if term not in ("Monsoon", "Winter", "Summer"):
        raise HTTPException(status_code=400, detail="semester_term must be Monsoon, Winter, or Summer")
    year = semester_year.strip()
    if not year.isdigit() or len(year) != 4:
        raise HTTPException(status_code=400, detail="semester_year must be a 4-digit year")
    semester_label = f"{term} {year}"
    section = section_label.strip().upper() or None
    if section and section.startswith("SECTION "):
        section = section[8:].strip() or None

    try:
        result = await submit_final_consolidated(
            db,
            current_user.id,
            course_title.strip(),
            course_file,
            mapping_path,
            mapping_filename,
            programmes,
            branches,
            indirect_attainment,
            target_value=target_value,
            semester_label=semester_label,
            section_label=section,
            remove_marks_after=remove_marks_after,
            skip_database_save=skip_database_save,
            preview_upload_id=preview_upload_id or None,
            mapping_type=mapping_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}") from exc
    finally:
        remove_file_if_exists(tmp_mapping)

    return EvaluationResultResponse(
        public_id=result["public_id"],
        course_title=result["course_title"],
        course_filename=result.get("course_filename"),
        mapping_filename=result.get("mapping_filename"),
        unique_COs=result["unique_COs"],
        intermediate=result["intermediate"],
        co_warnings=result.get("co_warnings", []),
        download_token=result.get("download_token"),
        download_filename=result.get("download_filename"),
        ephemeral=bool(result.get("ephemeral")),
        data_deleted=bool(result.get("data_deleted")),
        marks_cleared=bool(result.get("marks_cleared")),
    )


@router.get("/template")
def download_marks_template():
    """Faculty Excel template for consolidated semester marks upload."""
    template = DATA_ASSETS.parent / "templates" / "Course_Marks_Template.xlsx"
    if not template.exists():
        raise HTTPException(
            status_code=404,
            detail="Template not found. Run: python scripts/generate_marks_template.py",
        )
    return FileResponse(
        template,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Course_Marks_Template.xlsx",
    )


@router.get("/template-components", response_model=MarksTemplateComponentsResponse)
def list_marks_template_components():
    from app.copo.services.marks_template_builder import PRESET_COMPONENT_NAMES

    return MarksTemplateComponentsResponse(presets=PRESET_COMPONENT_NAMES)


@router.post("/generate-constraint-template")
def generate_constraint_marks_template(
    body: MarksTemplateGenerateRequest,
    _: Annotated[User, Depends(get_current_user)],
):
    """Build a course/semester-specific marks Excel matching portal upload constraints."""
    from app.copo.services.marks_template_builder import build_constraint_workbook

    try:
        payload = build_constraint_workbook(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from app.copo.services.marks_template_builder import constraint_template_filename

    filename = constraint_template_filename(body.course_code, body.semester)
    from fastapi.responses import Response

    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


_QUESTION_PAPER_MAX_BYTES = 15 * 1024 * 1024


@router.post("/analyze-question-paper", response_model=QuestionPaperAnalyzeResponse)
async def analyze_question_paper(
    _: Annotated[User, Depends(get_current_user)],
    question_paper: UploadFile = File(...),
):
    """LLM analysis of an uploaded question paper (questions, COs, marks, bonus flags)."""
    from app.copo.services.question_paper_analyzer import analyze_question_paper_file

    content = await question_paper.read()
    if len(content) > _QUESTION_PAPER_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Question paper too large (max 15 MB)")
    try:
        result = await analyze_question_paper_file(question_paper.filename or "paper.pdf", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Analysis failed: {exc}") from exc
    return QuestionPaperAnalyzeResponse.model_validate(result)


@router.post("/generate-from-question-paper")
def generate_from_question_paper(
    body: QuestionPaperGenerateRequest,
    _: Annotated[User, Depends(get_current_user)],
):
    """Build a single-component marks Excel from analyzed question-paper data."""
    from app.copo.services.question_paper_analyzer import generate_component_workbook

    try:
        payload = generate_component_workbook(
            component_name=body.component_name,
            questions=body.questions,
            paper_total_marks=body.paper_total_marks,
            weightage=body.weightage,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in body.component_name.strip())
    filename = f"{safe or 'component'}_marks_template.xlsx"
    from fastapi.responses import Response

    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/parse-students", response_model=ParseStudentsResponse)
async def parse_students(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    course_file: UploadFile = File(...),
    course_title: str = Form(""),
    persist: bool = Form(True),
):
    if not allowed_file(course_file.filename):
        raise HTTPException(status_code=400, detail="Invalid course file")
    title = course_title.strip() or None
    path = await save_upload(course_file, "parsed_input", course_title=title)
    try:
        from app.copo.services.parse_scope import build_parse_api_payload, build_sanitized_parse_metadata
        from app.copo.services.student_parser import parse_student_rolls

        result = parse_student_rolls(path)
        api_payload = build_parse_api_payload(result)
        upload_id = 0
        if persist:
            upload = copo_repo.create_marks_upload(
                db,
                current_user.id,
                course_file.filename or "course.xlsx",
                path,
                parse_metadata=build_sanitized_parse_metadata(result),
                course_title=title,
                upload_type="parsed_input",
            )
            upload_id = upload.id
        else:
            remove_file_if_exists(path)
    except Exception as exc:
        remove_file_if_exists(path)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ParseStudentsResponse(upload_id=upload_id, **api_payload)


@router.post("/course-cos", response_model=CourseCosResponse)
async def course_cos(
    course_title: str = Form(...),
    mapping_option: str = Form("default"),
    mapping_type: str = Form("UG"),
    mapping_file: UploadFile | None = File(None),
):
    if not course_title.strip():
        raise HTTPException(status_code=400, detail="No course title provided")
    tmp_mapping_path = None
    if mapping_option == "upload" and mapping_file and allowed_file(mapping_file.filename):
        tmp_mapping_path = await save_upload(mapping_file, "tmp_cos_mapping")
        mapping_path = tmp_mapping_path
    elif str(mapping_type).upper() == "PG":
        mapping_path = settings.resolved_pg_mapping_path
    else:
        mapping_path = settings.resolved_mapping_path
    try:
        co_labels = mapping_service.extract_cos_for_course(mapping_path, course_title)
        indirect_values = mapping_service.lookup_indirect_values(
            settings.resolved_indirect_path, course_title, co_labels
        )
    finally:
        remove_file_if_exists(tmp_mapping_path)
    return CourseCosResponse(
        cos=co_labels,
        indirect_values=indirect_values,
        found_in_file=bool(indirect_values),
    )


@router.post("/evaluate", response_model=EvaluationResultResponse)
async def evaluate_standard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    course_title: str = Form(...),
    upload_id: int = Form(...),
    use_default_mapping: bool = Form(True),
    mapping_type: str = Form("UG"),
    mapping_file: UploadFile | None = File(None),
    programmes: list[str] = Form(default=[]),
    branches: list[str] = Form(default=[]),
    indirect_attainment_json: str = Form("{}"),
    target_value: int = Form(50),
):
    import json

    indirect_attainment = json.loads(indirect_attainment_json or "{}")
    upload = copo_repo.get_marks_upload(db, upload_id, current_user.id)
    if not upload or upload.status.value == "cleared":
        raise HTTPException(status_code=404, detail="Upload session not found")
    course_path = str(resolve_storage_path(upload.storage_path))

    mapping_path = settings.resolved_mapping_path
    mapping_filename = os.path.basename(mapping_path)
    tmp_mapping = None
    if not use_default_mapping and mapping_file:
        if not allowed_file(mapping_file.filename):
            raise HTTPException(status_code=400, detail="Invalid mapping file")
        tmp_mapping = await save_upload(mapping_file, "custom_mapping")
        mapping_path = tmp_mapping
        mapping_filename = mapping_file.filename or mapping_filename
    elif str(mapping_type).upper() == "PG":
        mapping_path = settings.resolved_pg_mapping_path
        mapping_filename = os.path.basename(mapping_path)

    included_rolls = build_included_rolls(course_path, programmes, branches)
    scope = summarize_scope_selection(programmes, branches)
    run = copo_repo.create_evaluation_run(
        db,
        current_user.id,
        course_title,
        evaluation_type="standard",
        marks_upload_id=upload.id,
        mapping_filename=mapping_filename,
        scope_summary=scope,
        target_value=target_value,
    )

    try:
        payload = evaluation_service.prepare_results_payload(
            course_path,
            mapping_path,
            course_title,
            included_rolls=included_rolls,
            indirect_attainment=indirect_attainment,
            course_filename=upload.original_filename,
            mapping_filename=mapping_filename,
            target_value=target_value,
            mapping_type=mapping_type,
        )
        download_token = None
        excel_path = payload.get("excel_path")
        if excel_path and os.path.exists(excel_path):
            download_token = issue_download_token(excel_path)
        copo_repo.complete_evaluation_run(
            db,
            run,
            result_summary={
                "course_title": payload["course_title"],
                "course_filename": payload.get("course_filename"),
                "mapping_filename": payload.get("mapping_filename"),
                "scope_summary": scope,
                "target_value": target_value,
                "unique_COs": payload["unique_COs"],
                "intermediate": payload["intermediate"],
                "co_warnings": payload.get("co_warnings", []),
                "download_filename": payload.get("download_filename"),
            },
            excel_path=excel_path,
        )
        from app.copo.services.assessment_mapping_service import persist_assessment_co_mappings

        persist_assessment_co_mappings(
            db,
            run,
            course_title=course_title,
            semester_label=run.semester_label,
            section_label=run.section_label,
            intermediate=payload["intermediate"],
        )
        db.commit()
    except ValueError as exc:
        copo_repo.fail_evaluation_run(db, run, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        copo_repo.fail_evaluation_run(db, run, str(exc))
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}") from exc
    finally:
        remove_file_if_exists(tmp_mapping)

    return EvaluationResultResponse(
        public_id=run.public_id,
        course_title=payload["course_title"],
        course_filename=payload.get("course_filename"),
        mapping_filename=payload.get("mapping_filename"),
        unique_COs=payload["unique_COs"],
        intermediate=payload["intermediate"],
        co_warnings=payload.get("co_warnings", []),
        download_token=download_token,
        download_filename=payload.get("download_filename") or result_filename(course_title),
    )


@router.post("/evaluate/compare", response_model=CompareResultResponse)
async def evaluate_compare(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    course_title: str = Form(...),
    upload_id: int = Form(...),
    compare_file: UploadFile = File(...),
    mapping_option: str = Form("default"),
    mapping_file: UploadFile | None = File(None),
    programmes: list[str] = Form(default=[]),
    branches: list[str] = Form(default=[]),
    co_attainment_cell: str = Form(""),
    po_attainment_cell: str = Form(""),
    target_value: int = Form(50),
):
    upload = copo_repo.get_marks_upload(db, upload_id, current_user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    if not allowed_file(compare_file.filename):
        raise HTTPException(status_code=400, detail="Invalid comparison file")

    compare_path = await save_upload(compare_file, "eval_compare")
    mapping_path = settings.resolved_mapping_path
    mapping_filename = os.path.basename(mapping_path)
    tmp_mapping = None
    if mapping_option == "upload" and mapping_file and allowed_file(mapping_file.filename):
        tmp_mapping = await save_upload(mapping_file, "eval_mapping")
        mapping_path = tmp_mapping
        mapping_filename = mapping_file.filename or mapping_filename

    marks_path = str(resolve_storage_path(upload.storage_path))
    included_rolls = build_included_rolls(marks_path, programmes, branches)
    scope_summary = summarize_scope_selection(programmes, branches)

    evaluation = None
    try:
        evaluation = evaluation_service.build_evaluation_payload(
            marks_path,
            mapping_path,
            course_title,
            compare_path,
            included_rolls=included_rolls,
            co_cell_ref=co_attainment_cell or None,
            po_cell_ref=po_attainment_cell or None,
            target_value=target_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        remove_file_if_exists(compare_path)
        remove_file_if_exists(tmp_mapping)

    excel_path = (evaluation or {}).get("intermediate", {}).get("excel_path")
    if excel_path and os.path.exists(excel_path):
        copo_repo.create_percentage_results_upload(
            db,
            current_user.id,
            excel_path,
            course_title=course_title,
            source_upload_id=upload.id,
        )

    threshold_rule = "max(50, Mean - 0.5*Std)"
    setup = ComparisonSetup(
        input_sheet=upload.original_filename,
        compare_filename=compare_file.filename or "compare.xlsx",
        mapping_filename=mapping_filename,
        scope_summary=scope_summary,
        threshold_rule=threshold_rule,
    )
    return CompareResultResponse(
        course_title=course_title,
        course_filename=upload.original_filename,
        compare_filename=compare_file.filename or "compare.xlsx",
        mapping_filename=mapping_filename,
        target_value=target_value,
        scope_summary=scope_summary,
        threshold_rule=threshold_rule,
        comparison_setup=setup,
        co_warnings=evaluation.get("co_warnings", []),
        co_table=evaluation["co_table"],
        po_table=evaluation["po_table"],
    )


@router.post("/evaluate/bulk", response_model=BulkResultResponse)
async def evaluate_bulk(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    use_default_mapping: bool = Form(True),
    mapping_type: str = Form("UG"),
    mapping_file: UploadFile | None = File(None),
    rows_json: str = Form(...),
    compare_files: list[UploadFile] = File(default=[]),
):
    """Bulk compare: rows_json array aligned with compare_files upload order."""
    import json

    try:
        rows = json.loads(rows_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid rows_json") from exc
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=400, detail="At least one bulk row is required")

    mapping_path = settings.resolved_mapping_path
    mapping_filename = os.path.basename(mapping_path)
    tmp_mapping = None
    if not use_default_mapping and mapping_file and allowed_file(mapping_file.filename):
        tmp_mapping = await save_upload(mapping_file, "bulk_eval_mapping")
        mapping_path = tmp_mapping
        mapping_filename = mapping_file.filename or mapping_filename
    elif str(mapping_type).upper() == "PG":
        mapping_path = settings.resolved_pg_mapping_path
        mapping_filename = os.path.basename(mapping_path)

    results_data = []
    compare_index = 0

    try:
        for row_number, row in enumerate(rows, start=1):
            course_title = (row.get("course_title") or "").strip()
            upload_id = row.get("upload_id")
            if not course_title or not upload_id:
                results_data.append(
                    {
                        "status": "error",
                        "row_number": row_number,
                        "course_title": course_title or "(not selected)",
                        "error_message": "Course title and parsed marks upload are required.",
                    }
                )
                continue

            compare_file = (
                compare_files[compare_index] if compare_index < len(compare_files) else None
            )
            compare_index += 1
            if not compare_file or not allowed_file(compare_file.filename):
                results_data.append(
                    {
                        "status": "error",
                        "row_number": row_number,
                        "course_title": course_title,
                        "error_message": "Comparison Excel file is required for each row.",
                    }
                )
                continue

            upload = copo_repo.get_marks_upload(db, int(upload_id), current_user.id)
            resolved_upload = resolve_storage_path(upload.storage_path) if upload else None
            if not upload or resolved_upload is None or not resolved_upload.exists():
                results_data.append(
                    {
                        "status": "error",
                        "row_number": row_number,
                        "course_title": course_title,
                        "error_message": "Marks upload session not found. Parse the marks file again.",
                    }
                )
                continue

            compare_path = await save_upload(compare_file, f"bulk_eval_compare_{row_number}")
            progs = row.get("programmes") or []
            brs = row.get("branches") or []

            result = evaluation_service.process_bulk_row(
                str(resolved_upload),
                compare_path,
                course_title,
                mapping_path,
                mapping_filename,
                progs,
                brs,
                co_cell_ref=row.get("co_cell") or "",
                po_cell_ref=row.get("po_cell") or "",
                row_number=row_number,
                course_filename=upload.original_filename,
                compare_filename=compare_file.filename or "compare.xlsx",
                mapping_type=mapping_type,
            )
            results_data.append(result)
            remove_file_if_exists(compare_path)
            generated = result.get("excel_path") if result.get("status") == "success" else None
            if generated and os.path.exists(generated):
                copo_repo.create_percentage_results_upload(
                    db,
                    current_user.id,
                    generated,
                    course_title=course_title,
                    source_upload_id=upload.id,
                )
    finally:
        remove_file_if_exists(tmp_mapping)

    if not results_data:
        raise HTTPException(status_code=400, detail="No valid bulk rows submitted")

    success_count = sum(1 for r in results_data if r.get("status") == "success")
    error_count = sum(1 for r in results_data if r.get("status") == "error")
    return BulkResultResponse(
        results=results_data,
        mapping_filename=mapping_filename,
        total_rows=len(results_data),
        success_count=success_count,
        error_count=error_count,
    )


@router.get("/results/{public_id}", response_model=EvaluationResultResponse)
def get_results(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    run = copo_repo.get_evaluation_by_public_id(db, public_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Results not found")
    summary = run.result_summary or {}
    token = (
        issue_download_token(str(resolve_storage_path(run.excel_result_path)))
        if run.excel_result_path
        else None
    )
    return EvaluationResultResponse(
        public_id=run.public_id,
        course_title=run.course_title,
        course_filename=summary.get("course_filename"),
        mapping_filename=summary.get("mapping_filename") or run.mapping_filename,
        scope_summary=summary.get("scope_summary") or run.scope_summary,
        target_value=summary.get("target_value") or run.target_value,
        unique_COs=summary.get("unique_COs", []),
        intermediate=summary.get("intermediate", {}),
        co_warnings=summary.get("co_warnings")
        or (summary.get("intermediate") or {}).get("co_warnings", []),
        download_token=token,
        download_filename=summary.get("download_filename")
        or (result_filename(run.course_title) if run.excel_result_path else None),
    )


@router.get("/assets/status")
def copo_assets_status():
    mapping = settings.resolved_mapping_path
    indirect = settings.resolved_indirect_path
    return {
        "mapping_path": mapping,
        "mapping_exists": os.path.exists(mapping),
        "course_count": len(mapping_service.extract_course_names(mapping))
        if os.path.exists(mapping)
        else 0,
        "indirect_path": indirect,
        "indirect_exists": os.path.exists(indirect),
    }


@router.get("/download/{token}")
def download_results(token: str):
    excel_path = pop_download_path(token)
    resolved = resolve_storage_path(excel_path) if excel_path else None
    if not resolved or not resolved.exists():
        raise HTTPException(status_code=404, detail="Results file not found or expired")
    return FileResponse(
        resolved,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(resolved),
    )


@router.post("/uploads/clear", response_model=ClearUploadsResponse)
def clear_uploads(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    removed = cleanup_upload_directory()
    from app.database.models.copo import CopoMarksUpload, UploadStatus

    uploads = (
        db.query(CopoMarksUpload)
        .filter(
            CopoMarksUpload.user_id == current_user.id,
            CopoMarksUpload.status != UploadStatus.cleared,
        )
        .all()
    )
    cleared = 0
    for upload in uploads:
        copo_repo.clear_marks_for_upload(db, upload)
        cleared += 1
    return ClearUploadsResponse(removed_files=removed, cleared_sessions=cleared)


@router.post("/runs/{public_id}/delete-data", response_model=DeleteEvaluationDataResponse)
def delete_evaluation_data(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    delete_excel_report: bool = Form(True),
):
    """Manual cascade delete: marks upload, optional result Excel, archives, and run row."""
    from app.copo.services.cleanup_service import delete_evaluation_sensitive_data

    run = copo_repo.get_evaluation_by_public_id(db, public_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    if run.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    outcome = delete_evaluation_sensitive_data(
        db,
        run,
        full_delete=True,
        delete_excel_report=delete_excel_report,
    )
    return DeleteEvaluationDataResponse(
        removed_files=int(outcome.get("removed_files", 0)),
        run_deleted=bool(outcome.get("run_deleted")),
        message="Evaluation data removed from server.",
    )


@router.post("/runs/{public_id}/archive-and-clear-marks")
def archive_and_clear_marks(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    run = copo_repo.get_evaluation_by_public_id(db, public_id)
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    upload = copo_repo.get_marks_upload(db, run.marks_upload_id, current_user.id) if run.marks_upload_id else None
    try:
        archive = copo_repo.archive_and_clear_marks(db, run, upload)
    except FileNotFoundError as exc:
        run.excel_result_path = None
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not archive:
        raise HTTPException(status_code=400, detail="No result file to archive")
    return {
        "archived": True,
        "archive_path": archive.archive_path,
        "marks_cleared": upload is not None,
    }


@router.get("/admin/data-overview", response_model=AdminDataOverviewResponse)
def admin_data_overview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.copo.services.admin_data_service import list_admin_overview

    return list_admin_overview(db)


@router.post("/admin/runs/{public_id}/delete", response_model=DeleteEvaluationDataResponse)
def admin_delete_run(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.copo.services.admin_data_service import admin_delete_run

    run = copo_repo.get_evaluation_by_public_id(db, public_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    outcome = admin_delete_run(db, public_id)
    return DeleteEvaluationDataResponse(
        removed_files=int(outcome.get("removed_files", 0)),
        run_deleted=bool(outcome.get("run_deleted")),
        message="Evaluation run and related data removed.",
    )


@router.post("/admin/uploads/{upload_id}/delete")
def admin_delete_upload(
    upload_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.copo.services.admin_data_service import admin_delete_upload

    return admin_delete_upload(db, upload_id)


@router.post("/admin/archives/{archive_id}/delete")
def admin_delete_archive(
    archive_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.copo.services.admin_data_service import admin_delete_archive

    return admin_delete_archive(db, archive_id)


@router.post("/admin/runs/{public_id}/archive")
def admin_archive_run(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.copo.services.admin_data_service import admin_archive_run

    return admin_archive_run(db, public_id)


@router.post("/admin/purge-all", response_model=AdminPurgeResponse)
def admin_purge_all(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    from app.copo.services.cleanup_service import purge_all_copo_data

    outcome = purge_all_copo_data(db)
    return AdminPurgeResponse(
        removed_files=int(outcome.get("removed_files", 0)),
        runs_deleted=bool(outcome.get("runs_deleted")),
        message="All CO-PO uploads, runs, archives, and linked files were removed.",
    )
