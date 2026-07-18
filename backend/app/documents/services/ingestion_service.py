from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.database.session import SessionLocal

from app.documents.models.entities import DOCUMENT_TYPE_ECE_FACULTY_MEET, DocumentChunk, Meeting, MeetingFile
from app.documents.services.embedding_service import embed_texts, embedding_to_json
from app.documents.services.file_manager import DOCUMENT_TYPE_DIRS, resolve_document_path
from app.documents.services.pdf_service import extract_pdf_metadata
from app.llm.services.errors import LlmError
from app.llm.services.llm_dispatch import generate_text

_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 200
_MIN_AGENDA_CHUNK = 180
_AGENDA_ITEM_RE = re.compile(r"\b\d+(?:\.\d+)+\b")


def _normalize_pdf_text(text: str) -> str:
    """Collapse PDF extraction noise so embeddings and keyword search work better."""
    text = (text or "").replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Soft hyphen / odd spaces from pypdf
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _merge_small_chunks(
    chunks: list[tuple[int, str | None, str]], *, min_chars: int = _MIN_AGENDA_CHUNK
) -> list[tuple[int, str | None, str]]:
    if not chunks:
        return []
    merged: list[tuple[int, str | None, str]] = []
    page, section, buf = chunks[0]
    for next_page, next_section, next_text in chunks[1:]:
        if next_page == page and len(buf) < min_chars:
            buf = f"{buf}\n{next_text}".strip()
            if section and next_section:
                section = f"{section}-{next_section}"
            elif next_section and not section:
                section = next_section
        else:
            if buf.strip():
                merged.append((page, section, buf.strip()))
            page, section, buf = next_page, next_section, next_text
    if buf.strip():
        merged.append((page, section, buf.strip()))
    return merged


def _chunk_page_text(page_number: int, text: str) -> list[tuple[int, str | None, str]]:
    text = _normalize_pdf_text(text)
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
        return _merge_small_chunks(chunks)
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


def _is_weak_description(description: str | None) -> bool:
    """True if a description is missing or a raw-text/placeholder fallback
    rather than a real LLM summary."""
    if not description or not description.strip():
        return True
    text = description.strip()
    if text.startswith("Meeting document:"):
        return True
    # Raw PDF-text dumps from the old buggy fallback were truncated with an ellipsis.
    if text.endswith("\u2026") or text.endswith("..."):
        return True
    # Raw minutes/agenda headers that leaked through instead of a summary.
    compact = text.replace(" ", "")
    if compact.startswith("MinutesofECEFM") or compact.startswith("AGENDA"):
        return True
    if text.startswith("Minutes of the") and "held on" in text[:80]:
        return True
    if len(text) < 80:
        return True
    return False


async def generate_document_description(
    title: str,
    sample_text: str,
    *,
    file_role: str = "minutes",
) -> str:
    """Generate a short plain-language summary via the LLM.

    Raises LlmError if the model is unavailable. Never returns raw PDF text,
    so a transient failure cannot poison stored descriptions.
    """
    role_label = "agenda" if file_role == "agenda" else "minutes"
    excerpt = (sample_text or "").strip()
    prompt = (
        f"Write a 2-4 sentence plain-language summary of this meeting {role_label}.\n"
        f"Cover the main topics discussed, decisions taken, and any notable action items.\n"
        f"Do not repeat the title or filename; summarize the substantive content only.\n"
        f"Meeting title: {title}\n\nExcerpt:\n{excerpt[:1600]}"
    )
    system = (
        "You summarize academic meeting documents for faculty. Be factual and concise. "
        "Do not invent details beyond the excerpt."
    )
    return await generate_text(
        prompt,
        provider="local",
        system_prompt=system,
        temperature=0.3,
        max_tokens=180,
    )


async def regenerate_meeting_file_description(db: Session, meeting_file: MeetingFile) -> str:
    path = resolve_document_path(meeting_file.file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF missing on disk: {path}")
    meeting = meeting_file.meeting
    meta = extract_pdf_metadata(path, fallback_title=meeting.meeting_title)
    sample = "\n".join(text for _, text in meta.pages[:3])
    # Raises LlmError if the model is unavailable; caller keeps the old value.
    description = await generate_document_description(
        meeting.meeting_title,
        sample,
        file_role=meeting_file.file_role,
    )
    meeting_file.description = description
    db.commit()
    return description


async def regenerate_weak_descriptions(
    db: Session,
    *,
    only_weak: bool = True,
    concurrency: int = 6,
) -> dict[str, int]:
    import asyncio

    stmt = select(MeetingFile).options(joinedload(MeetingFile.meeting))
    files = db.scalars(stmt).unique().all()
    if only_weak:
        files = [f for f in files if _is_weak_description(f.description)]

    sem = asyncio.Semaphore(concurrency)
    ok = 0
    failed = 0

    async def _one(mf: MeetingFile) -> None:
        nonlocal ok, failed
        async with sem:
            session = SessionLocal()
            try:
                row = session.scalar(
                    select(MeetingFile)
                    .options(joinedload(MeetingFile.meeting))
                    .where(MeetingFile.id == mf.id)
                )
                if not row:
                    failed += 1
                    return
                await regenerate_meeting_file_description(session, row)
                ok += 1
            except Exception:
                session.rollback()
                failed += 1
            finally:
                session.close()
            await asyncio.sleep(0.4)

    await asyncio.gather(*[_one(mf) for mf in files])
    return {"total": len(files), "ok": ok, "failed": failed}


def index_meeting_file_chunks(db: Session, meeting_file: MeetingFile, pages: list[tuple[int, str]]) -> int:
    db.execute(delete(DocumentChunk).where(DocumentChunk.meeting_file_id == meeting_file.id))
    pending: list[tuple[int, str | None, str]] = []
    for page_number, page_text in pages:
        pending.extend(_chunk_page_text(page_number, page_text))

    embeddings: list[list[float]] = []
    if pending:
        try:
            embeddings = embed_texts([chunk_text for _, _, chunk_text in pending])
        except Exception:
            embeddings = []

    count = 0
    for index, (page, section, chunk_text) in enumerate(pending):
        embedding_json = embedding_to_json(embeddings[index]) if index < len(embeddings) else None
        db.add(
            DocumentChunk(
                meeting_file_id=meeting_file.id,
                page_number=page,
                section_label=section,
                chunk_text=chunk_text,
                embedding_json=embedding_json,
            )
        )
        count += 1
    db.commit()
    return count


def reindex_meeting_file(db: Session, meeting_file: MeetingFile) -> int:
    """Re-read PDF from disk, re-chunk, and re-embed."""
    path = resolve_document_path(meeting_file.file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF missing on disk: {path}")
    meta = extract_pdf_metadata(path, fallback_title=meeting_file.meeting.meeting_title if meeting_file.meeting else None)
    return index_meeting_file_chunks(db, meeting_file, meta.pages)


def reindex_all_meeting_chunks(
    db: Session,
    *,
    document_type: str | None = None,
    missing_embeddings_only: bool = False,
) -> dict[str, int]:
    """Reindex every meeting PDF (or only those with missing embeddings)."""
    stmt = select(MeetingFile).options(joinedload(MeetingFile.meeting))
    files = list(db.scalars(stmt).unique().all())
    if document_type:
        files = [f for f in files if f.meeting and f.meeting.document_type == document_type]

    if missing_embeddings_only:
        filtered: list[MeetingFile] = []
        for mf in files:
            chunks = db.scalars(
                select(DocumentChunk).where(DocumentChunk.meeting_file_id == mf.id)
            ).all()
            if not chunks or any(not (c.embedding_json or "").strip() for c in chunks):
                filtered.append(mf)
        files = filtered

    ok = 0
    failed = 0
    chunks_total = 0
    for mf in files:
        try:
            chunks_total += reindex_meeting_file(db, mf)
            ok += 1
        except Exception:
            db.rollback()
            failed += 1
    return {"files": len(files), "ok": ok, "failed": failed, "chunks": chunks_total}


async def ingest_meeting_file(
    db: Session,
    *,
    meeting: Meeting,
    file_role: str,
    file_path: Path,
    title: str | None = None,
    meeting_date: str | None = None,
    description: str | None = None,
    generate_description: bool = True,
    preserve_meeting_title: bool = False,
) -> MeetingFile:
    meta = extract_pdf_metadata(file_path, fallback_title=title)
    resolved_title = title or meta.title
    resolved_date = meeting_date or meta.meeting_date
    sample_text = "\n".join(text for _, text in meta.pages[:3])
    resolved_description = description
    if generate_description and not resolved_description:
        try:
            resolved_description = await generate_document_description(
                resolved_title, sample_text, file_role=file_role
            )
        except LlmError:
            resolved_description = None

    existing = db.scalar(
        select(MeetingFile).where(
            MeetingFile.meeting_id == meeting.id,
            MeetingFile.file_role == file_role,
        )
    )
    if existing:
        mf = existing
        mf.file_name = file_path.name
        mf.file_path = str(file_path.resolve())
        mf.description = resolved_description
    else:
        mf = MeetingFile(
            meeting_id=meeting.id,
            file_role=file_role,
            file_name=file_path.name,
            file_path=str(file_path.resolve()),
            description=resolved_description,
        )
        db.add(mf)
    if not preserve_meeting_title:
        preserve_meeting_title = meeting.document_type == DOCUMENT_TYPE_ECE_FACULTY_MEET
    if not preserve_meeting_title:
        if not meeting.meeting_title or file_role == "minutes":
            meeting.meeting_title = resolved_title
    if resolved_date and (not meeting.meeting_date or file_role == "minutes"):
        meeting.meeting_date = resolved_date
    db.commit()
    db.refresh(mf)
    index_meeting_file_chunks(db, mf, meta.pages)
    return mf


async def sync_new_documents_from_disk(
    db: Session,
    documents_root: Path,
    *,
    document_type: str | None = None,
) -> dict[str, int]:
    from app.documents.services.meeting_matcher import (
        build_meeting_title,
        meeting_identity,
        meeting_key,
    )

    type_dirs = tuple(DOCUMENT_TYPE_DIRS.items())
    if document_type:
        type_dirs = tuple(pair for pair in type_dirs if pair[0] == document_type)

    ingested = 0
    for resolved_type, subdir in type_dirs:
        base = documents_root / subdir
        if not base.exists():
            continue

        # Collect PDFs grouped by (type, year, meeting_number).
        groups: dict[tuple[str, int, int | str], dict[str, Path]] = {}
        for year_dir in sorted(base.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            year = int(year_dir.name)

            for role in ("agenda", "minutes"):
                role_dir = year_dir / role
                if role_dir.is_dir():
                    for pdf_path in sorted(role_dir.glob("*.pdf")):
                        identity = meeting_identity(pdf_path.name)
                        key = meeting_key(resolved_type, year, identity)
                        groups.setdefault(key, {})[role] = pdf_path

            # Legacy flat layout: year/*.pdf (treated as minutes).
            for pdf_path in sorted(year_dir.glob("*.pdf")):
                identity = meeting_identity(pdf_path.name)
                key = meeting_key(resolved_type, year, identity)
                groups.setdefault(key, {}).setdefault("minutes", pdf_path)

        def _sort_key(item: tuple[tuple[str, int, int | str], dict[str, Path]]) -> tuple:
            key, _ = item
            _, year, identity = key
            id_key = (0, identity) if isinstance(identity, int) else (1, str(identity))
            return (year, id_key)

        for (rtype, year, identity), files in sorted(groups.items(), key=_sort_key):
            # Dedup by the (hash-prefixed, unique) basename rather than the full path:
            # stored paths are absolute to the ingesting machine, so a Windows path in a
            # DB dump never equals the container's /app/documents/... path and would
            # otherwise re-ingest every file as a duplicate on each scan.
            candidate_names = [p.name for p in files.values()]
            already = db.scalars(
                select(MeetingFile).where(MeetingFile.file_name.in_(candidate_names))
            ).all()
            if already:
                continue

            title = build_meeting_title(
                rtype,
                identity=identity,
                year=year,
                fallback=next(iter(files.values())).stem,
            )
            meeting = Meeting(
                document_type=rtype,
                year=year,
                meeting_title=title,
            )
            db.add(meeting)
            db.flush()

            for role, pdf_path in files.items():
                await ingest_meeting_file(
                    db,
                    meeting=meeting,
                    file_role=role,
                    file_path=pdf_path,
                    generate_description=True,
                    preserve_meeting_title=rtype == DOCUMENT_TYPE_ECE_FACULTY_MEET,
                )
                ingested += 1
    return {"ingested": ingested}


async def seed_documents_from_disk(db: Session, documents_root: Path) -> dict[str, int]:
    return await sync_new_documents_from_disk(db, documents_root)
