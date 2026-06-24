from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.documents.models.entities import DocumentChunk, DocumentQueryLog, Meeting, MeetingFile
from app.llm.services.groq_service import LlmError, generate_llm_text_with_system

_MIN_RELEVANCE_SCORE = 2
_TOP_K = 6


@dataclass
class RetrievedChunk:
    meeting_file_id: int
    document_title: str
    file_role: str
    year: int
    page_number: int | None
    section_label: str | None
    chunk_text: str
    score: float


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", text) if len(t) > 2}


def _score_chunk(question_tokens: set[str], chunk_text: str) -> float:
    chunk_tokens = _tokenize(chunk_text)
    if not question_tokens or not chunk_tokens:
        return 0.0
    overlap = len(question_tokens & chunk_tokens)
    return overlap


def retrieve_chunks(db: Session, *, document_type: str, question: str, top_k: int = _TOP_K) -> list[RetrievedChunk]:
    question_tokens = _tokenize(question)
    rows = db.scalars(
        select(DocumentChunk)
        .join(MeetingFile)
        .join(Meeting)
        .where(Meeting.document_type == document_type)
        .options(joinedload(DocumentChunk.meeting_file).joinedload(MeetingFile.meeting))
    ).unique().all()

    scored: list[RetrievedChunk] = []
    for row in rows:
        score = _score_chunk(question_tokens, row.chunk_text)
        if score <= 0:
            continue
        mf = row.meeting_file
        meeting = mf.meeting
        scored.append(
            RetrievedChunk(
                meeting_file_id=mf.id,
                document_title=meeting.meeting_title,
                file_role=mf.file_role,
                year=meeting.year,
                page_number=row.page_number,
                section_label=row.section_label,
                chunk_text=row.chunk_text,
                score=score,
            )
        )
    scored.sort(key=lambda item: (-item.score, -item.year, item.meeting_file_id))
    return scored[:top_k]


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        location = f"page {chunk.page_number}" if chunk.page_number else "unknown page"
        if chunk.section_label:
            location += f", section {chunk.section_label}"
        role_label = "Agenda" if chunk.file_role == "agenda" else "Minutes"
        parts.append(
            f"[Source {index}] Meeting: {chunk.document_title} ({chunk.year}), {role_label}, {location}\n{chunk.chunk_text}"
        )
    return "\n\n".join(parts)


async def answer_document_question(
    db: Session,
    *,
    document_type: str,
    question: str,
    user_id: int | None,
) -> dict:
    chunks = retrieve_chunks(db, document_type=document_type, question=question)
    max_score = max((c.score for c in chunks), default=0)
    if max_score < _MIN_RELEVANCE_SCORE:
        log = DocumentQueryLog(
            document_type=document_type,
            question=question,
            document_ids=json.dumps([]),
            user_id=user_id,
        )
        db.add(log)
        db.commit()
        return {
            "answer": "I couldn't find this in the available minutes.",
            "sources": [],
            "context_chunks": [],
            "not_found": True,
        }

    context = _format_context(chunks)
    prompt = (
        f"Answer the question using ONLY the provided meeting minutes excerpts.\n"
        f"If the excerpts do not contain enough information, reply exactly: "
        f"\"I couldn't find this in the available minutes.\"\n"
        f"Cite document title, year, and page/section when possible.\n\n"
        f"Question: {question}\n\nContext:\n{context}"
    )
    system = (
        "You are a helpful assistant for faculty reading official meeting minutes. "
        "Never use outside knowledge. Always cite sources from the context."
    )
    try:
        answer = await generate_llm_text_with_system(prompt, system_prompt=system, temperature=0.2, max_tokens=1200)
    except LlmError as exc:
        raise exc

    if "couldn't find this in the available minutes" in answer.lower():
        not_found = True
    else:
        not_found = False

    source_map: dict[int, dict] = {}
    for chunk in chunks:
        if chunk.meeting_file_id not in source_map:
            source_map[chunk.meeting_file_id] = {
                "document_id": chunk.meeting_file_id,
                "title": chunk.document_title,
                "file_role": chunk.file_role,
                "year": chunk.year,
                "pages": set(),
            }
        if chunk.page_number:
            source_map[chunk.meeting_file_id]["pages"].add(chunk.page_number)

    sources = [
        {
            "document_id": item["document_id"],
            "title": item["title"],
            "year": item["year"],
            "pages": sorted(item["pages"]),
        }
        for item in source_map.values()
    ]

    log = DocumentQueryLog(
        document_type=document_type,
        question=question,
        document_ids=json.dumps([s["document_id"] for s in sources]),
        user_id=user_id,
    )
    db.add(log)
    db.commit()

    return {
        "answer": answer,
        "sources": sources,
        "context_chunks": [
            {
                "document_id": c.meeting_file_id,
                "title": c.document_title,
                "file_role": c.file_role,
                "year": c.year,
                "page_number": c.page_number,
                "section_label": c.section_label,
                "text": c.chunk_text,
            }
            for c in chunks
        ],
        "not_found": not_found,
    }
