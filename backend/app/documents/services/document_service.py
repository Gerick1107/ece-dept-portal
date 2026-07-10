from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.documents.models.entities import (
    DOCUMENT_TYPE_ECE_FACULTY_MEET,
    DOCUMENT_TYPE_LABELS,
    Meeting,
    MeetingFile,
)
from app.documents.services.file_manager import resolve_document_path


def _meeting_to_dict(meeting: Meeting, *, include_type: bool = False) -> dict:
    files = {f.file_role: f for f in meeting.files}
    agenda = files.get("agenda")
    minutes = files.get("minutes")
    item = {
        "id": meeting.id,
        "title": meeting.meeting_title,
        "meeting_date": meeting.meeting_date,
        "year": meeting.year,
        "has_agenda": agenda is not None,
        "has_minutes": minutes is not None,
        "agenda": (
            {
                "id": agenda.id,
                "file_name": agenda.file_name,
                "description": agenda.description,
            }
            if agenda
            else None
        ),
        "minutes": (
            {
                "id": minutes.id,
                "file_name": minutes.file_name,
                "description": minutes.description,
            }
            if minutes
            else None
        ),
    }
    if include_type:
        item["document_type"] = meeting.document_type
        item["document_type_label"] = DOCUMENT_TYPE_LABELS.get(meeting.document_type, meeting.document_type)
    return item


def list_documents_grouped(db: Session, document_type: str) -> dict:
    rows = db.scalars(
        select(Meeting)
        .where(Meeting.document_type == document_type)
        .options(joinedload(Meeting.files))
        .order_by(Meeting.year.desc(), Meeting.meeting_title.asc())
    ).unique().all()
    years: dict[int, list[dict]] = {}
    for meeting in rows:
        years.setdefault(meeting.year, []).append(_meeting_to_dict(meeting))
    return {"years": [{"year": year, "documents": docs} for year, docs in sorted(years.items(), reverse=True)]}


def list_all_documents_grouped(db: Session) -> dict:
    rows = db.scalars(
        select(Meeting)
        .options(joinedload(Meeting.files))
        .order_by(Meeting.year.desc(), Meeting.document_type.asc(), Meeting.meeting_title.asc())
    ).unique().all()
    years: dict[int, list[dict]] = {}
    for meeting in rows:
        years.setdefault(meeting.year, []).append(_meeting_to_dict(meeting, include_type=True))
    return {"years": [{"year": year, "documents": docs} for year, docs in sorted(years.items(), reverse=True)]}


def get_meeting(db: Session, meeting_id: int) -> Meeting | None:
    return db.scalar(
        select(Meeting).where(Meeting.id == meeting_id).options(joinedload(Meeting.files))
    )


def get_meeting_file(db: Session, file_id: int) -> MeetingFile | None:
    return db.get(MeetingFile, file_id)


from app.documents.services.ingestion_service import generate_document_description
from app.documents.services.pdf_service import extract_pdf_metadata, parse_date_from_text


async def extract_upload_metadata(file_path: Path, *, document_type: str | None = None) -> dict:
    meta = extract_pdf_metadata(file_path, fallback_title=file_path.stem)
    sample = "\n".join(text for _, text in meta.pages[:3])
    auto_description = await generate_document_description(
        meta.title, sample, file_role="minutes"
    )
    meeting_date = meta.meeting_date
    if not meeting_date:
        meeting_date = parse_date_from_text(auto_description) or parse_date_from_text(sample)

    title = meta.title
    # ECE Faculty Meets are named by meeting type (e.g. "Moderation Meeting"),
    # not by an ordinal, so derive a proper title from the document content.
    if document_type == DOCUMENT_TYPE_ECE_FACULTY_MEET:
        from app.documents.services.meeting_title_service import derive_meeting_title

        derived = await derive_meeting_title(sample)
        if derived:
            title = derived

    return {
        "title": title,
        "meeting_date": meeting_date,
        "description": auto_description,
    }


def delete_meeting(db: Session, meeting: Meeting) -> None:
    paths = [resolve_document_path(f.file_path) for f in meeting.files]
    db.delete(meeting)
    db.commit()
    for path in paths:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
