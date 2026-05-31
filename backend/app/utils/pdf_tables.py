from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _plain_para(text: str, style_name: str = "Normal") -> Paragraph:
    styles = getSampleStyleSheet()
    safe = escape(str(text or "")).replace("\n", "<br/>")
    return Paragraph(safe, styles[style_name])


def _labeled_field(label: str, value: str) -> Paragraph:
    """Bold label + escaped value (ReportLab mini-HTML)."""
    styles = getSampleStyleSheet()
    safe_label = escape(label.replace("_", " "))
    safe_value = escape(str(value or "")).replace("\n", "<br/>") or "—"
    return Paragraph(f"<b>{safe_label}:</b> {safe_value}", styles["Normal"])


def records_to_list_pdf_bytes(
    title: str,
    records: list[dict[str, str]],
    *,
    entry_title_key: str | None = None,
) -> bytes:
    """Render each record as a labeled block (no table cells) so long text never overlaps."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = [_plain_para(title, "Heading2"), Spacer(1, 14)]
    for i, record in enumerate(records, start=1):
        if entry_title_key and record.get(entry_title_key):
            story.append(_plain_para(f"{i}. {record[entry_title_key]}", "Heading4"))
        else:
            story.append(_plain_para(f"Entry {i}", "Heading4"))
        for label, value in record.items():
            if entry_title_key and label == entry_title_key:
                continue
            story.append(_labeled_field(label, value))
        story.append(Spacer(1, 12))
    doc.build(story)
    return buffer.getvalue()


def dataframe_to_pdf_bytes(headers: list[str], rows: list[list[str]], title: str) -> bytes:
    records: list[dict[str, str]] = []
    for row in rows:
        records.append({headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))})
    return records_to_list_pdf_bytes(title, records)
