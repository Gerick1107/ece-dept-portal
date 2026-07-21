"""Analyze uploaded question papers with the local LLM and build component marks templates."""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass

from app.copo.services.marks_template_builder import build_analyzed_component_workbook

_MAX_TEXT_CHARS = 12000
_CO_RE = re.compile(r"^CO\s*\d+$", re.IGNORECASE)


@dataclass
class AnalyzedQuestion:
    label: str
    co_labels: list[str]
    max_marks: float
    is_bonus: bool = False

    @property
    def co_label(self) -> str:
        return _format_co_cell(self.co_labels)


def extract_document_text(filename: str, content: bytes) -> str:
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        parts = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(parts).strip()
    if lower.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(content))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
        return "\n".join(parts).strip()
    if lower.endswith(".txt"):
        return content.decode("utf-8", errors="replace").strip()
    raise ValueError("Unsupported file type. Upload PDF, DOCX, or TXT.")


def _parse_llm_json(text: str) -> dict:
    cleaned = text.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if match:
            cleaned = match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _normalize_co(value: str) -> str:
    value = (value or "").strip().upper().replace(" ", "")
    if not value:
        return ""
    if value.startswith("CO") and value[2:].isdigit():
        return f"CO{int(value[2:])}"
    return value if _CO_RE.match(value) else ""


def _normalize_co_list(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        labels: list[str] = []
        for item in raw:
            co = _normalize_co(str(item))
            if co and co not in labels:
                labels.append(co)
        return labels
    text = str(raw).strip()
    if not text:
        return []
    labels = []
    for part in text.split(","):
        co = _normalize_co(part)
        if co and co not in labels:
            labels.append(co)
    return labels


def _format_co_cell(labels: list[str]) -> str:
    return ", ".join(labels)


async def _generate_analysis_text(prompt: str) -> str:
    from app.llm.services.llm_dispatch import generate_text

    return await generate_text(prompt, provider="local", temperature=0.0, max_tokens=1200)


def _validated_co_labels(item: dict, source_text: str) -> list[str]:
    """Only accept CO labels backed by an exact quote from the uploaded paper."""
    labels = _normalize_co_list(item.get("co_labels"))
    if not labels:
        labels = _normalize_co_list(item.get("co_label"))
    evidence = str(item.get("co_evidence") or "").strip()
    if not labels or not evidence:
        return []

    normalized_source = " ".join(source_text.split()).casefold()
    normalized_evidence = " ".join(evidence.split()).casefold()
    if normalized_evidence not in normalized_source:
        return []

    evidence_labels = _normalize_co_list(
        re.findall(r"\bCO\s*\d+\b", evidence, flags=re.IGNORECASE)
    )
    return [label for label in labels if label in evidence_labels]


def scale_questions(
    questions: list[AnalyzedQuestion],
    *,
    paper_total_marks: float,
    weightage: float,
) -> list[AnalyzedQuestion]:
    if paper_total_marks <= 0 or weightage <= 0:
        return questions
    factor = weightage / paper_total_marks
    scaled: list[AnalyzedQuestion] = []
    for q in questions:
        scaled.append(
            AnalyzedQuestion(
                q.label,
                q.co_labels,
                round(q.max_marks * factor, 2),
                is_bonus=q.is_bonus,
            )
        )
    return scaled


async def analyze_question_paper_text(text: str) -> dict:
    snippet = text[:_MAX_TEXT_CHARS]
    prompt = f"""Analyze this exam question paper and return ONLY valid JSON (no markdown) with this schema:
{{
  "component_name": "Quiz|MidSem|EndSem|Assignment|Lab|etc",
  "paper_total_marks": number,
  "questions": [
    {{
      "label": "Q1 or Q1a",
      "co_labels": ["CO1", "CO2"],
      "co_evidence": "exact quote from the paper containing the CO label(s), or empty string",
      "max_marks": number,
      "is_bonus": false,
      "parts": []
    }}
  ]
}}

Rules:
- Treat sub-parts (a,b,c,d or i,ii,iii or 1,2,3 under one main question) as separate questions with labels like Q1a, Q1b.
- Map a question/part only to CO labels explicitly printed next to or attached to that question in the paper.
- Never infer, guess, or invent a CO from the question topic, course content, or another question.
- If no CO is explicitly attached, return co_labels=[] and co_evidence="".
- For every non-empty co_labels array, co_evidence must be an exact quote from the paper that contains those CO labels.
- If only one CO applies, still use a one-element co_labels array.
- Mark bonus questions with is_bonus=true.
- paper_total_marks excludes bonus marks and is the total for this component before scaling.

Question paper text:
{snippet}
"""
    raw = await _generate_analysis_text(prompt)
    data = _parse_llm_json(raw)
    questions: list[AnalyzedQuestion] = []
    for item in data.get("questions") or []:
        label = str(item.get("label") or "").strip() or f"Q{len(questions) + 1}"
        cos = _validated_co_labels(item, snippet)
        try:
            marks = float(item.get("max_marks") or 0)
        except (TypeError, ValueError):
            marks = 0.0
        is_bonus = bool(item.get("is_bonus"))
        questions.append(AnalyzedQuestion(label, cos, marks, is_bonus=is_bonus))
        for part in item.get("parts") or []:
            plabel = str(part.get("label") or "").strip()
            if not plabel:
                continue
            pcos = _validated_co_labels(part, snippet)
            try:
                pmarks = float(part.get("max_marks") or 0)
            except (TypeError, ValueError):
                pmarks = 0.0
            questions.append(
                AnalyzedQuestion(plabel, pcos, pmarks, is_bonus=bool(part.get("is_bonus")))
            )
    try:
        paper_total = float(data.get("paper_total_marks") or 0)
    except (TypeError, ValueError):
        paper_total = sum(q.max_marks for q in questions if not q.is_bonus)
    missing_co_labels = [q.label for q in questions if not q.is_bonus and not q.co_labels]
    warnings = []
    if missing_co_labels:
        warnings.append(
            "No COs found for: "
            + ", ".join(missing_co_labels)
            + ". Manually edit/add CO mappings before downloading."
        )
    return {
        "component_name": str(data.get("component_name") or "Component").strip() or "Component",
        "paper_total_marks": paper_total,
        "warnings": warnings,
        "questions": [
            {
                "label": q.label,
                "co_labels": q.co_labels,
                "co_label": q.co_label,
                "max_marks": q.max_marks,
                "is_bonus": q.is_bonus,
            }
            for q in questions
        ],
    }


async def analyze_question_paper_file(filename: str, content: bytes) -> dict:
    text = extract_document_text(filename, content)
    if not text.strip():
        raise ValueError("Could not extract text from the uploaded file.")
    return await analyze_question_paper_text(text)


def generate_component_workbook(
    *,
    component_name: str,
    questions: list[dict],
    paper_total_marks: float,
    weightage: float,
) -> bytes:
    parsed = [
        AnalyzedQuestion(
            str(q.get("label") or ""),
            _normalize_co_list(q.get("co_labels")) or _normalize_co_list(q.get("co_label")),
            float(q.get("max_marks") or 0),
            is_bonus=bool(q.get("is_bonus")),
        )
        for q in questions
        if str(q.get("label") or "").strip()
    ]
    scaled = scale_questions(parsed, paper_total_marks=paper_total_marks, weightage=weightage)
    from app.copo.services.marks_template_builder import AnalyzedQuestionSpec

    specs = [
        AnalyzedQuestionSpec(q.label, q.co_label, q.max_marks, is_bonus=q.is_bonus) for q in scaled
    ]
    return build_analyzed_component_workbook(
        component_name=component_name,
        questions=specs,
    )
