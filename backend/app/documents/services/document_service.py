from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.models.entities import PortalDocument
from app.documents.services.ingestion_service import generate_document_description, ingest_document_file
from app.documents.services.pdf_service import extract_pdf_metadata, parse_date_from_text


def list_documents_grouped(db: Session, document_type: str) -> dict:
    rows = db.scalars(
        select(PortalDocument)
        .where(PortalDocument.document_type == document_type)
        .order_by(PortalDocument.year.desc(), PortalDocument.title.asc())
    ).all()
    years: dict[int, list[dict]] = {}
    for row in rows:
        years.setdefault(row.year, []).append(
            {
                "id": row.id,
                "title": row.title,
                "meeting_date": row.meeting_date,
                "description": row.description,
                "file_name": row.file_name,
                "year": row.year,
            }
        )
    return {"years": [{"year": year, "documents": docs} for year, docs in sorted(years.items(), reverse=True)]}


def get_document(db: Session, document_id: int) -> PortalDocument | None:
    return db.get(PortalDocument, document_id)


def delete_document(db: Session, document: PortalDocument) -> None:
    path = Path(document.file_path)
    db.delete(document)
    db.commit()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


async def save_uploaded_document(
    db: Session,
    *,
    document_type: str,
    year: int,
    dest_path: Path,
    title: str,
    meeting_date: str | None,
    description: str,
) -> PortalDocument:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    return await ingest_document_file(
        db,
        document_type=document_type,
        year=year,
        file_path=dest_path,
        title=title,
        meeting_date=meeting_date,
        description=description,
        generate_description=False,
    )


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
