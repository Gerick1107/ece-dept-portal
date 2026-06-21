from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.documents.models.entities import DOCUMENT_TYPE_ECE_FACULTY_MEET, DOCUMENT_TYPE_SENATE, DocumentChunk, PortalDocument
from app.documents.services.pdf_service import extract_pdf_metadata
from app.llm.services.groq_service import LlmError, generate_llm_text_with_system

_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 200
_AGENDA_ITEM_RE = re.compile(r"\b\d+(?:\.\d+)+\b")


def _chunk_page_text(page_number: int, text: str) -> list[tuple[int, str | None, str]]:
    """Split page text by agenda items when possible, else fixed overlapping chunks."""
    text = (text or "").strip()
    if not text:
        return []

    matches = list(_AGENDA_ITEM_RE.finditer(text))
    if len(matches) >= 2:
        chunks: list[tuple[int, str | None, str]] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = match.group(0)
            snippet = text[start:end].strip()
            if snippet:
                chunks.append((page_number, section, snippet))
        return chunks

    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + _CHUNK_SIZE)
        snippet = text[start:end].strip()
        if snippet:
            chunks.append((page_number, None, snippet))
        if end >= len(text):
            break
        start = max(end - _CHUNK_OVERLAP, start + 1)
    return chunks


async def generate_document_description(title: str, sample_text: str) -> str:
    prompt = (
        f"Write a 2-4 sentence plain-language summary of this meeting document.\n"
        f"Title: {title}\n\nExcerpt:\n{sample_text[:3000]}"
    )
    system = (
        "You summarize academic meeting minutes for faculty. Be factual and concise. "
        "Do not invent details beyond the excerpt."
    )
    try:
        return await generate_llm_text_with_system(prompt, system_prompt=system, temperature=0.3, max_tokens=300)
    except LlmError:
        return f"Meeting minutes: {title}."


def index_document_chunks(db: Session, document: PortalDocument, pages: list[tuple[int, str]]) -> int:
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    count = 0
    for page_number, page_text in pages:
        for page, section, chunk_text in _chunk_page_text(page_number, page_text):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_number=page,
                    section_label=section,
                    chunk_text=chunk_text,
                )
            )
            count += 1
    db.commit()
    return count


async def ingest_document_file(
    db: Session,
    *,
    document_type: str,
    year: int,
    file_path: Path,
    title: str | None = None,
    meeting_date: str | None = None,
    description: str | None = None,
    generate_description: bool = True,
) -> PortalDocument:
    meta = extract_pdf_metadata(file_path, fallback_title=title)
    resolved_title = title or meta.title
    resolved_date = meeting_date or meta.meeting_date
    sample_text = "\n".join(text for _, text in meta.pages[:2])
    resolved_description = description
    if generate_description and not resolved_description:
        resolved_description = await generate_document_description(resolved_title, sample_text)

    existing = db.scalar(
        select(PortalDocument).where(
            PortalDocument.document_type == document_type,
            PortalDocument.file_path == str(file_path.resolve()),
        )
    )
    if existing:
        doc = existing
        doc.title = resolved_title
        doc.meeting_date = resolved_date
        doc.description = resolved_description
        doc.year = year
        doc.file_name = file_path.name
    else:
        doc = PortalDocument(
            document_type=document_type,
            year=year,
            file_name=file_path.name,
            file_path=str(file_path.resolve()),
            title=resolved_title,
            meeting_date=resolved_date,
            description=resolved_description,
        )
        db.add(doc)
    db.commit()
    db.refresh(doc)
    index_document_chunks(db, doc, meta.pages)
    return doc


async def sync_new_documents_from_disk(
    db: Session,
    documents_root: Path,
    *,
    document_type: str | None = None,
) -> dict[str, int]:
    """Register PDFs on disk that are not yet in the database."""
    type_dirs = (
        (DOCUMENT_TYPE_SENATE, "senate-minutes"),
        (DOCUMENT_TYPE_ECE_FACULTY_MEET, "ece-faculty-meets"),
    )
    if document_type:
        type_dirs = tuple(pair for pair in type_dirs if pair[0] == document_type)

    ingested = 0
    for resolved_type, subdir in type_dirs:
        base = documents_root / subdir
        if not base.exists():
            continue
        for year_dir in sorted(base.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            year = int(year_dir.name)
            for pdf_path in sorted(year_dir.glob("*.pdf")):
                resolved_path = str(pdf_path.resolve())
                existing = db.scalar(select(PortalDocument).where(PortalDocument.file_path == resolved_path))
                if existing:
                    continue
                await ingest_document_file(
                    db,
                    document_type=resolved_type,
                    year=year,
                    file_path=pdf_path,
                    generate_description=True,
                )
                ingested += 1
    return {"ingested": ingested}


async def seed_documents_from_disk(db: Session, documents_root: Path) -> dict[str, int]:
    """Backward-compatible alias: only ingests PDFs missing from the database."""
    return await sync_new_documents_from_disk(db, documents_root)
