from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.config import get_settings
from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.documents.models.entities import DOCUMENT_TYPE_ECE_FACULTY_MEET, DOCUMENT_TYPE_SENATE
from app.documents.services.document_service import (
    delete_document,
    extract_upload_metadata,
    get_document,
    list_documents_grouped,
)
from app.documents.services.rag_service import answer_document_question
from app.llm.services.groq_service import LlmError

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_PDF_BYTES = 25 * 1024 * 1024


class DocumentQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


def _resolve_type(document_type: str) -> str:
    mapping = {
        "senate": DOCUMENT_TYPE_SENATE,
        "ece-faculty-meets": DOCUMENT_TYPE_ECE_FACULTY_MEET,
    }
    resolved = mapping.get(document_type)
    if not resolved:
        raise HTTPException(status_code=404, detail="Unknown document type")
    return resolved


@router.get("/{document_type}")
async def list_documents(
    document_type: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    try:
        from app.documents.services.file_manager import ensure_documents_dirs
        from app.documents.services.ingestion_service import seed_documents_from_disk

        docs_root = ensure_documents_dirs()
        await seed_documents_from_disk(db, docs_root)
    except Exception:
        pass
    return list_documents_grouped(db, _resolve_type(document_type))


@router.get("/{document_type}/{document_id}/download")
def download_document(
    document_type: str,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    resolved = _resolve_type(document_type)
    doc = get_document(db, document_id)
    if not doc or doc.document_type != resolved:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=doc.file_name)


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
        )
    except LlmError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/{document_type}/upload/preview")
async def preview_upload(
    document_type: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
    file: UploadFile = File(...),
):
    _resolve_type(document_type)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    payload = await file.read()
    if len(payload) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")
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
    file: UploadFile = File(...),
):
    resolved = _resolve_type(document_type)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    payload = await file.read()
    if len(payload) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")

    settings = get_settings()
    subdir = "senate-minutes" if resolved == DOCUMENT_TYPE_SENATE else "ece-faculty-meets"
    dest_dir = Path(settings.documents_dir) / subdir / str(year)
    dest_path = dest_dir / file.filename
    if dest_path.exists():
        dest_path = dest_dir / f"{uuid.uuid4().hex[:8]}_{file.filename}"
    dest_path.write_bytes(payload)

    from app.documents.services.ingestion_service import ingest_document_file

    doc = await ingest_document_file(
        db,
        document_type=resolved,
        year=year,
        file_path=dest_path,
        generate_description=True,
    )
    return {
        "id": doc.id,
        "title": doc.title,
        "meeting_date": doc.meeting_date,
        "description": doc.description,
        "year": doc.year,
        "file_name": doc.file_name,
    }


@router.delete("/{document_type}/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(
    document_type: str,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    resolved = _resolve_type(document_type)
    doc = get_document(db, document_id)
    if not doc or doc.document_type != resolved:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document(db, doc)
