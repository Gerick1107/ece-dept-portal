from __future__ import annotations

import json
import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.documents.models.entities import (
    DOCUMENT_TYPE_AAC,
    DOCUMENT_TYPE_ALL,
    DOCUMENT_TYPE_ECE_FACULTY_MEET,
    DOCUMENT_TYPE_PGC,
    DOCUMENT_TYPE_SENATE,
    DOCUMENT_TYPE_UGC,
    DocumentChunk,
    DocumentQueryLog,
    Meeting,
    MeetingFile,
)
from app.documents.services.embedding_service import (
    cosine_similarity,
    embed_text,
    embedding_from_json,
)
from app.documents.services.meeting_matcher import parse_meeting_number
from app.llm.services.groq_service import LlmError
from app.llm.services.llm_dispatch import generate_text

_MIN_RELEVANCE_SCORE = 0.32
_TOP_K = 12
_USE_EMBEDDINGS = True
_NOT_FOUND_REPLY = "I couldn't find this in the available minutes."

# "meeting 22", "meeting no. 22", "meeting #22"
_MEETING_NUM_RE = re.compile(r"\bmeeting\s*(?:no\.?|number|num|#)?\s*[:\-]?\s*(\d{1,3})\b", re.IGNORECASE)
# "22nd", "41th" (typo), "36 th" (stray space) — used for "the 22nd Senate meeting"
_ORDINAL_RE = re.compile(r"\b(\d{1,3})\s*(?:st|nd|rd|th)\b", re.IGNORECASE)

# Series keywords → document type, so "22nd Senate Meeting" never matches a
# different series that happens to share the number.
_SERIES_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        DOCUMENT_TYPE_ECE_FACULTY_MEET,
        re.compile(r"(ece\s*fm|ece\s+faculty|faculty\s+meet(?:ing)?s?|\bfm\b)", re.IGNORECASE),
    ),
    (DOCUMENT_TYPE_SENATE, re.compile(r"\bsenate\b", re.IGNORECASE)),
    (DOCUMENT_TYPE_AAC, re.compile(r"\baac\b", re.IGNORECASE)),
    (DOCUMENT_TYPE_PGC, re.compile(r"\bpgc\b", re.IGNORECASE)),
    (DOCUMENT_TYPE_UGC, re.compile(r"\bugc\b", re.IGNORECASE)),
]

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_DAY_MONTH_YEAR_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})\b", re.IGNORECASE
)
_MONTH_DAY_YEAR_RE = re.compile(
    r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", re.IGNORECASE
)
_MONTH_YEAR_RE = re.compile(r"\b([A-Za-z]+)\s+(\d{4})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
# Vague follow-up pronouns ("did they finalize it?")
_FOLLOWUP_PRONOUN_RE = re.compile(r"\b(it|its|they|them|their|that|those|these|this|he|she)\b", re.IGNORECASE)
_FOLLOWUP_PREFIX_RE = re.compile(r"^(and|also|then|did|was|were|is|are|what about|how about|who|when|why|how)\b", re.IGNORECASE)


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


def retrieve_chunks(
    db: Session,
    *,
    document_type: str,
    question: str,
    top_k: int = _TOP_K,
    meeting_file_ids: set[int] | None = None,
) -> list[RetrievedChunk]:
    question_tokens = _tokenize(question)
    stmt = (
        select(DocumentChunk)
        .join(MeetingFile)
        .join(Meeting)
        .options(joinedload(DocumentChunk.meeting_file).joinedload(MeetingFile.meeting))
    )
    if document_type != DOCUMENT_TYPE_ALL:
        stmt = stmt.where(Meeting.document_type == document_type)
    if meeting_file_ids is not None:
        if not meeting_file_ids:
            return []
        stmt = stmt.where(MeetingFile.id.in_(meeting_file_ids))
    rows = db.scalars(stmt).unique().all()

    query_vec: np.ndarray | None = None
    if _USE_EMBEDDINGS:
        try:
            query_vec = np.asarray(embed_text(question), dtype=np.float32)
        except Exception:
            query_vec = None

    scored: list[RetrievedChunk] = []
    for row in rows:
        score = 0.0
        if query_vec is not None:
            chunk_vec = embedding_from_json(row.embedding_json)
            if chunk_vec is not None:
                score = cosine_similarity(query_vec, chunk_vec)
        if score <= 0:
            score = _score_chunk(question_tokens, row.chunk_text) / max(len(question_tokens), 1)
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


# --- Conversation history helpers (Part 3) -------------------------------------------------


def _format_history(history: list[dict] | None, limit: int = 6) -> str:
    if not history:
        return ""
    recent = [h for h in history if h.get("content")][-limit:]
    lines = []
    for turn in recent:
        role = "User" if str(turn.get("role")) == "user" else "Assistant"
        lines.append(f"{role}: {str(turn.get('content')).strip()}")
    return "\n".join(lines)


def _looks_like_followup(question: str) -> bool:
    q = question.strip()
    if not q:
        return False
    if len(q.split()) <= 8:
        return True
    if _FOLLOWUP_PRONOUN_RE.search(q):
        return True
    if _FOLLOWUP_PREFIX_RE.match(q):
        return True
    return False


# --- Meeting-number routing (Part 2) -------------------------------------------------------


def detect_meeting_number(text: str) -> int | None:
    """Detect a specific meeting number from question text (e.g. 'meeting 22', 'the 22nd meeting')."""
    match = _MEETING_NUM_RE.search(text)
    if match:
        return int(match.group(1))
    match = _ORDINAL_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def detect_series(text: str) -> str | None:
    """Detect the meeting series implied by the question (Senate / AAC / PGC / UGC / ECE Faculty)."""
    for dtype, pattern in _SERIES_PATTERNS:
        if pattern.search(text):
            return dtype
    return None


def detect_date_hint(text: str) -> dict | None:
    """Detect a date/month/year reference (used for date-based ECE Faculty lookups)."""
    m = _ISO_DATE_RE.search(text)
    if m:
        return {"year": int(m.group(1)), "month": int(m.group(2)), "day": int(m.group(3))}
    m = _DAY_MONTH_YEAR_RE.search(text)
    if m and m.group(2).lower() in _MONTHS:
        return {"year": int(m.group(3)), "month": _MONTHS[m.group(2).lower()], "day": int(m.group(1))}
    m = _MONTH_DAY_YEAR_RE.search(text)
    if m and m.group(1).lower() in _MONTHS:
        return {"year": int(m.group(3)), "month": _MONTHS[m.group(1).lower()], "day": int(m.group(2))}
    m = _MONTH_YEAR_RE.search(text)
    if m and m.group(1).lower() in _MONTHS:
        return {"year": int(m.group(2)), "month": _MONTHS[m.group(1).lower()], "day": None}
    m = _YEAR_RE.search(text)
    if m:
        return {"year": int(m.group(1)), "month": None, "day": None}
    return None


def _effective_types(document_type: str, series: str | None) -> list[str] | None:
    """Resolve which document types a meeting lookup may search.

    The currently selected set is authoritative; within "All Meetings" the
    series named in the question (if any) constrains the search. Returns
    ``None`` to mean "any type" (only possible in All Meetings with no series).
    """
    if document_type != DOCUMENT_TYPE_ALL:
        return [document_type]
    if series:
        return [series]
    return None


def _meetings_for_types(db: Session, types: list[str] | None) -> list[Meeting]:
    stmt = select(Meeting).options(joinedload(Meeting.files))
    if types is not None:
        stmt = stmt.where(Meeting.document_type.in_(types))
    return list(db.scalars(stmt).unique().all())


def find_meetings_by_number(db: Session, *, types: list[str] | None, number: int) -> list[Meeting]:
    """Find meetings whose title encodes the given number, within the allowed types."""
    return [m for m in _meetings_for_types(db, types) if parse_meeting_number(m.meeting_title) == number]


def _meeting_date_parts(meeting: Meeting) -> tuple[int | None, int | None, int | None]:
    """Best-available (year, month, day) for a meeting.

    ECE Faculty meetings encode the date in the title ("ECE FM - 08 May 2026"),
    so fall back to parsing the title when the meeting_date column is empty.
    """
    for source in (meeting.meeting_date, meeting.meeting_title):
        if not source:
            continue
        hint = detect_date_hint(source)
        if hint and hint.get("year"):
            return hint["year"], hint.get("month"), hint.get("day")
    return meeting.year, None, None


def find_meetings_by_date(db: Session, *, types: list[str] | None, hint: dict) -> list[Meeting]:
    """Find meetings matching a date hint, preferring the most specific match available."""
    candidates = _meetings_for_types(db, types)
    target_year = hint.get("year")
    target_month = hint.get("month")
    target_day = hint.get("day")

    scored: list[tuple[int, Meeting]] = []
    for meeting in candidates:
        m_year, m_month, m_day = _meeting_date_parts(meeting)
        if target_year is not None and m_year != target_year:
            continue
        specificity = 1  # year matched
        if target_month is not None:
            if m_month is None or m_month != target_month:
                continue
            specificity = 2
        if target_day is not None:
            if m_day is None or m_day != target_day:
                continue
            specificity = 3
        scored.append((specificity, meeting))
    if not scored:
        return []
    best = max(s for s, _ in scored)
    return [m for s, m in scored if s == best]


def _meeting_description_context(meetings: list[Meeting]) -> tuple[str, list[dict]]:
    """Build primary context from each meeting's stored AI-generated Agenda/Minutes summaries."""
    parts: list[str] = []
    pseudo_chunks: list[dict] = []
    for meeting in meetings:
        files = {f.file_role: f for f in meeting.files}
        agenda = files.get("agenda")
        minutes = files.get("minutes")
        block = [f"Meeting: {meeting.meeting_title} ({meeting.year})"]
        if agenda and agenda.description:
            block.append(f"Agenda summary: {agenda.description}")
            pseudo_chunks.append(
                {
                    "document_id": agenda.id,
                    "title": meeting.meeting_title,
                    "file_role": "agenda",
                    "year": meeting.year,
                    "page_number": None,
                    "section_label": "AI summary",
                    "text": agenda.description,
                }
            )
        if minutes and minutes.description:
            block.append(f"Minutes summary: {minutes.description}")
            pseudo_chunks.append(
                {
                    "document_id": minutes.id,
                    "title": meeting.meeting_title,
                    "file_role": "minutes",
                    "year": meeting.year,
                    "page_number": None,
                    "section_label": "AI summary",
                    "text": minutes.description,
                }
            )
        if len(block) > 1:
            parts.append("\n".join(block))
    return "\n\n".join(parts), pseudo_chunks


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


_FORMATTING_GUIDANCE = (
    "Write in clear, plain prose suitable for a chat reply. Keep light structure only: short "
    "paragraphs, and a simple bullet list (using '- ') when listing several items. Do not use "
    "markdown tables, headings, or bold/asterisk emphasis."
)

_RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant for faculty reading official institute meeting minutes. "
    "Answer using only the provided context excerpts and the conversation so far. "
    "The user's question may use different wording than the source documents — match based on "
    "meaning, not exact phrasing (for example, 'TA allotment eligibility' and 'TAship criteria' "
    "refer to the same thing, and 'finalised' and 'approved' may describe the same decision). "
    "Only say you cannot find the answer if the provided context genuinely does not address the "
    "question — not merely because the wording differs. Do not use outside knowledge and do not "
    "invent details that are not supported by the context. When you answer, cite the meeting "
    "title, year, and page/section the information came from. " + _FORMATTING_GUIDANCE
)

_MEETING_SYSTEM_PROMPT = (
    "You are a helpful assistant for faculty reading official institute meeting minutes. "
    "The user is asking about one specific meeting. The meeting's official AI-generated summary "
    "is the primary source; supporting excerpts may add detail. Match the question to the content "
    "by meaning, not exact wording. Do not use outside knowledge and do not invent details beyond "
    "the provided summary and excerpts. Cite the meeting title and year. " + _FORMATTING_GUIDANCE
)


async def _generate_and_pack(
    db: Session,
    *,
    document_type: str,
    question: str,
    user_id: int | None,
    provider: str,
    system: str,
    prompt: str,
    chunks: list[RetrievedChunk],
    extra_context_chunks: list[dict] | None = None,
    extra_sources: list[dict] | None = None,
) -> dict:
    answer = await generate_text(prompt, provider=provider, system_prompt=system, temperature=0.2, max_tokens=1200)
    not_found = "couldn't find this in the available minutes" in answer.lower()

    source_map: dict[int, dict] = {}
    for source in extra_sources or []:
        source_map[source["document_id"]] = {**source, "pages": set(source.get("pages") or [])}
    for chunk in chunks:
        entry = source_map.setdefault(
            chunk.meeting_file_id,
            {
                "document_id": chunk.meeting_file_id,
                "title": chunk.document_title,
                "year": chunk.year,
                "pages": set(),
            },
        )
        if chunk.page_number:
            entry["pages"].add(chunk.page_number)

    sources = [
        {"document_id": item["document_id"], "title": item["title"], "year": item["year"], "pages": sorted(item["pages"])}
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

    context_chunks = list(extra_context_chunks or [])
    context_chunks.extend(
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
    )

    return {"answer": answer, "sources": sources, "context_chunks": context_chunks, "not_found": not_found}


def _resolve_target_meetings(db: Session, document_type: str, question: str) -> tuple[list[Meeting], bool, str]:
    """Resolve which specific meeting(s) a question targets.

    Returns ``(meetings, requested, label)`` where ``requested`` is True when the
    question explicitly references a specific meeting (by number, or by date for
    the ECE Faculty series). Scoping is airtight: matches stay within the selected
    set and the series implied by the question.
    """
    series = detect_series(question)
    types = _effective_types(document_type, series)

    number = detect_meeting_number(question)
    if number is not None:
        return find_meetings_by_number(db, types=types, number=number), True, f"the {_ordinal(number)} meeting"

    # Date-based lookup applies to the date-identified ECE Faculty series only.
    date_series_active = document_type == DOCUMENT_TYPE_ECE_FACULTY_MEET or series == DOCUMENT_TYPE_ECE_FACULTY_MEET
    if date_series_active:
        hint = detect_date_hint(question)
        if hint:
            date_types = [DOCUMENT_TYPE_ECE_FACULTY_MEET] if types is None else types
            return find_meetings_by_date(db, types=date_types, hint=hint), True, "that meeting"

    return [], False, ""


async def answer_document_question(
    db: Session,
    *,
    document_type: str,
    question: str,
    user_id: int | None,
    provider: str = "groq",
    history: list[dict] | None = None,
) -> dict:
    history = history or []
    history_text = _format_history(history)

    # --- Part 2/3: route specific-meeting questions to the stored AI descriptions ---
    meetings, requested, label = _resolve_target_meetings(db, document_type, question)
    if not requested and _looks_like_followup(question):
        # Vague follow-up → inherit the most recent meeting referenced earlier.
        for turn in reversed(history):
            if str(turn.get("role")) != "user" or not turn.get("content"):
                continue
            prev_meetings, prev_requested, prev_label = _resolve_target_meetings(
                db, document_type, str(turn.get("content"))
            )
            if prev_requested and prev_meetings:
                meetings, requested, label = prev_meetings, True, prev_label
                break

    if requested:
        if not meetings:
            log = DocumentQueryLog(
                document_type=document_type,
                question=question,
                document_ids=json.dumps([]),
                user_id=user_id,
            )
            db.add(log)
            db.commit()
            return {
                "answer": (
                    f"I couldn't find {label} in this document set. "
                    "It may not be uploaded, or it might belong to a different set."
                ),
                "sources": [],
                "context_chunks": [],
                "not_found": True,
            }

        desc_context, pseudo_chunks = _meeting_description_context(meetings)
        file_ids = {f.id for m in meetings for f in m.files}
        support_chunks = retrieve_chunks(
            db, document_type=document_type, question=question, top_k=6, meeting_file_ids=file_ids
        )
        support_context = _format_context(support_chunks)

        prompt_parts = []
        if history_text:
            prompt_parts.append(f"Conversation so far:\n{history_text}\n")
        prompt_parts.append(f"Question: {question}\n")
        if desc_context:
            prompt_parts.append(f"Meeting summary (primary source):\n{desc_context}\n")
        if support_context:
            prompt_parts.append(f"Supporting excerpts:\n{support_context}\n")
        prompt_parts.append(
            "Answer using the meeting summary above as the primary source, drawing on the supporting "
            "excerpts for extra detail. If neither addresses the question, say so clearly."
        )
        prompt = "\n".join(prompt_parts)

        return await _generate_and_pack(
            db,
            document_type=document_type,
            question=question,
            user_id=user_id,
            provider=provider,
            system=_MEETING_SYSTEM_PROMPT,
            prompt=prompt,
            chunks=support_chunks,
            extra_context_chunks=pseudo_chunks,
            extra_sources=[
                {"document_id": f.id, "title": m.meeting_title, "year": m.year}
                for m in meetings
                for f in m.files
            ],
        )

    # --- Normal chunk-retrieval path (general topic/fact questions) ---
    # For vague follow-ups, widen the retrieval query with the prior user turn so
    # borderline-but-relevant chunks aren't filtered out before reaching the LLM.
    retrieval_query = question
    if _looks_like_followup(question) and history:
        prior_user = next(
            (str(h.get("content")) for h in reversed(history) if str(h.get("role")) == "user" and h.get("content")),
            "",
        )
        if prior_user:
            retrieval_query = f"{prior_user}\n{question}"

    chunks = retrieve_chunks(db, document_type=document_type, question=retrieval_query)
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
            "answer": _NOT_FOUND_REPLY,
            "sources": [],
            "context_chunks": [],
            "not_found": True,
        }

    context = _format_context(chunks)
    prompt_parts = []
    if history_text:
        prompt_parts.append(f"Conversation so far:\n{history_text}\n")
    prompt_parts.append(f"Question: {question}\n")
    prompt_parts.append(f"Context excerpts:\n{context}\n")
    prompt_parts.append(
        f'If the context genuinely does not address the question, reply exactly: "{_NOT_FOUND_REPLY}"'
    )
    prompt = "\n".join(prompt_parts)

    return await _generate_and_pack(
        db,
        document_type=document_type,
        question=question,
        user_id=user_id,
        provider=provider,
        system=_RAG_SYSTEM_PROMPT,
        prompt=prompt,
        chunks=chunks,
    )
