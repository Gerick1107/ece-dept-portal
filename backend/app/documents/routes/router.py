from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, require_roles
from app.config import get_settings
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.documents.models.entities import DOCUMENT_TYPE_ALL, Meeting, MeetingFile
from app.documents.services.document_service import (
    delete_meeting,
    extract_upload_metadata,
    get_meeting,
    get_meeting_file,
    list_all_documents_grouped,
    list_documents_grouped,
)
from app.documents.services.file_manager import SLUG_TO_TYPE, resolve_document_path, subdir_for_type
from app.documents.services.ingestion_service import ingest_meeting_file
from app.documents.services.rag_service import answer_document_question
from app.llm.services.groq_service import LlmError

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_PDF_BYTES = 25 * 1024 * 1024


class DocumentQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    provider: Literal["groq", "local"] = "groq"


def _resolve_type(document_type: str) -> str:
    resolved = SLUG_TO_TYPE.get(document_type)
    if not resolved:
        raise HTTPException(status_code=404, detail="Unknown document type")
    return resolved


async def _read_pdf(upload: UploadFile) -> bytes:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    payload = await upload.read()
    if len(payload) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")
    return payload


@router.get("/{document_type}")
async def list_documents(
    document_type: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    resolved = _resolve_type(document_type)
    try:
        from app.documents.services.file_manager import ensure_documents_dirs
        from app.documents.services.ingestion_service import sync_new_documents_from_disk

        docs_root = ensure_documents_dirs()
        if resolved != DOCUMENT_TYPE_ALL:
            await sync_new_documents_from_disk(db, docs_root, document_type=resolved)
    except Exception:
        pass
    if resolved == DOCUMENT_TYPE_ALL:
        return list_all_documents_grouped(db)
    return list_documents_grouped(db, resolved)


@router.get("/{document_type}/files/{file_id}/download")
def download_file(
    document_type: str,
    file_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    resolved = _resolve_type(document_type)
    mf = db.scalar(
        select(MeetingFile).options(joinedload(MeetingFile.meeting)).where(MeetingFile.id == file_id)
    )
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    if resolved != DOCUMENT_TYPE_ALL and mf.meeting.document_type != resolved:
        raise HTTPException(status_code=404, detail="File not found")
    path = resolve_document_path(mf.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=mf.file_name)


@router.post("/{document_type}/query")
async def query_documents(
    document_type: str,
    body: DocumentQueryRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await answer_document_question(
            db,
            document_type=_resolve_type(document_type),
            question=body.question.strip(),
            user_id=user.id,
            provider=body.provider,
        )
    except LlmError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/{document_type}/upload/preview")
async def preview_upload(
    document_type: str,
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
    file: UploadFile = File(...),
):
    resolved = _resolve_type(document_type)
    if resolved == DOCUMENT_TYPE_ALL:
        raise HTTPException(status_code=400, detail="Upload is not supported on the All Meetings view")
    payload = await _read_pdf(file)
    settings = get_settings()
    temp_dir = Path(settings.documents_dir) / "_upload_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}_{file.filename}"
    temp_path.write_bytes(payload)
    try:
        return await extract_upload_metadata(temp_path)
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass


@router.post("/{document_type}/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
    year: int = Form(...),
    title: str | None = Form(None),
    meeting_date: str | None = Form(None),
    agenda_description: str | None = Form(None),
    minutes_description: str | None = Form(None),
    agenda_file: UploadFile | None = File(None),
    minutes_file: UploadFile | None = File(None),
):
    resolved = _resolve_type(document_type)
    if resolved == DOCUMENT_TYPE_ALL:
        raise HTTPException(status_code=400, detail="Upload is not supported on the All Meetings view")
    if not agenda_file or not agenda_file.filename:
        agenda_file = None
    if not minutes_file or not minutes_file.filename:
        minutes_file = None
    if not agenda_file and not minutes_file:
        raise HTTPException(status_code=400, detail="At least one of Agenda or Minutes PDF is required")

    settings = get_settings()
    subdir = subdir_for_type(resolved)
    base_dir = Path(settings.documents_dir) / subdir / str(year)

    previews: dict[str, dict] = {}
    saved: dict[str, Path] = {}
    for role, upload in (("agenda", agenda_file), ("minutes", minutes_file)):
        if not upload:
            continue
        payload = await _read_pdf(upload)
        role_dir = base_dir / role
        role_dir.mkdir(parents=True, exist_ok=True)
        temp_path = role_dir / f"{uuid.uuid4().hex[:8]}_{upload.filename}"
        temp_path.write_bytes(payload)
        saved[role] = temp_path
        previews[role] = await extract_upload_metadata(temp_path)

    canonical_title = (title or "").strip() or None
    canonical_date = (meeting_date or "").strip() or None
    if not canonical_title:
        if minutes_file and "minutes" in previews:
            canonical_title = previews["minutes"]["title"]
        elif "agenda" in previews:
            canonical_title = previews["agenda"]["title"]
    if not canonical_date:
        if minutes_file and "minutes" in previews:
            canonical_date = previews["minutes"]["meeting_date"]
        elif "agenda" in previews:
            canonical_date = previews["agenda"]["meeting_date"]

    meeting = Meeting(
        document_type=resolved,
        year=year,
        meeting_title=canonical_title or "Meeting",
        meeting_date=canonical_date,
    )
    db.add(meeting)
    db.flush()

    result_files: dict[str, dict] = {}
    if agenda_file and "agenda" in saved:
        mf = await ingest_meeting_file(
            db,
            meeting=meeting,
            file_role="agenda",
            file_path=saved["agenda"],
            title=previews["agenda"]["title"],
            meeting_date=previews["agenda"]["meeting_date"],
            description=(agenda_description or previews["agenda"]["description"] or "").strip() or None,
            generate_description=False,
        )
        result_files["agenda"] = {"id": mf.id, "file_name": mf.file_name}
    if minutes_file and "minutes" in saved:
        mf = await ingest_meeting_file(
            db,
            meeting=meeting,
            file_role="minutes",
            file_path=saved["minutes"],
            title=previews["minutes"]["title"],
            meeting_date=previews["minutes"]["meeting_date"],
            description=(minutes_description or previews["minutes"]["description"] or "").strip() or None,
            generate_description=False,
        )
        result_files["minutes"] = {"id": mf.id, "file_name": mf.file_name}

    db.refresh(meeting)
    return {
        "id": meeting.id,
        "title": meeting.meeting_title,
        "meeting_date": meeting.meeting_date,
        "year": meeting.year,
        "files": result_files,
    }


@router.delete("/{document_type}/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(
    document_type: str,
    meeting_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    resolved = _resolve_type(document_type)
    meeting = get_meeting(db, meeting_id)
    if not meeting or meeting.document_type != resolved:
        raise HTTPException(status_code=404, detail="Meeting not found")
    delete_meeting(db, meeting)
