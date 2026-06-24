from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.documents.models.entities import Meeting, MeetingFile


def list_documents_grouped(db: Session, document_type: str) -> dict:
    rows = db.scalars(
        select(Meeting)
        .where(Meeting.document_type == document_type)
        .options(joinedload(Meeting.files))
        .order_by(Meeting.year.desc(), Meeting.meeting_title.asc())
    ).unique().all()
    years: dict[int, list[dict]] = {}
    for meeting in rows:
        files = {f.file_role: f for f in meeting.files}
        agenda = files.get("agenda")
        minutes = files.get("minutes")
        years.setdefault(meeting.year, []).append(
            {
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
        )
    return {"years": [{"year": year, "documents": docs} for year, docs in sorted(years.items(), reverse=True)]}


def get_meeting(db: Session, meeting_id: int) -> Meeting | None:
    return db.scalar(
        select(Meeting).where(Meeting.id == meeting_id).options(joinedload(Meeting.files))
    )


def get_meeting_file(db: Session, file_id: int) -> MeetingFile | None:
    return db.get(MeetingFile, file_id)


from app.documents.services.ingestion_service import generate_document_description
from app.documents.services.pdf_service import extract_pdf_metadata, parse_date_from_text


async def extract_upload_metadata(file_path: Path) -> dict:
    meta = extract_pdf_metadata(file_path, fallback_title=file_path.stem)
    sample = "\n".join(text for _, text in meta.pages[:2])
    auto_description = await generate_document_description(meta.title, sample)
    meeting_date = meta.meeting_date
    if not meeting_date:
        meeting_date = parse_date_from_text(auto_description) or parse_date_from_text(sample)
    return {
        "title": meta.title,
        "meeting_date": meeting_date,
        "description": auto_description,
    }


def delete_meeting(db: Session, meeting: Meeting) -> None:
    paths = [Path(f.file_path) for f in meeting.files]
    db.delete(meeting)
    db.commit()
    for path in paths:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
